"""
panesplit.py — split-pane tab container for TimbreTalk

Drag a tab off its bar → shows drop zones on every pane.
  • Drop on centre → move tab to that pane
  • Drop on an edge → split that pane (left/right/top/bottom)
  • Drop outside all panes → new pane appended to root splitter

Right-click a tab → Split Right / Split Down / Rename / Close.
"""
from PyQt5 import QtCore, QtGui, QtWidgets

EDGE_PX   = 48    # pixels from edge that counts as a split zone
DRAG_DIST = 20    # manhattan distance before drag-out activates


# ---------------------------------------------------------------------------
# Global drag state  (one tab in flight at a time)
# ---------------------------------------------------------------------------
class _DS:
    active  = False
    widget  = None   # PortTab being dragged
    label   = ''
    source  = None   # PaneTabWidget it came from


# ---------------------------------------------------------------------------
# Drop-zone overlay
# ---------------------------------------------------------------------------
class _Overlay(QtWidgets.QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self._zone = None
        self.hide()

    def setZone(self, z):
        if z != self._zone:
            self._zone = z
            self.update()

    def zoneAt(self, p):
        r = self.rect()
        # Cursor over the tab bar → always merge (not split)
        par = self.parent()
        if isinstance(par, QtWidgets.QTabWidget):
            if p.y() <= par.tabBar().height():
                return 'center'
        if p.x() < EDGE_PX:              return 'left'
        if p.x() > r.width() - EDGE_PX:  return 'right'
        if p.y() < EDGE_PX:              return 'top'
        if p.y() > r.height() - EDGE_PX: return 'bottom'
        return 'center'

    def paintEvent(self, _):
        if not self._zone:
            return
        r = self.rect()
        w, h = r.width(), r.height()
        if   self._zone == 'left':   zr = QtCore.QRect(0,    0,    w//2, h)
        elif self._zone == 'right':  zr = QtCore.QRect(w//2, 0,    w//2, h)
        elif self._zone == 'top':    zr = QtCore.QRect(0,    0,    w,    h//2)
        elif self._zone == 'bottom': zr = QtCore.QRect(0,    h//2, w,    h//2)
        else:                        zr = r.adjusted(8, 8, -8, -8)
        p = QtGui.QPainter(self)
        p.fillRect(zr, QtGui.QColor(0, 130, 210, 65))
        p.setPen(QtGui.QPen(QtGui.QColor(0, 130, 210, 190), 2))
        p.drawRect(zr.adjusted(1, 1, -1, -1))


# ---------------------------------------------------------------------------
# Tab bar that detects drag-out
# ---------------------------------------------------------------------------
class _DetachBar(QtWidgets.QTabBar):
    tabDraggedOut = QtCore.pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._dstart = None
        self._didx   = -1

    def mousePressEvent(self, e):
        if e.button() == QtCore.Qt.LeftButton:
            self._dstart = e.globalPos()
            self._didx   = self.tabAt(e.pos())
        super().mousePressEvent(e)

    def mouseMoveEvent(self, e):
        super().mouseMoveEvent(e)
        if not (e.buttons() & QtCore.Qt.LeftButton) or self._didx < 0:
            return
        if (e.globalPos() - self._dstart).manhattanLength() < DRAG_DIST:
            return
        local = self.mapFromGlobal(e.globalPos())
        if not self.rect().adjusted(-12, -8, 12, 8).contains(local):
            idx = self._didx
            self._didx = -1
            self.tabDraggedOut.emit(idx)

    def mouseReleaseEvent(self, e):
        self._didx = -1
        super().mouseReleaseEvent(e)


# ---------------------------------------------------------------------------
# Single pane  (one QTabWidget with drag-out + context menu)
# ---------------------------------------------------------------------------
class PaneTabWidget(QtWidgets.QTabWidget):
    # (widget, label) detached — caller must place widget somewhere
    tabDetached    = QtCore.pyqtSignal(object, str)
    # user chose split from context menu
    splitRequested = QtCore.pyqtSignal(str, object, str)
    # user clicked close button
    tabCloseRequest = QtCore.pyqtSignal(object, int)   # (pane, local_idx)
    # user clicked "+" in this pane
    addRequested   = QtCore.pyqtSignal(object)          # (pane)

    def __init__(self, parent=None):
        super().__init__(parent)
        bar = _DetachBar(self)
        self.setTabBar(bar)
        bar.tabDraggedOut.connect(self._detach)
        self.setTabsClosable(True)
        self.setMovable(True)
        self.tabCloseRequested.connect(
            lambda i: self.tabCloseRequest.emit(self, i))
        bar.tabBarDoubleClicked.connect(self._rename)
        bar.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        bar.customContextMenuRequested.connect(self._ctx)

        # "+" corner button
        btn = QtWidgets.QToolButton()
        btn.setText("+")
        btn.setToolTip("New port tab")
        btn.clicked.connect(lambda: self.addRequested.emit(self))
        self.setCornerWidget(btn, QtCore.Qt.TopRightCorner)

        self._overlay = _Overlay(self)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._overlay.resize(self.size())

    # --- drag-out ---
    def _detach(self, idx):
        w, lbl = self.widget(idx), self.tabText(idx)
        self.removeTab(idx)
        # Sever the parent link so that if the source pane is later deleted
        # (e.g. because it becomes empty) it won't take this widget with it.
        w.setParent(None)
        w.hide()
        _DS.active  = True
        _DS.widget  = w
        _DS.label   = lbl
        _DS.source  = self
        self.tabDetached.emit(w, lbl)

    # --- overlay helpers (called by PaneSplitter event filter) ---
    def showOverlay(self, local_pos):
        self._overlay.resize(self.size())
        self._overlay.show()
        self._overlay.raise_()
        self._overlay.setZone(self._overlay.zoneAt(local_pos))

    def hideOverlay(self):
        self._overlay.setZone(None)
        self._overlay.hide()

    def zoneAt(self, local_pos):
        return self._overlay.zoneAt(local_pos)

    # --- context menu ---
    def _ctx(self, pos):
        idx = self.tabBar().tabAt(pos)
        if idx < 0:
            return
        m = QtWidgets.QMenu(self)
        m.addAction("Rename…",     lambda: self._rename(idx))
        m.addSeparator()
        m.addAction("Split Right", lambda: self._splitOff(idx, 'right'))
        m.addAction("Split Down",  lambda: self._splitOff(idx, 'bottom'))
        m.addSeparator()
        m.addAction("Close Tab",   lambda: self.tabCloseRequest.emit(self, idx))
        m.exec_(self.tabBar().mapToGlobal(pos))

    def _splitOff(self, idx, direction):
        if self.count() <= 1:
            return
        w, lbl = self.widget(idx), self.tabText(idx)
        self.removeTab(idx)
        self.splitRequested.emit(direction, w, lbl)

    def _rename(self, idx):
        old  = self.tabText(idx)
        name, ok = QtWidgets.QInputDialog.getText(
            self, "Rename Tab", "Tab name:", text=old)
        if ok and name:
            self.setTabText(idx, name)


# ---------------------------------------------------------------------------
# Root split container
# ---------------------------------------------------------------------------
class PaneSplitter(QtWidgets.QWidget):
    """
    Public interface mirrors QTabWidget closely so terminalApp.py
    needs minimal changes:
      count()            total tabs across all panes
      currentWidget()    tab in the focused pane
      addTab(w,lbl)      add to the focused pane
      widget(i)          by global index
      tabText(i)
      setTabText(i,t)
      removeTab(i)       by global index
      allTabs()          [(widget, label), ...]

    Signals (replacing QTabWidget signals):
      tabCloseRequest(pane, local_idx)
      currentChanged(int)          — local index, from focused pane
      addTabRequested(pane)        — "+" clicked on a pane
    """
    tabCloseRequest  = QtCore.pyqtSignal(object, int)
    currentChanged   = QtCore.pyqtSignal(int)
    addTabRequested  = QtCore.pyqtSignal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self._splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal, self)
        layout.addWidget(self._splitter)
        self._panes = []
        # Start with one pane
        self._primary = self._newPane()
        self._primary.setFocus()

    # ------------------------------------------------------------------
    # Pane factory
    # ------------------------------------------------------------------
    def _newPane(self, add_to_splitter=True, splitter=None, insert_at=None):
        pane = PaneTabWidget(self)
        pane.tabDetached.connect(self._onDetached)
        pane.splitRequested.connect(self._onSplitReq)
        pane.tabCloseRequest.connect(self.tabCloseRequest)
        pane.currentChanged.connect(self.currentChanged)
        pane.addRequested.connect(self.addTabRequested)
        self._panes.append(pane)
        if add_to_splitter:
            sp = splitter or self._splitter
            if insert_at is not None:
                sp.insertWidget(insert_at, pane)
            else:
                sp.addWidget(pane)
        return pane

    def _removePane(self, pane):
        if len(self._panes) <= 1:
            return
        parent_splitter = pane.parent()   # capture before reparenting
        self._panes.remove(pane)
        if self._primary is pane:
            self._primary = self._panes[0]
        pane.hide()
        pane.setParent(None)
        pane.deleteLater()
        # Redistribute freed space — defer so Qt can assign real geometry first
        # (the parent may be a newly created sub-splitter with size still zero).
        if isinstance(parent_splitter, QtWidgets.QSplitter) and parent_splitter.count() > 0:
            QtCore.QTimer.singleShot(0, lambda s=parent_splitter: self._equalise(s))

    # ------------------------------------------------------------------
    # Drag-out handling (app-level event filter while _DS.active)
    # ------------------------------------------------------------------
    def _onDetached(self, widget, label):
        # Empty-source cleanup happens after the drop (in eventFilter) so we
        # don't race against widget reparenting.  Just start tracking the mouse.
        QtWidgets.QApplication.instance().installEventFilter(self)

    def eventFilter(self, obj, event):
        if not _DS.active:
            QtWidgets.QApplication.instance().removeEventFilter(self)
            return False

        tp = event.type()

        if tp == QtCore.QEvent.MouseMove:
            cursor = QtGui.QCursor.pos()
            for pane in self._panes:
                local = pane.mapFromGlobal(cursor)
                if pane.rect().contains(local):
                    pane.showOverlay(local)
                else:
                    pane.hideOverlay()
            return False

        if tp == QtCore.QEvent.MouseButtonRelease:
            QtWidgets.QApplication.instance().removeEventFilter(self)
            cursor  = QtGui.QCursor.pos()
            widget  = _DS.widget
            label   = _DS.label
            source  = _DS.source      # save before clearing
            _DS.active = False
            _DS.widget = None
            _DS.source = None

            # Clear all overlays
            for pane in self._panes:
                pane.hideOverlay()

            def _cleanup_source():
                """Remove source pane if it ended up empty after the drop."""
                if (source is not None
                        and source in self._panes
                        and source.count() == 0
                        and len(self._panes) > 1):
                    self._removePane(source)

            # Find which pane the cursor landed on
            for pane in self._panes:
                local = pane.mapFromGlobal(cursor)
                if pane.rect().contains(local):
                    zone = pane.zoneAt(local)
                    if zone == 'center':
                        pane.addTab(widget, label)
                        pane.setCurrentWidget(widget)
                    else:
                        self._splitPane(pane, zone, widget, label)
                    _cleanup_source()
                    return True

            # Dropped outside all panes — append a new pane
            new = self._newPane()
            new.addTab(widget, label)
            new.setCurrentWidget(widget)
            self._equalise(self._splitter)
            _cleanup_source()
            return True

        return False

    # ------------------------------------------------------------------
    # Split logic
    # ------------------------------------------------------------------
    def _onSplitReq(self, direction, widget, label):
        pane = self.sender()
        self._splitPane(pane, direction, widget, label)

    def _splitPane(self, target, zone, widget, label):
        orientation = (QtCore.Qt.Horizontal
                       if zone in ('left', 'right')
                       else QtCore.Qt.Vertical)
        after = zone in ('right', 'bottom')

        # Find which splitter currently owns target
        owner = target.parent()
        if not isinstance(owner, QtWidgets.QSplitter):
            owner = self._splitter

        if owner.orientation() == orientation:
            idx = owner.indexOf(target)
            new = self._newPane(add_to_splitter=False)
            owner.insertWidget(idx + (1 if after else 0), new)
        else:
            # Wrap target in a new nested splitter of the right orientation
            idx = owner.indexOf(target)
            sub = QtWidgets.QSplitter(orientation, owner)
            owner.insertWidget(idx, sub)
            target.setParent(sub)
            new = self._newPane(add_to_splitter=False)
            if after:
                sub.addWidget(target)
                sub.addWidget(new)
            else:
                sub.addWidget(new)
                sub.addWidget(target)
            sub.show()
            # sub is brand-new and has no layout dimensions yet; calling
            # setSizes with size=0 pins every item to 0 permanently because
            # Qt honours explicit sizes even after a real layout pass.
            # Defer until the next event-loop iteration when geometry is live.
            QtCore.QTimer.singleShot(0, lambda s=sub: self._equalise(s))

        new.addTab(widget, label)
        new.setCurrentWidget(widget)
        new.show()
        self._equalise(owner)

    def _equalise(self, splitter):
        n = splitter.count()
        if n:
            size = (splitter.width() if splitter.orientation() == QtCore.Qt.Horizontal
                    else splitter.height())
            splitter.setSizes([size // n] * n)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def activePane(self):
        """Return the PaneTabWidget that currently has focus, or primary."""
        focused = QtWidgets.QApplication.focusWidget()
        w = focused
        while w:
            if isinstance(w, PaneTabWidget):
                return w
            w = w.parent() if hasattr(w, 'parent') else None
        return self._primary

    def currentWidget(self):
        return self.activePane().currentWidget()

    def addTab(self, widget, label, pane=None):
        if pane is None:
            pane = self.activePane()
        idx = pane.addTab(widget, label)
        pane.setCurrentIndex(idx)
        return idx

    def setCurrentIndex(self, idx):
        """Set current tab in primary pane (used by load_settings)."""
        if 0 <= idx < self._primary.count():
            self._primary.setCurrentIndex(idx)

    def count(self):
        return sum(p.count() for p in self._panes)

    def paneCount(self):
        return len(self._panes)

    def allTabs(self):
        """Return [(widget, label), …] across all panes in order."""
        result = []
        for pane in self._panes:
            for i in range(pane.count()):
                result.append((pane.widget(i), pane.tabText(i)))
        return result

    def _globalIndex(self, pane, local_idx):
        n = 0
        for p in self._panes:
            if p is pane:
                return n + local_idx
            n += p.count()
        return -1

    def _localIndex(self, global_idx):
        n = 0
        for pane in self._panes:
            c = pane.count()
            if n + c > global_idx:
                return pane, global_idx - n
            n += c
        return None, -1

    def widget(self, global_idx):
        pane, li = self._localIndex(global_idx)
        return pane.widget(li) if pane else None

    def tabText(self, global_idx):
        pane, li = self._localIndex(global_idx)
        return pane.tabText(li) if pane else ''

    def setTabText(self, global_idx, text):
        pane, li = self._localIndex(global_idx)
        if pane:
            pane.setTabText(li, text)

    def removeTab(self, global_idx):
        pane, li = self._localIndex(global_idx)
        if pane:
            pane.removeTab(li)
            if pane.count() == 0 and len(self._panes) > 1:
                self._removePane(pane)

    def removePane(self, pane):
        self._removePane(pane)

    def allTabsWithPane(self):
        """Return [(widget, label, pane_idx), …] across all panes in order."""
        result = []
        for pi, pane in enumerate(self._panes):
            for i in range(pane.count()):
                result.append((pane.widget(i), pane.tabText(i), pi))
        return result

    def paneAt(self, idx):
        """Return the pane at *idx*, creating new panes as needed.
        Does NOT add them to any splitter — applyLayout() handles placement."""
        while len(self._panes) <= idx:
            self._newPane(add_to_splitter=False)
        return self._panes[idx]

    def resetLayout(self):
        """Tear everything down to one empty pane (called before load_settings)."""
        for pane in list(self._panes):
            while pane.count():
                pane.removeTab(0)
            pane.hide()
            pane.setParent(None)
            pane.deleteLater()
        self._panes.clear()
        # Strip any nested sub-splitters that remained in the root splitter
        while self._splitter.count():
            self._splitter.widget(0).setParent(None)
        # Primary pane is created but NOT yet placed; applyLayout() will do that
        self._primary = self._newPane(add_to_splitter=False)

    # ------------------------------------------------------------------
    # Layout save / restore
    # ------------------------------------------------------------------

    def saveLayout(self):
        """Return a JSON string describing the full splitter/pane tree."""
        import json
        structure = {
            'orientation': 'h' if self._splitter.orientation() == QtCore.Qt.Horizontal else 'v',
            'children':    self._specFromSplitter(self._splitter),
        }
        return json.dumps(structure)

    def _specFromSplitter(self, splitter):
        items = []
        for i in range(splitter.count()):
            child = splitter.widget(i)
            if isinstance(child, PaneTabWidget):
                try:
                    items.append({'type': 'pane', 'idx': self._panes.index(child)})
                except ValueError:
                    pass
            elif isinstance(child, QtWidgets.QSplitter):
                items.append({
                    'type':        'splitter',
                    'orientation': 'h' if child.orientation() == QtCore.Qt.Horizontal else 'v',
                    'children':    self._specFromSplitter(child),
                })
        return items

    def applyLayout(self, layout_str):
        """Restore the splitter/pane tree from a JSON string saved by saveLayout().
        All panes must already exist in self._panes before calling this."""
        import json
        try:
            structure = json.loads(layout_str)
        except (json.JSONDecodeError, TypeError, ValueError):
            structure = None

        if not structure or 'children' not in structure:
            # Fallback: place all panes side-by-side in root
            for pane in self._panes:
                self._splitter.addWidget(pane)
                pane.show()
        else:
            orient_map = {'h': QtCore.Qt.Horizontal, 'v': QtCore.Qt.Vertical}
            self._splitter.setOrientation(
                orient_map.get(structure.get('orientation', 'h'), QtCore.Qt.Horizontal))
            self._buildFromSpec(self._splitter, structure['children'])

        # Defer equalise — widgets have no real geometry until after layout pass
        QtCore.QTimer.singleShot(0, lambda: self._equaliseRecursive(self._splitter))

    def _buildFromSpec(self, splitter, children):
        orient_map = {'h': QtCore.Qt.Horizontal, 'v': QtCore.Qt.Vertical}
        for item in children:
            t = item.get('type')
            if t == 'pane':
                idx = item.get('idx', 0)
                if 0 <= idx < len(self._panes):
                    pane = self._panes[idx]
                    splitter.addWidget(pane)
                    pane.show()
            elif t == 'splitter':
                orient = orient_map.get(item.get('orientation', 'h'), QtCore.Qt.Horizontal)
                sub = QtWidgets.QSplitter(orient)
                splitter.addWidget(sub)
                sub.show()
                self._buildFromSpec(sub, item.get('children', []))

    def _equaliseRecursive(self, splitter):
        """Equalise this splitter, then recurse into any nested splitters."""
        self._equalise(splitter)
        for i in range(splitter.count()):
            child = splitter.widget(i)
            if isinstance(child, QtWidgets.QSplitter):
                self._equaliseRecursive(child)

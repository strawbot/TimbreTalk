# historylineedit.py — QLineEdit with Up/Down command history  Robert Chapman
#
# Up   — recall progressively older sent entries.
# Down — move back toward newer entries; pressing Down past the newest
#         restores whatever was being typed when browsing started.
#
# Call record() after each successful send so the entry is stored.

from PyQt5 import QtCore, QtWidgets


class HistoryLineEdit(QtWidgets.QLineEdit):
    """QLineEdit with shell-style Up/Down arrow key history."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._history = []   # index 0 = oldest, -1 = newest
        self._histIdx = -1   # -1 = not browsing
        self._saved   = ''   # text snapshot taken when browsing starts

    # ------------------------------------------------------------------ API

    def record(self):
        """Store the current text as a history entry.  Call after every send."""
        text = self.text()
        if text and (not self._history or self._history[-1] != text):
            self._history.append(text)
        self._histIdx = -1
        self._saved   = ''

    # ---------------------------------------------------------- key handling

    def keyPressEvent(self, event):
        key = event.key()

        if key == QtCore.Qt.Key_Up:
            if not self._history:
                return
            if self._histIdx == -1:
                # Start browsing — snapshot whatever is currently typed
                self._saved   = self.text()
                self._histIdx = len(self._history) - 1
            elif self._histIdx > 0:
                self._histIdx -= 1
            # (already at oldest — stay there, do nothing extra)
            self.setText(self._history[self._histIdx])
            self.selectAll()

        elif key == QtCore.Qt.Key_Down:
            if self._histIdx == -1:
                return  # not browsing
            if self._histIdx < len(self._history) - 1:
                self._histIdx += 1
                self.setText(self._history[self._histIdx])
                self.selectAll()
            else:
                # Past newest — restore the text that was being typed
                self._histIdx = -1
                self.setText(self._saved)
                self._saved = ''
                self.end(False)   # cursor to end of line

        else:
            super().keyPressEvent(event)

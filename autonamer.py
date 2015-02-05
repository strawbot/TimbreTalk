#! /usr/bin/env python

import glob
from xml.dom.minidom import parse


folder = "./"
uifiles = glob.glob(folder+'*.ui')

def widgetClass(dom, what):
	wclass = []
	widgets = dom.getElementsByTagName('widget')
	for widget in widgets:
		if widget.getAttribute('class') == what:
			wclass.append(widget)
	return wclass

def subnodes(node, what):
	nodes = node.getElementsByTagName('what')
	for widget in widgets:
		if widget.getAttribute('class') == what:
			wclass.append(widget)
	return wclass

def getNode(node, type, nodename):
	nodes = node.getElementsByTagName(type)
	for node in nodes:
		if node.getAttribute('name') == nodename:
			return node
	return None

def qwidgetname(dom):
	qwidget = widgetClass(dom, 'QWidget')
	if qwidget:
		return qwidget[0].getAttribute('name')
	return ''

def groupNames(dom):
	names = []
	for group in widgetClass(dom, 'QGroupBox'):
		names.append(group.getAttribute('name'))
	return names

def name(node):
	node.getAttribute('name')

for file in uifiles:
	dom = parse(file)
	screenName = qwidgetname(dom)
	groups = widgetClass(dom, 'QGroupBox')
	print screenName
	for group in groups:
		print name(group),
'''
get screen name
get groups
find pairs in each group
	for each pair
		label left 
find pairs in screen not in group

for each group in screen
	get group name
	for each pair in group  // find pairs in layouts? >> done first? what if no layouts? could be grid, table, or horizontal layout
		get label string
			if label in column 0 of a layout or left side of a horizontal layout
				set label name to 'vl_'+screenName+GroupName+LabelString
			else
				if in column 1 of layout or right side of a horizontal layout
					set widget name to 'v_'+ name of column 0 label

for each 
#	widgets = dom.getElementsByTagName('widget')
#	for widget in widgets:
#		print widget.attributes
		#print map(lambda x: x.firstChild.nodeValue, widget.getElementsByTagName('name'))

#	print file
'''
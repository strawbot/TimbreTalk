
import sys, os
from message import *


class MessageQueue():
	def __init__(self, mqName):
		error("posix_ipc MessageQueue not available this system")

	def receive(self):
		error("posix_ipc receive not available this system")
	
	def send(self, name):
		error("posix_ipc send not available this system")

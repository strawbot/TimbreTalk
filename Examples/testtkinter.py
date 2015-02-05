#!/usr/bin/python
import sys, time
from Tkinter import *

class Logger(Frame):
    def __init__(self):
        Frame.__init__(self)
        self.pack(expand=YES, fill=BOTH)
        self.master.title("Timestamp logging application")
        self.tslist = []
        self.tsdisp = Text(height=6, width=25)
        self.count = StringVar()
        self.cntdisp = Message(font=('Sans',24),
                               textvariable=self.count)
        self.log = Button(text="Log Timestamp",
                          command=self.log_timestamp)
        self.quit = Button(text="Quit", command=sys.exit)
        self.tsdisp.pack(side=LEFT)
        self.cntdisp.pack()
        self.log.pack(side=TOP, expand=YES, fill=BOTH)
        self.quit.pack(side=BOTTOM, fill=BOTH)
    def log_timestamp(self):
        stamp = time.ctime()
        self.tsdisp.insert(END, stamp+"\n")
        self.tsdisp.see(END)
        self.tslist.append(stamp)
        self.count.set("% 3d" % len(self.tslist))

if __name__=='__main__':
    Logger().mainloop()
# support for background task with finisher and threads
# Usage: tasks = background()
#  There are two use cases: background task or multiple instances working on an array of data
#        Run sometask in the background and then run followuptask if present. If either task
#        causes an exception, then the aborttask will run
#          tasks.put(sometask, finishTask=followuptask, abortTask=cleanuptask)
#
#        Run multiple copies of the same function on an array of arguments and wait till done. This is
#        best done by sometask so it won't block the foreground task
#         tasks.concurrent(function, argumentlist)
# Example:
#        def sometask():
#            def function(arg):
#                do_something(arg)
#            tasks.concurrent(function, arglist)
#        tasks.put(sometask)

import sys
import time
import traceback
from queue import Queue
from threading import Thread

from PyQt5.QtCore import QObject, QThread, pyqtSignal
# from PyQt5 import Qt

from . import abort


def extract(function): # try and extract a name from an object
    s = '{}'.format(function)
    if s.find('<function ') > -1:
        return s.split()[1]
    if s.find('<bound method') > -1:
        return s.split()[2]
    return s


class wrap(object): # put exception protection around an object
    def __init__(self, function):
        self.function = function

    def wrapper(self, arg):
        try:
            self.function(arg)
        except Exception as e:
            print('Thread for {} excepted: {}'.format(extract(self.function),e))


class aborted(QObject):
    abort = pyqtSignal(bool)
    def __init__(self):
        QObject.__init__(self)

    def emitted(self, bool):
        self.abort.emit(bool)

    def connected(self, method):
        self.abort.connect(method)


class background(Thread):
    ab = aborted()
    # aborted = pyqtSignal(bool) # Doesn't work
    def __init__(self):
        Thread.__init__(self)
        self.machineq = Queue()
        self.sequential = False
        self.start()
        self.nthreads = 0

    def run(self):
        while True:
            self.do_tasks()

    def do_tasks(self):
        machine = self.machineq.get()
        task = machine[0]
        args = machine[1:]
        if not abort.flag:
            start = time.time()
            print('Run new task: {}'.format(extract(task)))
            if len(args):
                task(args)
            else:
                task()
            self.report("Tasks", start)
        else:
            print('Abort task {}'.format(extract(task)))
            if self.machineq.empty():
                print('Tasks finished')
                abort.flag = False
                self.ab.emitted(False)

    def run_link(self, tasks):
        (task, finishTask, abortTask) = tasks
        print ('executing: {}'.format(extract(task)))
        try:
            task()
            if finishTask and not abort.flag:
                print('Finish task: {}'.format(extract(finishTask)))
                finishTask()
        except Exception as e:
            print(e, file=sys.stderr)
            traceback.print_exc(file=sys.stderr)
            if abortTask:
                abortTask()

    def abortTasks(self):
        def block_abort():
            pass

        self.put((block_abort,))
        abort.flag = True
        self.ab.emitted(True)

    def put(self, task_tupple):
        self.status()
        if not abort.flag:
            self.machineq.put(task_tupple)

    def threaded(self, function):
        Thread(name=extract(function), target=function).start()

    # parallelize function with array of arguments'

    def concurrent(self, function, args, timeout=5):
        if abort.flag: raise Exception
        print('concurrent: {} ({}S)'.format(extract(function), timeout))
        start = time.time()
        if self.sequential:
            for arg in args:
                if abort.flag: raise Exception
                function(arg)
        else:
            threads = []
            for arg in args:
                threads.append(Thread(name=extract(function), target=wrap(function).wrapper, args=(arg,)))
            for t in threads:
                t.start()
                self.nthreads += 1
            for t in threads:
                # if abort.flag: raise Exception
                t.join(timeout)
                if t.is_alive():
                    print('ERROR: thread ({}) timed out. Attempting to abort it... '.format(t.name))
                    abort.flag = True
                    t.join()
                    abort.flag = False
                    print('Thread abort complete.')
                self.nthreads -= 1

        self.report("Threads", start)

    def report(self, who, start):
        elapsed = time.time() - start
        if elapsed < .01:
            print('{} took {:.3f} mS'.format(who, elapsed * 1000))
        else:
            print('{} took {:.2f} S'.format(who, elapsed))

    def status(self):
        state = 'is empty' if self.machineq.empty() else 'has {} items'.format(self.machineq.qsize())
        print('machineq {}  abort flag = {}'.format(state, abort.flag))
        print('{} threads are running'.format(self.nthreads))
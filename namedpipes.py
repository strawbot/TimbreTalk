import os, time, sys
pipe_name = 'pipe_test'

def child( ):
    pipeout = os.open(pipe_name, os.O_WRONLY)
    counter = 0
    while True:
        time.sleep(1)
        os.write(pipeout, 'Number %03d\n' % counter)
        counter = (counter+1) % 5

def parent( ):
    pipein = open(pipe_name, 'r')
#    pipein = os.open(pipe_name, os.O_RDONLY)
    while True:
        line = pipein.readline()[:-1]
#        line = os.read(pipein, 100)
        print 'Parent %d got "%s" at %s' % (os.getpid(), line.strip(), time.time( ))

if not os.path.exists(pipe_name):
    os.mkfifo(pipe_name)  
pid = os.fork()    
if pid != 0:
    parent()
else:       
    child()

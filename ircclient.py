import sys
import socket
import string
import sets
import time
from threading import Thread
from Queue import Queue, Empty
import traceback
import itertools

class IrcClient(Thread):
    def __init__(self, nick, host='localhost', port=6667):
        Thread.__init__(self)
        self.channels = sets.Set()
        self.nick = nick
        self.host = host
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.msgQ = Queue()
        self.msgQ.put(("NICK %s\r\n" % self.nick, 0))
        self.msgQ.put(("USER %s %s bla :%s\r\n" % 
            (self.nick, self.host, self.nick), 0))
        
    def enter(self, channel):
        if not channel in self.channels:
            self.msgQ.put(("JOIN %s\r\n" % channel, 0))
            self.channels.add(channel)
        else:
            raise Exception("Trying to join a channel you are already in")

    def leave(self, channel):
        if channel in self.channels:
            self.msgQ.put(("PART %s\r\n" % channel, 0))
            self.channels.remove(channel)
        else:
            raise Exception("Trying to leave a channel you are not in")

    def quit(self):
        self.msgQ.put(("QUIT\n", 0))
    
    def send(self, channel, msg):
        if channel in self.channels:
            print 'put', msg, 'in queue'
            self.msgQ.put(("PRIVMSG %s %s\r\n" % (channel, msg), 2))
        else:
            raise Exception("Trying to send to a channel you are not connected to")
    
    def socketSend(self, msg, wait=False):
        sent = 0
        (contents, wait) = msg
        print 'contents:', contents, 'wait:', wait
        msgLen = len(contents)
        while sent < msgLen:
            l = self.sock.send(contents)
            sent += l
            print 'sent:', contents[:l], 'sending:', contents[l:]
            contents = contents[l:]
        if wait:
            time.sleep(wait)
    
    def run(self):
        self.sock.connect((self.host, self.port))
        self.sock.setblocking(False)
        readbuffer=""
        print 'entering loop'
        while 1:
            try:
                newMsg = self.sock.recv(1024)
                print 'newMsg:', newMsg, 'delim', len(newMsg)
                if len(newMsg) == 0:
                    print 'about to return'
                    return
                readbuffer += newMsg
                temp=string.split(readbuffer, "\n")
                print 'temp:', temp
                readbuffer=temp.pop( )
                print 'readbuffer:', readbuffer

                for line in temp:
                    print 'line:', line
                    line=string.rstrip(line)
                    line=string.split(line)
                    if(line[0]=="PING"):
                        self.sock.sendall("PONG %s\r\n" % line[1])
            except:
                pass  
            
            try:
                while True:
                    msg = self.msgQ.get_nowait()
                    print 'msg:', msg
                    self.socketSend(msg)
                    if msg == "QUIT\n":
                        print 'got quit', '!'*30
                        return
            except:
                pass
                #exc_type, exc_value, exc_traceback = sys.exc_info()
                #print "*** print_tb:"
                #traceback.print_tb(exc_traceback, limit=1, file=sys.stdout)

def enqueue_stream(stream, queue, loop=False):
    for line in iter(stream.readline, ''):
        queue.put(line)
    stream.close()
    queue.put(('done',))

if __name__ == '__main__':
    print sys.argv
    
    stream = sys.stdin    
    host = 'localhost'
    channel = ''
    nickname = ''
    loop = False

    for item in sys.argv:
        if item.startswith('-s='):
            stream = open(item.split('=', 1)[1])
        if item.startswith('-h='):
            host = item.split('=', 1)[1]
        if item.startswith('-c='):
            channel = item.split('=', 1)[1]
        if item.startswith('-n='):
            nickname = item.split('=', 1)[1]
        if item == '-l':
            loop = True

    # start irc client thread
    c = IrcClient(nickname, host)
    c.start()
    c.enter(channel)

    # start enqueue thread
    q = Queue()
    t = Thread(target=enqueue_stream, args=(stream, q, loop))
    t.daemon = True
    t.start()
    
    while True:
        try:
            line = q.get(True)
            print 'got line:', line
            if not type(line) is str:
                break
            else:
                c.send(channel, line)
        except Empty:
            continue

    c.leave(channel)
    c.quit()
    
    c.join()
    print 'done'







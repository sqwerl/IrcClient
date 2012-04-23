import sys
import socket
import string
import sets
import time
from threading import Thread, Event
from Queue import Queue, Empty
import traceback
import itertools
import random

class IrcClient(Thread):
    def __init__(self, nick, host='localhost', port=6667):
        Thread.__init__(self)
        self.inputStreamDoneEvent = Event()
        self.channels = sets.Set()
        self.nick = nick
        self.host = host
        self.port = port
        self.hasQuit = False
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.msgQ = Queue()
        self.msgQ.put(("NICK %s\r\n" % self.nick, 0))
        self.msgQ.put(("USER %s %s bla :%s\r\n" % 
            (self.nick, self.host, self.nick), 0))
        
    def enter(self, channel):
        if not channel in self.channels:
            self.msgQ.put(("JOIN %s\r\n" % channel, 0))
            self.channels.add(channel)
            print 'joined channel:', channel
        else:
            raise Exception("Trying to join a channel you are already in")

    def leave(self, channel):
        if channel in self.channels:
            self.msgQ.put(("PART %s\r\n" % channel, 0))
            self.channels.remove(channel)
        else:
            raise Exception("Trying to leave a channel you are not in")

    def quit(self):
        for channel in self.channels:
            self.leave(channel)
        self.msgQ.put(("QUIT\n", 0))
        self.hasQuit = True
    
    def send(self, channel, msg, delay):
        if channel in self.channels:
            #print 'put', msg, 'in queue'
            self.msgQ.put(("PRIVMSG %s :%s\r\n" % (channel, msg), delay))
        else:
            raise Exception("Trying to send to a channel you are not connected to")

    def sendAllChannels(self, msg, delay):
        if len(self.channels) == 0:
            raise Exception("You have not joined any channels")
        for channel in self.channels:
            self.send(channel, msg, delay)
        
    def socketSend(self, msg, wait=False):
        sent = 0
        (contents, wait) = msg
        #print 'contents:', contents, 'wait:', wait
        msgLen = len(contents)
        while sent < msgLen:
            l = self.sock.send(contents)
            sent += l
            #print 'sent:', contents[:l], 'sending:', contents[l:]
            contents = contents[l:]
        if wait:
            time.sleep(wait)

    def inputStreamDone(self):
        self.inputStreamDoneEvent.set()
        
    def run(self):
        self.sock.connect((self.host, self.port))
        self.sock.setblocking(False)
        readbuffer=""
        #print 'entering loop'
        while 1:
            try:
                newMsg = self.sock.recv(1024)
                #print 'newMsg:', newMsg, 'delim', len(newMsg)
                if len(newMsg) == 0:
                    #print 'about to return'
                    return
                readbuffer += newMsg
                temp=string.split(readbuffer, "\n")
                #print 'temp:', temp
                readbuffer=temp.pop( )
                #print 'readbuffer:', readbuffer

                for line in temp:
                    #print 'line:', line
                    line=string.rstrip(line)
                    line=string.split(line)
                    if(line[0]=="PING"):
                        self.sock.sendall("PONG %s\r\n" % line[1])
                    if line[1] == 'PRIVMSG':
                        print 'recv' + ' '.join(line[3:])
            except:
                pass  
            
            try:
                while True:
                    if self.inputStreamDoneEvent.isSet() and not self.hasQuit:
                        #print 'self.quit', self.hasQuit
                        self.quit()
                    msg = self.msgQ.get_nowait()
                    self.socketSend(msg)
                    if msg == "QUIT\n":
                        return
            except:
                pass

def enqueue_stream(stream, client, delay, randDelay):
    for line in iter(stream.readline, ''):
        client.sendAllChannels(line, delay + random.random()*randDelay)
    client.inputStreamDone()
    stream.close()

def startIrcClient(host, channel, nickname, delay, stream):
    # start irc client thread
    c = IrcClient(nickname, host)
    c.start()
    c.enter(channel)
    
    Thread(target=enqueue_stream, args=(stream, c, delay, 0)).start()

    return c

if __name__ == '__main__':
    print sys.argv
    
    stream = sys.stdin    
    host = 'localhost'
    channel = ''
    nickname = ''
    loop = False
    delay = 1

    for item in sys.argv:
        if item.startswith('-s='):
            stream = open(item.split('=', 1)[1])
        if item.startswith('-h='):
            host = item.split('=', 1)[1]
        if item.startswith('-c='):
            channel = item.split('=', 1)[1]
        if item.startswith('-n='):
            nickname = item.split('=', 1)[1]
        if item.startswith('-d='):
            delay = int(item.split('=', 1)[1])
        if item == '-l':
            loop = True

    c = startIrcClient(host, channel, nickname, delay, stream)
    c.join()
    print '\n\n\ndone'

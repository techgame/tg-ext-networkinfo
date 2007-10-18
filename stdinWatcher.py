#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#~ Imports 
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

import sys, os
import select

try:
    import tty
except ImportError:
    tty = None

try:
    import msvcrt
except ImportError:
    msvcrt = None

from TG.notifications.notify import Notification
from TG.netTools.selectTask import task, NetworkSelectable

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#~ Stdin Event Method
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def stdinEvent(blather, onReadableCB):
    if msvcrt is not None:
        return winStdinEvent(blather, onReadableCB)
    else:
        return posixStdinEvent(blather, onReadableCB)

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#~ Posix Selectable Task
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class PosixStdinSelectable(NetworkSelectable):
    onReadable = Notification.property()

    def __init__(self, onReadableCB=None):
        if onReadableCB is not None:
            self.onReadable.add(onReadableCB)
        
    def getSelectable(self):
        return sys.stdin

    def needsRead(self):
        self._prepare()
        return True

    def performRead(self):
        self._restore()
        self.onReadable.notify(self.getSelectable())
        return 0

    def needsWrite(self):
        return False

    def performWrite(self):
        pass

    _fdTTYMode = None
    def _prepare(self):
        if self._fdTTYMode is None:
            fd = self.getSelectable().fileno()
            ttyMode = tty.tcgetattr(fd)
            tty.setcbreak(fd)
            self._fdTTYMode = fd, ttyMode

    def _restore(self):
        if self._fdTTYMode is not None:
            fd, ttyMode = self._fdTTYMode
            tty.tcsetattr(fd, tty.TCSANOW, ttyMode)
            self._fdTTYMode = None

def posixStdinEvent(blather, onReadableCB):
    stdinWatcher = PosixStdinSelectable(onReadableCB)
    blather.networkSelector.add(stdinWatcher)
    return stdinWatcher

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#~ Windows Stdin Task
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class WindowsStdinWatcher(task.TaskBase):
    onReadable = Notification.property()

    def __init__(self, onReadableCB=None):
        if onReadableCB is not None:
            self.onReadable.add(onReadableCB)
        
    def isTaskReady(self, incIdle=True):
        return msvcrt.kbhit()

    def runTask(self):
        self.onReadable.notify(sys.stdin)

def winStdinEvent(blather, onReadableCB):
    stdinWatcher = WindowsStdinWatcher(onReadableCB)
    blather.tasks.add(stdinWatcher)
    return stdinWatcher


##~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~##
##~ Copyright (C) 2002-2005  TechGame Networks, LLC.              ##
##~                                                               ##
##~ This library is free software; you can redistribute it        ##
##~ and/or modify it under the terms of the BSD style License as  ##
##~ found in the LICENSE file included with this distribution.    ##
##~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~##

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#~ Imports 
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

import time
import errno # for socket error codes
import socket
from socket import AF_INET, AF_INET6
import select
import struct

try:
    import fcntl
except ImportError:
    fcntl = None

from TG.tasking import task

from TG.netTools import netif

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#~ Constants / Variables / Etc. 
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

SocketError = socket.error

socketErrorMap = {}
socketErrorMap[errno.EAGAIN] = False
socketErrorMap[errno.EINTR] = False
socketErrorMap[errno.EWOULDBLOCK] = False

socketErrorMap[errno.EMSGSIZE] = True

socketErrorMap[errno.ECONNABORTED] = True
socketErrorMap[errno.ECONNREFUSED] = True
socketErrorMap[errno.ECONNRESET] = True

socketErrorMap[errno.EADDRNOTAVAIL] = True
socketErrorMap[errno.ENETUNREACH] = True

if hasattr(errno, 'WSAEINTR'):
    socketErrorMap[errno.WSAEINTR] = False
    socketErrorMap[errno.WSAEWOULDBLOCK] = False

    socketErrorMap[errno.WSAECONNABORTED] = True
    socketErrorMap[errno.WSAECONNREFUSED] = True
    socketErrorMap[errno.WSAECONNRESET] = True

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#~ Definitions 
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class NetworkCommon(object):
    SocketError = SocketError
    socketErrorMap = socketErrorMap
    def reraiseSocketError(self, socketError, errorNumber):
        """Return socketError if the exception is to be reraised"""
        if self.socketErrorMap.get(errorNumber, True):
            return socketError

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class NetworkSelectable(NetworkCommon):
    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    #~ Socket and select.select machenery
    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def getSelectable(self):
        raise NotImplementedError('Subclass Responsibility: %r' % (self,))

    #~ callbacks selectable/select machenery ~~~~~~~~~~~~~~~~~~~~~~~~~~

    def fileno(self):
        """Used by select.select so that we can use this class in a
        non-blocking fasion."""
        selectable = self.getSelectable()
        if selectable is not None:
            return selectable.fileno()
        else: return 0

    def needsRead(self):
        return True

    def performRead(self):
        """Called by the selectable select/poll process when selectable is ready to
        harvest.  Note that this is called during NetworkSelectTask's
        timeslice, and should not be used for intensive processing."""
        raise NotImplementedError('Subclass Responsibility: %r' % (self,))

    def needsWrite(self):
        raise NotImplementedError('Subclass Responsibility: %r' % (self,))

    def performWrite(self):
        """Called by the selectable select/poll process when selectable is ready for
        writing.  Note that this is called during NetworkSelectTask's timeslice, and
        should not be used for intensive processing."""
        raise NotImplementedError('Subclass Responsibility: %r' % (self,))

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class SocketSelectable(NetworkSelectable):
    afamily = AF_INET
    sockType = None
    disallowMixedIPv4andIPv6 = True

    _sock = None
    def getSocket(self):
        return self._sock
    getSelectable = getSocket

    def setSocket(self, sock):
        self._sock = sock
        self._socketConfig()
    sock = property(getSocket, setSocket)

    def createSocket(self, afamily=None, sockType=None):
        self.afamily = afamily or self.afamily
        self.sockType = sockType or self.sockType
        sock = socket.socket(self.afamily, self.sockType)
        self.setSocket(sock)

    def _socketConfig(self):
        self.getSocket().setblocking(False)
        self._socketReuseAddress()
        self._socketConfigFcntl()

    def _normSockAddr(self, address):
        # normalize the address into a routing token
        ip, port = address[:2]
        info = socket.getaddrinfo(ip, int(port))[0]
        # grab the address portion of the info
        afamily, address  = info[0], info[-1]
        return afamily, address

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    #~ Socket Config Methods 
    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def _asSockAddr(self, address):
        if address is not None:
            if not isinstance(address, tuple):
                address = (address, 0)
            address = self._normSockAddr(address)[1]
        return address

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def _socketReuseAddress(self):
        sock = self.getSocket()
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        if hasattr(socket, "SO_REUSEPORT"):
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)

        if (self.afamily == AF_INET6) and  self.disallowMixedIPv4andIPv6:
            sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 1)

    def _socketConfigFcntl(self):
        if fcntl and hasattr(fcntl, 'FD_CLOEXEC'):
            fileno = self.getSocket().fileno()
            bitmask = fcntl.fcntl(fileno, fcntl.F_GETFD)
            bitmask |= fcntl.FD_CLOEXEC
            fcntl.fcntl(fileno, fcntl.F_SETFD, bitmask)

    def _socketSetMaxBufferSize(self):
        sock = self.getSocket()
        size = self._socketFindMaxBufferSize(sock)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, size)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, size)

    _socketMaxBufferSize = None
    @classmethod
    def _socketFindMaxBufferSize(klass, sock, size=0x40000, size0=0x02000, size1=0x80000):
        if not klass._socketMaxBufferSize:
            SOL_SOCKET = socket.SOL_SOCKET
            SO_RCVBUF = socket.SO_RCVBUF
            SO_SNDBUF = socket.SO_SNDBUF
            while size1 > size0+1:
                try:
                    sock.setsockopt(SOL_SOCKET, SO_RCVBUF, size)
                    sock.setsockopt(SOL_SOCKET, SO_SNDBUF, size)
                except socket.error:
                    # size is too big, so it is now our upper bound
                    size1 = size
                else:
                    # size works, so it is now our lower bound
                    size0 = size
                # go to the next size to test using binary search
                size = (size1+size0) >> 1
            klass._socketMaxBufferSize = size

        return klass._socketMaxBufferSize

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    #~ Socket Multicast Config
    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def _socketSetMulticastTTL(self, ttl):
        self._socketSetMulticastHops(ttl)
    def _socketSetMulticastHops(self, hops):
        sock = self.getSocket()
        if self.afamily == AF_INET:
            sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, hops)
        elif self.afamily == AF_INET6:
            sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_MULTICAST_HOPS, hops)

    def _socketSetMulticastLoop(self, loop=True):
        sock = self.getSocket()
        if self.afamily == AF_INET:
            sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_LOOP, loop)
        elif self.afamily == AF_INET6:
            sock.setsockopt(socket.IPPROTO_IPV6, socket.IP_MULTICAST_LOOP, loop)

    def _socketMulticastInterfacePacked(self, group, if_address=None):
        if self.afamily == AF_INET:
            # IPV4 require the interface IP to bind the multicast interface
            if if_address:
                if_address = self._asSockAddr(if_address)[0]
            else:
                if_address = self._socketGetMulticastInterface(group)

            return socket.inet_aton(if_address)

        elif self.afamily == AF_INET6:
            # IPV6 require the interface number to bind the multicast interface
            # which is happily packed at position 3 (zero based) of the IPV6 if_address
            if if_address:
                if_address = netif.getIFIndex(if_address) 
            if not if_address and group:
                if_address = netif.getIFIndexForIP(group[0], self.afamily) 
            if not if_address:
                if_address = self._socketGetMulticastInterface(group)

            return struct.pack('I', if_address)

    def _socketGetMulticastInterface(self, group):
        sock = self.getSocket()
        if self.afamily == AF_INET:
            result = sock.getsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_IF)
            result = socket.inet_ntoa(struct.pack('I', result))
        elif self.afamily == AF_INET6:
            result = sock.getsockopt(socket.IPPROTO_IPV6, socket.IPV6_MULTICAST_IF)
        return result

    def _socketSetMulticastInterface(self, group, if_address=None):
        sock = self.getSocket()
        groupAddr = self._asSockAddr(group)
        if_address = self._socketMulticastInterfacePacked(groupAddr, if_address)

        if self.afamily == AF_INET:
            sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_IF, if_address)
            return True
        elif self.afamily == AF_INET6:
            sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_MULTICAST_IF, if_address)
            return True
        return False

    def _socketMulticastGroupPack(self, group, if_address=None):
        groupAddr = self._asSockAddr(group)
        interface = self._socketMulticastInterfacePacked(None, if_address)
        if self.afamily == AF_INET:
            group = socket.inet_aton(groupAddr[0])
        elif self.afamily == AF_INET6:
            group = socket.inet_pton(self.afamily, groupAddr[0])
        return group + interface

    def _socketMulticastGroupJoin(self, group, if_address=None):
        sock = self.getSocket()
        groupAndIF = self._socketMulticastGroupPack(group, if_address)
        if self.afamily == AF_INET:
            sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, groupAndIF)
        elif self.afamily == AF_INET6:
            sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_JOIN_GROUP, groupAndIF)

    def _socketMulticastGroupLeave(self, group, if_address=None):
        sock = self.getSocket()
        groupAndIF = self._socketMulticastGroupPack(group, if_address)
        if self.afamily == AF_INET:
            sock.setsockopt(socket.IPPROTO_IP, socket.IP_DROP_MEMBERSHIP, groupAndIF)
        elif self.afamily == AF_INET6:
            sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_LEAVE_GROUP, groupAndIF)

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#~ Network Select Task -- The real workhorse
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class CountdownTimer(object):
    timestamp = staticmethod(time.clock)
    duration = 0.1
    lastTimestamp = 0.0

    def __init__(self, duration=0.1):
        self.duration = duration
    def isReady(self):
        return self.lastTimestamp < (self.timestamp() - self.duration)
    def touch(self):
        self.lastTimestamp = self.timestamp()

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class NetworkSelectTask(NetworkCommon, task.TaskBase):
    TimerFactory = CountdownTimer
    _select = staticmethod(select.select)
    _delay = staticmethod(time.sleep)

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    _selectables = None
    def getSelectableSet(self):
        if self._selectables is None:
            self._selectables = set()
        return self._selectables

    def add(self, selectable):
        self._verifySelectable(selectable, True)
        self.getSelectableSet().add(selectable)
    def remove(self, selectable):
        self.getSelectableSet().discard(selectable)

    def _iterReadables(self):
        return (s for s in self.getSelectableSet() if s.needsRead())
    def _iterWriteables(self):
        return (s for s in self.getSelectableSet() if s.needsWrite())

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    #~ Selectables verification
    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def filterSelectables(self):
        selectableSet = self.getSelectableSet()
        badSelectables = set(s for s in selectableSet if not self._verifySelectable(selectable))
        selectableSet -= badSelectables

    def _verifySelectable(self, selectable, reraise=False):
        items = [selectable]
        try:
            self._select(items, items, items, 0)
        except Exception:
            if reraise:
                raise
            return False
        else:
            return True

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    #~ Processing
    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def isTaskReady(self, incIdle=True):
        if incIdle:
            return True

        if not self._selectables:
            return False

        if self.isTimerReady():
            return True

        for w in self._iterWriteables():
            return True

        return False

    def runTask(self):
        self.process(0)

    def runTaskWithTimeout(self, timeout):
        self.process(timeout)

    def process(self, timeout=0):
        selectableSet = self.getSelectableSet()
        if not selectableSet:
            if timeout:
                # delay manually, since all platform implementations are not
                # consistent when there are no selectableSet present 
                self._delay(timeout)
            return

        readers, writers = self._iterReadables(), self._iterWriteables()
        try:
            readers, writers = self._select(readers, writers, [], timeout)[:2]
        except (ValueError, TypeError), err:
            self.filterSelectables()
            return
        except self.SocketError, err:
            if err.args[0] == errno.EBADF:
                self.filterSelectables()
                return
            elif self.reraiseSocketError(err, err.args[0]) is err:
                raise

        self.touchTimer()
        # now process our readers and writers
        return self.proccessSelected(readers, writers)

    def proccessSelected(self, readers, writers):
        recvBytes = 0
        for r in readers:
            recvBytes += r.performRead()
        self.recvBytes += recvBytes

        sentBytes = 0
        for w in writers:
            sentBytes += w.performWrite()
        self.sentBytes += sentBytes

    #~ Transfer stats tracking ~~~~~~~~~~~~~~~~~~~~~~~~~~

    recvBytes = 0
    sentBytes = 0

    def stats(self):
        return self.recvBytes, self.sentBytes
    def statsReset(self):
        self.recvBytes = 0
        self.sentBytes = 0

    def statsRepr(self):
        MB = float(1<<20)
        sentMB = self.sentBytes/MB
        recvMB = self.recvBytes/MB
        return 'sent: %8.1f MB, recv: %8.1f MB' % (sentMB, recvMB)

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    #~ Timer and task related
    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    _timer = None
    def getTimer(self):
        if self._timer is None:
            self._initTimer()
        return self._timer
    def setTimer(self, timer):
        self._timer = timer
    def isTimerReady(self):
        return self.getTimer().isReady()
    def touchTimer(self):
        return self.getTimer().touch()

    def _initTimer(self):
        self.setTimer(self.TimerFactory())


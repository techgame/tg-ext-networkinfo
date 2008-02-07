#!/usr/bin/env python
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

import struct
import socket
from socket import AF_INET, AF_INET6
from itertools import groupby, takewhile

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#~ Constants / Variables / Etc. 
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

_IPbyFamily = {}
_IPNetbyFamily = {}

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#~ Definitions 
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class IPBase(object):
    afamily = None
    _isNetmask = False
    byteCount = None

    def __init__(self, ip, isNetmask=False):
        if isNetmask != self._isNetmask:
            self._isNetmask = isNetmask
        self._setIP(ip)

    def sockaddr(self, port=None, *args, **kw):
        ip = self._getIP()
        try:
            address = socket.getaddrinfo(ip, port, *args, **kw)[0][-1]
        except socket.gaierror, e:
            if e.args[0] == socket.EAI_SERVICE:
                address = socket.getaddrinfo(ip, None, *args, **kw)[0][-1]
                address = (address[0], int(port)) + address[2:]
            else: raise
        return address

    def normalize(self):
        ip = self.sockaddr()[0]
        return self.asIP(ip, self._isNetmask)

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    @classmethod
    def asIP(klass, ip, isNetmask=False):
        if isinstance(ip, IPBase):
            return ip
        elif isinstance(ip, IPNetBase):
            return ip.ip
        return klass(ip, isNetmask)

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def __eq__(self, other):
        other = self.asIP(other)._getIPNumber()
        return (self._getIPNumber() == other)
    def __ne__(self, other):
        return not (self == other)

    _ip = None
    def _getIP(self):
        return self._ip
    def _setIP(self, ip):
        if self._ip is not None:
            raise Exception("IP has already been set, and this class is intended to be immutable")

        if isinstance(ip, (int, long)):
            self._setIPNumber(ip)
        elif self._isNetmask and ip.isdigit():
            ip = long(ip)
            ip = (1L<<ip)-1
            ip = self.max ^ ip
            self._setIPNumber(ip)
        else:
            self._ip = ip

    _ipNumber = None
    def _getIPNumber(self):
        n = self._ipNumber
        if n is None:
            n = 0L
            for e in self.packed():
                n = (n << 8) | ord(e)
            self._ipNumber = n
        return n
    def _setIPNumber(self, ipNumber):
        bytes = [((ipNumber >> 8*(n-1)) & 0xff) for n in xrange(self.byteCount,0,-1)]
        packed = ''.join(map(chr, bytes))
        self._ip = self.unpack(packed)

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def __int__(self):
        return self._getIPNumber()
    def __long__(self):
        return self._getIPNumber()
    def __oct__(self):
        return oct(self._getIPNumber())
    def __hex__(self):
        return hex(self._getIPNumber())
    def __hash__(self):
        return hash(self._getIP())

    def __repr__(self):
        return '%s(%s)' % (self.__class__.__name__, self.asStr(True, True))
    def __str__(self):
        return self.asStr(False, False)
    def __unicode__(self):
        return unicode(self.asStr(False, False))
    def asStr(self, short=True, incNetmask=True):
        raise NotImplementedError('Subclass Responsibility: %r' % (self.__class__,))

    if hasattr(socket, 'inet_pton'):
        def packed(self):
            return socket.inet_pton(self.afamily, self._getIP())
        @classmethod
        def unpack(klass, packed):
            return socket.inet_ntop(klass.afamily, packed)
    else:
        def packed(self):
            if self.afamily != AF_INET:
                raise NotImplementedError()
            return socket.inet_aton(self._getIP())
        @classmethod
        def unpack(klass, packed):
            if self.afamily != AF_INET:
                raise NotImplementedError()
            return socket.inet_ntoa(packed)

    @classmethod
    def fromPacked(self, packed, *args, **kw):
        return klass(self.unpack(packed), *args, **kw)

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def __invert__(self):
        return self.asIP(~self._getIPNumber())

    def __and__(self, other):
        return self.asIP(self._getIPNumber() & long(other))
    def __or__(self, other):
        return self.asIP(self._getIPNumber() | long(other))
    def __xor__(self, other):
        return self.asIP(self._getIPNumber() ^ long(other))

    def __rand__(self, other):
        return self.asIP(long(other) & self._getIPNumber())
    def __ror__(self, other):
        return self.asIP(long(other) | self._getIPNumber())
    def __rxor__(self, other):
        return self.asIP(long(other) ^ self._getIPNumber())

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def inNetwork(self, ipaddr0, *ipaddrs):
        ipn = self._getIPNumber()
        network = ipaddr0 & ipn
        for eachAddr in ipaddrs:
            if network != (eachAddr & ipn):
                return False
        return True

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class IPv4(IPBase):
    afamily = AF_INET
    max = (1L<<32) - 1
    byteCount = 4

    _shortNetmasks = {}
    for i in xrange(0, 33):
        _shortNetmasks[max & ~((1L<<i)-1)] = i

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def asStr(self, short=True, incNetmask=True):
        if short and self._isNetmask:
            result = self._shortNetmasks.get(self._getIPNumber())
            if result is not None:
                return str(result)
        return self._getIP()

_IPbyFamily[None] = IPv4
_IPbyFamily[IPv4.afamily] = IPv4

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class IPv6(IPBase):
    afamily = AF_INET6
    max = (1L<<128) - 1
    byteCount = 16

    _shortNetmasks = {}
    for i in xrange(0, 129):
        _shortNetmasks[max & ~((1L<<i)-1)] = i

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def asStr(self, short=True, incNetmask=True):
        if short and self._isNetmask:
            result = self._shortNetmasks.get(self._getIPNumber())
            if result is not None:
                return str(result)

        return self._getIP()

_IPbyFamily[IPv6.afamily] = IPv6

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#~ IP Conglomerates
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class IPNetBase(object):
    def __init__(self, ip, netmask=None):
        self.setIP(ip, netmask)

    def __repr__(self):
        return '%s(%s)' % (self.__class__.__name__, self.asStr(True, True))

    def __str__(self):
        return self.asStr(False, False)
    def __unicode__(self):
        return unicode(self.asStr(False, False))

    def sockaddr(self, port, *args, **kw):
        return self.ip.sockaddr(port, *args, **kw)

    def normalize(self):
        ip = self.ip
        if ip is not None:
            ip = ip.normalize()

        netmask = self.netmask
        if netmask is not None:
            netmask = netmask.normalize()

        return self.asIPNet(ip, netmask)

    def asStr(self, short=True, incNetmask=True):
        ip, netmask = self.ip, self.netmask
        if incNetmask and netmask is not None:
            return '%s/%s' % (ip.asStr(short, False), netmask.asStr(short, False))
        else: return ip.asStr(short, False)

    _ip = None
    def getIP(self):
        return self._ip
    def setIP(self, ip, netmask=None):
        ip, netmask = self._splitIPandNetmask(ip, netmask)
        self._ip = self.asIP(ip, isNetmask=False)
        if netmask:
            self.setNetmask(netmask)
    ip = property(getIP, setIP)

    _netmask = None
    def getNetmask(self):
        return self._netmask
    def setNetmask(self, netmask):
        self._netmask = self.asIP(netmask, isNetmask=True)
    netmask = property(getNetmask, setNetmask)

    def getNetwork(self):
        return self.ip & self.netmask
    network = property(getNetwork)

    def getLocal(self):
        return self.ip & ~self.netmask
    local = property(getLocal)

    def getBroadcast(self):
        return self.netmask & self.ip | ~self.netmask
    broadcast = property(getBroadcast)

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    @classmethod
    def asIPNet(klass, ip, netmask=None):
        return klass(ip, netmask)
    @classmethod
    def asIP(klass, ip, isNetmask=False):
        if hasattr(ip, 'getIP'):
            ip = ip.getIP()
        return klass.IPFactory(ip, isNetmask)
    @classmethod
    def _splitIPandNetmask(klass, ip, netmask=None):
        if not isinstance(ip, (str, unicode)):
            return ip, netmask

        ipAndNetmask = ip.split('/', 1)
        if len(ipAndNetmask) < 2:
            return ipAndNetmask[0], netmask
        elif netmask is not None:
            if netmask != ipAndNetmask[1]:
                raise ValueError("Netmask specified by both parameter and in IP address")
            return ipAndNetmask
        else:
            return ipAndNetmask

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def contains(self, ipOther):
        ipOther = self.asIP(ipOther)
        return self.getNetmask().inNetwork(self.getIP(), ipOther)
    __contains__ = contains

    def __hash__(self):
        return hash((self.getIP(), self.getNetmask()))

    def __eq__(self, other):
        if isinstance(other, IPBase):
            return self.ip == other
        elif not isinstance(other, self.__class__):
            other = self.asIP(other)
            return self.ip == other
        return (self.ip == other.ip) and (self.netmask == other.netmask)
    def __ne__(self, other):
        return not (self == other)


#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class IPNetv4(IPNetBase):
    afamily = IPv4.afamily
    IPFactory = IPv4.asIP
_IPNetbyFamily[None] = IPv4
_IPNetbyFamily[IPv4.afamily] = IPNetv4

class IPNetv6(IPNetBase):
    afamily = IPv6.afamily
    IPFactory = IPv6.asIP
_IPNetbyFamily[IPv6.afamily] = IPNetv6

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#~ Convience methods
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def guessIPFamily(ip):
    if ip.count(':') >= 2:
        return AF_INET6
    elif ip.count('.') == 3:
        return AF_INET
    else:
        raise ValueError("IP %r does not appear to be a valid ip address" % (ip,))

def ip(ip, isNetmask=False, afamily=None):
    if afamily is None:
        afamily = guessIPFamily(ip)

    factory = _IPbyFamily[afamily] 
    return factory(ip, isNetmask).normalize()
asIP = ip

def ipnet(ip, netmask=None, afamily=None):
    if afamily is None:
        afamily = guessIPFamily(ip)

    factory = _IPNetbyFamily[afamily] 
    return factory(ip, netmask).normalize()
asIPNet = ipnet

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#~ Main 
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

if __name__=='__main__':
    print asIPNet('127.0.0.1', '255.255.0.0')

    print repr(asIPNet('10.2.2.1'))
    print repr(asIPNet('127.0.0.1', '255.255.0.0'))
    print repr(asIPNet('127.0.0.1', '16'))
    print repr(asIPNet('127.0.0.1/16'))
    print repr(asIPNet('fe80:4:0:0:214:51ff:fe04:1366'))
    print repr(asIPNet('fe80:4:0:0:214:51ff:10.2.2.1'))
    print repr(asIPNet('fe80:4::214:51ff:fe04:1366'))
    print repr(asIPNet('fe80:4::214:51ff:10.2.2.1'))
    print repr(asIPNet('::1', 'ffff:ffff:ffff:ffff:0:0:0:0'))
    print repr(asIPNet('0:0:0:0:0:0:0:1'))
    print repr(asIPNet('::1/64'))
    print repr(asIPNet('::/96'))
    print repr(asIPNet('::1', 'ffff:ffff:ffff:ffff:ffff:ffff:ffff:ffff'))
    print repr(asIPNet('fe80:1:0:0:0:0:0:1'))
    print repr(asIPNet('fe80:1::1'))
    print repr(asIPNet('::1', 'ffff:ffff:ffff:ffff:0:0:0:0'))
    print repr(asIPNet('::1/ffff:ffff:ffff:ffff:0:0:0:0'))
    print repr(asIPNet('::1/ffff:ffff:ffff:ffff::'))
    print repr(asIPNet('::1/64'))
    print repr(asIPNet('::1/0'))


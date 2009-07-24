#!/usr/bin/env python
##~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~##
##~ Copyright (C) 2002-2005  TechGame Networks, LLC.              ##
##~                                                               ##
##~ This library is free software; you can redistribute it        ##
##~ and/or modify it under the terms of the BSD style License as  ##
##~ found in the LICENSE file included with this distribution.    ##
##~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~##

__all__ = [
    'posix_getifaddrs',
    'platform_getifaddrs',
    'platform_if_indextoname',
    'platform_if_nametoindex',

    'AF_INET',
    'AF_INET6',
    'AF_LINK',
    ]

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#~ Imports 
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

import sys
import os
import array
import struct

from socket import inet_ntop, AF_INET, AF_INET6
import ctypes
from ctypes.util import find_library

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#~ Definitions 
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

AF_LINK = 18

_libc = ctypes.cdll.LoadLibrary(find_library('libc'))

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class sockaddr(ctypes.Structure):
    _fields_ = [
        ('sa_len', ctypes.c_ubyte),
        ('sa_family', ctypes.c_ubyte),
        ('sa_data', ctypes.c_ubyte*64),
        ]

    _dataByFamily = {}

    def getFamily(self):
        return self.sa_family
    def getAddress(self):
        data = array.array('B', self.sa_data[0:self.sa_len+1]).tostring()
        handler = self._dataByFamily.get(self.sa_family)
        if handler is not None:
            return handler(self, data)
        else: return None

    def asTuple(self):
        return self.getFamily(), self.getAddress()

    def _link(self, data):
        # data is packed as follows::
        #   (2) sdl_index, 
        #   (1) sdl_type, 
        #   (1) sdl_nlen, 
        #   (1) sdl_alen,
        #   (1) sdl_slen,
        #   (12) sdl_data
        n = 6; ne = n+ord(data[3])
        a = ne; ae = a+ord(data[4])
        s = ae; se = s+ord(data[5])
        addr = ':'.join([x.encode('hex') for x in data[a:ae]])
        #selctor = data[s:se]
        return addr
    _dataByFamily[AF_LINK] = _link

    def _ipv4(self, data):
        # data is packed as follows::
        #   (2) port, 
        #   (4) address,
        #   (8) zeros

        ipv4 = inet_ntop(AF_INET, data[2:6])
        #port = struct.unpack('H', data[0:2])[0]
        return ipv4
    _dataByFamily[AF_INET] = _ipv4

    def _ipv6(self, data):
        # data is packed as follows::
        #   (2) port, 
        #   (4) flow info, 
        #   (16) address, 
        #   (4) scope id, 

        ipv6 = inet_ntop(AF_INET6, data[6:22])
        #port = struct.unpack('H', data[0:2])[0]
        return ipv6
    _dataByFamily[AF_INET6] = _ipv6

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

ifaddrs_p = ctypes.POINTER('ifaddrs')
class ifaddrs(ctypes.Structure):
    _fields_ = [
        ('ifa_next', ifaddrs_p),
        ('ifa_name', ctypes.c_char_p),
        ('ifa_flags', ctypes.c_uint),
        ('ifa_addr', ctypes.POINTER(sockaddr)),
        ('ifa_netmask', ctypes.POINTER(sockaddr)),
        ('ifa_dstaddr', ctypes.POINTER(sockaddr)),
        ('ifa_data', ctypes.c_void_p),
        ]

    def addInterface(self, ifMap):
        result = {}
        ifName = self.ifa_name
        ifMap.append((ifName, result))

        result['name'] = ifName
        result['if_index'] = _if_nametoindex(ifName)
        result['desc'] = ''
        result['flags'] = self.ifa_flags

        addrs = result.setdefault('addrs', [])

        family, addr = self.ifa_addr and self.ifa_addr[0].asTuple() or (None,None)
        netmask = self.ifa_netmask and self.ifa_netmask[0].getAddress() or None
        dstaddr = self.ifa_dstaddr and self.ifa_dstaddr[0].getAddress() or None

        if family == AF_LINK:
            addrs.append((family, addr))
        elif family == AF_INET:
            addrs.append((family, addr, netmask, dstaddr))
        elif family == AF_INET6:
            addrs.append((family, addr, netmask))

ctypes.SetPointerType(ifaddrs_p, ifaddrs)

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def _if_indextoname(idx):
    # this only requires 16 bytes, but I prefer to overallocate
    interfaceName = ctypes.c_buffer("\x00", 256)
    _libc.if_indextoname(idx, interfaceName)
    return interfaceName.value
platform_if_indextoname = _if_indextoname

def _if_nametoindex(interfaceName):
    return _libc.if_nametoindex(interfaceName)
platform_if_nametoindex = _if_nametoindex

def _getifaddrs():
    pAddrs = ifaddrs_p()
    err = _libc.getifaddrs(ctypes.byref(pAddrs))
    if err == 0:
        return pAddrs
    else:
        raise OSError(os.strerror(err), err)

def _freeifaddrs(addrs):
    _libc.freeifaddrs(addrs)

def posix_getifaddrs():
    ifMap = []
    rootAddrs = _getifaddrs()
    try:
        entry = rootAddrs
        while entry:
            entry[0].addInterface(ifMap)
            entry = entry[0].ifa_next
    finally:
        _freeifaddrs(rootAddrs)
    return ifMap
platform_getifaddrs = posix_getifaddrs


#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#~ Main 
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

if __name__=='__main__':
    from pprint import pprint
    pprint(platform_getifaddrs())


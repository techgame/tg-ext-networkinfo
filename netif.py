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

import sys
import platform as _platform
from ip import asIP, asIPNet

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#~ Definitions 
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

if _platform.win32_ver()[0]:
    import win_netif as platform_netif
    from win_netif import *
elif _platform.libc_ver()[0]:
    import posix_netif as platform_netif
    from posix_netif import *
elif _platform.mac_ver()[0]:
    import posix_netif as platform_netif
    from posix_netif import *
elif sys.platform == 'win32':
    import win_netif as platform_netif
    from win_netif import *
else:
    raise Exception("No platform_getifaddrs implementation for: %s" % (_platform.platform,))

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def ifaddrAsIP(afamily, addr, netmask=None, *args):
    try:
        return asIPNet(addr, netmask, afamily=afamily)
    except LookupError:
        return (afamily, addr, netmask)

def getifinfo(*afamilies):
    order = []
    result = {}
    for k, e in platform_getifaddrs():
        addrs = e['addrs']
        addrs = [a for a in addrs if a[1]]
        if afamilies:
            addrs = [a for a in addrs if a[0] in afamilies]
        if not addrs:
            continue

        addrs = [ifaddrAsIP(*a) for a in addrs]
        e['addrs'] = addrs
        if k not in order:
            order.append(k)
        result.setdefault(k, []).append(e)
    return [(n, result[n]) for n in order]

def orderedset(l):
    v = dict(zip(l,l))
    return [v.pop(e) for e in l if e in v]
def getifindexes(*afamilies):
    return [(n,orderedset([k['if_index'] for k in entries])) 
                for n, entries in getifinfo(*afamilies)]

def getifaddrs(*afamilies):
    return [(n,[a for k in entries for a in k['addrs']])
                for n, entries in getifinfo(*afamilies)]

def getifaddrs_mac(): 
    return getifaddrs(AF_LINK)
getifaddrs_link = getifaddrs_mac
def getifaddrs_v4(): 
    return getifaddrs(AF_INET)
def getifaddrs_v6(): 
    return getifaddrs(AF_INET6)

def getIFAddressList(ifname, *afamilies):
    return [k for n, k in getifaddrs(*afamilies) if n == ifname]
def getIFAddressList_v4(ifname):
    return getIFAddressList(ifname, AF_INET)
def getIFAddressList_v6(ifname):
    return getIFAddressList(ifname, AF_INET6)

def getIFIndex(ifname):
    if isinstance(ifname, (int, long)):
        if platform_if_indextoname(ifname):
            return ifname
    elif isinstance(ifname, (str, unicode)):
        return platform_if_nametoindex(ifname)
    return None

def getIFIndexForIP(ip, *afamilies):
    ip = asIP(ip)
    ifipMap = getifaddrs(*afamilies)
    for ifname, iplist in ifipMap:
        if ip in iplist:
            return getIFIndex(ifname)
    return None

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#~ Main 
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

if __name__=='__main__':
    from pprint import pprint
    print
    print 'getifaddrs:'
    pprint(getifaddrs())
    print

    print "IPv4 addresses:"
    pprint(getifaddrs_v4())
    print

    print "IPv6 addresses:"
    pprint(getifaddrs_v6())
    print

    print "Indexes:"
    pprint(getifindexes())
    print


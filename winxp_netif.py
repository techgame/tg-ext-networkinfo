##~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~##
##~ Copyright (C) 2002-2007  TechGame Networks, LLC.              ##
##~                                                               ##
##~ This library is free software; you can redistribute it        ##
##~ and/or modify it under the terms of the BSD style License as  ##
##~ found in the LICENSE file included with this distribution.    ##
##~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~##

__all__ = [
    'winxp_getifaddrs',
    'platform_getifaddrs',

    'AF_INET',
    'AF_INET6',
    'AF_LINK',
    ]

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#~ Imports 
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

import struct
from socket import AF_INET, AF_INET6
import ctypes

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#~ Definitions 
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

PSOCKET_ADDRESS = ctypes.POINTER('SOCKET_ADDRESS')
class SOCKET_ADDRESS(ctypes.Structure):
    _fields_ = [
        ('lpSockAddr', ctypes.POINTER(ctypes.c_char)),
        ('iSockaddrLength', ctypes.c_int), ]

    formats = {
        }

    def iterAddresses(self, prefixLen=0):
        bytes = self.lpSockAddr[:self.iSockaddrLength]
        decode = self.formats.get(ord(bytes[0]))
        if decode is not None:
            yield decode(self, bytes, prefixLen)

    def decode_AF_INET(self, bytes, prefixLen):
        afamily, port, addr = struct.unpack('@hH4s8x', bytes)
        addr = '.'.join('%d' % ord(c) for c in addr)

        mask = ~((1<<(32-prefixLen)) - 1)
        mask = struct.pack('!L', mask & 0xffffffff)
        mask = '.'.join('%d' % ord(c) for c in mask)
        return (afamily, addr, mask)
    formats[AF_INET] = decode_AF_INET

    def decode_AF_INET6(self, bytes, prefixLen):
        afamily, port, addr = struct.unpack('@hH4x16s4x', bytes)
        addr = addr.encode('hex')

        mask = ~((1L<<(128-prefixLen)) - 1)
        mask = struct.pack('!QQ', 
                    (mask>>64) & 0xffffffffffffffff,
                    (mask>> 0) & 0xffffffffffffffff)
        mask = socket.inet_ntop(AF_INET6, mask)
        return (afamily, addr, mask)
    formats[AF_INET6] = decode_AF_INET6

ctypes.SetPointerType(PSOCKET_ADDRESS, SOCKET_ADDRESS)

def linkedListIterAddresses(self, prefixLen=0):
    cur = [self]
    while cur:
        for addr in cur[0].Address.iterAddresses(prefixLen):
            yield addr
        cur = cur[0].Next


PIP_ADAPTER_UNICAST_ADDRESS = ctypes.POINTER('IP_ADAPTER_UNICAST_ADDRESS')
class IP_ADAPTER_UNICAST_ADDRESS(ctypes.Structure):
    _fields_ = [
        ('Length', ctypes.c_ulong),
        ('Flags', ctypes.c_ulong),
        ('Next', PIP_ADAPTER_UNICAST_ADDRESS),
        ('Address', SOCKET_ADDRESS),
        ('PrefixOrigin', ctypes.c_ulong),
        ('SuffixOrigin', ctypes.c_ulong),
        ('DadState', ctypes.c_ulong),
        ('ValidLifetime', ctypes.c_ulong),
        ('PreferredLifetime', ctypes.c_ulong),
        ('LeaseLifetime', ctypes.c_ulong),
        ('OnLinkPrefixLength', ctypes.c_ubyte), ]

    _iterAddresses = linkedListIterAddresses
    def iterAddresses(self):
        if ctypes.sizeof(self) == self.Length:
            prefixLen = self.OnLinkPrefixLength
        else: prefixLen = 0
        return self._iterAddresses(prefixLen)

ctypes.SetPointerType(PIP_ADAPTER_UNICAST_ADDRESS, IP_ADAPTER_UNICAST_ADDRESS)

PIP_ADAPTER_ANYCAST_ADDRESS = ctypes.POINTER('IP_ADAPTER_ANYCAST_ADDRESS')
class IP_ADAPTER_ANYCAST_ADDRESS(ctypes.Structure):
    _fields_ = [
        ('Length', ctypes.c_ulong),
        ('Flags', ctypes.c_ulong),
        ('Next', PIP_ADAPTER_ANYCAST_ADDRESS),
        ('Address', SOCKET_ADDRESS),]

    iterAddresses = linkedListIterAddresses
ctypes.SetPointerType(PIP_ADAPTER_ANYCAST_ADDRESS, IP_ADAPTER_ANYCAST_ADDRESS)

PIP_ADAPTER_MULTICAST_ADDRESS = ctypes.POINTER('PIP_ADAPTER_MULTICAST_ADDRESS')
class IP_ADAPTER_MULTICAST_ADDRESS(ctypes.Structure):
    _fields_ = [
        ('Length', ctypes.c_ulong),
        ('Flags', ctypes.c_ulong),
        ('Next', PIP_ADAPTER_MULTICAST_ADDRESS),
        ('Address', SOCKET_ADDRESS),]

    iterAddresses = linkedListIterAddresses
ctypes.SetPointerType(PIP_ADAPTER_MULTICAST_ADDRESS, IP_ADAPTER_MULTICAST_ADDRESS)

PIP_ADAPTER_DNS_SERVER_ADDRESS = ctypes.POINTER('IP_ADAPTER_DNS_SERVER_ADDRESS')
class IP_ADAPTER_DNS_SERVER_ADDRESS(ctypes.Structure):
    _fields_ = [
        ('Length', ctypes.c_ulong),
        ('Reserved', ctypes.c_ulong),
        ('Next', PIP_ADAPTER_DNS_SERVER_ADDRESS),
        ('Address', SOCKET_ADDRESS),]

    iterAddresses = linkedListIterAddresses
ctypes.SetPointerType(PIP_ADAPTER_DNS_SERVER_ADDRESS, IP_ADAPTER_DNS_SERVER_ADDRESS)

PIP_ADAPTER_PREFIX = ctypes.POINTER('IP_ADAPTER_PREFIX')
class IP_ADAPTER_PREFIX(ctypes.Structure):
    _fields_ = [
        ('Length', ctypes.c_ulong),
        ('Flags', ctypes.c_ulong),
        ('Next', PIP_ADAPTER_PREFIX),
        ('Address', SOCKET_ADDRESS),
        ('PrefixLength', ctypes.c_ulong),]

    iterAddresses = linkedListIterAddresses
ctypes.SetPointerType(PIP_ADAPTER_PREFIX, IP_ADAPTER_PREFIX)

PIP_ADAPTER_ADDRESSES = ctypes.POINTER('IP_ADAPTER_ADDRESSES')
class IP_ADAPTER_ADDRESSES(ctypes.Structure):
    MAX_ADAPTER_ADDRESS_LENGTH = 8

    _fields_ = [
        ('Length', ctypes.c_ulong),
        ('IfIndex', ctypes.c_ulong),
        ('Next', PIP_ADAPTER_ADDRESSES),
        ('AdapterName', ctypes.c_char_p),

        ('FirstUnicastAddress', PIP_ADAPTER_UNICAST_ADDRESS),
        ('FirstAnycastAddress', PIP_ADAPTER_ANYCAST_ADDRESS),
        ('FirstMulticastAddress', PIP_ADAPTER_MULTICAST_ADDRESS),
        ('FirstDnsServerAddress', PIP_ADAPTER_DNS_SERVER_ADDRESS),

        ('DnsSuffix', ctypes.c_wchar_p),
        ('Description', ctypes.c_wchar_p),
        ('FriendlyName', ctypes.c_wchar_p),

        ('PhysicalAddress', ctypes.c_char*MAX_ADAPTER_ADDRESS_LENGTH),
        ('PhysicalAddressLength', ctypes.c_ulong),

        ('Flags', ctypes.c_ulong),
        ('Mtu', ctypes.c_ulong),

        ('OperStatus', ctypes.c_ulong),

        # NOTE: SP1 and later
        ('Ipv6IfIndex', ctypes.c_ulong),
        ('ZoneIndices', ctypes.c_ulong*16),
        ('FirstPrefix', PIP_ADAPTER_PREFIX),

        # NOTE: Vista and later
        ##('TransmitLinkSpeed', ctypes.c_ulonglong),
        ##('ReceiveLinkSpeed', ctypes.c_ulonglong),
        ##('FirstWinsServerAddress', PIP_ADAPTER_WINS_SERVER_ADDRESS_LH),
        ##('FirstGatewayAddress', PIP_ADAPTER_GATEWAY_ADDRESS_LH),

        ##('Ipv4Metric', ctypes.c_ulong),
        ##('Ipv6Metric', ctypes.c_ulong),
        ##('Luid', IF_LUID),
        ##('Dhcpv4Server', SOCKET_ADDRESS),
        ##('CompartmentId', NET_IF_COMPARTMENT_ID),
        ##('NetworkGuid', NET_IF_NETWORK_GUID),
        ##('ConnectionType', ctypes.c_ulong),
        ##('NetworkGuid', NET_IF_NETWORK_GUID),
        ##('TunnelType', ctypes.c_ulong),
        ##('Dhcpv6Server', SOCKET_ADDRESS),
        ##('Dhcpv6ClientDuid', ctypes.c_ubyte*MAX_DHCPV6_DUID_LENGTH),
        ##('Dhcpv6ClientDuidLength', ctypes.c_ulong),
        ##('Dhcpv6Iaid', ctypes.c_ulong),

        # NOTE: Windows Server 208 and later
        ##('FirstDnsSuffix', PIP_ADAPTER_DNS_SUFFIX), 
        ]

    def addInteraface(self, ifMap):
        result = {}
        ifName = self.FriendlyName
        ifMap.append((ifName, result))

        result['name'] = ifName
        result['adapterName'] = self.AdapterName
        result['if_index'] = self.IfIndex
        result['desc'] = self.Description
        result['flags'] = self.Flags
        result['addrs'] = addrs = []

        macAddress = ':'.join(x.encode('hex') for x in self.PhysicalAddress[:self.PhysicalAddressLength])
        if macAddress: addrs.append(('mac', macAddress))

        addrs.extend(self.iterAddressesOf(self.FirstUnicastAddress))

    def iterAddressesOf(self, addrList):
        if addrList:
            return addrList[0].iterAddresses()
        else: return iter([])

ctypes.SetPointerType(PIP_ADAPTER_ADDRESSES, IP_ADAPTER_ADDRESSES)

iph = ctypes.windll.iphlpapi

def _if_indextoname(idx):
    raise NotImplementedError()
platform_if_indextoname = _if_indextoname

def _if_nametoindex(interfaceName):
    raise NotImplementedError()
platform_if_nametoindex = _if_nametoindex

def winxp_getifaddrs(afamily=0):
    ifMap = []
    bytecount = ctypes.c_ulong(0)
    iph.GetAdaptersAddresses(afamily, 0, None, None, ctypes.byref(bytecount))
    if 0 == bytecount.value:
        return ifMap

    count = 1 + bytecount.value/ctypes.sizeof(IP_ADAPTER_ADDRESSES)
    bytecount.value = count * ctypes.sizeof(IP_ADAPTER_ADDRESSES)
    adapterData = (IP_ADAPTER_ADDRESSES*count)()

    if 0 != iph.GetAdaptersAddresses(afamily, 0, None, adapterData, ctypes.byref(bytecount)):
        return ifMap

    entry = adapterData
    while entry:
        entry[0].addInteraface(ifMap)
        entry = entry[0].Next
    return ifMap
platform_getifaddrs = winxp_getifaddrs

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#~ Main 
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

if __name__=='__main__':
    from pprint import pprint
    pprint(platform_getifaddrs())


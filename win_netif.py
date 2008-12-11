##~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~##
##~ Copyright (C) 2002-2005  TechGame Networks, LLC.              ##
##~                                                               ##
##~ This library is free software; you can redistribute it        ##
##~ and/or modify it under the terms of the BSD style License as  ##
##~ found in the LICENSE file included with this distribution.    ##
##~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~##

__all__ = [
    'win_getifaddrs',
    'platform_getifaddrs',

    'AF_INET',
    'AF_INET6',
    'AF_LINK',
    ]

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#~ Imports 
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

import ctypes
from socket import AF_INET, AF_INET6

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#~ Definitions 
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

AF_LINK = 'mac'

IP_ADDRESS_STRING = ctypes.c_char*16
IP_MASK_STRING = IP_ADDRESS_STRING

PIP_ADDR_STRING = ctypes.POINTER('IP_ADDR_STRING')
class IP_ADDR_STRING(ctypes.Structure):
    _fields_ = [
        ('Next', PIP_ADDR_STRING),
        ('IpAddress', IP_ADDRESS_STRING),
        ('IpMask', IP_MASK_STRING),
        ('Context', ctypes.c_ushort),
        ]
    def hasValidAddress(self):
        return self.IpAddress != '0.0.0.0' 

ctypes.SetPointerType(PIP_ADDR_STRING, IP_ADDR_STRING)

PIP_ADAPTER_INFO = ctypes.POINTER('IP_ADAPTER_INFO')
class IP_ADAPTER_INFO(ctypes.Structure):
    MAX_ADAPTER_ADDRESS_LENGTH = 8
    MAX_ADAPTER_DESCRIPTION_LENGTH = 128
    MAX_ADAPTER_NAME_LENGTH = 256

    _fields_ = [
        ('Next', PIP_ADAPTER_INFO),
        ('ComboIndex', ctypes.c_ushort),
        ('AdapterNamePrefix', ctypes.c_ubyte*2),
        ('AdapterName', ctypes.c_char*(MAX_ADAPTER_NAME_LENGTH + 2)),
        ('DescriptionPrefix', ctypes.c_ubyte*2),
        ('Description', ctypes.c_char*(MAX_ADAPTER_DESCRIPTION_LENGTH + 2)),
        ('AddressLength', ctypes.c_uint),
        ('Address', ctypes.c_char*MAX_ADAPTER_ADDRESS_LENGTH),
        ('Index', ctypes.c_ushort),
        ('Type', ctypes.c_uint),
        ('DhcpEnabled', ctypes.c_uint),
        ('CurrentIpAddress', PIP_ADDR_STRING),
        ('IpAddressList', IP_ADDR_STRING),
        ('GatewayList', IP_ADDR_STRING),
        ('DhcpServer', IP_ADDR_STRING),
        ('HaveWins', ctypes.c_ulong),
        ('PrimaryWinsServer', IP_ADDR_STRING),
        ('SecondaryWinsServer', IP_ADDR_STRING),
        ('LeaseObtained', ctypes.c_ulong),
        ('LeaseExpires', ctypes.c_ulong),
    ]

    def addInteraface(self, ifMap):
        result = {}
        ifName = self.AdapterName
        ifMap.append((ifName, result))

        afamily = AF_INET
        result['name'] = ifName
        result['if_index'] = self.Index
        result['desc'] = self.Description
        result['flags'] = 0
        result['addrs'] = addrs = []
        macAddress = ':'.join(x.encode('hex') for x in self.Address[:self.AddressLength])
        if macAddress: addrs.append(('mac', macAddress))

        ipaddr = self.IpAddressList
        while ipaddr:
            if ipaddr.hasValidAddress():
                #addrs.append((ipaddr.Context, ipaddr.IpAddress, ipaddr.IpMask))
                addrs.append((afamily, ipaddr.IpAddress, ipaddr.IpMask))
            ipaddr = ipaddr.Next

ctypes.SetPointerType(PIP_ADAPTER_INFO, IP_ADAPTER_INFO)

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#~ Calls
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

iph = ctypes.windll.iphlpapi

def _if_indextoname(idx):
    raise NotImplementedError()
platform_if_indextoname = _if_indextoname

def _if_nametoindex(interfaceName):
    raise NotImplementedError()
platform_if_nametoindex = _if_nametoindex

def win_getifaddrs():
    bytecount = ctypes.c_ulong(0)
    iph.GetAdaptersInfo(None, ctypes.byref(bytecount))

    count = 1 + bytecount.value/ctypes.sizeof(IP_ADAPTER_INFO)
    bytecount.value = count * ctypes.sizeof(IP_ADAPTER_INFO)
    adapterData = (IP_ADAPTER_INFO*count)()
    iph.GetAdaptersInfo(adapterData, ctypes.byref(bytecount))

    ifMap = []
    entry = adapterData
    while entry:
        entry[0].addInteraface(ifMap)
        entry = entry[0].Next
    return ifMap
platform_getifaddrs = win_getifaddrs

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#~ Main 
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

if __name__=='__main__':
    from pprint import pprint
    pprint(platform_getifaddrs())


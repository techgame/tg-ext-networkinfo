#!/usr/bin/env python
##~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~##
##~ Copyright (C) 2002-2006  TechGame Networks, LLC.              ##
##~                                                               ##
##~ This library is free software; you can redistribute it        ##
##~ and/or modify it under the terms of the BSD style License as  ##
##~ found in the LICENSE file included with this distribution.    ##
##~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~##

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#~ Imports 
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

import os
from TG.gccxml.codeAnalyzer import CodeAnalyzer
from TG.gccxml.xforms.ctypes import AtomFilterVisitor, CCodeGenContext
from TG.gccxml.xforms.ctypes import utils

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#~ Definitions 
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

analyzer = CodeAnalyzer(
        inc=['.'],
        src=['src/genNetTools.c'], 
        baseline=['src/baseline.c'])

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class FilterVisitor(AtomFilterVisitor):
    selectNames = set([
            'if_nametoindex', 
            'if_indextoname',
            'getifaddrs',
            'freeifaddrs',
            ])

    def onFunction(self, item):
        if not item.extern: return
        if item.name in self.selectNames:
            self.select(item)

    def onPPInclude(self, item):
        if 0:
            print '"%s" includes "%s"' % (item.file.name, item.filename)

    def onPPDefine(self, item):
        if item.ident in self.filterConditionals:
            return

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    filterConditionals = set([
        ])
    def onPPConditional(self, item):
        if not item.isOpening():
            return 
        if item.body in self.filterConditionals:
            return

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#~ Main 
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def main():
    root = analyzer.loadModel()
    context = CCodeGenContext(root)
    context.atomFilter = FilterVisitor()

    ciFilesByName = dict((os.path.basename(f.name), f) for f in context if f)

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # setup imports

    for ciFile in ciFilesByName.itervalues():
        ciFile.importAll('_ctypes_nettools')
        ciFile.footer += '\ncleanupNamespace(globals())\n'

    socket = ciFilesByName.pop('socket.h')
    if_ = ciFilesByName['if.h']
    ifaddrs = ciFilesByName['ifaddrs.h']
    ifaddrs.prependFiles = [socket]

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # write output files

    context.outputPath = 'out'
    print
    print "Writing out ctypes code:"
    print "========================"
    for ciFile in ciFilesByName.values():
        print 'Writing:', ciFile.filename
        ciFile.writeToFile()
        print 'Done Writing:', ciFile.filename
        print
    print

    utils.includeSupportIn(context.getOutputFilename('_ctypes_support.py'), copySource=False)

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

if __name__=='__main__':
    main()


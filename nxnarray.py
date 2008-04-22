#!/usr/bin/env python

"""
-------------------------------------------
             Class NxNArray

What:

    NxNArray class written specifically for use with the
    HTMLTable class

Why:

    I needed something that could store data in an NxN array
    and dynamically grow the array


    Current-Version: $Revision: 1.3 $
    Last update:     $Date: 2003/02/27 22:37:20 $

    Home-Page:               http://pasko.net/PyHtmlTable
    Primary-Site:            http://pasko.net/PyHtmlTable

    Written and debugged under Python 2.2.2 by Joe Pasko
"""

import copy


class NxNArray(object):

    maxX    = 0
    maxY    = 0
    storage = []
    filltype = ''

    def __init__(self, x=1, y=1, fill=None):
        rowarr = []
        colarr = []
        newarr = []
        self.maxX = x
        self.maxY = y

        if fill == None:
            self.filltype = ''
        else:
            self.filltype = fill

        for i in range(y):
            rowarr.append(self.filltype)

        for j in range(x):
            newarr =  copy.copy(rowarr)
            colarr.append(newarr)

        self.storage = colarr

    def get_arr(self):
        return (self.storage)

    def add_col(self):
        for f in range( self.maxX ):
            self.storage[ f ].append(self.filltype)
        self.maxY = self.maxY +1

    def add_row(self):
        nrow = []
        for f in range(self.maxY):
            nrow.append(self.filltype)
        self.storage.append(copy.copy(nrow))
        self.maxX = self.maxX + 1

    def get_cell(self, x, y):
        if x > self.maxX or y > self.maxY:
            return None
        return self.storage[x][y]

    def set_cell(self, x, y, data):
        if x >= self.maxX:
            for i in range(self.maxX - 1 , x):
                self.add_row()
        if y >= self.maxY:
            for i in range(self.maxY - 1 , y):
                self.add_col()
        self.storage[x][y] = data

    def get_max_row(self):
        return self.maxX - 1

    def get_max_col(self):
        return self.maxY - 1

    def get_num_rows(self):
        return self.maxX

    def get_num_cols(self):
        return self.maxY


def main():
    b=NxNArray(1,4)
    print b.get_arr()
    print "MAX", b.get_max_row(), b.get_max_col()
    b.add_col()
    print "MAX", b.get_max_row(), b.get_max_col()
    b.add_row()
    print "MAX", b.get_max_row(), b.get_max_col()
    print b.get_arr()
    b.set_cell(1,8,"NEW")
    print b.get_arr()


if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
#
# nxnarray - part of the CRS-o-matic project
# Copyright (C) 2003  Joe Pasko
# Copyright (C) 2008  Darwin M. Bautista
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""
This module and its sole class, NxNArray, was forked from version 1.3 of
the twodarr class and module written by Joe Pasko (http://pasko.net/PyHtmlTable/).
"""

from copy import copy


class NxNArray(object):

    """A dynamic NxN array

    NxNArray is a 2-dimensional array that can grow dynamically.
    """

    def __init__(self, rows=1, cols=1, fill=""):
        self._rows = rows
        self._cols = cols
        self._fill = fill
        row = []
        col = []
        for i in range(cols):
            row.append(self._fill)
        for i in range(rows):
            col.append(copy(row))
        self._array = col

    @property
    def array(self):
        """Contents of the array"""
        return self._array

    @property
    def cols(self):
        """Current number of columns"""
        return self._cols

    @property
    def rows(self):
        """Current number of rows"""
        return self._rows

    @property
    def fill(self):
        """Fill type"""
        return self._fill

    def add_col(self):
        for i in range(self._rows):
            self._array[i].append(self._fill)
        self._cols += 1

    def add_row(self):
        row = []
        for i in range(self._cols):
            row.append(self._fill)
        self._array.append(row)
        self._rows += 1

    def get_cell(self, row, col):
        try:
            return self._array[row][col]
        except IndexError:
            return

    def set_cell(self, row, col, data):
        for i in range(row - self._rows + 1):
            self.add_row()
        for i in range(col - self._cols + 1):
            self.add_col()
        self._array[row][col] = data


def main():
    b = NxNArray(1, 4)
    print b.array
    print "MAX", b.rows - 1, b.cols - 1
    b.add_col()
    print "MAX", b.rows - 1, b.cols - 1
    b.add_row()
    print "MAX", b.rows - 1, b.cols - 1
    print b.array
    b.set_cell(1, 8, 'NEW')
    print b.array


if __name__ == "__main__":
    main()

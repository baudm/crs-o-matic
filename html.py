# -*- coding: utf-8 -*-
#
# html - A simplistic HTML Table generator
# Copyright (C) 2011  Darwin M. Bautista
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

class Cell(object):

    def __init__(self, data, attrs=None, th=True):
        self._data = str(data)
        self._attrs = attrs or {}
        self._tag = 'th' if th else 'td'

    @property
    def html_list(self):
        code = ['<', self._tag]
        for k, v in self._attrs.iteritems():
            attr = ' %s="%s"' % (k, v)
            code.append(attr)
        code.extend(['>', self._data, '</', self._tag, '>'])
        return code


class Table(object):

    def __init__(self, cols, rows, attrs=None):
        self._attrs = attrs or {}
        data = []
        for i in xrange(rows):
            row = [None] * cols
            data.append(row)
        self._data = data

    def set_header_row(self, row):
        self._data[0] = map(Cell, row)

    def set_cell(self, col, row, data, attrs=None):
        self._data[row][col] = Cell(data, attrs, False)

    def set_cell_attrs(self, col, row, attrs):
        self._data[row][col]._attrs = attrs

    @property
    def html(self):
        code = ['<table']
        for k, v in self._attrs.iteritems():
            attr = ' %s="%s"' % (k, v)
            code.append(attr)
        code.append('>\n')
        rowspans = {}
        for row in self._data:
            code.append('<tr>')
            for idx, cell in enumerate(row):
                if rowspans.get(idx, 0) > 1:
                    rowspans[idx] -= 1
                    continue
                if cell is None:
                    code.append('<td>&nbsp;</td>')
                else:
                    code.extend(cell.html_list)
                    rowspan = cell._attrs.get('rowspan', 0)
                    if rowspan:
                        rowspans[idx] = rowspan
            code.append('</tr>\n')
        code.append('</table>')
        return ''.join(code)

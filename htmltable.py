# $Id$
#
# htmltable - part of the CRS-o-matic project
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
This module and its sole class, HTMLTable, was forked from version 1.13 of
the PyHtmlTable class and module written by Joe Pasko (http://pasko.net/PyHtmlTable/).
"""

from nxnarray import NxNArray


class HTMLTable(object):

    """A Pythonic interface for HTML table manipulation and generation

    The tables generated by HTMLTable is XHTML 1.0-compliant.
    """

    def __init__(self, rows, cols, attrs={}):
        self.attrs = attrs
        self._htcells = NxNArray(rows, cols, '&nbsp;')
        self._cell_type = {} # th, td indexed by (row,col) tuple
        self._default_cell_attrs = {}
        self._cell_attrs = {}
        self._col_attrs = {}
        self._row_attrs = {}
        # On data insertion, should we append or overwrite cell attributes?
        # Defaults to append.
        self.overwriteattrs = False
        self._span_text = '<!-- spanned cell -->'

    def _get_attrs(self):
        return self._attrs

    def _set_attrs(self, attrs):
        self._attrs = attrs

    def _get_rows(self):
        # Don't use the NxNArray.rows property
        return self._htcells._rows

    def _get_cols(self):
        # Don't use the NxNArray.cols property
        return self._htcells._cols

    def _get_default_cell_attrs(self):
        return self._default_cell_attrs

    def _set_default_cell_attrs(self, attrs):
        self._default_cell_attrs = attrs

    # Class properties
    attrs = property(_get_attrs, _set_attrs, doc='Table attributes')
    rows = property(_get_rows, doc='Current number of rows')
    cols = property(_get_cols, doc='Current number of columns')
    default_cell_attrs = property(_get_default_cell_attrs, _set_default_cell_attrs, doc="Default cell attributes")

    @staticmethod
    def _get_tag_html(tag, attrs):
        html = ['<', tag]
        if attrs and attrs is not None:
            for key, val in attrs.iteritems():
                attr = ' %s="%s"' % (key.lower(), val)
                html.append(attr)
        html.append('>')
        return "".join(html)

    @staticmethod
    def _has_only_rowcolsp_attrs(attrs):
        if not attrs or attrs is None:
            return False
        count = 0
        if 'colspan' in attrs:
            count += 1

        if 'rowspan' in attrs:
            count += 1

        if len(attrs) > count:
            return False
        else:
            return True

    def _get_cell_html(self, row, col):
        data = self.get_cell_data(row, col)
        # Must be a spanned cell, don't print anything
        if data == self._span_text:
            return
        ctype = self.get_cell_type(row, col)
        cattr = self.get_cell_attrs(row, col)
        cdefattr = self._default_cell_attrs
        end_tag = '</%s>' % ctype

        if cattr is not None:
            # If we only have a single rowspan/colspan attribute, merge it with
            # the default cell attributes IF NO OTHER ATTRIBUTES EXIST FOR THAT CELL
            if cdefattr and HTMLTable._has_only_rowcolsp_attrs(cattr):
                cattr.update(cdefattr)
            start_tag = HTMLTable._get_tag_html(ctype, cattr)
        else:
            start_tag = HTMLTable._get_tag_html(ctype, cdefattr)

        html = [start_tag]
        html.append(data)
        html.append(end_tag)
        return "".join(html)

    def _adjust_dbl_indx_dict_rows_down(self, indict, add_after_this_row):
        """Run through the cells and adjust the tuple indexes down"""
        for i in range(self.rows, add_after_this_row, -1):
            for key, val in indict.iteritems():
                row, col = map(int, key)
                if row != i:
                    continue
                indict[(row + 1, col)] = val
                del indict[(row, col)]

    def _adjust_dict_rows_down(self, indict, add_after_this_row):
        """Run through the cells and adjust the tuple index down"""
        if add_after_this_row == self.rows - 1:
            return
        elif add_after_this_row == -1:
            stop = 0
        else:
            stop = add_after_this_row

        for i in range(self.rows, stop, -1):
            if (i - 1) in indict:
                val = indict[i - 1]
                indict[i] = val
                del indict[i - 1]

    def _adjust_dict_cols_right(self, indict, add_after_this_col):
        if add_after_this_col == self.cols - 1:
            return
        elif add_after_this_col == -1:
            stop = 0
        else:
            stop = add_after_this_col

        for i in range(self.cols, stop, -1):
            if (i - 1) in indict:
                val = indict[i - 1]
                indict[i] = val
                del indict[i - 1]

    def _adjust_dbl_indx_dict_cols_right(self, indict, shift_after_this_col):
        for i in range(self.cols, shift_after_this_col, -1):
            for key, val in indict.iteritems():
                row, col = map(int, key)
                if col != i:
                    continue
                indict[(row, col + 1)] = val
                del indict[(row, col)]

    def _adjust_2d_array_rows_down(self, inarr, add_after_this_row):
        deffill = self._htcells.fill
        # Adding to bottom, no need to move data
        if self.rows - 1 == add_after_this_row:
            i = self.rows
            for j in range(self.cols):
                inarr.set_cell(i, j, deffill)
        else:
            # Shift data
            for i in range(self.rows, add_after_this_row + 1, -1):
                for j in range(self.cols):
                    data2mv = inarr.get_cell(i - 1, j)
                    inarr.set_cell(i, j, data2mv)
                    inarr.set_cell(i - 1, j, deffill)

    def _adjust_2d_array_cols_right(self, inarr, add_after_this_col):
        deffill = self._htcells.fill
        # Adding cols to right edge no need for data moving
        if self.cols - 1 == add_after_this_col:
            i = self.cols
            for j in range(self.rows):
                inarr.set_cell(j, i, deffill)
        else:
            # Shift data
            for i in range(self.cols, add_after_this_col + 1, -1):
                for j in range(self.rows):
                    data2mv = inarr.get_cell(j, i - 1)
                    inarr.set_cell(j, i, data2mv)
                    inarr.set_cell(j, i - 1, deffill)

    def add_array_to_row(self, row, col, inarr, attrs=None):
        """Adds list of data specified by inarr to table object
           starting at row,col

           Optionally specify attributes to set on cells being added
           by defining the attrs dictionary

           Note: Cell attribute insertion can be additive or overwriting depending
                 on the value of self.overwriteattrs

                 Default is to append new attributes
        """
        for i in range(len(inarr)):
            self.set_cell_data(row, col + i, inarr[i], attrs)

    def add_array_to_col(self, row, col, inarr, attrs=None):
        """Adds list of data specified by inarr to table object
           starting at row,col

           Optionally specify attributes to set on cells being added
           by defining the attrs dictionary

           Note: Cell attribute insertion can be additive or overwriting depending
                 on the value of self.overwriteattrs

                 Default is to append new attributes
        """
        for i in range(len(inarr)):
            self.set_cell_data(row + i, col, inarr[i], attrs)

    def set_cell_colspan(self, row, col, numcells):
        """Sets colspan starting at rowidx, colidx spanning numcells
           (Remember rows,cols start at 0,0)
        """
        for i in range(col + 1, col + numcells):
            self.set_cell_data(row, i, self._span_text)
        self.set_cell_attrs(row, col, {'colspan': numcells})

    def set_cell_rowspan(self, row, col, numcells):
        """Sets rowspan starting at rowidx, colidx spanning numcells
           (Remember rows,cols start at 0,0)
        """
        for i in range(row + 1, row + numcells):
            self.set_cell_data(i, col, self._span_text)
        self.set_cell_attrs(row, col, {'rowspan': numcells})

    def get_col_attrs(self, col):
        """Presently unused"""
        if col in self._col_attrs:
            return self._col_attrs[col]

    def set_col_attrs(self, col, attrs):
        """Presently unused"""
        if col < self.cols:
            self._col_attrs[col] = attrs

    def get_row_attrs(self, row):
        """Returns attribute string for given rowidx which
           was set by set_row_attrs
        """
        if row in self._row_attrs:
            return self._row_attrs[row]

    def set_row_attrs(self, row, attrs):
        """Sets attributes for give rowidx

           attrs is a dictionary of key=val pairs
           {'bgcolor':'black'} translates to <tr bgcolor="black">
        """
        if row < self.rows:
            self._row_attrs[row] = attrs

    def clear_row_attrs(self, row):
        """Clear row attributes"""
        if row in self._row_attrs:
            del self._row_attrs[row]

    def get_cell_attrs(self, row, col):
        """Returns attributes set for specific cell at rowidx colidx"""
        if (row, col) in self._cell_attrs:
            return self._cell_attrs[(row, col)]

    def set_cell_attrs(self, row, col, attrs):
        """Sets cell attributes for cell at rowidx, colidx

           attrs is a dictionary of key=val pairs

           {'bgcolor':'black', 'width':200} yields

           <td bgcolor="black" width="200"> on output
        """
        if row >= self.rows or col >= self.cols:
            return
        if (row, col) not in self._cell_attrs or self.overwriteattrs:
            self._cell_attrs[(row, col)] = attrs
        else:
            self._cell_attrs[(row, col)].update(attrs)

    def clear_cell_attrs(self, row, col):
        """Clear cells attributes"""
        if (row, col) in self._cell_attrs:
            del self._cell_attrs[(row, col)]

    def get_cell_type(self, row, col):
        """Returns Celltypes which is td or th"""
        if row >= self.rows or col >= self.cols:
            return
        elif (row, col) in self._cell_type:
            return self._cell_type[(row, col)]
        else:
            return 'td'

    def set_cell_type(self, row, col, ctype):
        """Celltypes can be td or th"""
        if row < self.rows and col < self.cols:
            self._cell_type[(row, col)] = ctype

    def get_cell_data(self, row, col):
        """Get cells stored data values
           Return an &nbsp if cell is None
        """
        data = self._htcells.get_cell(row, col)
        if data is None:
            return self._htcells.fill
        else:
            return data

    def set_cell_data(self, row, col, data, attrs=None):
        """Puts data into cell at rowidx, colidx
           Takes optional attribute dictionary for cell
        """
        # Force casting as a string
        if data and data is not None:
            data = str(data)
        else:
            data = self._htcells.fill

        self._htcells.set_cell(row, col, data)

        if attrs is not None:
            self.set_cell_attrs(row, col, attrs)

    def add_row(self, row):
        """Adds row to table after specified rowidx.
           Adding row at rowidx -1 adds row to top of table
        """
        if row > self.rows:
            row = self.rows
        # Update attrs for rowattr, cellattr, then call array updater,
        if row != self.rows - 1: # Adding row to bottom, no need to move attrs
            self._adjust_dict_rows_down(self._row_attrs, row)
            self._adjust_dbl_indx_dict_rows_down(self._cell_attrs, row)
            self._adjust_dbl_indx_dict_rows_down(self._cell_type, row)
        self._adjust_2d_array_rows_down(self._htcells, row)

    def add_col(self, col):
        """Adds col to table after specified colidx
           Adding col at colidx -1 adds col to left of table
        """
        if col > self.cols:
            col = self.cols
        # Update attrs for colattr, cellattr, then call array updater,
        if col != self.cols - 1: # If Adding col to right,skip moving attrs
            self._adjust_dict_cols_right(self._row_attrs, col)
            self._adjust_dbl_indx_dict_cols_right(self._cell_attrs, col)
            self._adjust_dbl_indx_dict_cols_right(self._cell_type, col)
        self._adjust_2d_array_cols_right(self._htcells, col)

    def return_html(self):
        """Returns html table as string"""
        table = HTMLTable._get_tag_html('table', self._attrs)
        html = [table, '\n']
        for row in range(self.rows):
            attrs = self.get_row_attrs(row)
            tr = HTMLTable._get_tag_html('tr', attrs)
            html.append(tr)
            for col in range(self.cols):
                cell = self._get_cell_html(row, col)
                if cell: # Spanned cells return
                    html.append(cell)
            html.append('</tr>\n')
        html.append('</table>')
        return "".join(html)


def main():
    print 'Content-Type: text/html\n\n'
    print '<html><head></head><body bgcolor="white">\n\n'
    print '<b> 2 by 2 table</b>'

    t = HTMLTable(2, 2, {'width': '400', 'border': 2, 'bgcolor': 'white'})

    t.set_cell_data(0, 0, 'T1 Cell 00')
    t.set_cell_data(0, 1, 'T1 Cell 01')
    t.set_cell_data(1, 0, 'T1 Cell 01')
    t.set_cell_data(1, 1, 'T1 Cell 11')

    t.set_cell_attrs(0, 0, {'bgcolor': 'red', 'width': 100})
    t.set_cell_attrs(1, 1, {'bgcolor': 'red'})
    print t.return_html()

    print '<b>Dynamically grow outside initial table boundaries by setting cells outside current boundaries </b>'

    t.set_cell_data(2, 0, 'T1 Cell 20') # Grow outside initial bounds
    t.set_cell_data(2, 1, 'T1 Cell 21')
    print t.return_html()

    print '<p><b>Explicitly add row after row index 1</b>'

    t.add_row(1) # Add a row after row index 1
    print t.return_html()

    print '<p><b>Explicitly adding col after column index 1</b>'

    t.add_col(1) # Add a col after col index 1
    print t.return_html()

    print '<hr><b>AFTER  row and col SPANNING</b>'
    t.set_cell_rowspan(1, 0, 2) # Span cell at index row 1,col 0, make 2 high
    t.set_cell_colspan(1, 1, 2) # colSpan cell at index row 1, col 1, make 2 wide

    print t.return_html()

    print '<hr><b>Embed in new table</b>'

    htmlstr = t.return_html()

    nt = HTMLTable(1, 4, {'Width': '800', 'Border': 2, 'BGcolor': 'green'})
    nt.set_cell_data(0, 0, 'Cell th....text left')
    nt.set_cell_data(0, 1, 'Text right')
    nt.set_cell_data(0, 2, htmlstr)
    nt.set_cell_attrs(0, 0, {'bgcolor': 'blue', 'width': 200, 'align': 'left'})
    nt.set_cell_attrs(0, 1, {'width': 200, 'align': 'right'})
    nt.set_cell_type(0, 0, 'th')
    print nt.return_html()
    print '</body></html>'


if __name__ == "__main__":
    main()

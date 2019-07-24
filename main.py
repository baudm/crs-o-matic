# -*- coding: utf-8 -*-
#
# crs-o-matic - CRS Schedule Generator
# Copyright (C) 2008-2014  Darwin M. Bautista
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

import operator
from functools import reduce

from flask import Flask, render_template, request

import crs
from filters import filters


SEM, TERM = crs.get_current_term()


app = Flask(__name__)
app.register_blueprint(filters)


def _search(queries):
    desired = {
        'reg': [],
        'extra': [],
        'none': [],
        'units': 0,
        'matches': 0,
        'possible': 0
    }
    classes = []
    for s in queries:
        s = s.split(':', 1)
        if len(s) == 2:
            course_num, filters = s
            filters = [i.strip() for i in filters.split(',')]
        else:
            course_num = s[0]
            filters = []
        course_num = ' '.join(course_num.split())
        c = crs.search(course_num, TERM, filters, True)
        if c:
            classes.append(c)
            if not c[0].name.startswith('CWTS') and not c[0].name.startswith('PE '):
                desired['units'] += c[0].credit
                desired['reg'].append(c[0])
            else:
                desired['extra'].append(c[0])
        else:
            c = crs.Class(name=course_num)
            desired['none'].append(c)
    if classes:
        desired['matches'] = len(classes)
        desired['possible'] = reduce(operator.mul, [len(c) for c in classes])
    return desired, classes


@app.route('/')
def get():
    return render_template('index.html', sem=SEM)


@app.route('/', methods=['POST'])
def post():
    searchkey = request.form['searchkey']
    terms = [s for s in searchkey.split('\r\n') if s]
    desired, classes = _search(terms)
    scheds = crs.get_schedules(*classes) if classes else None
    return render_template('index.html', sem=SEM, desired=desired, scheds=scheds)


if __name__ == '__main__':
    # For debugging
    app.run(host='127.0.0.1', port=8080, debug=True)

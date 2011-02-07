# -*- coding: utf-8 -*-
#
# crs-o-matic - CRS Schedule Generator
# Copyright (C) 2008-2011  Darwin M. Bautista
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

import cgi
import os.path
import operator

from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app
template.register_template_library('filters')

import crs


SEM = 'Second Semester AY 2010-2011'


class MainPage(webapp.RequestHandler):

    @staticmethod
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
            c = crs.search(course_num, filters)
            if c:
                classes.append(c)
                if not c[0].name.startswith('CWTS') and not c[0].name.startswith('PE '):
                    desired['units'] += c[0].units
                    desired['reg'].append(c[0])
                else:
                    desired['extra'].append(c[0])
            else:
                c = crs.Class()
                c.name = course_num
                desired['none'].append(c)
        if classes:
            desired['matches'] = len(classes)
            desired['possible'] = reduce(operator.mul, [len(c) for c in classes])
        return desired, classes

    def _render(self, data):
        path = os.path.join(os.path.dirname(__file__), 'index.html')
        self.response.out.write(template.render(path, data))

    def get(self):
        data = {
            'sem': SEM
        }
        self._render(data)

    def post(self):
        searchkey = cgi.escape(self.request.get('searchkey'))
        terms = [s for s in searchkey.split('\r\n') if s]
        # Sort search queries to have the same output each and every time (for the same input).
        terms.sort()
        desired, classes = self._search(terms)
        scheds = crs.get_schedules(*classes) if classes else None

        data = {
            'desired': desired,
            'scheds': scheds,
            'sem': SEM
        }
        self._render(data)


application = webapp.WSGIApplication([('/', MainPage)], debug=True)


def main():
    run_wsgi_app(application)


if __name__ == "__main__":
    main()

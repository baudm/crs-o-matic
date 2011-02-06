import cgi
import math
import os.path
import operator

from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app

import crs
from htmltable import HTMLTable


SEM = 'Second Semester AY 2010-2011'


class MainPage(webapp.RequestHandler):

    @staticmethod
    def _search(queries):
        desired = {
            'reg': [],
            'extra': [],
            'none': [],
            'units': 0
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
        return desired, classes

    @staticmethod
    def _gen_tables(classes):
        scheds = crs.get_schedules(*classes)
        tables = []
        for s in scheds:
            table = HTMLTable(len(s), 2, {'class': 'schedule', 'cellpadding': 0, 'cellspacing': 0})
            ctr = 0
            table.set_cell_attrs(0, 1, {'class': 'probability'})
            for header in ('Class', 'Prob.'):
                table.set_cell_type(0, ctr, 'th')
                table.set_cell_data(0, ctr, header)
                ctr += 1

            ctr = 1
            prob_list = []
            for c in s:
                try:
                    prob_class = float(c.stats[0]) / c.stats[2]
                except ZeroDivisionError:
                    prob_class = 1.0

                if prob_class > 1.0:
                    prob_class = 1.0

                prob_list.append(prob_class)

                table.set_cell_data(ctr, 0, " ".join([c.name, c.section]))
                table.set_cell_data(ctr, 1, "%.2f%%" % (100 * prob_class, ))
                ctr += 1

            prob = sum(prob_list)/len(classes)
            stdev = math.sqrt(sum(map(lambda x: (x-prob)*(x-prob), prob_list))/len(classes))

            table.set_cell_data(ctr, 0, 'Mean')
            table.set_cell_data(ctr, 1, "%.2f%%" % (100 * prob, ))
            table.set_cell_data(ctr + 1, 0, 'Std. Dev.')
            table.set_cell_data(ctr + 1, 1, "%.2f%%" % (100 * stdev, ))
            for i in range(ctr, ctr + 2):
                table.set_cell_attrs(i, 0, {'class': 'highlight'})
                table.set_cell_attrs(i, 1, {'class': 'highlight'})
            tables.append((s, table))
        return tables

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

        if classes:
            p = reduce(operator.mul, [len(a) for a in classes])
            tables = self._gen_tables(classes)
        else:
            p = 0
            tables = None

        data = {
            'desired': desired,
            'p': p,
            'tables': tables,
            'sem': SEM
        }
        self._render(data)


application = webapp.WSGIApplication([('/', MainPage)], debug=True)


def main():
    run_wsgi_app(application)


if __name__ == "__main__":
    main()

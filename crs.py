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

import math
import time
import urllib
import urllib2
from BeautifulSoup import BeautifulSoup, SoupStrainer
from htmltable import HTMLTable
# sets module is deprecated since Python 2.6
try:
    set
except NameError:
    from sets import Set as set
try:
    from itertools import product
except ImportError:
    # Equivalent itertools.product() implementation copied from
    # http://docs.python.org/library/itertools.html#itertools.product
    def product(*args, **kwds):
        # product('ABCD', 'xy') --> Ax Ay Bx By Cx Cy Dx Dy
        # product(range(2), repeat=3) --> 000 001 010 011 100 101 110 111
        pools = map(tuple, args) * kwds.get('repeat', 1)
        result = [[]]
        for pool in pools:
            result = [x+[y] for x in result for y in pool]
        for prod in result:
            yield tuple(prod)


AYSEM = '120102'
URI = 'http://crs.upd.edu.ph/schedule'


def _strftime(fmt, t):
    return time.strftime(fmt, (1900, 1, 1, t[0], t[1], 0, 0, 1, -1))


class Time(tuple):

    def __new__(cls, hour, minute):
        return super(Time, cls).__new__(cls, (hour, minute))

    def __repr__(self):
        return _strftime('%I:%M%P', self)


class Interval(tuple):

    def __new__(cls, start, end):
        return super(Interval, cls).__new__(cls, (start, end))

    def __repr__(self):
        return '<%s-%s>' % self


class Class(object):

    def __init__(self, code=None, name=None, section=None):
        self.code = code
        self.name = name
        self.section = section
        self.credit = None
        self.schedule = None
        self.stats = None

    def __repr__(self):
        return "<%s %s>" % (self.name, self.section)


class ScheduleConflict(Exception):
    pass


class Schedule(list):

    def __init__(self):
        self.times = []

    def _check_conflicts(self, class_):
        for c in self:
            for day in c.schedule:
                if not day in class_.schedule:
                    continue
                for dur in c.schedule[day]:
                    for dur_new in class_.schedule[day]:
                        if (dur_new[0] <= dur[0] and dur_new[1] >= dur[1]) or \
                           (dur_new[0] >= dur[0] and dur_new[1] <= dur[1]) or \
                           dur[0] < dur_new[0] < dur[1] or dur[0] < dur_new[1] < dur[1]:
                            raise ScheduleConflict("%s conflicts with %s" % (class_, c))

    def append(self, class_):
        self._check_conflicts(class_)
        super(Schedule, self).append(class_)
        for day in class_.schedule:
            for duration in class_.schedule[day]:
                self.times += duration

    def get_table(self):
        self.times = list(set(self.times))
        self.times.sort()
        table = HTMLTable(len(self.times), 7, {'class': 'schedule', 'cellpadding': 0, 'cellspacing': 0})
        day_map = {'M': 1, 'T': 2, 'W': 3, 'Th': 4, 'F': 5, 'S': 6}
        for i, header in enumerate(('Time', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday')):
            table.set_cell_type(0, i, 'th')
            table.set_cell_data(0, i, header)
        table.set_cell_attrs(0, 0, {'class': 'time'})
        for idx in range(len(self.times) - 1):
            table.set_cell_data(idx+1, 0, "-".join([_strftime("%I:%M%P", self.times[idx]), _strftime("%I:%M%P", self.times[idx+1])]))
        for class_ in self:
            for day in class_.schedule:
                day_i = day_map[day]
                for duration in class_.schedule[day]:
                    start, end = duration
                    s = self.times.index(start)
                    e = self.times.index(end)
                    if (e - s) != 1:
                        table.set_cell_rowspan(s + 1, day_i, e - s)
                    table.set_cell_attrs(s + 1, day_i, {'class': 'highlight'})
                    table.set_cell_data(s + 1, day_i, class_.name)
        return table.return_html()

    def get_stats(self):
        table = HTMLTable(len(self), 2, {'class': 'schedule', 'cellpadding': 0, 'cellspacing': 0})
        table.set_cell_attrs(0, 1, {'class': 'probability'})
        for i, header in enumerate(('Class', 'Prob.')):
            table.set_cell_type(0, i, 'th')
            table.set_cell_data(0, i, header)
        prob_list = []
        ctr = 1
        for c in self:
            try:
                prob_class = float(c.stats[0]) / c.stats[2]
            except ZeroDivisionError:
                prob_class = 1.0
            # Normalize
            if prob_class > 1.0:
                prob_class = 1.0
            prob_list.append(prob_class)
            table.set_cell_data(ctr, 0, " ".join([c.name, c.section]))
            table.set_cell_data(ctr, 1, "%.2f%%" % (100 * prob_class, ))
            ctr += 1
        prob = sum(prob_list)/len(self)
        stdev = math.sqrt(sum(map(lambda x: (x-prob)*(x-prob), prob_list))/len(self))
        table.set_cell_data(ctr, 0, 'Mean')
        table.set_cell_data(ctr, 1, "%.2f%%" % (100 * prob, ))
        table.set_cell_data(ctr + 1, 0, 'Std. Dev.')
        table.set_cell_data(ctr + 1, 1, "%.2f%%" % (100 * stdev, ))
        for i in range(ctr, ctr + 2):
            table.set_cell_attrs(i, 0, {'class': 'highlight'})
            table.set_cell_attrs(i, 1, {'class': 'highlight'})
        return table.return_html()


class ClassParser(object):

    def __init__(self, course_num, pe=None, filters=()):
        self.course_num = course_num.lower()
        self.pe = pe
        if filters:
            self.whitelist = [i.upper() for i in filters if not i.startswith('!')]
            self.blacklist = [i.upper().lstrip('!') for i in filters if i.startswith('!')]
        else:
            self.whitelist = []
            self.blacklist = []

    def feed(self, data):
        parents = {}
        children = []
        tbody = SoupStrainer('tbody')
        soup = BeautifulSoup(data, parseOnlyThese=tbody)
        for tr in soup.findAll('tr'):
            try:
                code, name, credit, schedule, stats, remarks = tr.findAll('td')
            except ValueError:
                continue
            kls = Class(code=code.string)
            # name, section
            name = name.renderContents().strip().split('<br')[0]
            kls.name, kls.section = name.rsplit(' ', 1)
            kls.name = ' '.join(kls.name.split())
            # Filter classes based on the course number
            if self.pe is None:
                if kls.name.lower() != self.course_num:
                    continue
            else:
                if kls.name.lower() != self.course_num + ' ' + self.pe:
                    continue
            # credit
            kls.credit = float(credit.string)
            # schedule
            schedule = schedule.renderContents().strip().split('<br')[0]
            kls.schedule = self._parse_sched(schedule)
            # stats
            try:
                kls.stats = tuple([int(i.strip('/')) for i in stats.renderContents().\
                    replace('<strong>', '').replace('</strong>', '').split() if i != '/'])
            except ValueError:
                continue
            if ' lab ' in schedule or  ' disc ' in schedule:
                children.append(kls)
            else:
                parents[kls.section] = kls
        return self._postprocess(parents, children)

    def _filter_class(self, kls):
        """Filter based on section preferences"""
        return not any(map(kls.section.startswith, self.blacklist)) and \
            (not self.whitelist or any(map(kls.section.startswith, self.whitelist)))

    def _postprocess(self, parents, children):
        if children:
            results = filter(self._filter_class, children)
            # Merge schedules with the respective parent
            if parents:
                for kls in results:
                    try:
                        parent = filter(kls.section.startswith, parents.keys())[0]
                    except IndexError:
                        for i in reversed(range(1, len(kls.section))):
                            for parent in parents:
                                if kls.section[:i] in parent:
                                    break
                            if kls.section[:i] in parent:
                                break
                    # Choose the non-zero credit
                    kls.credit = kls.credit or parents[parent].credit
                    self._merge_sched(kls.schedule, parents[parent].schedule)
        else:
            results = filter(self._filter_class, parents.values())
        return results

    @staticmethod
    def _parse_time(data):
        start, end = data.upper().split('-')

        if not end.endswith('M'):
            # Append 'M'.
            end = "".join([end, 'M'])

        for fmt in ['%I%p', '%I:%M%p']:
            try:
                time_end = Time(*time.strptime(end, fmt)[3:5])
            except ValueError:
                continue
            else:
                break
        # Get the int value of the hours.
        start_hour = int(start.split(':')[0].rstrip('APM'))
        end_hour = int(_strftime('%I', time_end))

        if start.endswith('A') or start.endswith('P'):
            # Append 'M'.
            start = "".join([start, 'M'])
        elif start_hour <= end_hour and end_hour != 12:
            # Append the same am/pm to the start time.
            start = "".join([start, _strftime("%P", time_end)])

        for fmt in ['%I', '%I:%M', '%I%p', '%I:%M%p']:
            try:
                time_start = Time(*time.strptime(start, fmt)[3:5])
            except ValueError:
                continue
            else:
                break
        return Interval(time_start, time_end)

    @staticmethod
    def _parse_days(data):
        # Replace 'Th' by 'th' to avoid confusion with 'T'.
        data = data.replace('Th', 'th')
        days = []
        for day in ['M', 'T', 'W', 'th', 'F', 'S']:
            if day in data:
                days.append(day.title())
        return days

    @staticmethod
    def _parse_sched(data):
        data = data.split()
        sched = {}
        for i, block in enumerate(data[1:], 1):
            if '-' not in block:
                continue
            # Assume that this is a valid time
            try:
                time = ClassParser._parse_time(block)
            except ValueError:
                continue
            # Assume that the previous block is valid days
            for day in ClassParser._parse_days(data[i - 1]):
                if day in sched:
                    sched[day].append(time)
                else:
                    sched[day] = [time]
        return sched

    @staticmethod
    def _merge_sched(dest, source):
        for day in source:
            if day in dest:
                dest[day] += source[day]
            else:
                dest[day] = source[day]


def search(course_num, filters=(), aysem=AYSEM):
    """Search using CRS"""
    # Stupid code for PE classes
    pe = None
    c = course_num.lower().split()
    if c[0] == 'pe':
        course_num = ' '.join(c[:2])
        if len(c) == 3 and not c[2].isdigit():
            pe = c[2]
    url = '%s/%s/%s' % (URI, aysem, urllib.quote(course_num))
    request = urllib2.Request(url)
    request.add_header('User-Agent', 'Python-urllib/CRS-o-matic')
    page = urllib2.urlopen(request)
    data = page.read()
    page.close()
    parser = ClassParser(course_num, pe, filters)
    return parser.feed(data)


def get_schedules(*classes):
    schedules = []
    for combination in product(*classes):
        sched = Schedule()
        try:
            map(sched.append, combination)
        except ScheduleConflict:
            continue
        else:
            schedules.append(sched)
    return schedules


def get_schedules2(*classes):
    """Generator version of get_schedules()"""
    for combination in product(*classes):
        sched = Schedule()
        try:
            map(sched.append, combination)
        except ScheduleConflict:
            continue
        else:
            yield sched

# -*- coding: utf-8 -*-
# $Id$
#
# crs-o-matic - CRS Schedule Generator
# Copyright (C) 2008-2010  Darwin M. Bautista
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

import time
import urllib
import urllib2
from sgmllib import SGMLParser
from htmltable import HTMLTable
# sets module is deprecated since Python 2.6
try:
    set
except NameError:
    from sets import Set as set
# Prefer itertools.product over probstat.Cartesian
try:
    from itertools import product
except ImportError:
    try:
        from probstat import Cartesian
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
    else:
        def product(*args):
            return Cartesian(list(args))


AYSEM = '120093'
URI = 'http://crs.upd.edu.ph/schedule'


def strftime(format, t):
    return time.strftime(format, (1900, 1, 1, t[0], t[1], 0, 0, 1, -1))


class ScheduleConflict(Exception):
    pass


class Duration(tuple):

    def __repr__(self):
        return "<%s-%s>" % (strftime("%I:%M%P", self[0]), strftime("%I:%M%P", self[1]))


class Class(object):

    def __init__(self):
        self.code = None
        self.name = None
        self.section = None
        self.credits = None
        self.schedule = None
        self.stats = None

    def __repr__(self):
        return "<%s %s>" % (self.name, self.section)


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
        if not isinstance(class_, Class):
            raise TypeError("argument should be an instance of Class")
        self._check_conflicts(class_)
        super(Schedule, self).append(class_)
        for day in class_.schedule:
            for duration in class_.schedule[day]:
                self.times += duration

    def remove(self, class_):
        try:
            super(Schedule, self).remove(class_)
        except ValueError:
            raise ValueError("no such class: %s" % (class_, ))

    def table(self):
        self.times = list(set(self.times))
        self.times.sort()
        table = HTMLTable(len(self.times), 7, {'class': 'schedule', 'cellpadding': 0, 'cellspacing': 0})
        day_map = {'M': 1, 'T': 2, 'W': 3, 'Th': 4, 'F': 5, 'S': 6}
        ctr = 0
        for header in ('Time', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'):
            table.set_cell_type(0, ctr, 'th')
            table.set_cell_data(0, ctr, header)
            ctr += 1
        table.set_cell_attrs(0, 0, {'class': 'time'})
        for idx in range(len(self.times) - 1):
            table.set_cell_data(idx+1, 0, "-".join([strftime("%I:%M%P", self.times[idx]), strftime("%I:%M%P", self.times[idx+1])]))
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


class CRSParser(SGMLParser):

    def __init__(self, target):
        SGMLParser.__init__(self)
        self.target = target.strip().lower()

    @staticmethod
    def _parse_time(start, end):
        start = start.upper()
        end = end.upper()

        if not end.endswith('M'):
            # Append 'M'.
            end = "".join([end, 'M'])

        for format in ('%I%p', '%I:%M%p'):
            try:
                time_end = time.strptime(end, format)[3:5]
            except ValueError:
                continue
            else:
                break
        # Get the int value of the hours.
        start_hour = int(start.split(':')[0].rstrip('APM'))
        end_hour = int(strftime('%I', time_end))

        if start.endswith('A') or start.endswith('P'):
            # Append 'M'.
            start = "".join([start, 'M'])
        elif start_hour <= end_hour and end_hour != 12:
            # Append the same am/pm to the start time.
            start = "".join([start, strftime("%P", time_end)])

        for format in ('%I', '%I:%M', '%I%p', '%I:%M%p'):
            try:
                time_start = time.strptime(start, format)[3:5]
            except ValueError:
                continue
            else:
                break
        return Duration((time_start, time_end))

    @staticmethod
    def _parse_day(combi):
        # Replace 'Th' by 'th' to avoid confusion with 'T'.
        combi = combi.replace('Th', 'th')
        days = []
        for day in ('M', 'T', 'W', 'th', 'F', 'S'):
            if day in combi:
                days.append(day.title())
        return days

    @staticmethod
    def _parse_sched(string):
        days = ('M', 'T', 'W', 'Th', 'F', 'S', 'TTh', 'WF', 'MTThF', 'TWThF', 'MTWThF')
        split = string.split()
        sched = {}
        for idx in range(len(split)):
            if split[idx] in days:
                start, end = split[idx + 1].split('-')
                time = CRSParser._parse_time(start, end)
                for day in CRSParser._parse_day(split[idx]):
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

    def reset(self):
        SGMLParser.reset(self)
        self.class_ = Class()
        self.results = []
        self.parents = {}
        self.start = False
        self.table = False
        self.row = False
        self.column = 0
        self.last_section = ''

    def start_table(self, attrs):
        self.table = True

    def end_table(self):
        self.table = False
        self.start = False

    def start_tr(self, attrs):
        if self.table:
            self.row = True

    def end_tr(self):
        if self.row:
            if self.start:
                if self.class_.stats is not None and self.class_.name.lower() == self.target:
                    section_start = self.class_.section[:3]
                    if section_start == self.last_section:
                        parent = self.results.pop()
                        self.parents[parent.section] = parent
                        self._merge_sched(self.class_.schedule, parent.schedule)
                    elif section_start in self.parents:
                        parent = self.parents[section_start]
                        self._merge_sched(self.class_.schedule, parent.schedule)
                    self.last_section = self.class_.section
                    self.results.append(self.class_)
                self.class_ = Class()
            #elif self.column == 6:
            #    self.start = True
            self.row = False
            self.column = 0

    def start_th(self, attrs):
        if self.row:
            self.start = True

    def start_td(self, attrs):
        if self.row:
            self.column += 1

    def handle_data(self, data):
        if self.start and self.row:
            data = data.strip()
            if not data:
                return
            if self.column == 1 and self.class_.code is None:
                try:
                    self.class_.code = int(data)
                except ValueError:
                    return
            elif self.column == 2 and self.class_.name is None and self.class_.section is None:
                try:
                    self.class_.name, self.class_.section = data.rsplit(' ', 1)
                except ValueError:
                    return
                else:
                    # Strip off any trailing whitespace, if any.
                    self.class_.name = self.class_.name.rstrip()
            elif self.column == 3 and self.class_.credits is None:
                try:
                    self.class_.credits = int(float(data))
                except ValueError:
                    return
            elif self.column == 4 and self.class_.schedule is None:
                self.class_.schedule = self._parse_sched(data)
            elif self.column == 5 and (self.class_.stats is None or len(self.class_.stats) == 1):
                if self.class_.stats is None:
                    self.class_.stats = (int(data), )
                else:
                    try:
                        self.class_.stats += tuple([int(i) for i in data.split() if i != '/'])
                    except ValueError:
                        return


def search(course_num, aysem=AYSEM):
    """Search using CRS"""
    url = '%s/%s/%s' % (URI, aysem, urllib.quote(course_num))
    page = urllib2.urlopen(url)
    data = page.read()
    page.close()
    parser = CRSParser(course_num)
    parser.feed(data)
    parser.close()
    return parser.results


def get_schedules(*classes):
    schedules = []
    for combination in product(*classes):
        sched = Schedule()
        try:
            map(sched.append, combination)
        except ScheduleConflict:
            continue
        schedules.append(sched)

    return schedules

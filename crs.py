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
from BeautifulSoup import BeautifulSoup, SoupStrainer
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


AYSEM = '120101'
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
        self._check_conflicts(class_)
        super(Schedule, self).append(class_)
        for day in class_.schedule:
            for duration in class_.schedule[day]:
                self.times += duration

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


class CRSParser(object):
    
    def __init__(self, course_num, filters=()):
        self.course_num = course_num.lower()
        if filters:
            self.whitelist = [i.upper() for i in filters if not i.startswith('!')]
            self.blacklist = [i.upper().lstrip('!') for i in filters if i.startswith('!')]
        else:
            self.whitelist = []
            self.blacklist = []
        
    def feed(self, data):
        results = []
        tbody = SoupStrainer('tbody')
        soup = BeautifulSoup(data, parseOnlyThese=tbody)
        for tr in soup.findAll('tr'):
            try:
                code, name, credits, schedule, stats, remarks = tr.findAll('td')
            except ValueError:
                continue
            kls = Class()
            # code
            kls.code = code.string
            # name, section
            name = name.renderContents().strip().split('<br')[0]
            kls.name, kls.section = name.rsplit(' ', 1)
            kls.name = ' '.join(kls.name.split())
            # Filter classes based on the course number
            if kls.name.lower() != self.course_num:
                continue
            # Filter based on section preferences
            if (self.whitelist and not any(map(kls.section.startswith, self.whitelist))) or \
                any(map(kls.section.startswith, self.blacklist)):
                continue
            # credits
            kls.credits = float(credits.string)
            # schedule
            schedule = schedule.renderContents().strip().split('<br')[0]
            kls.schedule = self._parse_sched(schedule)
            # stats
            kls.stats = tuple([int(i.strip('/')) for i in stats.renderContents().\
                replace('<strong>', '').replace('</strong>', '').split() if i != '/'])
            results.append(kls)
        return results

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


def search(course_num, filters=(), aysem=AYSEM):
    """Search using CRS"""
    url = '%s/%s/%s' % (URI, aysem, urllib.quote(course_num))
    request = urllib2.Request(url)
    request.add_header('User-Agent', 'Python-urllib/CRS-o-matic')
    page = urllib2.urlopen(request)
    data = page.read()
    page.close()
    parser = CRSParser(course_num, filters)
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

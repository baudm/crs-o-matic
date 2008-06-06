# $Id$
#
# crs-o-matic - CRS Schedule Generator
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

import time
import urllib
from sets import Set
from HTMLParser import HTMLParser

from htmltable import HTMLTable
from probstat import Cartesian


url = 'http://crs2.upd.edu.ph/schedule'


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
        self.total_units = 0
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
        self.total_units += class_.credits
        for day in class_.schedule:
            for duration in class_.schedule[day]:
                self.times += duration

    def remove(self, class_):
        try:
            super(Schedule, self).remove(class_)
        except ValueError:
            raise ValueError("no such class: %s" % (class_, ))

    def table(self):
        self.times = list(Set(self.times))
        self.times.sort()
        table = HTMLTable(len(self.times), 7, {'cellpadding': 0, 'cellspacing': 0})
        day_map = {'M': 1, 'T': 2, 'W': 3, 'Th': 4, 'F': 5, 'S': 6}
        ctr = 0
        for header in ('Time', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'):
            table.setCellcontents(0, ctr, header)
            table.setCelltype(0, ctr, 'th')
            ctr += 1
        for idx in range(len(self.times) - 1):
            table.setCellcontents(idx+1, 0, "-".join([strftime("%I:%M%P", self.times[idx]), strftime("%I:%M%P", self.times[idx+1])]))
        for class_ in self:
            for day in class_.schedule:
                day_i = day_map[day]
                for duration in class_.schedule[day]:
                    start, end = duration
                    s = self.times.index(start)
                    e = self.times.index(end)
                    if (e - s) != 1:
                        table.setCellRowSpan(s + 1, day_i, e - s)
                    table.setCellattrs(s + 1, day_i, {'class': 'subject'})
                    table.setCellcontents(s + 1, day_i, " ".join([class_.name, class_.section]))
        return table.return_html()


class CRSParser(HTMLParser):

    def __init__(self, target):
        HTMLParser.__init__(self)
        self.target = target.lower()

    @staticmethod
    def _parse_time(start, end):
        start = start.upper()
        end = end.upper()

        if 'M' not in end:
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
        start_hour = int(start.split(':')[0].rstrip('M').rstrip('A').rstrip('P'))
        end_hour = int(strftime('%I', time_end))

        if ('A' in start or 'P' in start) and 'M' not in start:
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

    def feed(self, data):
        # Workaround for malformed HTML of CRS2's search results.
        data = data.replace('"style="', '" style="')
        HTMLParser.feed(self, data)

    def reset(self):
        HTMLParser.reset(self)
        self.class_ = Class()
        self.results = []
        self.start = False
        self.table = False
        self.row = False
        self.column = 0

    def handle_starttag(self, tag, attrs):
        if self.row and tag == 'td':
            self.column += 1
        elif self.table and tag == 'tr':
            self.row = True
        elif tag == 'table':
            self.table = True

    def handle_endtag(self, tag):
        if self.row and tag == 'tr':
            if self.start:
                if self.class_.name.lower() == self.target:
                    self.results.append(self.class_)
                self.class_ = Class()
            elif self.column == 6:
                self.start = True
            self.row = False
            self.column = 0
        elif tag == 'table':
            self.table = False
            self.start = False

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


class SemParser(HTMLParser):

    def reset(self):
        HTMLParser.reset(self)
        self.span = False
        self.result = None

    def handle_starttag(self, tag, attrs):
        if tag == 'span':
            self.span = True

    def handle_endtag(self, tag):
        if tag == 'span':
            self.span = False

    def handle_data(self, data):
        if self.span and self.result is None:
            self.result = data


def search(course_number):
    """Search using CRS2"""

    query = urllib.urlencode({'course_num': course_number})
    socket = urllib.urlopen("?".join([url, query]))
    data = socket.read()
    socket.close()
    parser = CRSParser(course_number)
    parser.feed(data)
    parser.close()
    return parser.results


def get_semester():
    socket = urllib.urlopen(url)
    data = socket.read()
    socket.close()
    parser = SemParser()
    parser.feed(data)
    parser.close()
    return parser.result


def get_schedules(*classes):
    schedules = []
    for combination in Cartesian(list(classes)):
        sched = Schedule()
        try:
            map(sched.append, combination)
        except ScheduleConflict:
            continue
        schedules.append(sched)

    return schedules

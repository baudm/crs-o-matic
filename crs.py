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
from html import Table
# sets module is deprecated since Python 2.6
try:
    set
except NameError:
    from sets import Set as set
# Python 2.5 compatibility
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


URI = 'https://crs.upd.edu.ph'


def _strftime(fmt, t):
    return time.strftime(fmt, (1900, 1, 1, t[0], t[1], 0, 0, 1, -1))


def _merge_similar(classes):
    i = 0
    while i < len(classes) - 1:
        j = i + 1
        while j < len(classes):
            if classes[i].schedule == classes[j].schedule:
                # Add to similar classes
                append = classes[i].similar.append
                append(classes.pop(j))
            else:
                j += 1
        i += 1


class Time(tuple):

    def __new__(cls, hour, minute):
        return super(Time, cls).__new__(cls, (hour, minute))

    def __repr__(self):
        return _strftime("%I:%M%P", self)


class Interval(tuple):

    def __new__(cls, start, end):
        return super(Interval, cls).__new__(cls, (start, end))

    def __repr__(self):
        return "<%s-%s>" % self


class Class(object):

    def __init__(self, code=None, name=None, section=None):
        self.code = code
        self.name = name
        self.section = section
        self.credit = None
        self.schedule = None
        self.stats = None
        self.similar = []

    def get_odds(self):
        try:
            prob = float(self.stats[0]) / self.stats[2]
        except ZeroDivisionError:
            prob = 1.0
        # Normalize
        if prob > 1.0:
            prob = 1.0
        probs = map(Class.get_odds, self.similar)
        probs.append(prob)
        # Get average, for now
        return sum(probs) / len(probs)


class ScheduleConflict(Exception):
    pass


class Schedule(list):

    def append(self, class_):
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
        super(Schedule, self).append(class_)

    def get_table(self):
        times = []
        for class_ in self:
            for i in class_.schedule.values():
                map(times.extend, i)
        times = list(set(times))
        times.sort()
        table = Table(7, len(times), {'class': 'schedule', 'cellpadding': 0, 'cellspacing': 0})
        table.set_header_row(('Time', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'))
        table.set_cell_attrs(0, 0, {'class': 'time'})
        for idx in xrange(len(times) - 1):
            table.set_cell(0, idx + 1, "%s-%s" % (str(times[idx]), str(times[idx + 1])))
        day_map = {'M': 1, 'T': 2, 'W': 3, 'Th': 4, 'F': 5, 'S': 6}
        for class_ in self:
            for day in class_.schedule:
                day_i = day_map[day]
                for interval in class_.schedule[day]:
                    start, end = interval
                    s = times.index(start)
                    e = times.index(end)
                    attrs = {'class': 'highlight'}
                    if (e - s) != 1:
                        attrs['rowspan'] = e - s
                    table.set_cell(day_i, s + 1, class_.name, attrs)
        return table.html

    def get_stats(self):
        table = Table(2, len(self) + 3, {'class': 'schedule', 'cellpadding': 0, 'cellspacing': 0})
        table.set_header_row(('Class', 'Prob.'))
        table.set_cell_attrs(1, 0, {'class': 'probability'})
        prob_list = []
        ctr = 1
        for c in self:
            data = "%s %s" % (c.name, c.section)
            if c.similar:
                sections = [data]
                sections.extend([s.section for s in c.similar])
                data = "/ ".join(sections)
            prob_class = c.get_odds()
            prob_list.append(prob_class)
            table.set_cell(0, ctr, data)
            table.set_cell(1, ctr, "%.2f%%" % (100 * prob_class, ))
            ctr += 1
        prob = sum(prob_list)/len(self)
        stdev = math.sqrt(sum(map(lambda x: (x-prob)*(x-prob), prob_list))/len(self))
        attrs = {'class': 'highlight'}
        table.set_cell(0, ctr, 'Mean', attrs)
        table.set_cell(1, ctr, "%.2f%%" % (100 * prob, ), attrs)
        table.set_cell(0, ctr + 1, 'Std. Dev.', attrs)
        table.set_cell(1, ctr + 1, "%.2f%%" % (100 * stdev, ), attrs)
        return table.html


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
            kls = Class(code=code.contents[0].strip())
            # name, section
            kls.name, kls.section = name.contents[0].rsplit(None, 1)
            # Remove extra spaces, if any
            kls.name = ' '.join(kls.name.split())
            # Filter classes based on the course number
            if self.pe is None:
                if kls.name.lower() != self.course_num:
                    continue
            else:
                if kls.name.lower() != self.course_num + ' ' + self.pe:
                    continue
            # credit
            kls.credit = float(credit.contents[0].strip())
            # schedule
            schedule = schedule.contents[0].strip()
            kls.schedule = self._parse_sched(schedule)
            # stats
            try:
                kls.stats = tuple([int(i.strip('/')) for i in stats.text.split() if i != '/'])
            except ValueError:
                # get rid of DISSOLVED classes
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
                        for i in reversed(xrange(1, len(kls.section))):
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
        start, end = map(str.strip, str(data).upper().split('-'))
        # If both start and end are digits, they are probably room numbers.
        if start.isdigit() and end.isdigit():
            raise ValueError

        if not end.endswith('M'):
            end += 'M'

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
            # Append 'M'
            start += 'M'
        elif start_hour <= end_hour and end_hour != 12:
            # Append the same am/pm to the start time
            start += _strftime("%P", time_end)

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
        all_days = ['M', 'T', 'W', 'th', 'F', 'S']
        days = (day.title() for day in all_days if day in data)
        return days

    @staticmethod
    def _parse_sched(data):
        data = data.split()
        sched = {}
        for i, block in enumerate(data[1:]):
            if '-' not in block:
                continue
            # Assume that this is a valid time
            try:
                time = ClassParser._parse_time(block)
            except ValueError:
                continue
            # Assume that the previous block is valid days
            for day in ClassParser._parse_days(data[i]):
                sched.setdefault(day, []).append(time)
        return sched

    @staticmethod
    def _merge_sched(dest, source):
        for day in source:
            dest.setdefault(day, []).extend(source[day])


def get_current_term():
    request = urllib2.Request(URI)
    request.add_header('User-Agent', 'Python-urllib/CRS-o-matic')
    page = urllib2.urlopen(request)
    data = page.read()
    page.close()
    ul = SoupStrainer('ul')
    soup = BeautifulSoup(data, parseOnlyThese=ul)
    # Find all links from the last <ul>
    links = soup.findAll('ul')[-1].findAll('a')
    # Get only the correct links
    links = filter(lambda a: a['href'].split('/')[-1].startswith('1'), links)
    links.sort(key=lambda a: a['href'].split('/')[-1])
    return links[-1]['href'].split('/')[-1]


def get_term_name(term):
    sem = {
        '1': '1st Semester',
        '2': '2nd Semester',
        '3': 'Summer'
    }
    s = sem[term[5]]
    start = int(term[1:5])
    end = start + 1
    name = '%s AY %d-%d' % (s, start, end)
    return name


def search(course_num, term=None, filters=(), distinct=False):
    """Search using CRS"""
    # Stupid code for PE classes
    pe = None
    c = course_num.lower().split()
    if c[0] == 'pe':
        course_num = ' '.join(c[:2])
        if len(c) == 3 and not c[2].isdigit():
            pe = c[2]
    if term is None:
        term = get_current_term()
    url = '%s/schedule/%s/%s' % (URI, term, urllib.quote(course_num))
    request = urllib2.Request(url)
    request.add_header('User-Agent', 'Python-urllib/CRS-o-matic')
    page = urllib2.urlopen(request)
    data = page.read()
    page.close()
    parser = ClassParser(course_num, pe, filters)
    classes = parser.feed(data)
    if distinct:
        _merge_similar(classes)
    # Sort by the odds of getting a class
    classes.sort(key=Class.get_odds, reverse=True)
    return classes


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

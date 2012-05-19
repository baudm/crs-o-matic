# -*- coding: utf-8 -*-
#
# crs-o-matic - CRS Schedule Generator
# Copyright (C) 2008-2012  Darwin M. Bautista
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

# Make crs.py usable outside of GAE
# urlfetch.fetch() has to be used when running in GAE so that
# validate_certificate can be set to False
try:
    from google.appengine.api.urlfetch import fetch
except ImportError:
    import urllib2

    class Result(object):

        def __init__(self, content):
            self.content = content

    def fetch(url, headers={}, deadline=None, validate_certificate=None):
        request = urllib2.Request(url)
        for k, v in headers.iteritems():
            request.add_header(k, v)
        timeout = 5 if deadline is None else deadline
        data = urllib2.urlopen(request, timeout=timeout).read()
        return Result(data)

from BeautifulSoup import BeautifulSoup, SoupStrainer
from html import Table

import itertools
# sets module is deprecated since Python 2.6
try:
    set
except NameError:
    from sets import Set as set

URI = 'https://crs.upd.edu.ph'
HTTP_HEADERS = {'User-Agent': 'Python-urllib/CRS-o-matic'}


def _strftime(fmt, t):
    return time.strftime(fmt, (2012, 1, 1, t[0], t[1], 0, 0, 1, 0))


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
        return _strftime('%I:%M%p', self).lower()


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
        self.similar = []

    def get_odds(self):
        available = 0
        demand = 0
        # Get the cumulative demand and available slots
        for c in [self] + self.similar:
            # Only include stats with non-zero available slots
            if c.stats[0]:
                available += c.stats[0]
                demand += c.stats[2]
        try:
            prob = float(available) / demand
        except ZeroDivisionError:
            prob = 1.0
        # Normalize
        if prob > 1.0:
            prob = 1.0
        return prob


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
                            raise ScheduleConflict('%s conflicts with %s' % (class_, c))
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
            table.set_cell(0, idx + 1, '%s-%s' % (str(times[idx]), str(times[idx + 1])))
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
            data = '%s %s' % (c.name, c.section)
            if c.similar:
                sections = [data]
                sections.extend([s.section for s in c.similar])
                data = ', '.join(sections)
            prob_class = c.get_odds()
            prob_list.append(prob_class)
            table.set_cell(0, ctr, data)
            table.set_cell(1, ctr, '%.2f%%' % (100 * prob_class, ))
            ctr += 1
        prob = sum(prob_list)/len(self)
        stdev = math.sqrt(sum(map(lambda x: (x-prob)*(x-prob), prob_list))/len(self))
        attrs = {'class': 'highlight'}
        table.set_cell(0, ctr, 'Mean', attrs)
        table.set_cell(1, ctr, '%.2f%%' % (100 * prob, ), attrs)
        table.set_cell(0, ctr + 1, 'Std. Dev.', attrs)
        table.set_cell(1, ctr + 1, '%.2f%%' % (100 * stdev, ), attrs)
        return table.html


class ClassParser(object):

    def __init__(self, course_num, filters=()):
        self.course_num = course_num.lower()
        if 'cwts' in self.course_num:
            self.course_num = self._get_fuzzy_cwts_name(self.course_num)

        if filters:
            self.whitelist = [i.upper() for i in filters if not i.startswith('!')]
            self.blacklist = [i.upper().lstrip('!') for i in filters if i.startswith('!')]
        else:
            self.whitelist = []
            self.blacklist = []

    @staticmethod
    def _get_fuzzy_cwts_name(raw_name):
        tokens = str(raw_name).split()
        tokens = map(str.strip, tokens, [' -12']*len(tokens))
        tokens = filter(None, tokens)
        return ' '.join(tokens)

    @staticmethod
    def _tokenize_name(data):
        data = data.split()
        # Remove any separating hyphens
        data = map(unicode.strip, data, ['-']*len(data))
        data = filter(None, data)
        # Build the name from the 1st to the 2nd-to-the-last items;
        # the last item is the section
        name = ' '.join(data[:-1])
        section = data[-1]
        return name, section

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
            kls.name, kls.section = self._tokenize_name(name.contents[0])

            # Get class name for filtering
            class_name = kls.name.lower()
            if 'cwts' in self.course_num:
                class_name = self._get_fuzzy_cwts_name(class_name)

            # Filter classes based on the course number
            # except in the case where 'CWTS' is the search key
            if class_name != self.course_num and self.course_num != 'cwts':
                continue
            # credit
            kls.credit = float(credit.contents[0].strip())
            # schedule
            schedule = schedule.contents[0].strip()
            kls.schedule = self._parse_sched(schedule)
            # stats
            try:
                kls.stats = tuple(map(int, stats.text.split('/')))
            except ValueError:
                # get rid of DISSOLVED classes
                continue
            if ' disc ' in schedule:
                children.append(kls)
            elif ' lab ' in schedule:
                # Is this really a lab class? or just a typo?
                # Check the timeslots of all days in the schedule
                # to see if at least one timeslot is at least 2 hours
                child = False
                for dayscheds in kls.schedule.values():
                    for timeslot in dayscheds:
                        hours = timeslot[1][0] - timeslot[0][0]
                        if hours >= 2:
                            child = True
                            break
                if child:
                    children.append(kls)
                else:
                    parents[kls.section] = kls
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
        try:
            end_hour = int(_strftime('%I', time_end))
        except NameError:
            raise ValueError

        if start.endswith('A') or start.endswith('P'):
            # Append 'M'
            start += 'M'
        elif start_hour <= end_hour and end_hour != 12:
            # Append the same am/pm to the start time
            start += _strftime('%p', time_end)
        elif start_hour == 12:
            start += 'PM'

        for fmt in ['%I', '%I:%M', '%I%p', '%I:%M%p']:
            try:
                time_start = Time(*time.strptime(start, fmt)[3:5])
            except ValueError:
                continue
            else:
                break
        try:
            return Interval(time_start, time_end)
        except NameError:
            raise ValueError

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
    result = fetch(URI, headers=HTTP_HEADERS, deadline=20, validate_certificate=False)
    data = result.content
    ul = SoupStrainer('ul')
    soup = BeautifulSoup(data, parseOnlyThese=ul)
    # Find all links starting from the last <ul>
    links = []
    index = -1
    while not links:
        links = soup.findAll('ul')[index].findAll('a')
        index -= 1
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
    # For filtering to work, PE classes have to be specified as: PE <number> <code>
    # However, for CRS search to work, the format should be:     PE <number>
    if not course_num.upper().startswith('PE '):
        search_key = course_num
    else:
        # Include only the first two words, i.e. PE <number>, in the search key
        search_key = ' '.join(course_num.split()[:2])
    if term is None:
        term = get_current_term()
    url = '%s/schedule/%s/%s' % (URI, term, urllib.quote(search_key))
    result = fetch(url, headers=HTTP_HEADERS, deadline=20, validate_certificate=False)
    data = result.content
    parser = ClassParser(course_num, filters)
    classes = parser.feed(data)
    if distinct:
        _merge_similar(classes)
    # Sort by the odds of getting a class
    classes.sort(key=Class.get_odds, reverse=True)
    return classes


def get_schedules(*classes):
    schedules = []
    for combination in itertools.product(*classes):
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
    for combination in itertools.product(*classes):
        sched = Schedule()
        try:
            map(sched.append, combination)
        except ScheduleConflict:
            continue
        else:
            yield sched

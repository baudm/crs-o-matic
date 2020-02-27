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

import colorsys
import hashlib
import math
import time
import requests

from bs4 import BeautifulSoup, SoupStrainer

import color
from htmltable import Table

import itertools
from itertools import chain

URI = 'https://crs.upd.edu.ph'
HTTP_HEADERS = {'User-Agent': '{} CRS-o-matic/{}'.format(requests.utils.default_user_agent(), 'VER_ABBREV')}


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
        return super().__new__(cls, (hour, minute))

    def __repr__(self):
        return _strftime('%I:%M%p', self).lower()


class Interval(tuple):

    def encode(self):
        """Encodes the interval into its binary representation
        Each bit corresponds to a 15-minute interval
        """
        # Earliest start hour is 7am
        ref_hour = 7
        start, end = self
        start = 1 << ((start[0] - ref_hour) * 4 + start[1] // 15)
        end = 1 << ((end[0] - ref_hour) * 4 + end[1] // 15 - 1)
        return (start - 1) ^ (end - 1) | end

    def __new__(cls, start, end):
        return super().__new__(cls, (start, end))

    def __repr__(self):
        return '<{}-{}>'.format(*self)


class Class:

    def __init__(self, code=None, name=None, section=None):
        self.code = code
        self.name = name
        self.section = section
        self.credit = None
        self.schedule = None
        self._schedule_enc = None
        self.stats = None
        self.similar = []

    def __str__(self) -> str:
        # Get a combined string representation of this class which focuses on the schedule
        days = sorted(self.schedule.keys())
        times = [self.schedule[d] for d in days]
        return '{} {} {}'.format(self.name, days, times)

    def get_odds(self):
        available = 0
        demand = 0
        # Get the cumulative demand and available slots
        for c in [self] + self.similar:
            # Only include stats with non-zero available slots
            if c.stats[0]:
                available += c.stats[0]
                demand += c.stats[2]
        if available == 0:
            prob = 0.
        elif demand == 0:
            prob = 1.
        else:
            prob = min(available / demand, 1.)
        return prob


class ScheduleConflict(Exception):
    pass


class Schedule(tuple):

    def __new__(cls, classes):
        cls._check_conflicts(classes)
        return super().__new__(cls, classes)

    @staticmethod
    def _check_conflicts(classes):
        sched = [0] * 6
        for c in classes:
            for i, day in enumerate(c._schedule_enc):
                if (sched[i] ^ day) & day != day:
                    raise ScheduleConflict('Schedule conflict(s) detected.')
                sched[i] |= day

    def get_table(self):
        # Obtain a flat list of all interval bounds
        times = chain.from_iterable(chain.from_iterable(chain.from_iterable([c.schedule.values() for c in self])))
        times = sorted(set(times))
        table = Table(7, len(times), {'class': 'schedule', 'cellpadding': 0, 'cellspacing': 0})
        table.set_header_row(('Time', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'))
        table.set_cell_attrs(0, 0, {'class': 'time'})
        for idx in range(len(times) - 1):
            table.set_cell(0, idx + 1, '{}-{}'.format(times[idx], times[idx + 1]))
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
            sections = [c.section] + [s.section for s in c.similar]
            sections = ', '.join(sorted(sections))
            data = '{} {}'.format(c.name, sections)
            prob_class = c.get_odds()
            prob_list.append(prob_class)
            table.set_cell(0, ctr, data)
            table.set_cell(1, ctr, '{:.2f}%'.format(100 * prob_class))
            ctr += 1
        prob = sum(prob_list)/len(self)
        stdev = math.sqrt(sum([(x - prob)*(x - prob) for x in prob_list])/len(self))
        attrs = {'class': 'highlight'}
        table.set_cell(0, ctr, 'Mean', attrs)
        table.set_cell(1, ctr, '{:.2f}%'.format(100 * prob), attrs)
        table.set_cell(0, ctr + 1, 'Std. Dev.', attrs)
        table.set_cell(1, ctr + 1, '{:.2f}%'.format(100 * stdev), attrs)
        return table.html

    @property
    def id(self):
        # hash based on sorted representations of the individual classes
        r = ''.join(sorted([str(c) for c in self]))
        return hashlib.sha1(r.encode('utf-8')).hexdigest()[:5]


class Heatmap(Schedule):

    def __new__(cls, classes):
        # No need to check for conflicts
        return tuple.__new__(cls, classes)

    @staticmethod
    def get_color(value):
        """Get heatmap color of value [0, 1] in 8-bit RGB values"""
        h = 0.5960
        s = 0.0353 + 0.89 * value
        v = 0.4196 + 0.5804 * (1. - value)
        rgb = colorsys.hsv_to_rgb(h, s, v)
        return color.rgb_to_8bit(rgb)

    def get_table(self):
        # Obtain a flat list of all interval bounds
        times = chain.from_iterable(chain.from_iterable(chain.from_iterable([c.schedule.values() for c in self])))
        times = sorted(set(times))
        table = Table(7, len(times), {'class': 'schedule', 'cellpadding': 0, 'cellspacing': 0})
        table.set_header_row(('Time', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'))
        table.set_cell_attrs(0, 0, {'class': 'time'})
        for idx in range(len(times) - 1):
            table.set_cell(0, idx + 1, '{}-{}'.format(times[idx], times[idx + 1]))
        day_map = {'M': 1, 'T': 2, 'W': 3, 'Th': 4, 'F': 5, 'S': 6}

        max_value = 1
        for class_ in self:
            for day in class_.schedule:
                day_i = day_map[day]
                for interval in class_.schedule[day]:
                    start, end = interval
                    s = times.index(start)
                    e = times.index(end)
                    for i in range(s, e):
                        c = table._data[i + 1][day_i]
                        if c is None:
                            table.set_cell(day_i, i + 1, 1)
                        else:
                            c._data += 1
                            max_value = max(max_value, c._data)

        for row in range(1, len(table._data)):
            for col in range(1, len(table._data[row])):
                cell = table._data[row][col]
                if cell is not None:
                    v = cell._data / max_value
                    bg_color = self.get_color(v)
                    fg_color = '#fff' if color.rgb_relative_luminance(bg_color) < 0.1791 else '#000'
                    bg_color = color.rgb_to_hex(bg_color)
                    cell._attrs = {'style': 'font-weight: bold; color: ' + fg_color + '; background-color: ' + bg_color}

        return table.html


class ClassParser:

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
        tokens = raw_name.split()
        tokens = map(str.strip, tokens, [' -12']*len(tokens))
        tokens = filter(None, tokens)
        return ' '.join(tokens)

    @staticmethod
    def _tokenize_name(data):
        data = data.split()
        # Remove any separating hyphens
        data = map(str.strip, data, ['-']*len(data))
        data = list(filter(None, data))
        # Build the name from the 1st to the 2nd-to-the-last items;
        # the last item is the section
        name = ' '.join(data[:-1])
        section = data[-1]
        return name, section

    def feed(self, data):
        parents = {}
        children = []
        tbody = SoupStrainer('tbody')
        soup = BeautifulSoup(data, 'lxml', parse_only=tbody)
        for tr in soup.find_all('tr'):
            try:
                code, name, credit, schedule, remarks, slots, demand, restrictions = tr.find_all('td')
            except ValueError:
                continue
            kls = Class(code=code.text.strip())
            # name, section
            kls.name, kls.section = self._tokenize_name(name.text)

            # Get class name for filtering
            class_name = kls.name.lower()
            if 'cwts' in self.course_num:
                class_name = self._get_fuzzy_cwts_name(class_name)

            # Filter classes based on the course number
            # except in the case where 'CWTS' is the search key
            if class_name != self.course_num and self.course_num != 'cwts':
                continue
            # credit
            kls.credit = float(credit.text)
            # schedule
            schedule = schedule.text
            kls.schedule, kls._schedule_enc = self._parse_sched(schedule)
            # stats
            try:
                stats = slots.text.split('/')
            except ValueError:
                # get rid of DISSOLVED classes
                continue
            stats.append(demand.text)
            kls.stats = []
            for s in stats:
                try:
                    v = int(s)
                except ValueError:
                    v = 0
                kls.stats.append(v)
            kls.stats = tuple(kls.stats)
            if schedule.count(' disc ') == 1 and not ' lec ' in schedule:
                children.append(kls)
            elif schedule.count(' lab ') == 1 and not ' lec ' in schedule:
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
            results = list(filter(self._filter_class, children))
            # Merge schedules with the respective parent
            if parents:
                for kls in results:
                    # Match parents with children based on their sections
                    try:
                        parent = list(filter(kls.section.startswith, parents.keys()))[0]
                    except IndexError:
                        matched = False
                        for i in reversed(range(3, len(kls.section))):
                            for parent in parents:
                                if kls.section[:i] in parent:
                                    matched = True
                                    break
                            if matched:
                                break
                        if not matched:
                            continue
                    p_kls = parents[parent]
                    # Merge parent info into child
                    if not kls.section.startswith(p_kls.section):
                        kls.section = p_kls.section + '/' + kls.section
                    # Choose the non-zero credit
                    kls.credit = kls.credit or p_kls.credit
                    self._merge_sched(kls.schedule, p_kls.schedule)
        else:
            results = list(filter(self._filter_class, parents.values()))
        return results

    @staticmethod
    def _parse_time(data):
        start, end = tuple(map(str.strip, data.upper().split('-')))
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
        days = ((i, day.title()) for i, day in enumerate(all_days) if day in data)
        return days

    @staticmethod
    def _parse_sched(data):
        data = data.split()
        sched = {}
        sched_enc = [0] * 6
        for i, block in enumerate(data[1:]):
            if '-' not in block:
                continue
            # Assume that this is a valid time
            try:
                time = ClassParser._parse_time(block)
            except ValueError:
                continue
            time_enc = time.encode()
            # Assume that the previous block is valid days
            for d, day in ClassParser._parse_days(data[i]):
                sched_enc[d] |= time_enc
                sched.setdefault(day, []).append(time)
        return sched, sched_enc

    @staticmethod
    def _merge_sched(dest, source):
        for day in source:
            dest.setdefault(day, []).extend(source[day])


def get_current_term():
    result = requests.get(URI + '/schedule/', headers=HTTP_HEADERS)
    tags = SoupStrainer('select')
    soup = BeautifulSoup(result.text, 'lxml', parse_only=tags)
    selected = soup.find(selected='selected')
    name = selected.text
    value = selected['value']
    return name, value


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
        name, term = get_current_term()
    url = '{}/schedule/{}/{}'.format(URI, term, search_key)
    result = requests.get(url, headers=HTTP_HEADERS)
    parser = ClassParser(course_num, filters)
    classes = parser.feed(result.text)
    if distinct:
        _merge_similar(classes)
    # Sort by the odds of getting a class
    classes.sort(key=Class.get_odds, reverse=True)
    return classes


def get_heatmap(*classes):
    heatmap = Heatmap(chain.from_iterable(classes))
    return [heatmap]


def get_schedules(*classes):
    schedules = []
    for combination in itertools.product(*classes):
        try:
            sched = Schedule(combination)
        except ScheduleConflict:
            continue
        else:
            schedules.append(sched)
    return schedules


def get_schedules2(*classes):
    """Generator version of get_schedules()"""
    for combination in itertools.product(*classes):
        try:
            sched = Schedule(combination)
        except ScheduleConflict:
            continue
        else:
            yield sched

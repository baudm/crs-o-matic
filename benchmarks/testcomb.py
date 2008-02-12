#!/usr/bin/python

from pure import combine

ctr = 0
for a in combine(range(25), range(20), range(30), range(50)): ctr += 1
print ctr

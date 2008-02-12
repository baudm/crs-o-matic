#!/usr/bin/python

from pure import xcombine

ctr = 0
for a in xcombine(range(25), range(20), range(30), range(50)): ctr += 1
print ctr

#!/usr/bin/python

from probstat import Cartesian

ctr = 0
for a in Cartesian([range(25), range(20), range(30), range(50)]): ctr += 1
print ctr

# -*- coding: utf-8 -*-
#
# crs-o-matic - CRS Schedule Generator
# Copyright (C) 2008-2020  Darwin M. Bautista
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

"""Various color-related utility functions"""

import operator


def rgb_relative_luminance(rgb):
    """Calculate relative luminance as defined by WCAG
       https://www.w3.org/TR/WCAG/#dfn-relative-luminance"""
    def norm(c):
        c /= 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = tuple(map(norm, rgb))
    # Assume sRGB color space
    L = 0.2126 * r + 0.7152 * g + 0.0722 * b
    return L


def rgb_to_hex(rgb):
    """8-bit RGB to hex"""
    return '#{:02x}{:02x}{:02x}'.format(*rgb)


def rgb_to_8bit(rgb):
    """Convert RGB from normalized [0, 1] to 8-bit"""
    return tuple(map(round, map(operator.mul, rgb, [255] * 3)))

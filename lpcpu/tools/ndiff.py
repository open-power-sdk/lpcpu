#!/usr/bin/python

#
# LPCPU (Linux Performance Customer Profiler Utility): ./tools/ndiff.py
#
# (C) Copyright IBM Corp. 2018
#
# This file is subject to the terms and conditions of the Eclipse
# Public License.  See the file LICENSE.TXT in the main directory of the
# distribution for more details.
#

#
# LPCPU (Linux Performance Customer Profiler Utility): ./tools/ndiff.py
#
# (C) Copyright IBM Corp. 2017. All rights reserved.

# This script compares the numbers present at identical locations in two
# given files, and produces a file which contains the same contents as the
# original file(s), except with the numbers replaced by the difference of
# the numbers in the original files.  It attempts to preserve whitespace
# in a way such that vertical alignment is preserved.
#
# Arguments:  <before-file> <after-file>

import sys;
import re;

whitespace = re.compile('\s*')
blackspace = re.compile('\S*')
integer = re.compile('^\d+$')
decimal = re.compile('^\d*\.\d+$')

B=sys.argv[1]
A=sys.argv[2]
fileB = open(B,'r') # after
fileA = open(A,'r') # before

for lineB in fileB:
	lineA = fileA.readline()

	segmentwhiteBend = 0
	segmentblackBend = 0
	segmentwhiteAend = 0
	segmentblackAend = 0
	whiteB = ''
	blackB = ''
	whiteA = ''
	blackA = ''

	while (segmentblackAend != len(lineA)):
		segmentwhiteB = whitespace.search(lineB,segmentblackBend)
		if (segmentwhiteB):
			whiteB = segmentwhiteB.group()
			segmentwhiteBend = segmentwhiteB.end()

		segmentwhiteA = whitespace.search(lineA,segmentblackAend)
		if (segmentwhiteA):
			whiteA = segmentwhiteA.group()
			segmentwhiteAend = segmentwhiteA.end()

		segmentblackB = blackspace.search(lineB,segmentwhiteBend)
		if (segmentblackB):
			blackB = segmentblackB.group()
			segmentblackBend = segmentblackB.end()

		segmentblackA = blackspace.search(lineA,segmentwhiteAend)
		if (segmentblackA):
			blackA = segmentblackA.group()
			segmentblackAend = segmentblackA.end()

		numberB = integer.search(blackB)
		if (numberB):
			numberA = integer.search(blackA)
			if (numberA):
				blackA = str(int(numberA.group()) - int(numberB.group()))
				newWhite = len(numberA.group()) - len(blackA)
				while newWhite > 0:
					blackA = ' ' + blackA
					newWhite = newWhite - 1
		else:
			numberB = decimal.search(blackB)
			if (numberB):
				digits = len(numberB.group()) - numberB.group().index('.') - 1
				numberA = decimal.search(blackA)
				if (numberA):
					fmt = "." + str(digits) + "f"
					blackA = format(float(numberA.group()) - float(numberB.group()),fmt)
					newWhite = len(numberA.group()) - len(blackA)
					while newWhite > 0:
						blackA = ' ' + blackA
						newWhite = newWhite - 1

		sys.stdout.write(whiteA)
		sys.stdout.write(blackA)


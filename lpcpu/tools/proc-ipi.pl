#! /usr/bin/perl

#
# LPCPU (Linux Performance Customer Profiler Utility): ./tools/proc-ipi.pl
#
# (C) Copyright IBM Corp. 2018
#
# This file is subject to the terms and conditions of the Eclipse
# Public License.  See the file LICENSE.TXT in the main directory of the
# distribution for more details.
#

# This script monitors Inter-Process Interrupts (IPIs) by extracting
# IPI-specific data from /proc/interrupts and calculating the difference
# between successive snapshots taken at a given interval.
# The output, sent to stdout, shows IPI deltas in a format similar to
# /proc/interrupts but with only IPI lines and delta values.
#
# Arguments:  [interval]

use strict;
use File::Basename;

# disable output buffering
$|++;

my $interval = 5;
if (@ARGV) {
	$interval = $ARGV[0];
}

my @lines;
my @ipi_data_prev;
my @ipi_data_curr;

my @headers;
my $cpu_count;
my $i;
my $j;

if (!open(INPUT, "</proc/interrupts")) {
	print STDERR "ERROR: Could not open /proc/interrupts\n";
	exit 1;
}

@lines = <INPUT>;

@headers = split(" ", $lines[0]);
$cpu_count = @headers;

# Extract only IPI lines from the initial snapshot
for ($i = 1; $i < @lines; $i++) {
	# Process lines that start with IPI (x86/ARM) or contain IPI at the end (PowerPC)
	if ($lines[$i] =~ /^\s*IPI/ || $lines[$i] =~ /\s+IPI\s*$/) {
		my @fields = ();
		@fields = split(" ", $lines[$i], $cpu_count + 1);
		# Parse the description out of the last field.
		# The description was purposely not parsed in the previous split
		# because we want to preserve any leading spaces before the
		# description.
		$fields[$#fields] =~ /([0-9]*)(.*)/;
		$fields[$#fields] = $1;
		push @fields, $2;
		push @ipi_data_prev, \@fields;
	}
}

while (1) {
	sleep $interval;

	seek INPUT, 0, 0;
	@lines = <INPUT>;

	@ipi_data_curr = ();
	
	# Extract only IPI lines from the current snapshot
	for ($i = 1; $i < @lines; $i++) {
		# Process lines that start with IPI (x86/ARM) or contain IPI at the end (PowerPC)
		if ($lines[$i] =~ /^\s*IPI/ || $lines[$i] =~ /\s+IPI\s*$/) {
			my @fields = ();
			@fields = split(" ", $lines[$i], $cpu_count + 1);
			# Parse the description out of the last field.
			# The description was purposely not parsed in the previous split
			# because we want to preserve any leading spaces before the
			# description.
			$fields[$#fields] =~ /([0-9]*)(.*)/;
			$fields[$#fields] = $1;
			push @fields, $2;
			push @ipi_data_curr, \@fields;
		}
	}

	printf "%02d:%02d:%02d / %d\n", (localtime)[2], (localtime)[1], (localtime)[0], time;
	print "      ";
	for ($i = 0; $i < $cpu_count; $i++) {
		printf "%10s", $headers[$i];
	}
	print "\n";

	for ($i = 0; $i < @ipi_data_prev; $i++) {
		printf "%6s", $ipi_data_prev[$i][0];
		for ($j = 1; $j < $cpu_count + 1; $j++) {
			printf "%10d",  $ipi_data_curr[$i][$j] - $ipi_data_prev[$i][$j];
		}
		print "$ipi_data_curr[$i][$cpu_count + 1]\n";
	}

	print "\n";
	@ipi_data_prev = @ipi_data_curr;
	@ipi_data_curr = ();
}

close INPUT;

# Made with Bob

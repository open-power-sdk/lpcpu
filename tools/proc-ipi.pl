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
# Supports two /proc/interrupts formats:
# 1. Linux x86: "IPI0:  123  456  789  ..."
# 2. POWER/XICS: "16:  123  456  789  ... XICS 2 Edge IPI"
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
	# Process lines that contain IPI (case-insensitive word boundary match)
	# Supports two formats:
	# 1. Linux x86: "IPI0:  123  456  789  ..."
	# 2. POWER/XICS: "16:  123  456  789  ... XICS 2 Edge IPI"
	if ($lines[$i] =~ /\bIPI\b/i) {
		my @fields = ();
		my $line = $lines[$i];
		
		# Check if line starts with interrupt number (POWER format)
		if ($line =~ /^\s*(\d+):/) {
			# POWER format: skip the interrupt number, extract IPI name from end
			$line =~ s/^\s*\d+:\s*//;  # Remove interrupt number
			@fields = split(" ", $line);
			
			# Find where CPU counts end (before text description like "XICS")
			my $ipi_name = "IPI";
			my @cpu_counts;
			for (my $k = 0; $k < @fields; $k++) {
				if ($fields[$k] =~ /^\d+$/ && $k < $cpu_count) {
					push @cpu_counts, $fields[$k];
				} else {
					# Rest is description, extract IPI name
					$ipi_name = join(" ", @fields[$k..$#fields]);
					last;
				}
			}
			@fields = ($ipi_name, @cpu_counts, "");
		} else {
			# Linux x86 format: IPI name at start
			@fields = split(" ", $line, $cpu_count + 1);
			# Parse the description out of the last field
			$fields[$#fields] =~ /([0-9]*)(.*)/;
			$fields[$#fields] = $1;
			push @fields, $2;
		}
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
		# Process lines that contain IPI (case-insensitive word boundary match)
		# Supports two formats:
		# 1. Linux x86: "IPI0:  123  456  789  ..."
		# 2. POWER/XICS: "16:  123  456  789  ... XICS 2 Edge IPI"
		if ($lines[$i] =~ /\bIPI\b/i) {
			my @fields = ();
			my $line = $lines[$i];
			
			# Check if line starts with interrupt number (POWER format)
			if ($line =~ /^\s*(\d+):/) {
				# POWER format: skip the interrupt number, extract IPI name from end
				$line =~ s/^\s*\d+:\s*//;  # Remove interrupt number
				@fields = split(" ", $line);
				
				# Find where CPU counts end (before text description like "XICS")
				my $ipi_name = "IPI";
				my @cpu_counts;
				for (my $k = 0; $k < @fields; $k++) {
					if ($fields[$k] =~ /^\d+$/ && $k < $cpu_count) {
						push @cpu_counts, $fields[$k];
					} else {
						# Rest is description, extract IPI name
						$ipi_name = join(" ", @fields[$k..$#fields]);
						last;
					}
				}
				@fields = ($ipi_name, @cpu_counts, "");
			} else {
				# Linux x86 format: IPI name at start
				@fields = split(" ", $line, $cpu_count + 1);
				# Parse the description out of the last field
				$fields[$#fields] =~ /([0-9]*)(.*)/;
				$fields[$#fields] = $1;
				push @fields, $2;
			}
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

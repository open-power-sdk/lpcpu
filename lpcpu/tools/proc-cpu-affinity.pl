#! /usr/bin/perl

#
# LPCPU (Linux Performance Customer Profiler Utility): ./tools/proc-cpu-affinity.pl
#
# (C) Copyright IBM Corp. 2024
#
# This file is subject to the terms and conditions of the Eclipse
# Public License.  See the file LICENSE.TXT in the main directory of the
# distribution for more details.
#

# This script monitors thread-to-CPU assignment by reading the processor field
# (field 39) from /proc/[pid]/task/[tid]/stat for all threads in the system.
# The processor field indicates the last CPU the thread executed on, not
# necessarily the current CPU at the exact instant of reading.
#
# Output format: Timestamp PID TID PSR PCPU COMM
# - Timestamp: Unix epoch with milliseconds (if available)
# - PID: Process ID
# - TID: Thread ID
# - PSR: Processor (last CPU thread executed on, from field 39)
# - PCPU: CPU utilization percentage (calculated from utime+stime deltas)
# - COMM: Command name
#
# Arguments: <interval>
#   interval: Sampling interval in seconds (synchronized with IPI profiler)

use strict;
use warnings;
use Time::HiRes qw(time sleep);

# Disable output buffering
$| = 1;

# Get interval from command line
if (@ARGV < 1) {
    print STDERR "Usage: $0 <interval>\n";
    print STDERR "  interval: Sampling interval in seconds\n";
    exit 1;
}

my $interval = $ARGV[0];

# Get system clock ticks per second for CPU% calculation
my $clock_ticks = `getconf CLK_TCK 2>/dev/null` || 100;
chomp $clock_ticks;

# Storage for previous sample (for CPU% calculation)
my %prev_data;  # tid -> {utime, stime, timestamp}

# Print header
print "# Timestamp PID TID PSR PCPU COMM\n";
print "# PSR = Last CPU thread executed on (from /proc/[pid]/task/[tid]/stat field 39)\n";
print "# PCPU = CPU utilization percentage (calculated from utime+stime deltas)\n";

# Main sampling loop
while (1) {
    my $timestamp = time();  # High-resolution timestamp
    my %curr_data;
    
    # Scan all processes
    opendir(my $proc_dh, "/proc") or die "Cannot open /proc: $!";
    my @pids = grep { /^\d+$/ } readdir($proc_dh);
    closedir($proc_dh);
    
    foreach my $pid (@pids) {
        my $task_dir = "/proc/$pid/task";
        
        # Skip if process disappeared or no permission
        next unless -d $task_dir;
        
        # Scan all threads for this process
        opendir(my $task_dh, $task_dir) or next;
        my @tids = grep { /^\d+$/ } readdir($task_dh);
        closedir($task_dh);
        
        foreach my $tid (@tids) {
            my $stat_file = "$task_dir/$tid/stat";
            
            # Skip if thread disappeared or no permission
            next unless -r $stat_file;
            
            # Read stat file
            open(my $stat_fh, "<", $stat_file) or next;
            my $line = <$stat_fh>;
            close($stat_fh);
            
            # Skip if empty
            next unless defined $line;
            
            # Parse stat file
            # Format: pid (comm) state ppid pgrp session tty_nr tpgid flags minflt cminflt majflt cmajflt utime stime cutime cstime ... processor ...
            # The comm field can contain spaces and parentheses, so we need careful parsing
            if ($line =~ /^(\d+)\s+\(([^)]*)\)\s+(\S+)\s+(.*)$/) {
                my $parsed_pid = $1;
                my $comm = $2;
                my $state = $3;
                my $rest = $4;
                
                my @fields = split(/\s+/, $rest);
                
                # Field indices (0-based from $rest):
                # 0=ppid, 1=pgrp, 2=session, 3=tty_nr, 4=tpgid, 5=flags,
                # 6=minflt, 7=cminflt, 8=majflt, 9=cmajflt,
                # 10=utime, 11=stime, 12=cutime, 13=cstime,
                # ... (more fields) ...
                # 35=processor (field 39 in original stat file)
                
                # Check if we have enough fields
                next unless @fields > 35;
                
                my $utime = $fields[10];
                my $stime = $fields[11];
                my $psr = $fields[35];  # Processor (last CPU executed on)
                
                # Store current data for next iteration
                $curr_data{$tid} = {
                    utime => $utime,
                    stime => $stime,
                    timestamp => $timestamp
                };
                
                # Calculate CPU% if we have previous data
                my $pcpu = 0.0;
                if (exists $prev_data{$tid}) {
                    my $time_delta = $timestamp - $prev_data{$tid}{timestamp};
                    if ($time_delta > 0) {
                        my $cpu_time_delta = ($utime - $prev_data{$tid}{utime}) + 
                                            ($stime - $prev_data{$tid}{stime});
                        # Convert from clock ticks to seconds, then to percentage
                        $pcpu = ($cpu_time_delta / $clock_ticks) / $time_delta * 100.0;
                        # Cap at 100% per CPU (can exceed for multi-threaded)
                        $pcpu = 100.0 if $pcpu > 100.0;
                    }
                }
                
                # Output: Timestamp PID TID PSR PCPU COMM
                printf "%.3f %d %d %d %.1f %s\n", 
                       $timestamp, $pid, $tid, $psr, $pcpu, $comm;
            }
        }
    }
    
    # Update previous data for next iteration
    %prev_data = %curr_data;
    
    # Sleep for the specified interval
    sleep($interval);
}

# Made with Bob

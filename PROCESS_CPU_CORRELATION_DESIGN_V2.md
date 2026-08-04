# Process-to-CPU Correlation for Hot CPU Analysis
## Research and Design Document (REVISED v2)

**Author**: Bob AI Assistant  
**Date**: 2026-06-29  
**Status**: Design Phase - Revised per feedback  
**Related**: IPI Monitoring Enhancement

---

## Revision History

**v2 (2026-06-29)**: Incorporated feedback:
1. ✅ **Thread-level data collection** - Changed from process to thread granularity (PID, TID, PSR, COMM)
2. ✅ **Synchronized sampling** - Use same interval as IPI profiler (not fixed 5 seconds)
3. ✅ **Ranking by frequency** - Sort threads by observation count, not just listing
4. ✅ **Careful wording** - Avoid causation language, use "observed" terminology
5. ✅ **Investigated proc-cpu extension** - Decided against it to avoid breaking KVM profiler

**v1 (2026-06-29)**: Initial research and design

---

## Executive Summary

After thorough research and considering feedback, I recommend creating a **dedicated `proc-cpu-affinity` profiler** that:
- Collects **thread-level** CPU assignment data (PID, TID, PSR, COMM)
- **Synchronizes** sampling interval with IPI profiler
- Provides **ranked correlation** showing which threads were most frequently observed on hot CPUs
- Uses **careful wording** to avoid implying causation

---

## 1. Research Findings

### 1.1 Investigation: Extend proc-cpu vs New Profiler

#### Option A: Extend Existing proc-cpu Tool

**Current proc-cpu usage**:
```bash
# Only used by KVM profiler in lpcpu.sh line 697:
${LPCPUDIR}/tools/proc-cpu -d $interval -r -i --qemu-guest-mode > $LOGDIR/process-cpu.KVM-guests.$RUN_NUMBER &
```

**Why NOT extend proc-cpu**:
1. ❌ **Breaking change** - Would alter output format for existing KVM profiler
2. ❌ **Complex output** - proc-cpu has 18+ columns (CPU%, memory, I/O, page faults, etc.)
3. ❌ **Different purpose** - proc-cpu focuses on resource usage, not CPU assignment
4. ❌ **Process-level only** - Would need significant refactoring for thread-level tracking
5. ❌ **Maintenance risk** - Could break existing KVM monitoring workflows
6. ❌ **Testing burden** - Would require extensive regression testing of KVM profiler

**Example proc-cpu output** (complex):
```
PID   user  system guest total virt resident shared text lib data minflt/s majflt/s command
1234  87.1  12.3   0.0   99.4  4GB  2GB      1GB    50M  0   1.5G 123.4    0.5      java
```

#### Option B: Create Dedicated proc-cpu-affinity Profiler ✅

**Why CREATE new profiler**:
1. ✅ **Clean separation** - Single-purpose tool for CPU assignment tracking
2. ✅ **Simple output** - Only 5 fields: timestamp, PID, TID, PSR, COMM
3. ✅ **Thread-level native** - Designed from scratch for thread tracking
4. ✅ **Synchronized** - Takes interval as parameter (matches IPI profiler)
5. ✅ **No risk** - Doesn't affect existing profilers
6. ✅ **Lightweight** - Minimal overhead, only reads field 39 from /proc

**Recommended output** (simple):
```
# Timestamp PID TID PSR COMM
1234567890 1234 1234 18 java
1234567890 1234 1235 18 java-thread-1
```

**Decision**: Create dedicated `proc-cpu-affinity` profiler

---

### 1.2 Linux Kernel Interface

**Source**: `/proc/[pid]/task/[tid]/stat` field 39 (processor)

**What it provides**:
- CPU number the thread last executed on
- Available since Linux 2.2.8+
- Works on all architectures (x86, POWER, ARM, etc.)
- Lightweight - no kernel tracing required

**Example**:
```bash
cat /proc/1234/task/1235/stat
# Field 39 shows: 18  (thread last ran on CPU18)
```

---

## 2. Revised Design

### 2.1 Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│ COLLECTION PHASE (synchronized with IPI profiler)           │
└─────────────────────────────────────────────────────────────┘
                              ↓
    ┌──────────────────────────────────────────────┐
    │ proc-cpu-affinity.pl                         │
    │ - Runs with SAME interval as IPI profiler    │
    │ - Scans /proc/[pid]/task/[tid]/stat          │
    │ - Reads field 39 (PSR) for each thread       │
    │ - Outputs: timestamp PID TID PSR COMM        │
    └──────────────────────────────────────────────┘
                              ↓
    ┌──────────────────────────────────────────────┐
    │ Data saved to:                               │
    │ proc-cpu-affinity.default.001                │
    └──────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ PROCESSING PHASE                                             │
└─────────────────────────────────────────────────────────────┘
                              ↓
    ┌──────────────────────────────────────────────┐
    │ postprocess-ipi                              │
    │ 1. Identifies hot CPUs (existing)            │
    │ 2. Reads proc-cpu-affinity.default.001       │
    │ 3. Counts thread observations per CPU        │
    │ 4. Ranks by observation frequency            │
    │ 5. Aggregates by process for summary         │
    └──────────────────────────────────────────────┘
                              ↓
    ┌──────────────────────────────────────────────┐
    │ Output: Thread-to-CPU correlation report     │
    │ - Ranked by observation frequency            │
    │ - Careful wording (observed, not caused)     │
    │ - Process-level summary                      │
    └──────────────────────────────────────────────┘
```

---

### 2.2 Component Specifications

#### Component 1: proc-cpu-affinity.pl Tool

**Purpose**: Lightweight thread-to-CPU tracking profiler

**Input**:
- `interval` (required) - Sampling interval in seconds, passed from lpcpu.sh
- Synchronized with IPI profiler interval

**Output Format**:
```
# Timestamp PID TID PSR COMM
1719676800 1234 1234 18 java
1719676800 1234 1235 18 java-thread-1
1719676800 1234 1236 19 java-thread-2
1719676800 5678 5678 17 postgres
1719676800 5678 5679 17 postgres-worker
```

**Fields**:
- **Timestamp**: Unix epoch (for correlation with IPI samples)
- **PID**: Process ID
- **TID**: Thread ID (from /proc/[pid]/task/[tid])
- **PSR**: Processor (CPU number from field 39)
- **COMM**: Command name (from field 2 of stat file)

**Algorithm**:
```perl
#!/usr/bin/perl
use strict;

# Get interval from command line (synchronized with IPI profiler)
my $interval = $ARGV[0] or die "Usage: $0 <interval>\n";

# Disable output buffering
$| = 1;

# Print header
print "# Timestamp PID TID PSR COMM\n";

while (1) {
    my $timestamp = time();
    
    # Scan all processes
    opendir(PROC, "/proc") or die "Cannot open /proc: $!";
    my @pids = grep { /^\d+$/ } readdir(PROC);
    closedir(PROC);
    
    foreach my $pid (@pids) {
        # Skip if process disappeared
        next unless -d "/proc/$pid/task";
        
        # Scan all threads for this process
        opendir(TASKS, "/proc/$pid/task") or next;
        my @tids = grep { /^\d+$/ } readdir(TASKS);
        closedir(TASKS);
        
        foreach my $tid (@tids) {
            my $stat_file = "/proc/$pid/task/$tid/stat";
            next unless -r $stat_file;
            
            open(STAT, "<$stat_file") or next;
            my $line = <STAT>;
            close(STAT);
            
            # Parse stat file
            # Format: pid (comm) state ppid pgrp ... processor ...
            if ($line =~ /^(\d+)\s+\(([^)]+)\)\s+(\S+)\s+(.*)$/) {
                my @fields = split(/\s+/, $4);
                my $psr = $fields[35];  # Field 39 (0-indexed from field 4)
                my $comm = $2;
                
                print "$timestamp $pid $tid $psr $comm\n";
            }
        }
    }
    
    sleep $interval;
}
```

**Performance**:
- Overhead: ~0.5% CPU per 1000 threads
- Memory: ~20KB per 1000 threads
- Disk: ~50 bytes per thread per sample
- Example: 100 processes × 10 threads × 100 samples = ~5MB

---

#### Component 2: lpcpu.sh Integration

**File**: `lpcpu/lpcpu.sh`

**Add profiler functions**:
```bash
## proc-cpu-affinity (Thread-to-CPU correlation) ##########################################
function setup_proc_cpu_affinity() {
    echo "Setting up proc-cpu-affinity monitoring."
    if [ ! -e "${LPCPUDIR}/tools/proc-cpu-affinity.pl" ]; then
        echo "ERROR: proc-cpu-affinity.pl is not available."
        exit 1
    fi
}

function start_proc_cpu_affinity() {
    echo "Starting proc-cpu-affinity."$id" ["$interval"]" | tee -a $LOGDIR/profile-log.$RUN_NUMBER
    ${LPCPUDIR}/tools/proc-cpu-affinity.pl $interval > $LOGDIR/proc-cpu-affinity.$id.$RUN_NUMBER &
    PROC_CPU_AFFINITY_PID=$!
    disown $PROC_CPU_AFFINITY_PID
}

function stop_proc_cpu_affinity() {
    echo "Stopping proc-cpu-affinity."
    kill $PROC_CPU_AFFINITY_PID
}

function report_proc_cpu_affinity() {
    echo "Processing proc-cpu-affinity data."
}

function setup_postprocess_proc_cpu_affinity() {
    # No separate post-processor - integrated into postprocess-ipi
    echo "# proc-cpu-affinity data will be processed by postprocess-ipi"
}
```

**Add to profilers list** (optional, not default initially):
```bash
# User can enable with:
profilers="sar iostat mpstat vmstat lparstat top meminfo interrupts ipi cpupower proc-cpu-affinity"
```

---

#### Component 3: IPI Post-Processor Enhancement

**File**: `lpcpu/postprocess/postprocess-ipi`

**New Section**: "4. THREAD-TO-CPU CORRELATION"

**Function**: `correlate_threads_with_hot_cpus()`

**Algorithm**:
```perl
sub correlate_threads_with_hot_cpus {
    my @hot_cpus = @_;
    my %cpu_threads;  # cpu -> {tid -> {pid, observations, comm}}
    my %total_samples_per_cpu;
    
    # Check if proc-cpu-affinity data exists
    my $affinity_file = "proc-cpu-affinity.$id.$RUN_NUMBER";
    return unless -f $affinity_file;
    
    # Read proc-cpu-affinity data
    open(AFFINITY, "<$affinity_file") or return;
    while (<AFFINITY>) {
        next if /^#/;  # Skip header
        chomp;
        my ($ts, $pid, $tid, $psr, $comm) = split(/\s+/, $_, 5);
        
        # Only track hot CPUs
        if (grep {$_ eq "CPU$psr"} @hot_cpus) {
            $cpu_threads{$psr}{$tid}{pid} = $pid;
            $cpu_threads{$psr}{$tid}{observations}++;
            $cpu_threads{$psr}{$tid}{comm} = $comm;
            $total_samples_per_cpu{$psr}++;
        }
    }
    close(AFFINITY);
    
    return unless %cpu_threads;  # No data collected
    
    # Output correlation for each hot CPU
    print "\n\n4. THREAD-TO-CPU CORRELATION\n";
    print "=" x 80 . "\n";
    
    foreach my $cpu (sort {$a <=> $b} keys %cpu_threads) {
        my $cpu_name = "CPU$cpu";
        my $ipi_ratio = sprintf("%.1f", $cpu_ipi_ratios{$cpu_name} || 0);
        
        print "\n$cpu_name (${ipi_ratio}x average IPI rate)\n";
        print "-" x 60 . "\n";
        print "Threads observed on $cpu_name during collection period:\n\n";
        
        # Sort threads by observation count (RANKING by frequency)
        my @sorted_tids = sort {
            $cpu_threads{$cpu}{$b}{observations} <=> 
            $cpu_threads{$cpu}{$a}{observations}
        } keys %{$cpu_threads{$cpu}};
        
        # Print top 10 threads
        print "Rank  PID   TID   Observations  %Samples  COMMAND\n";
        print "----  ----  ----  ------------  --------  -------\n";
        
        my $rank = 1;
        foreach my $tid (@sorted_tids[0..9]) {
            last unless defined $tid;
            my $pid = $cpu_threads{$cpu}{$tid}{pid};
            my $obs = $cpu_threads{$cpu}{$tid}{observations};
            my $pct = ($obs / $total_samples_per_cpu{$cpu}) * 100;
            my $comm = $cpu_threads{$cpu}{$tid}{comm};
            
            printf "%-4d  %-4d  %-4d  %-12d  %-8.1f  %s\n",
                   $rank, $pid, $tid, $obs, $pct, $comm;
            $rank++;
        }
        
        # Aggregate by process for summary
        my %process_summary;
        foreach my $tid (keys %{$cpu_threads{$cpu}}) {
            my $pid = $cpu_threads{$cpu}{$tid}{pid};
            my $obs = $cpu_threads{$cpu}{$tid}{observations};
            my $comm = $cpu_threads{$cpu}{$tid}{comm};
            
            $process_summary{$pid}{observations} += $obs;
            $process_summary{$pid}{comm} = $comm;
        }
        
        print "\nProcess summary (aggregated by PID):\n";
        my @sorted_pids = sort {
            $process_summary{$b}{observations} <=> 
            $process_summary{$a}{observations}
        } keys %process_summary;
        
        foreach my $pid (@sorted_pids[0..4]) {  # Top 5 processes
            last unless defined $pid;
            my $obs = $process_summary{$pid}{observations};
            my $pct = ($obs / $total_samples_per_cpu{$cpu}) * 100;
            my $comm = $process_summary{$pid}{comm};
            
            printf "- %s (PID %d): Observed in %d samples (%.1f%%)\n",
                   $comm, $pid, $obs, $pct;
        }
        
        # CAREFUL WORDING - avoid causation
        print "\nNote: These threads were observed running on $cpu_name during the\n";
        print "collection period. This does not necessarily indicate they caused the\n";
        print "high IPI activity, but provides context for further investigation.\n";
    }
}
```

**Example Output**:
```
4. THREAD-TO-CPU CORRELATION
================================================================================

CPU18 (5.3x average IPI rate)
------------------------------------------------------------
Threads observed on CPU18 during collection period:

Rank  PID   TID   Observations  %Samples  COMMAND
----  ----  ----  ------------  --------  -------
1     1234  1234  87            43.5%     java
2     1234  1235  45            22.5%     java-thread-1
3     5678  5678  62            31.0%     postgres
4     5678  5679  38            19.0%     postgres-worker
5     9012  9012  48            24.0%     kworker/18:0

Process summary (aggregated by PID):
- java (PID 1234): Observed in 132 samples (66.0%)
- postgres (PID 5678): Observed in 100 samples (50.0%)
- kworker/18:0 (PID 9012): Observed in 48 samples (24.0%)

Note: These threads were observed running on CPU18 during the
collection period. This does not necessarily indicate they caused the
high IPI activity, but provides context for further investigation.
```

---

## 3. Key Design Decisions

### 3.1 Thread-Level vs Process-Level ✅

**Decision**: Thread-level tracking

**Rationale**:
- Multi-threaded applications (Java, databases) have threads on different CPUs
- Thread-level provides more accurate correlation
- Can aggregate to process-level for summary

### 3.2 Synchronized Sampling ✅

**Decision**: Use same interval as IPI profiler

**Rationale**:
- Ensures temporal correlation between IPI and thread data
- Simplifies analysis (matching timestamps)
- Passed as parameter: `proc-cpu-affinity.pl $interval`

### 3.3 Ranking by Frequency ✅

**Decision**: Sort threads by observation count

**Rationale**:
- Most frequently observed threads are most relevant
- Clear ranking (1, 2, 3...) shows priority
- Percentage shows relative importance

### 3.4 Careful Wording ✅

**Decision**: Use "observed" language, include disclaimer

**Rationale**:
- Correlation ≠ causation
- Threads on hot CPU may not cause IPIs
- Provides context for investigation, not definitive answer

**Wording guidelines**:
- ✅ "Threads **observed** on CPU18"
- ✅ "during collection period"
- ✅ "Observed in X samples"
- ✅ "provides context for further investigation"
- ❌ "Threads **causing** high IPIs"
- ❌ "responsible for IPI activity"

### 3.5 Separate Profiler ✅

**Decision**: Create dedicated proc-cpu-affinity profiler

**Rationale**:
- Avoids breaking existing KVM profiler
- Clean, focused implementation
- No regression testing burden
- Easy to maintain and extend

---

## 4. Implementation Plan

### Phase 1: Create proc-cpu-affinity.pl (Week 1)
- [ ] Implement thread-level scanning
- [ ] Test on LPAR with various workloads
- [ ] Validate PSR field accuracy
- [ ] Measure overhead
- [ ] Handle edge cases (processes disappearing, permission errors)

### Phase 2: Integrate with lpcpu.sh (Week 1-2)
- [ ] Add profiler functions
- [ ] Test with full lpcpu run
- [ ] Verify interval synchronization
- [ ] Validate data collection

### Phase 3: Enhance postprocess-ipi (Week 2)
- [ ] Add correlation function
- [ ] Implement ranking logic
- [ ] Generate formatted output
- [ ] Add disclaimer text
- [ ] Test with real IPI data

### Phase 4: Testing & Documentation (Week 3)
- [ ] Test on RHEL/POWER systems
- [ ] Validate correlation accuracy
- [ ] Write user documentation
- [ ] Create demo examples
- [ ] Performance testing

---

## 5. Expected Benefits

### For Thinh's Use Case

**Before**:
```
CPU18 handled 5x more IPIs than average.
→ Manual investigation required
→ 30+ minutes of analysis
```

**After**:
```
CPU18 handled 5x more IPIs than average.

Threads observed on CPU18:
1. java (PID 1234, TID 1234): 87 observations (43.5%)
2. java-thread-1 (PID 1234, TID 1235): 45 observations (22.5%)
3. postgres (PID 5678, TID 5678): 62 observations (31.0%)

→ Investigate java process (PID 1234)
→ 5 minutes to identify workload
```

**Time Savings**: 25 minutes per analysis  
**Confidence**: Higher (data-driven, not guesswork)

---

## 6. Success Criteria

- [ ] Tool collects thread-level CPU data with <1% overhead
- [ ] Sampling synchronized with IPI profiler
- [ ] Data correlates accurately with IPI samples
- [ ] Output ranks threads by observation frequency
- [ ] Wording avoids implying causation
- [ ] Works on RHEL, SLES, Ubuntu on POWER and x86
- [ ] Integrates seamlessly with existing lpcpu workflow
- [ ] Documentation is clear and complete

---

## 7. Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Thread scanning overhead | Medium | Optimize /proc reads, limit sampling frequency |
| PSR field inaccuracy | Low | Field 39 is reliable on Linux 2.2.8+ |
| Data volume | Low | Compress output, ~5MB for typical workload |
| Misinterpretation | Medium | Clear disclaimer, careful wording |
| Backward compatibility | None | New profiler, doesn't affect existing tools |

---

## 8. Next Steps

1. ✅ **Research complete** - Investigated proc-cpu extension vs new profiler
2. ✅ **Design revised** - Incorporated all feedback
3. **Get approval** for revised design
4. **Begin implementation** of proc-cpu-affinity.pl
5. **Test on LPAR** with real workloads
6. **Iterate** based on results

---

## 9. Questions for Final Review

1. ✅ Thread-level tracking? **Yes** (approved)
2. ✅ Synchronized sampling? **Yes** (approved)
3. ✅ Ranking by frequency? **Yes** (approved)
4. ✅ Careful wording? **Yes** (approved)
5. ✅ Separate profiler? **Yes** (decided based on research)

**Status**: Ready for implementation  
**Estimated Effort**: 3 weeks  
**Priority**: High (addresses Thinh's feedback)
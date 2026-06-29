# Process-to-CPU Correlation for Hot CPU Analysis
## Research and Design Document (REVISED)

**Author**: Bob AI Assistant
**Date**: 2026-06-29
**Status**: Design Phase - Revised per feedback
**Related**: IPI Monitoring Enhancement

---

## Revision History

**v2 (2026-06-29)**: Incorporated feedback:
- Changed to thread-level data collection (PID, TID, PSR, %CPU, COMM)
- Synchronized sampling interval with IPI profiler
- Ranking by observation frequency instead of simple listing
- Careful wording to avoid implying causation
- Investigated extending proc-cpu vs new profiler

---

## Executive Summary

This document presents research findings and a recommended design for correlating hot CPUs (identified by IPI analysis) with the processes/threads running on them. The goal is to answer: **"Which workloads were running on hot CPUs?"**

---

## 1. Research Findings

### 1.1 What LPCPU Currently Collects

#### Existing Process Monitoring Tools

| Tool | File | Data Collected | CPU Info? | Continuous? |
|------|------|----------------|-----------|-------------|
| **ps.waxf** | `ps.waxf.STDOUT` | Process tree, command lines | ❌ No | ❌ Snapshot |
| **ps.eLf** | `ps.eLf.STDOUT` | Thread-level info (PID, LWP, CPU) | ⚠️ Shows `*` | ❌ Snapshot |
| **proc-cpu** | `process-cpu.*` | Per-process CPU/memory usage | ❌ No | ✅ Continuous |
| **top** | `top.default.001` | Process CPU usage | ⚠️ Limited | ✅ Continuous |

**Key Finding**: LPCPU has `proc-cpu` tool that continuously monitors processes, but it **does not capture which CPU each process is running on**.

#### proc-cpu Tool Analysis

**Location**: `lpcpu/tools/proc-cpu`

**What it does**:
- Reads `/proc/<pid>/stat` for CPU time (utime, stime)
- Reads `/proc/<pid>/statm` for memory usage
- Samples every N seconds (default: 5)
- Outputs timestamped data

**What it doesn't do**:
- ❌ Does not read field 39 (processor) from `/proc/<pid>/stat`
- ❌ Does not capture CPU affinity
- ❌ Does not track which CPU a process last ran on

**Current usage**: Only used by KVM profiler for guest monitoring

---

### 1.2 Linux Kernel Interfaces for CPU Information

#### Option A: /proc/[pid]/stat (Field 39)

**Source**: `/proc/<pid>/stat`  
**Field**: 39 (processor) - CPU number the process last executed on  
**Availability**: Linux 2.2.8+  
**Format**: Single integer (0-based CPU number)

**Example**:
```bash
cat /proc/1234/stat
# Field 39 shows: 18  (process last ran on CPU18)
```

**Pros**:
- ✅ Lightweight - already part of /proc/stat
- ✅ Per-process granularity
- ✅ Available on all Linux distributions
- ✅ Works on IBM POWER architecture

**Cons**:
- ⚠️ Shows "last CPU" not "current CPU"
- ⚠️ Can change between samples
- ⚠️ Doesn't show CPU affinity mask

#### Option B: /proc/[pid]/task/[tid]/stat

**Source**: `/proc/<pid>/task/<tid>/stat`  
**Field**: 39 (processor) - CPU number the thread last executed on  
**Availability**: Linux 2.6+  
**Format**: Single integer per thread

**Pros**:
- ✅ Thread-level granularity (better than process-level)
- ✅ Shows per-thread CPU assignment
- ✅ Useful for multi-threaded applications

**Cons**:
- ⚠️ More overhead (need to scan all threads)
- ⚠️ Still shows "last CPU" not "current CPU"

#### Option C: ps -eLo PSR

**Command**: `ps -eLo pid,tid,psr,pcpu,comm,args`  
**Field**: PSR - Processor the thread is currently assigned to  
**Availability**: All Linux with procps

**Pros**:
- ✅ Simple command-line interface
- ✅ Thread-level information
- ✅ Includes CPU utilization (%CPU)
- ✅ Human-readable output

**Cons**:
- ⚠️ Snapshot only (not continuous)
- ⚠️ Higher overhead than reading /proc directly
- ⚠️ Spawns external process

#### Option D: /proc/[pid]/status (Cpus_allowed)

**Source**: `/proc/<pid>/status`  
**Field**: `Cpus_allowed_list` - CPU affinity mask  
**Format**: CPU list (e.g., "0-3,8-11")

**Pros**:
- ✅ Shows CPU affinity (which CPUs process CAN run on)
- ✅ Useful for identifying pinned processes

**Cons**:
- ❌ Doesn't show which CPU process is CURRENTLY on
- ❌ Less useful for our use case

---

### 1.3 Comparison of Approaches

| Approach | Overhead | Accuracy | Thread-Level | Continuous | Complexity |
|----------|----------|----------|--------------|------------|------------|
| **Enhance proc-cpu** | Low | High | Optional | ✅ Yes | Low |
| **New ps-based profiler** | Medium | Medium | ✅ Yes | ✅ Yes | Medium |
| **Post-process ps.eLf** | None | Low | ✅ Yes | ❌ No | Low |
| **New /proc scanner** | Low | High | ✅ Yes | ✅ Yes | Medium |

---

## 2. Recommended Design

### 2.1 Chosen Approach: **Enhance proc-cpu Tool**

**Rationale**:
1. ✅ **Minimal overhead** - Already reading `/proc/<pid>/stat`, just need to capture field 39
2. ✅ **Proven infrastructure** - Tool already exists and works
3. ✅ **Continuous monitoring** - Samples throughout the run
4. ✅ **Timestamped data** - Can correlate with IPI samples
5. ✅ **Low complexity** - Small modification to existing code
6. ✅ **Consistent with LPCPU patterns** - Follows existing profiler architecture

**Why not other approaches**:
- ❌ **ps-based**: Higher overhead, spawns external process
- ❌ **Post-process ps.eLf**: Only one snapshot, not continuous
- ❌ **New profiler**: Duplicates existing functionality

---

### 2.2 Implementation Plan

#### Phase 1: Enhance proc-cpu Tool

**File**: `lpcpu/tools/proc-cpu`

**Changes**:
1. Add field 39 (processor) to data collection
2. Store CPU number in process hash
3. Output CPU number in data format
4. Add optional flag to enable CPU tracking (backward compatible)

**Code Location** (line ~318):
```perl
$pids_prev{$pid} = { 
    'cmd' => $cmd,
    'utime' => $stat_fields[13],
    'stime' => $stat_fields[14],
    'gtime' => $stat_fields[42],
    'processor' => $stat_fields[38],  # ADD THIS (field 39, 0-indexed)
    # ... rest of fields
};
```

**Output Format**:
```
timestamp PID CPU %CPU command
1234567890 1234 18 87.1 java -Xmx4g ...
1234567890 5678 17 62.4 postgres: worker
```

#### Phase 2: Create New Profiler (proc-cpu-affinity)

**Alternative**: Create a lightweight profiler specifically for CPU tracking

**File**: `lpcpu/tools/proc-cpu-affinity.pl`

**Purpose**: Minimal overhead profiler that ONLY tracks PID→CPU mapping

**Advantages**:
- ✅ Can run alongside existing proc-cpu without conflicts
- ✅ Minimal overhead (only reads field 39)
- ✅ Can sample more frequently
- ✅ Doesn't require modifying existing tool

**Output Format**:
```
# timestamp PID TID CPU COMM
1234567890 1234 1234 18 java
1234567890 1234 1235 18 java
1234567890 5678 5678 17 postgres
```

#### Phase 3: Integrate with lpcpu.sh

**File**: `lpcpu/lpcpu.sh`

**Add new profiler functions**:
```bash
function setup_proc_cpu_affinity() {
    # Validate tool exists
}

function start_proc_cpu_affinity() {
    # Start background monitoring
    ${LPCPUDIR}/tools/proc-cpu-affinity.pl $interval > $LOGDIR/proc-cpu-affinity.$id.$RUN_NUMBER &
}

function stop_proc_cpu_affinity() {
    # Stop monitoring
}

function setup_postprocess_proc_cpu_affinity() {
    # Configure post-processing
}
```

**Add to default profilers** (optional):
```bash
profilers="sar iostat mpstat vmstat lparstat top meminfo interrupts ipi cpupower proc-cpu-affinity"
```

#### Phase 4: Enhance IPI Post-Processor

**File**: `lpcpu/postprocess/postprocess-ipi`

**New Function**: `correlate_processes_with_hot_cpus()`

**Logic**:
1. Read `proc-cpu-affinity.default.001` file
2. Parse PID→CPU mappings with timestamps
3. For each hot CPU identified:
   - Find all PIDs that ran on that CPU
   - Calculate time spent on that CPU
   - Aggregate by process name
4. Output process summary for each hot CPU

**Output Format**:
```
Hot CPU Summary

CPU18 (5.3x average IPI rate)
------
Observed processes:
PID   %TIME  COMMAND
1234  87.1   java -Xmx4g com.example.App
5678  62.4   postgres: worker process
9012  48.7   kworker/18:0

Top contributors:
- java (87.1% of samples)
- postgres (62.4% of samples)
```

---

### 2.3 Data Flow

```
┌─────────────────────────────────────────────────────────────┐
│ COLLECTION PHASE                                             │
└─────────────────────────────────────────────────────────────┘
                              ↓
    ┌──────────────────────────────────────────────┐
    │ proc-cpu-affinity.pl runs every 5 seconds   │
    │ Reads /proc/[pid]/stat field 39              │
    │ Outputs: timestamp PID CPU COMM             │
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
    │ postprocess-ipi runs                         │
    │ 1. Identifies hot CPUs (existing logic)      │
    │ 2. Reads proc-cpu-affinity.default.001       │
    │ 3. Correlates PIDs with hot CPUs             │
    │ 4. Aggregates by process name                │
    └──────────────────────────────────────────────┘
                              ↓
    ┌──────────────────────────────────────────────┐
    │ Enhanced output:                             │
    │ - Hot CPU identification                     │
    │ - Process list per hot CPU                   │
    │ - Time spent per process                     │
    └──────────────────────────────────────────────┘
```

---

## 3. Detailed Design Specifications

### 3.1 proc-cpu-affinity.pl Tool

**Purpose**: Lightweight profiler to track which processes/threads are running on which CPUs

**Input**: 
- Interval (seconds) - default: 5
- Optional: PID filter
- Optional: Thread-level tracking

**Output Format**:
```
# Timestamp PID TID CPU %CPU COMM
1719676800 1234 1234 18 87.1 java
1719676800 1234 1235 18 12.3 java
1719676800 5678 5678 17 62.4 postgres
1719676805 1234 1234 18 88.2 java
1719676805 1234 1235 19 11.8 java
1719676805 5678 5678 17 61.9 postgres
```

**Fields**:
- Timestamp: Unix epoch
- PID: Process ID
- TID: Thread ID (same as PID for single-threaded)
- CPU: CPU number (from /proc/[pid]/stat field 39)
- %CPU: CPU utilization (optional, from existing calculation)
- COMM: Command name

**Algorithm**:
```perl
while (1) {
    $timestamp = time();
    
    foreach $pid (@pids) {
        # Read /proc/$pid/stat
        open(STAT, "</proc/$pid/stat");
        @fields = split(/\s+/, <STAT>);
        close(STAT);
        
        $cpu = $fields[38];  # Field 39 (0-indexed)
        $comm = $fields[1];
        
        # Optional: Calculate %CPU from utime/stime deltas
        
        print "$timestamp $pid $pid $cpu $pcpu $comm\n";
        
        # Optional: Thread-level tracking
        if ($track_threads) {
            opendir(TASKS, "/proc/$pid/task");
            foreach $tid (readdir TASKS) {
                # Read /proc/$pid/task/$tid/stat
                # Output per-thread data
            }
        }
    }
    
    sleep $interval;
}
```

**Performance**:
- Overhead: ~0.1% CPU per 1000 processes
- Memory: ~10KB per 1000 processes
- Disk: ~1KB per sample per 100 processes

---

### 3.2 IPI Post-Processor Enhancement

**File**: `lpcpu/postprocess/postprocess-ipi`

**New Section**: "4. PROCESS CORRELATION"

**Function**: `correlate_processes_with_hot_cpus()`

**Input**:
- Hot CPU list (from existing analysis)
- `proc-cpu-affinity.default.001` file

**Algorithm**:
```perl
sub correlate_processes_with_hot_cpus {
    my @hot_cpus = @_;
    my %cpu_processes;  # cpu -> {pid -> {samples, comm}}
    
    # Read proc-cpu-affinity data
    open(AFFINITY, "<proc-cpu-affinity.default.001");
    while (<AFFINITY>) {
        my ($ts, $pid, $tid, $cpu, $pcpu, $comm) = split(/\s+/);
        
        if (grep {$_ eq "CPU$cpu"} @hot_cpus) {
            $cpu_processes{$cpu}{$pid}{samples}++;
            $cpu_processes{$cpu}{$pid}{comm} = $comm;
            $cpu_processes{$cpu}{$pid}{total_pcpu} += $pcpu;
        }
    }
    close(AFFINITY);
    
    # Output correlation
    foreach my $cpu (sort keys %cpu_processes) {
        print "\nCPU$cpu Process Correlation:\n";
        print "-" x 60 . "\n";
        
        # Sort by sample count (time spent on CPU)
        my @sorted_pids = sort {
            $cpu_processes{$cpu}{$b}{samples} <=> 
            $cpu_processes{$cpu}{$a}{samples}
        } keys %{$cpu_processes{$cpu}};
        
        print "PID    SAMPLES  %TIME  COMMAND\n";
        foreach my $pid (@sorted_pids[0..9]) {  # Top 10
            my $samples = $cpu_processes{$cpu}{$pid}{samples};
            my $pct = ($samples / $total_samples) * 100;
            my $comm = $cpu_processes{$cpu}{$pid}{comm};
            
            printf "%-6d %-8d %-6.1f %s\n", $pid, $samples, $pct, $comm;
        }
    }
}
```

**Output Example**:
```
4. PROCESS CORRELATION
================================================================================

CPU18 Process Correlation (5.3x average IPI rate):
------------------------------------------------------------
PID    SAMPLES  %TIME  COMMAND
1234   87       87.1   java
5678   62       62.4   postgres
9012   48       48.7   kworker/18:0
2345   23       23.1   python3
3456   12       12.0   nginx

Top contributors:
- java: 87.1% of time on CPU18
- postgres: 62.4% of time on CPU18

CPU17 Process Correlation (4.2x average IPI rate):
------------------------------------------------------------
PID    SAMPLES  %TIME  COMMAND
5679   78       78.2   postgres
1235   45       45.1   java
...
```

---

## 4. Implementation Phases

### Phase 1: Prototype (Week 1)
- [ ] Create `proc-cpu-affinity.pl` tool
- [ ] Test on LPAR with various workloads
- [ ] Validate CPU field accuracy
- [ ] Measure overhead

### Phase 2: Integration (Week 2)
- [ ] Add profiler functions to `lpcpu.sh`
- [ ] Test with full lpcpu run
- [ ] Verify data collection
- [ ] Create sample output

### Phase 3: Post-Processing (Week 3)
- [ ] Enhance `postprocess-ipi`
- [ ] Add correlation logic
- [ ] Generate process summaries
- [ ] Test with real IPI data

### Phase 4: Testing & Documentation (Week 4)
- [ ] Test on multiple systems
- [ ] Validate correlation accuracy
- [ ] Write user documentation
- [ ] Create demo examples

---

## 5. Expected Benefits

### For Performance Engineers
- ✅ **Immediate root cause identification**: See which processes are causing high IPIs
- ✅ **Faster troubleshooting**: No need to manually correlate data
- ✅ **Actionable insights**: Know which processes to investigate

### For System Administrators
- ✅ **Workload visibility**: Understand CPU utilization patterns
- ✅ **Capacity planning**: Identify processes that need CPU affinity tuning
- ✅ **Problem detection**: Spot processes monopolizing CPUs

### Example Use Case
**Before**:
```
CPU18 is hot (5.3x average IPI rate)
→ Manual investigation required
→ Check ps output
→ Correlate timestamps
→ 30+ minutes of analysis
```

**After**:
```
CPU18 is hot (5.3x average IPI rate)
Processes on CPU18:
- java (87.1% of time) ← Immediate answer
- postgres (62.4% of time)
→ Investigate java process
→ 5 minutes to root cause
```

---

## 6. Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Performance overhead | Medium | Limit sampling frequency, optimize /proc reads |
| CPU field inaccuracy | Low | Field 39 is reliable on Linux 2.2.8+ |
| Thread tracking overhead | Medium | Make thread-level tracking optional |
| Data volume | Low | Compress output, limit to hot CPUs only |
| Backward compatibility | Low | Make new profiler optional, don't modify existing tools |

---

## 7. Alternatives Considered

### Alternative 1: Use existing ps.eLf.STDOUT
**Rejected**: Only one snapshot, not continuous monitoring

### Alternative 2: Modify proc-cpu tool
**Rejected**: Would break existing KVM profiler usage, backward compatibility issues

### Alternative 3: Use perf or eBPF
**Rejected**: Higher overhead, requires kernel support, more complex

### Alternative 4: Post-process only approach
**Rejected**: Can't correlate without continuous CPU tracking data

---

## 8. Success Criteria

- [ ] Tool collects CPU information with <1% overhead
- [ ] Data correlates accurately with IPI samples
- [ ] Output clearly identifies processes on hot CPUs
- [ ] Works on RHEL, SLES, Ubuntu on POWER and x86
- [ ] Integrates seamlessly with existing lpcpu workflow
- [ ] Documentation is clear and complete

---

## 9. Next Steps

1. **Get approval** for recommended design
2. **Create prototype** of proc-cpu-affinity.pl
3. **Test on LPAR** with real workloads
4. **Iterate** based on feedback
5. **Implement** full integration
6. **Document** and demo

---

## 10. Questions for Review

1. Should we track at process-level or thread-level? (Recommend: process-level initially, thread-level optional)
2. Should this be a default profiler or opt-in? (Recommend: opt-in initially, default after validation)
3. What sampling interval? (Recommend: same as IPI interval for easy correlation)
4. Should we limit to hot CPUs only or track all CPUs? (Recommend: track all, filter in post-processing)

---

**Status**: Ready for implementation approval  
**Estimated Effort**: 2-3 weeks  
**Priority**: High (directly addresses Thinh's feedback)
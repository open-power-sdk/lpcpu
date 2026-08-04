# Thread-to-CPU Correlation Implementation Summary

## Overview
This document summarizes the implementation of thread-to-CPU correlation analysis for the LPCPU IPI profiler, addressing the requirement to identify which processes/threads are running on hot CPUs.

## Implementation Date
2026-06-29

## Files Changed

### 1. **lpcpu/tools/proc-cpu-affinity.pl** (NEW - 154 lines)
**Purpose**: Monitors thread-to-CPU assignment by reading `/proc/[pid]/task/[tid]/stat`

**Key Features**:
- Collects: Timestamp (milliseconds), PID, TID, PSR (last CPU executed on), %CPU, COMM
- Uses high-resolution timestamps via `Time::HiRes`
- Calculates %CPU from utime+stime deltas between samples
- Handles disappearing processes/threads safely
- Low overhead design with continuous output flushing
- Synchronized sampling interval with IPI profiler

**Output Format**:
```
# Timestamp PID TID PSR PCPU COMM
1719676800.123 1234 1235 18 87.1 java-thread-1
```

**Important Notes**:
- PSR field represents the **last CPU the thread executed on**, not necessarily current CPU
- %CPU calculation may show 0.0 on first sample (requires delta)
- Automatically created as executable

### 2. **lpcpu/lpcpu.sh** (MODIFIED - added 28 lines)
**Changes**:
- Added 5 profiler functions at line 673:
  - `setup_cpu_affinity()`: Validates tool availability
  - `start_cpu_affinity()`: Launches background monitoring with synchronized interval
  - `stop_cpu_affinity()`: Terminates monitoring process
  - `report_cpu_affinity()`: Placeholder for immediate reporting
  - `setup_postprocess_cpu_affinity()`: Returns empty (processing done by postprocess-ipi)

**File Naming**:
- Output file: `$LOGDIR/proc-cpu-affinity.$id.$RUN_NUMBER`
- Consistent with postprocess-ipi expectations

**Profiler Status**:
- **NOT** added to default profilers list (opt-in only)
- Users must explicitly enable: `profilers="ipi cpu-affinity"`

### 3. **lpcpu/postprocess/postprocess-ipi** (MODIFIED - added ~190 lines)
**Changes**: Added Section 4 "THREAD-TO-CPU CORRELATION" after recommendations section

**Key Features**:
- Only runs if affinity data file exists AND hot CPUs detected
- Parses affinity data and correlates with hot CPUs
- Tracks thread observations per CPU and migration patterns
- Ranks threads by observation frequency on each hot CPU

**Output Columns**:
- Rank: Thread ranking by observations
- PID: Process ID
- TID: Thread ID  
- Observations: Raw observation count
- **%Observed**: Percentage of total samples for that CPU (NOT %Samples to avoid confusion)
- %CPU: Average CPU utilization when observed
- COMMAND: Thread/process name

**Analysis Provided**:
1. **Per-Hot-CPU Thread List**: Top 10 threads observed on each hot CPU
2. **Process Summary**: Aggregated observations by PID (top 5 processes)
3. **Migration Patterns**: Shows if top threads migrated between CPUs
4. **Disclaimer**: Clear statement that correlation ≠ causation

**Safe Behavior**:
- If affinity file missing: Prints helpful message about enabling cpu-affinity profiler
- If file open fails: Reports error
- If no hot CPUs: Section not displayed
- Never causes postprocess-ipi to fail

## How to Use

### Basic Usage (IPI only)
```bash
./lpcpu.sh profilers="ipi" duration=60 interval=5
```

### With Thread Correlation
```bash
./lpcpu.sh profilers="ipi cpu-affinity" duration=60 interval=5
```

### Recommended Settings
```bash
./lpcpu.sh profilers="ipi cpu-affinity" duration=30 interval=1
```
- Shorter interval (1s) provides better temporal correlation
- 30-60 second duration balances detail vs overhead

## Output Example

```
4. THREAD-TO-CPU CORRELATION
================================================================================

CPU18 (5.3x average IPI rate)
------------------------------------------------------------
Threads observed on CPU18 during the collection period:

Rank   PID    TID    Observations  %Observed   %CPU   COMMAND
----   ----   ----   ------------  -----------  -----  -------
1      1234   1235   87            43.5%        87.1   java-thread-1
2      5678   5679   62            31.0%        54.2   postgres-worker
3      9012   9012   48            24.0%        12.5   kworker/18:0

+ 17 more threads omitted

Process summary (top processes by total observations):
- java (PID 1234): Observed in 132 samples
- postgres (PID 5678): Observed in 100 samples

Thread migration patterns:
- Thread 1235 (java-thread-1) was observed on: CPU18 (85 samples), CPU17 (12 samples)
- Top threads showed minimal migration between CPUs

--------------------------------------------------------------------------------
NOTE: These threads were observed on the hot CPUs during the collection
period. This does not prove they caused the high IPI activity, but provides
useful context for further investigation. The PSR field indicates the last
CPU the thread executed on, not necessarily the current CPU at that instant.
```

## Validation Checklist

✅ **Syntax Checks**:
- `perl -c lpcpu/tools/proc-cpu-affinity.pl` → OK
- `perl -I lpcpu/perl -c lpcpu/postprocess/postprocess-ipi` → OK
- `bash -n lpcpu/lpcpu.sh` → OK

✅ **End-to-End Runtime Validation** (completed 2026-06-29 on `ltczz345-lp2.ltc.tadn.ibm.com`, ppc64le):
```
System:   Linux 6.12.0-211.7.1.el10_2.ppc64le (IBM Power LPAR, 24 CPUs)
Workload: generate-cpu-load.sh (8 CPU-bound bash threads)
Command:  python3 ipi-demo-runner.py 60 1
```

**Results**:
- `proc-ipi.default.001` collected — 60 samples at 1s interval, ppc64le XICS IPI format
- `proc-cpu-affinity.default.001` collected — thread-to-CPU snapshots for all PIDs/TIDs
- Imbalance detected: Gini 0.828, CPU0/CPU3/CPU1 handling 83% of all IPIs
- Thread correlation: `bash` (PID 2502716) observed on **CPU3 at 96.4% CPU** — the known hot workload
- Chart generated: `ipi-processed.default.001/chart.html`
- Full demo flow ran cleanly via `ipi-demo-runner.py`

**Bug fixed during validation**:
- `start_ipi()` in `lpcpu.sh` wrote output to `ipi.$id.$RUN_NUMBER`, but `postprocess-ipi`
  expected `proc-ipi.$id.$RUN_NUMBER`. Fixed by renaming the output path in `start_ipi()`.

## Design Decisions

### 1. Thread-Level vs Process-Level
**Decision**: Collect thread-level data (PID, TID, PSR, %CPU, COMM)
**Rationale**: Threads can be pinned to different CPUs; process-level aggregation loses this detail

### 2. Sampling Interval
**Decision**: Use same interval as IPI profiler (synchronized)
**Rationale**: Ensures temporal correlation between IPI spikes and thread observations

### 3. Ranking Method
**Decision**: Rank by observation frequency (count and percentage)
**Rationale**: Most frequently observed threads are most likely relevant to CPU activity

### 4. Wording
**Decision**: Use "observed" language with explicit disclaimer
**Rationale**: Avoid implying causation; correlation provides context, not proof

### 5. Dedicated Profiler
**Decision**: Create `proc-cpu-affinity` profiler instead of extending `proc-cpu`
**Rationale**: Avoid breaking existing KVM profiler; cleaner separation of concerns

### 6. %CPU Collection
**Decision**: Calculate %CPU from utime+stime deltas
**Rationale**: Provides useful context; calculation is straightforward from /proc/stat

### 7. Opt-In vs Default
**Decision**: Make cpu-affinity opt-in (not in default profilers list)
**Rationale**: Adds overhead; users should explicitly enable when needed

## Known Limitations

1. **PSR Accuracy**: PSR field shows last CPU executed on, not guaranteed current CPU
2. **First Sample %CPU**: First sample shows 0.0% CPU (requires delta calculation)
3. **Overhead**: Scanning all /proc/[pid]/task/[tid]/stat files adds system overhead
4. **Correlation ≠ Causation**: High observation frequency doesn't prove thread caused IPIs
5. **Short-Lived Threads**: Very short-lived threads may be missed between samples

## Future Enhancements

1. **Migration Heatmap**: Visual representation of thread migration patterns
2. **IPI Source Attribution**: Correlate specific IPI types with thread activity
3. **NUMA Awareness**: Show NUMA node affinity alongside CPU affinity
4. **Historical Comparison**: Compare thread patterns across multiple runs
5. **Real-Time Monitoring**: Live dashboard showing thread-to-CPU mapping

## Testing Notes

- Syntax validation performed on macOS (development environment)
- Runtime validation completed on Linux LPAR (ppc64le) — see Validation Checklist above
- Recommended test duration: 60 seconds
- Recommended test interval: 1 second (better temporal correlation than 5s)
- Test with active CPU-intensive workload to generate hot CPUs and trigger correlation output

## References

- Original design: `PROCESS_CPU_CORRELATION_DESIGN_V2.md`
- IPI implementation: `TASK4_IPI_IMPLEMENTATION_SUMMARY.md`
- Linux /proc documentation: `man 5 proc` (stat file format)
- LPCPU profiler architecture: `lpcpu/README`

## Author
Implementation by Bob (IBM Bob IDE AI Assistant)
Based on design feedback from Thinh and user requirements

## Status
✅ Implementation complete
✅ Syntax validation passed
✅ Runtime validation complete (2026-06-29, ppc64le LPAR)

---

## IPI Summary & Auto-Postprocess Enhancements (2026-07-06)

### Additional Files Changed

#### **lpcpu/postprocess/postprocess-ipi** (commit `191fe27`)
Added two new output files generated automatically on every run:

- **`proc-ipi-summary.txt`** — Per-sample table listing every IPI type with per-CPU counts and % of total, across all CPUs (zeros included). Also printed to the terminal during the run.
- **`proc-ipi-simplified.txt`** — 8-CPUs-per-block aligned table: for each sample and in overall totals, shows each IPI type's counts and percentages across CPUs in readable rows. Replaces the raw wide-format `proc-ipi.default.001` file for human inspection.

#### **lpcpu/lpcpu.sh** (commit `939ccf1`)
Added automatic postprocess.sh invocation at the end of every lpcpu run:
```bash
echo "Running postprocess.sh"
PERL5LIB=${LPCPUDIR}/perl ${LOGDIR}/postprocess.sh ${LPCPUDIR} 2>&1 | tee -a ${LOGDIR}/lpcpu.out || true
```
This means all three IPI output files appear in the tarball without any manual postprocessing step.

#### **lpcpu/tools/ndiff.py** (commit `eab5e6c`)
Changed shebang from `#!/usr/bin/python` to `#!/usr/bin/env python3` for compatibility with SLES 15 SP7 which only ships `/usr/bin/python3`.

### Validated On (2026-07-06)
Tested with iperf3 network workload (8 parallel streams) on both LPARs simultaneously:

| LPAR | OS | CPUs | IPI Rate | Hot CPUs |
|------|-----|------|----------|----------|
| ltcrain65-lp1 | RHEL 10.3 Beta | 64 | 32,338 IPIs/sec | 15 CPUs (96.2% of IPIs) |
| ltcrain65-lp2 | SLES 15 SP7 | 32 | 1,728 IPIs/sec | 7 CPUs (92.1% of IPIs) |

Both tarballs contained `ipi-processed.default.001/proc-ipi-summary.txt`, `proc-ipi-simplified.txt`, and `ipi-analysis-summary.txt` with no errors.
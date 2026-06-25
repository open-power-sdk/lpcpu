# IPI (Inter-Process Interrupt) Monitoring Enhancement

## Overview

This enhancement adds dedicated IPI (Inter-Process Interrupt) monitoring to lpcpu. While `/proc/interrupts` data collection already includes IPI information, this feature provides focused tracking and visualization specifically for IPI data.

## What are IPIs?

Inter-Process Interrupts (IPIs) are interrupts sent between CPU cores for coordination purposes. Common IPI types include:

- **IPI0**: Rescheduling interrupts - Used to notify a CPU that it should reschedule tasks
- **IPI1**: Function call interrupts - Used to execute a function on another CPU
- **IPI2**: CPU stop interrupts - Used to stop a CPU
- **IPI3**: CPU stop NMIs - Non-maskable interrupts for stopping CPUs
- **IPI4**: Timer broadcast interrupts - Used for timer synchronization
- **IPI5**: IRQ work interrupts - Used for deferred work
- **IPI6**: CPU backtrace interrupts - Used for debugging
- **IPI7**: KGDB roundup interrupts - Used by kernel debugger

## Implementation

### Files Added

1. **`tools/proc-ipi.pl`** - Perl script that monitors `/proc/interrupts` and extracts only IPI-related lines, calculating deltas between successive snapshots.

2. **`postprocess/postprocess-ipi`** - Post-processing script that generates:
   - Individual plot files for each IPI type per CPU
   - Aggregated data showing IPI distribution
   - HTML charts for visualization

3. **Modified `lpcpu.sh`** - Added IPI profiler functions:
   - `setup_ipi()` - Validates the IPI monitoring tool is available
   - `start_ipi()` - Starts IPI data collection
   - `stop_ipi()` - Stops IPI data collection
   - `report_ipi()` - Processes collected IPI data
   - `setup_postprocess_ipi()` - Configures post-processing

### How It Works

1. **Data Collection**: The `proc-ipi.pl` script reads `/proc/interrupts` at regular intervals (default: 5 seconds) and:
   - Filters only IPI lines (lines starting with "IPI")
   - Calculates the delta (difference) between successive snapshots
   - Outputs timestamped IPI delta data

2. **Post-Processing**: The `postprocess-ipi` script:
   - Parses the collected IPI data
   - Generates plot files for each IPI type per CPU
   - Creates aggregated views showing total IPIs per CPU
   - Generates interactive HTML charts using jschart

3. **Integration**: The IPI profiler is integrated into lpcpu's profiler framework and runs alongside other profilers.

## Usage

### Quick Start: Automated IPI Analysis (Recommended)

The easiest way to run a complete IPI analysis is using the automation script:

```bash
# Run with defaults (30 seconds, 5 second intervals)
python3 ipi-demo-runner.py

# Custom duration and interval
python3 ipi-demo-runner.py 60 10    # 60 seconds, 10 second intervals
python3 ipi-demo-runner.py 15 3     # 15 seconds, 3 second intervals
```

**What it does:**
1. Runs lpcpu with IPI profiler
2. Extracts and navigates to output directory
3. Shows raw IPI data
4. Runs postprocessing and analysis
5. Shows parsed data (plot files)
6. Shows complete analysis summary with recommendations

All output is displayed in the terminal with clear section labels.

### Alternative: Generate HTML Report

For a comprehensive HTML report with all data in one page:

```bash
# After running lpcpu, generate HTML report
python3 generate-ipi-report.py /path/to/lpcpu_data.directory
```

Opens a beautiful web page showing:
- Raw IPI data
- Parsed plot files
- Complete analysis
- Recommendations
- Link to interactive chart

### Manual: Including IPI Monitoring in a Profile Run

To run lpcpu manually with IPI monitoring:

```bash
# Add IPI to default profilers
./lpcpu.sh extra_profilers="ipi"

# Or specify all profilers explicitly
./lpcpu.sh profilers="sar iostat mpstat vmstat ipi"
```

### Excluding IPI Monitoring

To run without IPI monitoring, specify profilers without `ipi`:

```bash
./lpcpu.sh profilers="sar iostat mpstat vmstat"
```

### Custom Interval

To change the sampling interval (default is 5 seconds):

```bash
./lpcpu.sh extra_profilers="ipi" interval=2 duration=60
```

## Output Files

After running lpcpu with IPI monitoring, you'll find:

1. **Raw Data**: `proc-ipi.default.001` - Contains timestamped IPI counts from `/proc/interrupts`
2. **Processed Data**: `ipi-processed.default.001/` directory containing:
   - `plot-files/` - Individual plot files for each CPU (timestamp + IPI rate)
   - `chart.html` - Interactive visualization of IPI data
   - `ipi-analysis-summary.txt` - Analysis report with recommendations

## Viewing Results

### Option 1: Automated Script Output
If you used `ipi-demo-runner.py`, all results are already displayed in your terminal.

### Option 2: HTML Report
If you generated an HTML report with `generate-ipi-report.py`:
1. Open `ipi-comprehensive-report.html` in a web browser
2. Navigate through sections using the menu
3. View raw data, parsed data, analysis, and recommendations all in one page

### Option 3: Manual Viewing
1. Navigate to the output directory (e.g., `/tmp/lpcpu_data.*/`)
2. View raw data: `cat proc-ipi.default.001`
3. View analysis: `cat ipi-processed.default.001/ipi-analysis-summary.txt`
4. Open interactive chart: `firefox ipi-processed.default.001/chart.html`

### What the Analysis Shows

The IPI analysis provides:
- **IPI Rates**: Total IPIs, system-wide rate, per-CPU averages
- **Hot CPUs**: CPUs handling >200% of average load (potential bottlenecks)
- **Cold CPUs**: CPUs handling <10% of average load (underutilized)
- **Imbalance Coefficient**: 0-1 scale (0=perfect balance, 1=maximum imbalance)
- **Spike Detection**: CPUs with >2x average rate bursts
- **Recommendations**: HIGH and MEDIUM priority actions to improve performance

## Use Cases

IPI monitoring is valuable for:

1. **Performance Analysis**: High IPI rates can indicate:
   - Excessive cross-CPU communication
   - Lock contention
   - Scheduler inefficiencies

2. **NUMA Optimization**: Analyzing IPI patterns helps identify:
   - Cross-NUMA node communication
   - Suboptimal task placement

3. **Debugging**: Understanding IPI activity helps diagnose:
   - CPU hotspots
   - Synchronization issues
   - System responsiveness problems

## Technical Details

### Data Format

The IPI data file format matches `/proc/interrupts` structure but includes only IPI lines:

```
HH:MM:SS / timestamp
           CPU0       CPU1       CPU2       CPU3
 IPI0:        12         45         23         34  Rescheduling interrupts
 IPI1:       156        234        189        201  Function call interrupts
 ...
```

### Performance Impact

The IPI monitoring tool has minimal performance impact:
- Reads `/proc/interrupts` once per interval
- Filters and processes only IPI lines
- Runs as a background process

## Troubleshooting

### IPI Profiler Not Starting

If you see an error about `proc-ipi.pl` not being available:
1. Ensure you have the complete lpcpu distribution
2. Verify `tools/proc-ipi.pl` exists and is executable
3. Check file permissions: `chmod +x tools/proc-ipi.pl`

### No IPI Data in Output

If no IPI data appears:
1. Check if your system's `/proc/interrupts` includes IPI lines
2. Some architectures may not expose IPI data in `/proc/interrupts`
3. Review `profile-log.001` for any error messages

### Post-Processing Fails

If post-processing fails:
1. Ensure Perl modules are available: `PERL5LIB=./perl`
2. Check that `postprocess/postprocess-ipi` is executable
3. Verify the raw IPI data file was created

## Future Enhancements

Potential improvements for IPI monitoring:

1. **Threshold Alerts**: Warn when IPI rates exceed configurable thresholds
2. **NUMA-Aware Analysis**: Correlate IPI activity with NUMA topology
3. **Historical Comparison**: Compare IPI patterns across multiple runs
4. **IPI Source Tracking**: Identify which processes/threads trigger IPIs

## References

- Linux kernel documentation: `/proc/interrupts`
- IPI implementation: `arch/*/kernel/smp.c` in Linux kernel source
- Performance analysis: "Systems Performance" by Brendan Gregg
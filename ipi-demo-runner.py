#!/usr/bin/env python3
"""
IPI Demo Runner - Automated IPI Analysis Workflow
Runs lpcpu with IPI and cpu-affinity profilers and displays all results in one
go, including thread-to-CPU correlation for hot CPUs as the final highlight.

Usage:
    python3 ipi-demo-runner.py [duration] [interval]

Examples:
    python3 ipi-demo-runner.py           # 60 seconds, 1 second interval (default)
    python3 ipi-demo-runner.py 60 1      # 60 seconds, 1 second interval
    python3 ipi-demo-runner.py 30 5      # 30 seconds, 5 second intervals
"""

import subprocess
import sys
import os
import time
import glob
from pathlib import Path

def run_command(cmd, cwd=None, capture=True):
    """Run a shell command and return output"""
    print(f"\n{'='*80}")
    print(f"Running: {cmd}")
    print(f"{'='*80}")
    
    if capture:
        result = subprocess.run(cmd, shell=True, cwd=cwd, 
                              capture_output=True, text=True)
        if result.returncode != 0:
            print(f"ERROR: {result.stderr}")
            return None
        return result.stdout
    else:
        subprocess.run(cmd, shell=True, cwd=cwd)
        return None

def main():
    # Parse arguments
    duration = int(sys.argv[1]) if len(sys.argv) > 1 else 60
    interval = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    
    print(f"""
╔════════════════════════════════════════════════════════════════════════════╗
║                     IPI DEMO RUNNER - AUTOMATED WORKFLOW                   ║
╚════════════════════════════════════════════════════════════════════════════╝

Configuration:
  Duration: {duration} seconds
  Interval: {interval} seconds
  Samples: {duration // interval} samples
  
Starting in 3 seconds...
""")
    time.sleep(3)
    
    # Step 1: Run lpcpu with IPI profiler
    print("\n" + "="*80)
    print("STEP 1: COLLECTING IPI DATA")
    print("="*80)
    
    lpcpu_cmd = f'cd /tmp/lpcpu && ./lpcpu.sh profilers="ipi cpu-affinity" duration={duration} interval={interval}'
    run_command(lpcpu_cmd, capture=False)
    
    print("\n✓ Data collection complete!")
    time.sleep(2)
    
    # Step 2: Find and extract latest tarball
    print("\n" + "="*80)
    print("STEP 2: EXTRACTING DATA")
    print("="*80)
    
    os.chdir('/tmp')
    tarballs = sorted(glob.glob('lpcpu_data.*.tar.bz2'), key=os.path.getmtime, reverse=True)
    
    if not tarballs:
        print("ERROR: No lpcpu data files found!")
        sys.exit(1)
    
    latest = tarballs[0]
    print(f"Found: {latest}")
    
    run_command(f'tar -xjf {latest}')
    output_dir = latest.replace('.tar.bz2', '')
    os.chdir(output_dir)
    
    print(f"✓ Extracted to: {output_dir}")
    
    # Step 3: Show raw data
    print("\n" + "="*80)
    print("STEP 3: RAW IPI DATA")
    print("="*80)
    print("This is the unprocessed data collected from /proc/interrupts")
    print("Shows IPI counts for each CPU at each sampling interval")
    print("-" * 80 + "\n")
    
    raw_data = run_command('head -30 proc-ipi.default.001')
    print(raw_data)
    
    # Step 4: Run postprocessing
    print("\n" + "="*80)
    print("STEP 4: RUNNING POSTPROCESSING & ANALYSIS")
    print("="*80)
    print("Processing raw data to calculate rates, detect imbalance, and generate recommendations")
    print("-" * 80 + "\n")
    
    postprocess_cmd = 'PERL5LIB=/tmp/lpcpu/perl /tmp/lpcpu/postprocess/postprocess-ipi . 001 default'
    run_command(postprocess_cmd, capture=False)
    
    print("\n✓ Postprocessing complete!")
    
    # Step 5: Show parsed data
    print("\n" + "="*80)
    print("STEP 5: PARSED DATA (Plot Files)")
    print("="*80)
    print("Processed data in timestamp + IPI rate format, ready for charting")
    print("-" * 80 + "\n")
    
    plot_files = run_command('ls -lh ipi-processed.default.001/plot-files/ | head -10')
    print(plot_files)
    
    print("\n" + "-" * 80)
    print("Sample Plot File (CPU0) - Format: timestamp ipi_rate")
    print("-" * 80)
    sample_plot = run_command('head -15 ipi-processed.default.001/plot-files/CPU0.plot')
    print(sample_plot)
    
    # Step 6: IPI analysis summary (assessment + top CPUs)
    print("\n" + "="*80)
    print("STEP 6: IPI ANALYSIS SUMMARY")
    print("="*80)
    print("Assessment, top CPUs by IPI activity, and recommendations")
    print("-" * 80 + "\n")

    summary = run_command('cat ipi-processed.default.001/ipi-analysis-summary.txt')
    print(summary)

    # Phase 7: Thread-to-CPU Correlation — final highlight
    print("\n" + "="*80)
    print("PHASE 7: THREAD-TO-CPU CORRELATION FOR HOT CPUS  ← NEW FEATURE")
    print("="*80)
    print("""
SPEAKING NOTE:
  "Before, the IPI demo could show which CPUs were hot, but not what was
  running on them. With this new cpu-affinity profiler, we can now correlate
  hot CPUs with the threads and processes observed on those CPUs during
  collection. This gives performance engineers a starting point for
  investigation before digging deeper into kernel-level tracing."
""")
    print("What this demonstrates:")
    print("  1. LPCPU identifies hot CPUs from IPI data")
    print("  2. The new cpu-affinity profiler records which threads ran on which CPUs")
    print("  3. postprocess-ipi correlates hot CPUs with observed threads/processes")
    print("  4. Output uses 'observed' wording — correlation, not causation")
    print("-" * 80 + "\n")

    print("Both raw data files were collected:")
    run_command('ls -lh proc-ipi.default.001 proc-cpu-affinity.default.001')

    print("\nSample cpu-affinity data (Timestamp  PID  TID  PSR  %CPU  COMMAND):")
    print("-" * 80)
    affinity_sample = run_command('head -20 proc-cpu-affinity.default.001')
    print(affinity_sample)

    print("\nThe full thread-to-CPU correlation was printed above in Step 4 during")
    print("postprocessing. The summary file below shows the executive assessment:")
    print("-" * 80)
    assessment = run_command(
        'grep -A 2 "ASSESSMENT" ipi-processed.default.001/ipi-analysis-summary.txt'
    )
    if assessment and assessment.strip():
        print(assessment)

    print("\nTop CPUs by IPI activity (from summary):")
    print("-" * 80)
    top_cpus = run_command(
        'grep -A 8 "Top 5 CPUs by IPI Activity" ipi-processed.default.001/ipi-analysis-summary.txt'
    )
    if top_cpus and top_cpus.strip():
        print(top_cpus)

    print("\nInteractive chart:")
    run_command('ls -lh ipi-processed.default.001/chart.html')

    # Final summary
    print("\n" + "="*80)
    print("DEMO COMPLETE!")
    print("="*80)
    print(f"""
Output Location: /tmp/{output_dir}

Files Generated:
  • Raw IPI data:        proc-ipi.default.001
  • Raw affinity data:   proc-cpu-affinity.default.001
  • Plot files:          ipi-processed.default.001/plot-files/
  • HTML chart:          ipi-processed.default.001/chart.html
  • Analysis summary:    ipi-processed.default.001/ipi-analysis-summary.txt

To view the interactive chart:
  firefox ipi-processed.default.001/chart.html

To re-run analysis:
  PERL5LIB=/tmp/lpcpu/perl /tmp/lpcpu/postprocess/postprocess-ipi . 001 default
""")

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

# Made with Bob

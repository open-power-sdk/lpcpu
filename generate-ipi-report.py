#!/usr/bin/env python3
"""
IPI Comprehensive Report Generator
Creates a single HTML page with raw data, parsed data, analysis, and summary.

Usage:
    python3 generate-ipi-report.py <output_directory>
    
Example:
    python3 generate-ipi-report.py /tmp/lpcpu_data.ltczz345-lp2.default.2026-06-25_1056
"""

import sys
import os
from pathlib import Path
from datetime import datetime

def read_file(filepath, max_lines=None):
    """Read file content, optionally limiting lines"""
    try:
        with open(filepath, 'r') as f:
            if max_lines:
                lines = [f.readline() for _ in range(max_lines)]
                return ''.join(lines)
            return f.read()
    except Exception as e:
        return f"Error reading file: {e}"

def generate_html_report(output_dir):
    """Generate comprehensive HTML report"""
    
    output_dir = Path(output_dir)
    if not output_dir.exists():
        print(f"ERROR: Directory not found: {output_dir}")
        sys.exit(1)
    
    # Read data files
    raw_data = read_file(output_dir / 'proc-ipi.default.001', max_lines=50)
    
    # Read plot files
    plot_dir = output_dir / 'ipi-processed.default.001' / 'plot-files'
    plot_files = []
    if plot_dir.exists():
        plot_files = sorted([f.name for f in plot_dir.glob('*.plot')])
    
    sample_plot = ""
    if plot_files:
        sample_plot = read_file(plot_dir / plot_files[0], max_lines=20)
    
    # Read analysis summary
    summary_file = output_dir / 'ipi-processed.default.001' / 'ipi-analysis-summary.txt'
    analysis_summary = read_file(summary_file) if summary_file.exists() else "Analysis not yet run"
    
    # Generate HTML
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>IPI Analysis Report - {output_dir.name}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
            line-height: 1.6;
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 10px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.3);
            overflow: hidden;
        }}
        
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }}
        
        .header h1 {{
            font-size: 2.5em;
            margin-bottom: 10px;
        }}
        
        .header .subtitle {{
            font-size: 1.1em;
            opacity: 0.9;
        }}
        
        .nav {{
            background: #f8f9fa;
            padding: 15px 30px;
            border-bottom: 2px solid #e9ecef;
            display: flex;
            gap: 20px;
            flex-wrap: wrap;
        }}
        
        .nav a {{
            color: #667eea;
            text-decoration: none;
            padding: 8px 16px;
            border-radius: 5px;
            transition: all 0.3s;
            font-weight: 500;
        }}
        
        .nav a:hover {{
            background: #667eea;
            color: white;
        }}
        
        .content {{
            padding: 30px;
        }}
        
        .section {{
            margin-bottom: 40px;
            padding: 25px;
            background: #f8f9fa;
            border-radius: 8px;
            border-left: 4px solid #667eea;
        }}
        
        .section h2 {{
            color: #667eea;
            margin-bottom: 20px;
            font-size: 1.8em;
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        
        .section h3 {{
            color: #764ba2;
            margin: 20px 0 10px 0;
            font-size: 1.3em;
        }}
        
        .code-block {{
            background: #2d2d2d;
            color: #f8f8f2;
            padding: 20px;
            border-radius: 5px;
            overflow-x: auto;
            font-family: 'Courier New', monospace;
            font-size: 0.9em;
            line-height: 1.5;
            margin: 15px 0;
        }}
        
        .code-block pre {{
            margin: 0;
            white-space: pre-wrap;
            word-wrap: break-word;
        }}
        
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin: 20px 0;
        }}
        
        .stat-card {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            border-left: 4px solid #667eea;
        }}
        
        .stat-card .label {{
            color: #6c757d;
            font-size: 0.9em;
            margin-bottom: 5px;
        }}
        
        .stat-card .value {{
            color: #667eea;
            font-size: 1.8em;
            font-weight: bold;
        }}
        
        .file-list {{
            background: white;
            padding: 15px;
            border-radius: 5px;
            margin: 15px 0;
        }}
        
        .file-list ul {{
            list-style: none;
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
            gap: 10px;
        }}
        
        .file-list li {{
            padding: 8px 12px;
            background: #f8f9fa;
            border-radius: 4px;
            font-family: monospace;
            font-size: 0.9em;
        }}
        
        .alert {{
            padding: 15px 20px;
            border-radius: 5px;
            margin: 15px 0;
        }}
        
        .alert-info {{
            background: #d1ecf1;
            border-left: 4px solid #0c5460;
            color: #0c5460;
        }}
        
        .alert-warning {{
            background: #fff3cd;
            border-left: 4px solid #856404;
            color: #856404;
        }}
        
        .alert-success {{
            background: #d4edda;
            border-left: 4px solid #155724;
            color: #155724;
        }}
        
        .footer {{
            background: #f8f9fa;
            padding: 20px 30px;
            text-align: center;
            color: #6c757d;
            border-top: 2px solid #e9ecef;
        }}
        
        .icon {{
            font-size: 1.2em;
        }}
        
        @media print {{
            body {{
                background: white;
                padding: 0;
            }}
            .nav {{
                display: none;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔍 IPI Analysis Report</h1>
            <div class="subtitle">
                {output_dir.name}<br>
                Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            </div>
        </div>
        
        <div class="nav">
            <a href="#raw-data">📄 Raw Data</a>
            <a href="#parsed-data">📊 Parsed Data</a>
            <a href="#analysis">🔬 Analysis</a>
            <a href="#summary">📋 Summary</a>
            <a href="#chart">📈 Interactive Chart</a>
        </div>
        
        <div class="content">
            <!-- Raw Data Section -->
            <div class="section" id="raw-data">
                <h2><span class="icon">📄</span> Raw IPI Data</h2>
                <div class="alert alert-info">
                    <strong>What is this?</strong> Unprocessed IPI counts collected directly from /proc/interrupts at each sampling interval.
                </div>
                <div class="code-block">
                    <pre>{raw_data}</pre>
                </div>
                <p><em>Showing first 50 lines. Full data in: proc-ipi.default.001</em></p>
            </div>
            
            <!-- Parsed Data Section -->
            <div class="section" id="parsed-data">
                <h2><span class="icon">📊</span> Parsed Data (Plot Files)</h2>
                <div class="alert alert-info">
                    <strong>What is this?</strong> Processed data converted to timestamp + IPI rate format, ready for charting and visualization.
                </div>
                
                <h3>Generated Plot Files ({len(plot_files)} files)</h3>
                <div class="file-list">
                    <ul>
                        {''.join(f'<li>{f}</li>' for f in plot_files[:24])}
                    </ul>
                </div>
                
                <h3>Sample Plot File ({plot_files[0] if plot_files else 'N/A'})</h3>
                <div class="code-block">
                    <pre>{sample_plot if sample_plot else 'No plot files generated yet'}</pre>
                </div>
                <p><em>Format: timestamp ipi_rate (IPIs per second)</em></p>
            </div>
            
            <!-- Analysis Section -->
            <div class="section" id="analysis">
                <h2><span class="icon">🔬</span> IPI Analysis</h2>
                <div class="alert alert-warning">
                    <strong>What is this?</strong> Comprehensive analysis including IPI rates, imbalance detection, hot/cold CPU identification, and spike detection.
                </div>
                <div class="code-block">
                    <pre>{analysis_summary}</pre>
                </div>
            </div>
            
            <!-- Summary Section -->
            <div class="section" id="summary">
                <h2><span class="icon">📋</span> Quick Summary</h2>
                <div class="alert alert-success">
                    <strong>Key Takeaways:</strong> High-level overview of the most important findings.
                </div>
                
                <div class="stats-grid">
                    <div class="stat-card">
                        <div class="label">Output Directory</div>
                        <div class="value" style="font-size: 1.2em;">{output_dir.name}</div>
                    </div>
                    <div class="stat-card">
                        <div class="label">Plot Files Generated</div>
                        <div class="value">{len(plot_files)}</div>
                    </div>
                    <div class="stat-card">
                        <div class="label">Report Generated</div>
                        <div class="value" style="font-size: 1em;">{datetime.now().strftime('%H:%M:%S')}</div>
                    </div>
                </div>
                
                <h3>Files Generated</h3>
                <ul style="margin-left: 20px; margin-top: 10px;">
                    <li><strong>Raw data:</strong> proc-ipi.default.001</li>
                    <li><strong>Plot files:</strong> proc-ipi-processed.default.001/plot-files/</li>
                    <li><strong>HTML chart:</strong> proc-ipi-processed.default.001/chart.html</li>
                    <li><strong>Analysis:</strong> proc-ipi-processed.default.001/ipi-analysis-summary.txt</li>
                </ul>
            </div>
            
            <!-- Interactive Chart Section -->
            <div class="section" id="chart">
                <h2><span class="icon">📈</span> Interactive Chart</h2>
                <div class="alert alert-info">
                    <strong>View the interactive chart:</strong> Open chart.html in a browser for an interactive visualization of IPI rates over time.
                </div>
                <p style="margin-top: 15px;">
                    <a href="proc-ipi-processed.default.001/chart.html" 
                       style="display: inline-block; padding: 12px 24px; background: #667eea; color: white; 
                              text-decoration: none; border-radius: 5px; font-weight: bold;">
                        🚀 Open Interactive Chart
                    </a>
                </p>
            </div>
        </div>
        
        <div class="footer">
            <p>IPI Analysis Report | Generated by lpcpu postprocess-ipi</p>
            <p style="margin-top: 5px; font-size: 0.9em;">
                Location: {output_dir}
            </p>
        </div>
    </div>
</body>
</html>
"""
    
    # Write HTML file
    report_file = output_dir / 'ipi-comprehensive-report.html'
    with open(report_file, 'w') as f:
        f.write(html)
    
    print(f"""
╔════════════════════════════════════════════════════════════════════════════╗
║                   IPI COMPREHENSIVE REPORT GENERATED                       ║
╚════════════════════════════════════════════════════════════════════════════╝

Report saved to:
  {report_file}

To view:
  firefox {report_file}
  
Or open in IBM Bob:
  Right-click → Open in Browser
""")
    
    return report_file

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    
    generate_html_report(sys.argv[1])

# Made with Bob

"""
Basic tests for LPCPU script

Tests basic functionality of lpcpu.sh without requiring actual profiling.
"""

import pytest
import subprocess
import os
from pathlib import Path


class TestLPCPUScriptExists:
    """Test that LPCPU script exists and is accessible"""
    
    def test_lpcpu_script_exists(self):
        """Test that lpcpu.sh exists"""
        script_path = Path("lpcpu/lpcpu.sh")
        assert script_path.exists(), f"lpcpu.sh not found at {script_path}"
    
    def test_lpcpu_script_is_readable(self):
        """Test that lpcpu.sh is readable"""
        script_path = Path("lpcpu/lpcpu.sh")
        assert os.access(script_path, os.R_OK), "lpcpu.sh is not readable"


class TestLPCPUSyntax:
    """Test bash syntax of LPCPU script"""
    
    def test_lpcpu_bash_syntax(self):
        """Test that lpcpu.sh has valid bash syntax"""
        script_path = Path("lpcpu/lpcpu.sh")
        if not script_path.exists():
            pytest.skip("lpcpu.sh not found")
        
        result = subprocess.run(
            ['bash', '-n', str(script_path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True
        )
        assert result.returncode == 0, f"Syntax error in lpcpu.sh: {result.stderr}"


class TestLPCPUVersion:
    """Test LPCPU version information"""
    
    def test_version_string_exists(self):
        """Test that VERSION_STRING is defined in lpcpu.sh"""
        script_path = Path("lpcpu/lpcpu.sh")
        if not script_path.exists():
            pytest.skip("lpcpu.sh not found")
        
        content = script_path.read_text()
        assert "VERSION_STRING=" in content, "VERSION_STRING not found in lpcpu.sh"
    
    def test_version_string_format(self):
        """Test that VERSION_STRING has expected format"""
        script_path = Path("lpcpu/lpcpu.sh")
        if not script_path.exists():
            pytest.skip("lpcpu.sh not found")
        
        content = script_path.read_text()
        # Look for VERSION_STRING line
        for line in content.split('\n'):
            if 'VERSION_STRING=' in line and not line.strip().startswith('#'):
                # Should have a git hash and date
                assert len(line) > 30, "VERSION_STRING seems too short"
                break


class TestLPCPUDefaultParameters:
    """Test that default parameters are defined"""
    
    def test_profilers_defined(self):
        """Test that default profilers list is defined"""
        script_path = Path("lpcpu/lpcpu.sh")
        if not script_path.exists():
            pytest.skip("lpcpu.sh not found")
        
        content = script_path.read_text()
        assert 'profilers=' in content, "profilers variable not found"
    
    def test_duration_defined(self):
        """Test that duration parameter is defined"""
        script_path = Path("lpcpu/lpcpu.sh")
        if not script_path.exists():
            pytest.skip("lpcpu.sh not found")
        
        content = script_path.read_text()
        assert 'duration=' in content, "duration variable not found"
    
    def test_interval_defined(self):
        """Test that interval parameter is defined"""
        script_path = Path("lpcpu/lpcpu.sh")
        if not script_path.exists():
            pytest.skip("lpcpu.sh not found")
        
        content = script_path.read_text()
        assert 'interval=' in content, "interval variable not found"
    
    def test_output_dir_defined(self):
        """Test that output_dir parameter is defined"""
        script_path = Path("lpcpu/lpcpu.sh")
        if not script_path.exists():
            pytest.skip("lpcpu.sh not found")
        
        content = script_path.read_text()
        assert 'output_dir=' in content, "output_dir variable not found"


class TestLPCPUTools:
    """Test that LPCPU tools directory exists"""
    
    def test_tools_directory_exists(self):
        """Test that tools directory exists"""
        tools_path = Path("lpcpu/tools")
        assert tools_path.exists(), "tools directory not found"
        assert tools_path.is_dir(), "tools is not a directory"
    
    def test_ndiff_exists(self):
        """Test that ndiff.py tool exists"""
        ndiff_path = Path("lpcpu/tools/ndiff.py")
        if ndiff_path.exists():
            assert os.access(ndiff_path, os.R_OK), "ndiff.py is not readable"


class TestLPCPUHelperScripts:
    """Test that helper scripts exist"""
    
    def test_create_tarball_exists(self):
        """Test that create-tarball.sh exists"""
        script_path = Path("lpcpu/create-tarball.sh")
        if script_path.exists():
            assert os.access(script_path, os.R_OK), "create-tarball.sh is not readable"
    
    def test_rtst_exists(self):
        """Test that rtst.py exists"""
        script_path = Path("lpcpu/rtst.py")
        if script_path.exists():
            assert os.access(script_path, os.R_OK), "rtst.py is not readable"


class TestLPCPUIPIMonitoring:
    """Test that IPI monitoring support is integrated"""

    def test_ipi_profiler_in_script(self):
        """Test that IPI profiler functions exist in lpcpu.sh"""
        script_path = Path("lpcpu/lpcpu.sh")
        if not script_path.exists():
            pytest.skip("lpcpu.sh not found")

        content = script_path.read_text()
        assert "setup_ipi" in content, "setup_ipi function not found"
        assert "start_ipi" in content, "start_ipi function not found"
        assert "stop_ipi" in content, "stop_ipi function not found"
        assert 'profilers="sar iostat mpstat vmstat lparstat top meminfo interrupts ipi cpupower"' in content, "ipi not in default profilers"

    def test_proc_ipi_tool_exists(self):
        """Test that proc-ipi.pl tool exists"""
        tool_path = Path("lpcpu/tools/proc-ipi.pl")
        assert tool_path.exists(), "proc-ipi.pl not found"
        assert os.access(tool_path, os.R_OK), "proc-ipi.pl is not readable"

    def test_postprocess_ipi_exists(self):
        """Test that postprocess-ipi script exists"""
        script_path = Path("lpcpu/postprocess/postprocess-ipi")
        assert script_path.exists(), "postprocess-ipi not found"
        assert os.access(script_path, os.R_OK), "postprocess-ipi is not readable"


class TestLPCPUDocumentation:
    """Test that documentation files exist"""
    
    def test_readme_exists(self):
        """Test that README exists"""
        readme_path = Path("lpcpu/README")
        assert readme_path.exists(), "README not found"
    
    def test_license_exists(self):
        """Test that LICENSE.TXT exists"""
        license_path = Path("lpcpu/LICENSE.TXT")
        assert license_path.exists(), "LICENSE.TXT not found"

# Made with Bob

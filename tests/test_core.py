"""
Basic test suite for LPCPU

Simple tests to verify the testing infrastructure works.
Does not test LPCPU functionality yet.
"""

import pytest


class TestBasicPython:
    """Test that basic Python functionality works"""
    
    def test_python_works(self):
        """Test that Python is working"""
        assert True
    
    def test_basic_math(self):
        """Test basic math operations"""
        assert 1 + 1 == 2
        assert 5 * 5 == 25
    
    def test_string_operations(self):
        """Test string operations"""
        test_string = "hello world"
        assert "hello" in test_string
        assert test_string.upper() == "HELLO WORLD"
    
    def test_list_operations(self):
        """Test list operations"""
        test_list = [1, 2, 3, 4, 5]
        assert len(test_list) == 5
        assert sum(test_list) == 15


class TestPytestFeatures:
    """Test that pytest features work"""
    
    def test_assertions(self):
        """Test pytest assertions"""
        assert True is True
        assert False is False
        assert None is None
    
    def test_with_fixture(self, tmp_path):
        """Test using pytest fixtures"""
        # tmp_path is a built-in pytest fixture
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")
        assert test_file.read_text() == "test content"
    
    @pytest.mark.skip(reason="Example of skipping a test")
    def test_skipped(self):
        """This test is skipped"""
        assert False  # This won't run


class TestEnvironment:
    """Test that the environment is set up correctly"""
    
    def test_pytest_available(self):
        """Test that pytest is available"""
        import pytest
        assert pytest is not None
    
    def test_python_version(self):
        """Test Python version"""
        import sys
        assert sys.version_info.major == 3
        assert sys.version_info.minor >= 6

# Made with Bob

"""
Tests for Codebase Indexer module.

Tests:
- File scanning and filtering
- Code structure extraction
- Content hashing for change detection
"""

import pytest
from pathlib import Path
import tempfile
import os
import sys

# Add orchestrator/service to path
sys.path.insert(0, str(Path(__file__).parent.parent / "orchestrator" / "service"))

from codebase_indexer import (
    CodebaseIndexer,
    create_codebase_indexer,
)


class TestCodebaseIndexer:
    """Tests for the codebase indexer."""
    
    @pytest.fixture
    def temp_project(self):
        """Create a temporary project directory with sample files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            
            # Create sample Python file
            (project / "main.py").write_text('''
"""Main module."""
import os
from typing import List

class MyClass:
    """A sample class."""
    
    def __init__(self):
        self.value = 0
    
    def process(self, items: List[str]) -> int:
        """Process items."""
        return len(items)

def main():
    """Entry point."""
    obj = MyClass()
    print(obj.process(["a", "b", "c"]))

if __name__ == "__main__":
    main()
''')
            
            # Create sample JavaScript file
            (project / "app.js").write_text('''
import React from 'react';
export default function App() {
    return <div>Hello World</div>;
}
''')
            
            # Create sample YAML file
            (project / "config.yaml").write_text('''
name: test-project
version: 1.0.0
settings:
  debug: true
''')
            
            # Create subdirectory with Python file
            (project / "src").mkdir()
            (project / "src" / "utils.py").write_text('''
"""Utility functions."""

def helper():
    pass

async def async_helper():
    pass
''')
            
            # Create __pycache__ directory (should be excluded)
            (project / "__pycache__").mkdir()
            (project / "__pycache__" / "main.cpython-310.pyc").write_bytes(b"bytecode")
            
            # Create .git directory (should be excluded)
            (project / ".git").mkdir()
            (project / ".git" / "config").write_text("git config")
            
            yield project
    
    @pytest.fixture
    def indexer(self, temp_project):
        """Create an indexer for the temp project."""
        return CodebaseIndexer(
            memory_service_url="http://localhost:8002",
            project_root=temp_project
        )
    
    def test_should_index_file_python(self, indexer, temp_project):
        """Test that Python files are indexed."""
        py_file = temp_project / "main.py"
        assert indexer._should_index_file(py_file) is True
    
    def test_should_index_file_javascript(self, indexer, temp_project):
        """Test that JavaScript files are indexed."""
        js_file = temp_project / "app.js"
        assert indexer._should_index_file(js_file) is True
    
    def test_should_not_index_pycache(self, indexer, temp_project):
        """Test that __pycache__ files are excluded."""
        pyc_file = temp_project / "__pycache__" / "main.cpython-310.pyc"
        assert indexer._should_index_file(pyc_file) is False
    
    def test_should_not_index_git(self, indexer, temp_project):
        """Test that .git files are excluded."""
        git_file = temp_project / ".git" / "config"
        assert indexer._should_index_file(git_file) is False
    
    def test_get_language_python(self, indexer, temp_project):
        """Test language detection for Python."""
        py_file = temp_project / "main.py"
        assert indexer._get_language(py_file) == "python"
    
    def test_get_language_javascript(self, indexer, temp_project):
        """Test language detection for JavaScript."""
        js_file = temp_project / "app.js"
        assert indexer._get_language(js_file) == "javascript"
    
    def test_get_language_yaml(self, indexer, temp_project):
        """Test language detection for YAML."""
        yaml_file = temp_project / "config.yaml"
        assert indexer._get_language(yaml_file) == "yaml"
    
    def test_compute_hash_deterministic(self, indexer):
        """Test that hash is deterministic."""
        content = "test content"
        hash1 = indexer._compute_hash(content)
        hash2 = indexer._compute_hash(content)
        assert hash1 == hash2
    
    def test_compute_hash_different_content(self, indexer):
        """Test that different content produces different hashes."""
        hash1 = indexer._compute_hash("content 1")
        hash2 = indexer._compute_hash("content 2")
        assert hash1 != hash2
    
    def test_extract_code_structure_python(self, indexer, temp_project):
        """Test Python code structure extraction."""
        content = (temp_project / "main.py").read_text()
        structure = indexer._extract_code_structure(content, "python")
        
        # Should find class
        assert len(structure["classes"]) >= 1
        assert any(c["name"] == "MyClass" for c in structure["classes"])
        
        # Should find functions
        assert len(structure["functions"]) >= 1
        assert any(f["name"] == "main" for f in structure["functions"])
        
        # Should find imports
        assert len(structure["imports"]) >= 1
    
    def test_extract_code_structure_async(self, indexer, temp_project):
        """Test async function detection."""
        content = (temp_project / "src" / "utils.py").read_text()
        structure = indexer._extract_code_structure(content, "python")
        
        # Should find async function
        assert any(f["name"] == "async_helper" for f in structure["functions"])
    
    def test_scan_files(self, indexer, temp_project):
        """Test file scanning."""
        files = indexer.scan_files()
        
        # Should find our test files
        file_names = [f.name for f in files]
        assert "main.py" in file_names
        assert "app.js" in file_names
        assert "config.yaml" in file_names
        assert "utils.py" in file_names
        
        # Should not include excluded files
        assert not any("__pycache__" in str(f) for f in files)
        assert not any(".git" in str(f) for f in files)
    
    @pytest.mark.asyncio
    async def test_index_file(self, indexer, temp_project):
        """Test single file indexing."""
        py_file = temp_project / "main.py"
        entry = await indexer.index_file(py_file)
        
        assert entry is not None
        assert entry["path"] == "main.py"
        assert entry["language"] == "python"
        assert "content" in entry
        assert "content_hash" in entry
        assert "structure" in entry
        assert len(entry["structure"]["classes"]) >= 1
    
    @pytest.mark.asyncio
    async def test_index_file_skips_unchanged(self, indexer, temp_project):
        """Test that unchanged files are skipped on re-index."""
        py_file = temp_project / "main.py"
        
        # First index
        entry1 = await indexer.index_file(py_file)
        assert entry1 is not None
        
        # Second index should skip (unchanged)
        entry2 = await indexer.index_file(py_file)
        assert entry2 is None
    
    @pytest.mark.asyncio
    async def test_index_file_detects_changes(self, indexer, temp_project):
        """Test that changed files are re-indexed."""
        py_file = temp_project / "main.py"
        
        # First index
        entry1 = await indexer.index_file(py_file)
        assert entry1 is not None
        
        # Modify file
        py_file.write_text("# Modified\ndef new_func(): pass")
        
        # Clear the hash so it re-indexes
        indexer.indexed_files.clear()
        
        # Second index should detect change
        entry2 = await indexer.index_file(py_file)
        assert entry2 is not None
        assert entry2["content_hash"] != entry1["content_hash"]
    
    def test_get_index_status(self, indexer):
        """Test index status reporting."""
        status = indexer.get_index_status()
        
        assert "files_indexed" in status
        assert "last_index_time" in status
        assert "project_root" in status
        assert "namespace" in status


class TestCodebaseIndexerFactory:
    """Tests for factory functions."""
    
    def test_create_codebase_indexer(self):
        """Test factory function."""
        with tempfile.TemporaryDirectory() as tmpdir:
            indexer = create_codebase_indexer(
                memory_service_url="http://test:8002",
                project_root=tmpdir
            )
            
            assert indexer.memory_service_url == "http://test:8002"
            assert str(indexer.project_root) == tmpdir


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

"""
Codebase Indexer Module

Indexes the current codebase into the memory service so agents can:
- See the current code structure
- Query for relevant code sections
- Make edits via Ralph loop with full context

This enables self-modifying capabilities where agents can:
1. Understand the existing codebase
2. Propose changes based on PRDs
3. Implement changes with full context
"""

import asyncio
import hashlib
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
import httpx

logger = logging.getLogger(__name__)


class CodebaseIndexer:
    """
    Indexes codebase files into memory service for agent access.
    
    Features:
    - Indexes Python, JavaScript, TypeScript, YAML, JSON, Markdown files
    - Stores file content with metadata (path, language, size, hash)
    - Enables semantic search over codebase
    - Tracks changes via content hashing
    - Auto-excludes common non-code directories
    """
    
    # File extensions to index
    INDEXABLE_EXTENSIONS = {
        '.py': 'python',
        '.js': 'javascript',
        '.ts': 'typescript',
        '.jsx': 'javascript',
        '.tsx': 'typescript',
        '.yaml': 'yaml',
        '.yml': 'yaml',
        '.json': 'json',
        '.md': 'markdown',
        '.sh': 'bash',
        '.ps1': 'powershell',
        '.sql': 'sql',
        '.html': 'html',
        '.css': 'css',
        '.dockerfile': 'dockerfile',
    }
    
    # Directories to exclude
    EXCLUDE_DIRS = {
        '__pycache__', '.git', 'node_modules', '.venv', 'venv',
        'dist', 'build', '.pytest_cache', '.mypy_cache',
        '.tox', 'eggs', '*.egg-info', '.eggs',
        'htmlcov', '.coverage', '.hypothesis',
    }
    
    # Files to exclude
    EXCLUDE_FILES = {
        '.gitignore', '.dockerignore', '.env', '.env.local',
        'package-lock.json', 'yarn.lock', 'poetry.lock',
    }
    
    def __init__(
        self,
        memory_service_url: str = "http://localhost:8002",
        project_root: Optional[Path] = None,
        namespace: str = "codebase"
    ):
        """
        Initialize codebase indexer.
        
        Args:
            memory_service_url: URL of the memory service
            project_root: Root directory of the project to index
            namespace: Memory namespace for codebase entries
        """
        self.memory_service_url = memory_service_url.rstrip('/')
        self.project_root = project_root or Path.cwd()
        self.namespace = namespace
        
        # Track indexed files and their hashes
        self.indexed_files: Dict[str, str] = {}  # path -> content_hash
        self.last_index_time: Optional[datetime] = None
        
    def _should_index_file(self, file_path: Path) -> bool:
        """Check if a file should be indexed."""
        # Check extension
        if file_path.suffix.lower() not in self.INDEXABLE_EXTENSIONS:
            # Special case for Dockerfile
            if file_path.name.lower() != 'dockerfile':
                return False
        
        # Check excluded files
        if file_path.name in self.EXCLUDE_FILES:
            return False
        
        # Check excluded directories
        for part in file_path.parts:
            if part in self.EXCLUDE_DIRS:
                return False
            # Handle glob patterns
            for exclude in self.EXCLUDE_DIRS:
                if '*' in exclude and part.endswith(exclude.replace('*', '')):
                    return False
        
        return True
    
    def _get_language(self, file_path: Path) -> str:
        """Get the language/type of a file."""
        ext = file_path.suffix.lower()
        if ext in self.INDEXABLE_EXTENSIONS:
            return self.INDEXABLE_EXTENSIONS[ext]
        if file_path.name.lower() == 'dockerfile':
            return 'dockerfile'
        return 'text'
    
    def _compute_hash(self, content: str) -> str:
        """Compute content hash for change detection."""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()[:16]
    
    def _extract_code_structure(self, content: str, language: str) -> Dict[str, Any]:
        """
        Extract structural information from code.
        
        Returns:
            Dict with classes, functions, imports, etc.
        """
        structure = {
            "classes": [],
            "functions": [],
            "imports": [],
            "exports": [],
        }
        
        lines = content.split('\n')
        
        if language == 'python':
            for i, line in enumerate(lines):
                stripped = line.strip()
                if stripped.startswith('class '):
                    # Extract class name
                    class_def = stripped[6:].split('(')[0].split(':')[0].strip()
                    structure["classes"].append({
                        "name": class_def,
                        "line": i + 1
                    })
                elif stripped.startswith('def ') or stripped.startswith('async def '):
                    # Extract function name
                    if stripped.startswith('async def '):
                        func_def = stripped[10:].split('(')[0].strip()
                    else:
                        func_def = stripped[4:].split('(')[0].strip()
                    structure["functions"].append({
                        "name": func_def,
                        "line": i + 1
                    })
                elif stripped.startswith('import ') or stripped.startswith('from '):
                    structure["imports"].append({
                        "statement": stripped,
                        "line": i + 1
                    })
        
        elif language in ('javascript', 'typescript'):
            for i, line in enumerate(lines):
                stripped = line.strip()
                if 'class ' in stripped:
                    # Basic class detection
                    if 'class ' in stripped:
                        try:
                            class_name = stripped.split('class ')[1].split()[0].strip('{')
                            structure["classes"].append({
                                "name": class_name,
                                "line": i + 1
                            })
                        except:
                            pass
                elif stripped.startswith('function ') or 'function(' in stripped:
                    structure["functions"].append({
                        "statement": stripped[:80],
                        "line": i + 1
                    })
                elif stripped.startswith('import ') or stripped.startswith('export '):
                    if stripped.startswith('import '):
                        structure["imports"].append({
                            "statement": stripped,
                            "line": i + 1
                        })
                    else:
                        structure["exports"].append({
                            "statement": stripped,
                            "line": i + 1
                        })
        
        return structure
    
    def scan_files(self) -> List[Path]:
        """
        Scan project for indexable files.
        
        Returns:
            List of file paths to index
        """
        files = []
        
        for root, dirs, filenames in os.walk(self.project_root):
            # Filter excluded directories
            dirs[:] = [d for d in dirs if d not in self.EXCLUDE_DIRS]
            
            for filename in filenames:
                file_path = Path(root) / filename
                if self._should_index_file(file_path):
                    files.append(file_path)
        
        logger.info(f"Found {len(files)} indexable files in {self.project_root}")
        return files
    
    async def index_file(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """
        Index a single file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            File entry dict or None if failed
        """
        try:
            # Read file content
            content = file_path.read_text(encoding='utf-8', errors='replace')
            
            # Compute hash
            content_hash = self._compute_hash(content)
            
            # Check if file changed
            relative_path = file_path.relative_to(self.project_root)
            path_str = str(relative_path).replace('\\', '/')
            
            if path_str in self.indexed_files:
                if self.indexed_files[path_str] == content_hash:
                    logger.debug(f"Skipping unchanged file: {path_str}")
                    return None
            
            # Get language and structure
            language = self._get_language(file_path)
            structure = self._extract_code_structure(content, language)
            
            # Build entry
            entry = {
                "id": f"file:{path_str}",
                "path": path_str,
                "full_path": str(file_path),
                "language": language,
                "content": content,
                "content_hash": content_hash,
                "size_bytes": len(content.encode('utf-8')),
                "line_count": len(content.split('\n')),
                "structure": structure,
                "indexed_at": datetime.utcnow().isoformat(),
                "namespace": self.namespace,
            }
            
            # Update tracking
            self.indexed_files[path_str] = content_hash
            
            return entry
            
        except Exception as e:
            logger.error(f"Failed to index {file_path}: {e}")
            return None
    
    async def commit_to_memory(self, entries: List[Dict[str, Any]]) -> int:
        """
        Commit indexed entries to memory service.
        
        Args:
            entries: List of file entries to commit
            
        Returns:
            Number of entries committed
        """
        if not entries:
            return 0
        
        committed = 0
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            for entry in entries:
                try:
                    # Store as vector embedding for semantic search
                    payload = {
                        "content": entry["content"][:8000],  # Truncate for embedding
                        "metadata": {
                            "type": "codebase_file",
                            "path": entry["path"],
                            "language": entry["language"],
                            "line_count": entry["line_count"],
                            "structure": json.dumps(entry["structure"]),
                            "content_hash": entry["content_hash"],
                        },
                        "namespace": self.namespace,
                        "actor_id": "codebase-indexer",
                    }
                    
                    response = await client.post(
                        f"{self.memory_service_url}/memory/commit",
                        json=payload
                    )
                    
                    if response.status_code in (200, 201):
                        committed += 1
                        logger.debug(f"Committed: {entry['path']}")
                    else:
                        logger.warning(f"Failed to commit {entry['path']}: {response.status_code}")
                        
                except Exception as e:
                    logger.error(f"Error committing {entry['path']}: {e}")
        
        logger.info(f"Committed {committed}/{len(entries)} files to memory")
        return committed
    
    async def index_codebase(self, force_reindex: bool = False) -> Dict[str, Any]:
        """
        Index the entire codebase.
        
        Args:
            force_reindex: If True, reindex all files regardless of hash
            
        Returns:
            Summary of indexing operation
        """
        start_time = datetime.utcnow()
        
        if force_reindex:
            self.indexed_files.clear()
        
        # Scan for files
        files = self.scan_files()
        
        # Index files in parallel (batched)
        entries = []
        batch_size = 50
        
        for i in range(0, len(files), batch_size):
            batch = files[i:i + batch_size]
            batch_entries = await asyncio.gather(
                *[self.index_file(f) for f in batch]
            )
            entries.extend([e for e in batch_entries if e is not None])
        
        # Commit to memory
        committed = await self.commit_to_memory(entries)
        
        self.last_index_time = datetime.utcnow()
        
        summary = {
            "total_files_scanned": len(files),
            "files_indexed": len(entries),
            "files_committed": committed,
            "files_unchanged": len(files) - len(entries),
            "duration_seconds": (self.last_index_time - start_time).total_seconds(),
            "indexed_at": self.last_index_time.isoformat(),
            "project_root": str(self.project_root),
        }
        
        logger.info(f"Codebase indexing complete: {summary}")
        return summary
    
    async def query_code(self, query: str, top_k: int = 10) -> List[Dict[str, Any]]:
        """
        Query the codebase using semantic search.
        
        Args:
            query: Natural language query
            top_k: Number of results to return
            
        Returns:
            List of relevant code snippets
        """
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(
                    f"{self.memory_service_url}/memory/search",
                    json={
                        "query": query,
                        "top_k": top_k,
                        "namespace": self.namespace,
                        "filters": {"type": "codebase_file"},
                    }
                )
                
                if response.status_code == 200:
                    return response.json().get("results", [])
                else:
                    logger.error(f"Query failed: {response.status_code}")
                    return []
                    
            except Exception as e:
                logger.error(f"Query error: {e}")
                return []
    
    async def get_file_content(self, file_path: str) -> Optional[str]:
        """
        Get content of a specific file from the index.
        
        Args:
            file_path: Relative path to the file
            
        Returns:
            File content or None
        """
        full_path = self.project_root / file_path
        if full_path.exists():
            try:
                return full_path.read_text(encoding='utf-8')
            except Exception as e:
                logger.error(f"Error reading {file_path}: {e}")
        return None
    
    def get_index_status(self) -> Dict[str, Any]:
        """Get current indexing status."""
        return {
            "files_indexed": len(self.indexed_files),
            "last_index_time": self.last_index_time.isoformat() if self.last_index_time else None,
            "project_root": str(self.project_root),
            "namespace": self.namespace,
        }


# Factory function
def create_codebase_indexer(
    memory_service_url: str = "http://localhost:8002",
    project_root: Optional[str] = None,
) -> CodebaseIndexer:
    """
    Create a codebase indexer instance.
    
    Args:
        memory_service_url: URL of memory service
        project_root: Project root directory
        
    Returns:
        CodebaseIndexer instance
    """
    root = Path(project_root) if project_root else Path.cwd()
    return CodebaseIndexer(
        memory_service_url=memory_service_url,
        project_root=root
    )


# Global indexer instance
_indexer: Optional[CodebaseIndexer] = None


async def get_codebase_indexer(
    memory_service_url: str = "http://localhost:8002",
    project_root: Optional[str] = None,
) -> CodebaseIndexer:
    """Get or create global codebase indexer."""
    global _indexer
    if _indexer is None:
        _indexer = create_codebase_indexer(memory_service_url, project_root)
    return _indexer

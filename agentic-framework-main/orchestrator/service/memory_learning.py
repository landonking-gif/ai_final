"""
Memory Learning Module

Implements the /diary and /reflect learning system for agents:
- diary(): Logs task attempts with context, code, and outcomes
- reflect(): Analyzes patterns across diary entries to extract learnings
- query_past_learnings(): Retrieves relevant past experiences for new tasks

Based on ralph/memory_integration.py, integrated with agentic-framework memory-service.
"""

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

import httpx

logger = logging.getLogger(__name__)


class DiaryEntry:
    """
    Represents a diary entry capturing a task attempt.
    
    Captures:
    - What was attempted
    - What code was generated
    - Whether it succeeded or failed
    - Any errors encountered
    - Quality check results
    """
    
    def __init__(
        self,
        entry_id: str,
        story_id: str,
        story_title: str,
        attempt_number: int,
        success: bool,
        changes_made: int = 0,
        code_generated: str = None,
        error: str = None,
        quality_checks: List[Dict] = None,
        files_modified: List[str] = None,
        metadata: Dict = None
    ):
        self.id = entry_id
        self.story_id = story_id
        self.story_title = story_title
        self.attempt_number = attempt_number
        self.success = success
        self.changes_made = changes_made
        self.code_generated = code_generated
        self.error = error
        self.quality_checks = quality_checks or []
        self.files_modified = files_modified or []
        self.metadata = metadata or {}
        self.timestamp = datetime.utcnow()
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "story_id": self.story_id,
            "story_title": self.story_title,
            "attempt_number": self.attempt_number,
            "success": self.success,
            "changes_made": self.changes_made,
            "code_generated": self.code_generated,
            "error": self.error,
            "quality_checks": self.quality_checks,
            "files_modified": self.files_modified,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat()
        }
    
    def to_markdown(self) -> str:
        """Format as markdown for human-readable diary."""
        status = "✅ Success" if self.success else "❌ Failed"
        
        md = f"""## Diary Entry: {self.story_title}
**Date:** {self.timestamp.strftime('%Y-%m-%d %H:%M')}
**Story ID:** {self.story_id}
**Attempt:** #{self.attempt_number}
**Status:** {status}
**Changes Made:** {self.changes_made} files

"""
        if self.error:
            md += f"""### Error
```
{self.error}
```

"""
        
        if self.files_modified:
            md += "### Files Modified\n"
            for f in self.files_modified:
                md += f"- {f}\n"
            md += "\n"
        
        if self.quality_checks:
            md += "### Quality Checks\n"
            for check in self.quality_checks:
                status_emoji = "✅" if check.get("passed") else "❌"
                md += f"- {status_emoji} {check.get('name')}\n"
            md += "\n"
        
        return md


class Reflection:
    """
    Represents a reflection analyzing patterns across diary entries.
    
    Extracts:
    - What worked vs. what didn't
    - Common failure patterns
    - Success factors
    - Recommendations for future tasks
    """
    
    def __init__(
        self,
        reflection_id: str,
        story_id: str,
        story_title: str,
        total_attempts: int,
        final_success: bool,
        failure_patterns: List[str] = None,
        success_factors: List[str] = None,
        insights: List[str] = None,
        recommendations: List[str] = None,
        files_changed: List[str] = None,
        commit_sha: str = None
    ):
        self.id = reflection_id
        self.story_id = story_id
        self.story_title = story_title
        self.total_attempts = total_attempts
        self.final_success = final_success
        self.failure_patterns = failure_patterns or []
        self.success_factors = success_factors or []
        self.insights = insights or []
        self.recommendations = recommendations or []
        self.files_changed = files_changed or []
        self.commit_sha = commit_sha
        self.timestamp = datetime.utcnow()
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "story_id": self.story_id,
            "story_title": self.story_title,
            "total_attempts": self.total_attempts,
            "final_success": self.final_success,
            "failure_patterns": self.failure_patterns,
            "success_factors": self.success_factors,
            "insights": self.insights,
            "recommendations": self.recommendations,
            "files_changed": self.files_changed,
            "commit_sha": self.commit_sha,
            "timestamp": self.timestamp.isoformat()
        }
    
    def to_markdown(self) -> str:
        """Format as markdown for COPILOT.md."""
        status = "✅ Completed" if self.final_success else "❌ Failed"
        
        md = f"""## Reflection: {self.story_title}
**Date:** {self.timestamp.strftime('%Y-%m-%d %H:%M')}
**Status:** {status}
**Total Attempts:** {self.total_attempts}
**Commit:** {self.commit_sha or 'N/A'}

"""
        
        if self.insights:
            md += "### Key Insights\n"
            for insight in self.insights:
                md += f"- {insight}\n"
            md += "\n"
        
        if self.success_factors:
            md += "### What Worked\n"
            for factor in self.success_factors:
                md += f"- {factor}\n"
            md += "\n"
        
        if self.failure_patterns:
            md += "### Failure Patterns\n"
            for pattern in self.failure_patterns:
                md += f"- {pattern}\n"
            md += "\n"
        
        if self.recommendations:
            md += "### Recommendations\n"
            for rec in self.recommendations:
                md += f"- {rec}\n"
            md += "\n"
        
        return md


class MemoryLearningClient:
    """
    Client for the memory learning system.
    
    Provides:
    - diary(): Log task attempts
    - reflect(): Analyze patterns and extract learnings
    - query_past_learnings(): Retrieve relevant past experiences
    
    Stores data in:
    1. Memory Service (PostgreSQL + vector embeddings) for search
    2. Local .copilot/memory/ folder for human-readable access
    """
    
    def __init__(
        self,
        memory_service_url: str = "http://localhost:8002",
        workspace_root: Path = None,
        actor_id: str = "ralph-autonomous-loop",
        session_id: str = None
    ):
        self.memory_service_url = memory_service_url.rstrip("/")
        self.workspace_root = Path(workspace_root) if workspace_root else Path.cwd()
        self.actor_id = actor_id
        self.session_id = session_id or str(uuid4())
        
        # Local storage paths
        self.memory_dir = self.workspace_root / ".copilot" / "memory"
        self.diary_dir = self.memory_dir / "diary"
        self.reflections_dir = self.memory_dir / "reflections"
        self.copilot_md = self.memory_dir / "COPILOT.md"
        
        # Ensure directories exist
        self.diary_dir.mkdir(parents=True, exist_ok=True)
        self.reflections_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize COPILOT.md if needed
        if not self.copilot_md.exists():
            self._init_copilot_md()
        
        logger.info(f"MemoryLearningClient initialized: memory_dir={self.memory_dir}")
    
    def _init_copilot_md(self) -> None:
        """Initialize the COPILOT.md file."""
        content = """# Copilot Memory

This file contains learnings extracted from coding sessions.
The AI assistant uses this to improve future task implementations.

## Learnings

"""
        self.copilot_md.write_text(content, encoding="utf-8")
    
    async def diary(
        self,
        story_id: str,
        story_title: str,
        attempt_number: int,
        success: bool,
        changes_made: int = 0,
        code_generated: str = None,
        error: str = None,
        quality_checks: List[Dict] = None,
        files_modified: List[str] = None,
        metadata: Dict = None
    ) -> str:
        """
        Log a task attempt to the diary.
        
        This captures:
        - What story was being implemented
        - Which attempt this was
        - Whether it succeeded or failed
        - What code was generated
        - Any errors encountered
        - Quality check results
        
        Returns:
            Diary entry ID
        """
        entry_id = f"diary-{story_id}-{attempt_number}-{uuid4().hex[:8]}"
        
        entry = DiaryEntry(
            entry_id=entry_id,
            story_id=story_id,
            story_title=story_title,
            attempt_number=attempt_number,
            success=success,
            changes_made=changes_made,
            code_generated=code_generated,
            error=error,
            quality_checks=quality_checks,
            files_modified=files_modified,
            metadata=metadata
        )
        
        # Save to local diary folder
        diary_file = self.diary_dir / f"{datetime.now().strftime('%Y-%m-%d')}-{story_id}-{attempt_number}.md"
        diary_file.write_text(entry.to_markdown(), encoding="utf-8")
        
        # Save to memory service
        memory_id = await self._commit_to_memory_service(entry)
        
        logger.info(f"📔 Diary entry saved: {entry_id}")
        return entry_id
    
    async def _commit_to_memory_service(self, entry: DiaryEntry) -> Optional[str]:
        """Commit diary entry to memory service for vector search."""
        try:
            # Build content for embedding
            content = f"""Task: {entry.story_title}
Attempt: #{entry.attempt_number}
Success: {entry.success}
Changes: {entry.changes_made} files
"""
            if entry.error:
                content += f"Error: {entry.error}\n"
            
            if entry.files_modified:
                content += f"Files: {', '.join(entry.files_modified)}\n"
            
            # Commit to memory service with correct Artifact structure
            commit_request = {
                "artifact": {
                    "artifact_type": "research_snippet",  # Valid ArtifactType enum value
                    "content": {
                        "text": content,
                        "diary_data": entry.to_dict(),
                        "story_id": entry.story_id,
                        "attempt": entry.attempt_number,
                        "success": entry.success
                    },
                    "created_by": self.actor_id,
                    "session_id": self.session_id,
                    "tags": ["ralph", "diary", entry.story_id, "success" if entry.success else "failure"],
                    "metadata": {
                        "story_id": entry.story_id,
                        "attempt": entry.attempt_number,
                        "success": entry.success,
                        "timestamp": entry.timestamp.isoformat()
                    }
                },
                "actor_id": self.actor_id,
                "actor_type": "autonomous_loop",
                "tool_ids": ["ralph_loop", "code_generation"],
                "generate_embedding": True,
                "store_in_cold": False
            }
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.memory_service_url}/memory/commit",
                    json=commit_request
                )
                
                if response.status_code == 200:
                    result = response.json()
                    return result.get("memory_id")
                else:
                    logger.warning(f"Memory service returned {response.status_code}")
                    return None
                    
        except Exception as e:
            logger.warning(f"Failed to commit to memory service: {e}")
            return None
    
    async def reflect(
        self,
        story_id: str,
        story_title: str,
        total_attempts: int,
        final_success: bool,
        all_attempts: List[Dict],
        files_changed: List[str] = None,
        commit_sha: str = None
    ) -> Dict:
        """
        Reflect on a completed story to extract patterns and learnings.
        
        Analyzes:
        - What worked vs. what didn't
        - Common failure patterns
        - Success factors
        - Recommendations for future tasks
        
        Returns:
            Reflection data with insights
        """
        reflection_id = f"reflect-{story_id}-{uuid4().hex[:8]}"
        
        # Analyze attempts
        failures = [a for a in all_attempts if not a.get("success")]
        successes = [a for a in all_attempts if a.get("success")]
        
        # Extract patterns
        failure_patterns = self._analyze_failure_patterns(failures)
        success_factors = self._analyze_success_factors(successes, failures)
        insights = self._generate_insights(
            story_title, total_attempts, final_success, 
            failure_patterns, success_factors
        )
        recommendations = self._generate_recommendations(failure_patterns, success_factors)
        
        reflection = Reflection(
            reflection_id=reflection_id,
            story_id=story_id,
            story_title=story_title,
            total_attempts=total_attempts,
            final_success=final_success,
            failure_patterns=failure_patterns,
            success_factors=success_factors,
            insights=insights,
            recommendations=recommendations,
            files_changed=files_changed,
            commit_sha=commit_sha
        )
        
        # Save to local reflections folder
        reflection_file = self.reflections_dir / f"{datetime.now().strftime('%Y-%m-%d')}-{story_id}.md"
        reflection_file.write_text(reflection.to_markdown(), encoding="utf-8")
        
        # Append to COPILOT.md
        self._update_copilot_md(reflection)
        
        # Commit to memory service
        await self._commit_reflection_to_memory(reflection)
        
        logger.info(f"🤔 Reflection completed: {reflection_id}")
        return reflection.to_dict()
    
    def _analyze_failure_patterns(self, failures: List[Dict]) -> List[str]:
        """Analyze common patterns in failures."""
        patterns = []
        
        if not failures:
            return patterns
        
        # Count error types
        error_counts: Dict[str, int] = {}
        for failure in failures:
            error = failure.get("error", "Unknown error")
            # Simplify error to pattern
            if "test" in error.lower() or "pytest" in error.lower():
                error_type = "Test failures"
            elif "syntax" in error.lower():
                error_type = "Syntax errors"
            elif "import" in error.lower():
                error_type = "Import errors"
            elif "type" in error.lower():
                error_type = "Type errors"
            elif "quality" in error.lower():
                error_type = "Quality check failures"
            else:
                error_type = "Implementation errors"
            
            error_counts[error_type] = error_counts.get(error_type, 0) + 1
        
        # Report most common patterns
        for error_type, count in sorted(error_counts.items(), key=lambda x: -x[1]):
            if count > 0:
                patterns.append(f"{error_type} occurred in {count} attempt(s)")
        
        return patterns
    
    def _analyze_success_factors(
        self,
        successes: List[Dict],
        failures: List[Dict]
    ) -> List[str]:
        """Identify what made successful attempts work."""
        factors = []
        
        if not successes:
            return factors
        
        # Compare successful vs failed attempts
        successful_changes = sum(s.get("changes_made", 0) for s in successes)
        failed_changes = sum(f.get("changes_made", 0) for f in failures)
        
        if len(successes) > 0:
            avg_successful_changes = successful_changes / len(successes)
            factors.append(f"Successful attempts averaged {avg_successful_changes:.1f} file changes")
        
        # Check if retry eventually worked
        if failures and successes:
            factors.append("Persistence through failures led to success")
        
        # Check quality checks
        for success in successes:
            checks = success.get("quality_checks", [])
            passed_checks = [c for c in checks if c.get("passed")]
            if passed_checks:
                check_names = [c.get("name") for c in passed_checks]
                factors.append(f"Passed quality checks: {', '.join(check_names)}")
                break
        
        return factors
    
    def _generate_insights(
        self,
        story_title: str,
        total_attempts: int,
        final_success: bool,
        failure_patterns: List[str],
        success_factors: List[str]
    ) -> List[str]:
        """Generate high-level insights from the story implementation."""
        insights = []
        
        if final_success:
            if total_attempts == 1:
                insights.append(f"'{story_title}' completed on first attempt - similar tasks may be straightforward")
            elif total_attempts <= 3:
                insights.append(f"'{story_title}' required {total_attempts} attempts - some iteration expected")
            else:
                insights.append(f"'{story_title}' was complex, requiring {total_attempts} attempts")
        else:
            insights.append(f"'{story_title}' could not be completed after {total_attempts} attempts")
        
        if failure_patterns:
            primary_issue = failure_patterns[0].split(" occurred")[0]
            insights.append(f"Primary challenge: {primary_issue}")
        
        if success_factors:
            insights.append(f"Key success factor: {success_factors[0]}")
        
        return insights
    
    def _generate_recommendations(
        self,
        failure_patterns: List[str],
        success_factors: List[str]
    ) -> List[str]:
        """Generate recommendations for future similar tasks."""
        recommendations = []
        
        # Based on failure patterns
        for pattern in failure_patterns:
            if "Test failures" in pattern:
                recommendations.append("Write tests incrementally alongside implementation")
            elif "Syntax errors" in pattern:
                recommendations.append("Run syntax validation before applying changes")
            elif "Import errors" in pattern:
                recommendations.append("Verify all imports exist before implementation")
            elif "Type errors" in pattern:
                recommendations.append("Add type hints and run type checking early")
        
        # Based on success factors
        if "Persistence" in str(success_factors):
            recommendations.append("Retry with refined approach when initial attempt fails")
        
        # Default recommendations
        if not recommendations:
            recommendations.append("Break complex tasks into smaller incremental changes")
            recommendations.append("Run quality checks after each significant change")
        
        return recommendations[:5]  # Limit to top 5
    
    def _update_copilot_md(self, reflection: Reflection) -> None:
        """Append reflection insights to COPILOT.md."""
        try:
            current_content = self.copilot_md.read_text(encoding="utf-8")
            
            # Add new insights
            new_section = f"""
### {reflection.story_title}
*{reflection.timestamp.strftime('%Y-%m-%d')}* | Attempts: {reflection.total_attempts} | {'✅ Success' if reflection.final_success else '❌ Failed'}

"""
            for insight in reflection.insights[:3]:
                new_section += f"- {insight}\n"
            
            if reflection.recommendations:
                new_section += "\n**Recommendations:**\n"
                for rec in reflection.recommendations[:2]:
                    new_section += f"- {rec}\n"
            
            new_section += "\n---\n"
            
            # Append to file
            updated_content = current_content + new_section
            self.copilot_md.write_text(updated_content, encoding="utf-8")
            
        except Exception as e:
            logger.warning(f"Failed to update COPILOT.md: {e}")
    
    async def _commit_reflection_to_memory(self, reflection: Reflection) -> Optional[str]:
        """Commit reflection to memory service for future retrieval."""
        try:
            # Build content for embedding
            content = f"""Reflection: {reflection.story_title}
Attempts: {reflection.total_attempts}
Success: {reflection.final_success}

Insights:
{chr(10).join('- ' + i for i in reflection.insights)}

Recommendations:
{chr(10).join('- ' + r for r in reflection.recommendations)}
"""
            
            # Use correct Artifact structure for memory service
            commit_request = {
                "artifact": {
                    "artifact_type": "research_snippet",  # Valid ArtifactType enum value
                    "content": {
                        "text": content,
                        "reflection_data": reflection.to_dict(),
                        "story_id": reflection.story_id,
                        "insights": reflection.insights,
                        "recommendations": reflection.recommendations
                    },
                    "created_by": self.actor_id,
                    "session_id": self.session_id,
                    "tags": ["ralph", "reflection", reflection.story_id, "learning"],
                    "metadata": {
                        "story_id": reflection.story_id,
                        "total_attempts": reflection.total_attempts,
                        "final_success": reflection.final_success,
                        "timestamp": reflection.timestamp.isoformat()
                    }
                },
                "actor_id": self.actor_id,
                "actor_type": "autonomous_loop",
                "tool_ids": ["ralph_loop", "reflection"],
                "generate_embedding": True,
                "store_in_cold": True  # Store reflections long-term
            }
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.memory_service_url}/memory/commit",
                    json=commit_request
                )
                
                if response.status_code == 200:
                    result = response.json()
                    return result.get("memory_id")
                
        except Exception as e:
            logger.warning(f"Failed to commit reflection to memory service: {e}")
        
        return None
    
    async def query_past_learnings(
        self,
        query: str,
        tags: List[str] = None,
        limit: int = 5,
        min_relevance: float = 0.6
    ) -> List[Dict]:
        """
        Query past learnings relevant to a new task.
        
        Uses vector similarity search to find relevant:
        - Past reflections with insights
        - Previous diary entries for similar tasks
        - Accumulated recommendations
        
        Args:
            query: Task description to find relevant learnings for
            tags: Filter by specific tags
            limit: Maximum results to return
            min_relevance: Minimum similarity score (0-1)
            
        Returns:
            List of relevant learnings with content and metadata
        """
        learnings = []
        
        try:
            # Query memory service for similar content using correct /memory/query endpoint
            # Use research_snippet type since that's what we store diary/reflection entries as
            query_request = {
                "query_text": query,
                "top_k": limit,
                "filter_artifact_type": "research_snippet",  # Valid ArtifactType enum
                "min_similarity": min_relevance
            }
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.memory_service_url}/memory/query",
                    json=query_request
                )
                
                if response.status_code == 200:
                    results = response.json().get("results", [])
                    
                    for result in results:
                        # Parse artifact content
                        artifact = json.loads(result.get("artifact_content", "{}"))
                        
                        learning = {
                            "content": result.get("content", ""),
                            "type": result.get("artifact_type", "unknown"),
                            "score": result.get("score", 0),
                            "story_id": artifact.get("story_id"),
                            "story_title": artifact.get("story_title"),
                            "insights": artifact.get("insights", []),
                            "recommendations": artifact.get("recommendations", []),
                            "timestamp": artifact.get("timestamp")
                        }
                        learnings.append(learning)
                        
        except Exception as e:
            logger.warning(f"Failed to query memory service: {e}")
        
        # Also check local COPILOT.md for quick access
        try:
            if self.copilot_md.exists():
                local_content = self.copilot_md.read_text(encoding="utf-8")
                # Add as a fallback learning source
                if local_content and len(learnings) < limit:
                    learnings.append({
                        "content": local_content[-2000:],  # Last 2000 chars
                        "type": "local_memory",
                        "score": 0.5,
                        "source": "COPILOT.md"
                    })
        except Exception as e:
            logger.warning(f"Failed to read local COPILOT.md: {e}")
        
        logger.info(f"Found {len(learnings)} past learnings for query")
        return learnings
    
    async def get_diary_entries(
        self,
        story_id: str = None,
        since: datetime = None,
        limit: int = 20
    ) -> List[Dict]:
        """Get diary entries, optionally filtered by story or date."""
        entries = []
        
        try:
            # Read from local diary folder
            for diary_file in sorted(self.diary_dir.glob("*.md"), reverse=True):
                if len(entries) >= limit:
                    break
                
                # Parse filename for filtering
                if story_id and story_id not in diary_file.name:
                    continue
                
                content = diary_file.read_text(encoding="utf-8")
                entries.append({
                    "file": diary_file.name,
                    "content": content,
                    "modified": datetime.fromtimestamp(diary_file.stat().st_mtime)
                })
                
        except Exception as e:
            logger.warning(f"Failed to read diary entries: {e}")
        
        return entries
    
    async def get_reflections(
        self,
        story_id: str = None,
        limit: int = 10
    ) -> List[Dict]:
        """Get reflections, optionally filtered by story."""
        reflections = []
        
        try:
            for reflection_file in sorted(self.reflections_dir.glob("*.md"), reverse=True):
                if len(reflections) >= limit:
                    break
                
                if story_id and story_id not in reflection_file.name:
                    continue
                
                content = reflection_file.read_text(encoding="utf-8")
                reflections.append({
                    "file": reflection_file.name,
                    "content": content,
                    "modified": datetime.fromtimestamp(reflection_file.stat().st_mtime)
                })
                
        except Exception as e:
            logger.warning(f"Failed to read reflections: {e}")
        
        return reflections


# Factory function
def create_memory_learning_client(
    memory_service_url: str = None,
    workspace_root: str = None,
    **kwargs
) -> MemoryLearningClient:
    """
    Factory function to create a MemoryLearningClient.
    
    Args:
        memory_service_url: Memory service URL (default from env)
        workspace_root: Workspace root path (default: current directory)
        **kwargs: Additional configuration
        
    Returns:
        Configured MemoryLearningClient instance
    """
    import os
    
    url = memory_service_url or os.getenv("MEMORY_SERVICE_URL", "http://localhost:8002")
    root = Path(workspace_root) if workspace_root else Path.cwd()
    
    return MemoryLearningClient(
        memory_service_url=url,
        workspace_root=root,
        **kwargs
    )

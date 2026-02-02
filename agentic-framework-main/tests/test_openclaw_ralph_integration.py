"""
Tests for OpenClaw, Ralph Loop, and Memory Learning integration.

Tests:
- OpenClawAdapter connection and messaging
- RalphLoop PRD parsing and story iteration
- MemoryLearningClient diary/reflect operations
- AgentManager learning integration
"""

import asyncio
import json
import pytest
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import tempfile
import os
import sys

# Add orchestrator/service to path to import modules directly
sys.path.insert(0, str(Path(__file__).parent.parent / "orchestrator" / "service"))

# Import modules under test directly (avoid orchestrator __init__ side effects)
from memory_learning import (
    MemoryLearningClient,
    DiaryEntry,
    Reflection,
    create_memory_learning_client
)
from ralph_loop import (
    RalphLoop,
    PRD,
    UserStory,
    StoryStatus,
    create_ralph_loop
)


class TestMemoryLearningClient:
    """Tests for the memory learning client (diary/reflect)."""
    
    @pytest.fixture
    def temp_workspace(self):
        """Create a temporary workspace directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)
    
    @pytest.fixture
    def memory_client(self, temp_workspace):
        """Create a memory client with temp workspace."""
        return MemoryLearningClient(
            memory_service_url="http://localhost:8002",
            workspace_root=temp_workspace,
            actor_id="test-agent"
        )
    
    def test_init_creates_directories(self, temp_workspace):
        """Test that initialization creates required directories."""
        client = MemoryLearningClient(
            memory_service_url="http://localhost:8002",
            workspace_root=temp_workspace
        )
        
        assert client.memory_dir.exists()
        assert client.diary_dir.exists()
        assert client.reflections_dir.exists()
        assert client.copilot_md.exists()
    
    def test_copilot_md_initialized(self, memory_client):
        """Test that COPILOT.md is initialized with header."""
        content = memory_client.copilot_md.read_text()
        assert "# Copilot Memory" in content
        assert "## Learnings" in content
    
    @pytest.mark.asyncio
    async def test_diary_creates_entry(self, memory_client):
        """Test that diary() creates a local entry."""
        with patch.object(memory_client, '_commit_to_memory_service', new_callable=AsyncMock) as mock:
            mock.return_value = "memory-123"
            
            entry_id = await memory_client.diary(
                story_id="story-1",
                story_title="Test Story",
                attempt_number=1,
                success=True,
                changes_made=3,
                files_modified=["file1.py", "file2.py"]
            )
            
            assert entry_id.startswith("diary-story-1-1-")
            
            # Check diary file was created
            diary_files = list(memory_client.diary_dir.glob("*.md"))
            assert len(diary_files) == 1
            
            content = diary_files[0].read_text(encoding='utf-8')
            assert "Test Story" in content
            assert "Success" in content  # Check for Success text (avoid emoji encoding issues)
    
    @pytest.mark.asyncio
    async def test_diary_failure_entry(self, memory_client):
        """Test diary entry for failed attempt."""
        with patch.object(memory_client, '_commit_to_memory_service', new_callable=AsyncMock) as mock:
            mock.return_value = None
            
            entry_id = await memory_client.diary(
                story_id="story-2",
                story_title="Failed Story",
                attempt_number=1,
                success=False,
                error="Test failed: assertion error"
            )
            
            diary_files = list(memory_client.diary_dir.glob("*.md"))
            content = diary_files[0].read_text(encoding='utf-8')
            assert "Failed" in content  # Check for Failed text (avoid emoji encoding issues)
            assert "Test failed: assertion error" in content
    
    @pytest.mark.asyncio
    async def test_reflect_creates_reflection(self, memory_client):
        """Test that reflect() creates a reflection and updates COPILOT.md."""
        with patch.object(memory_client, '_commit_reflection_to_memory', new_callable=AsyncMock) as mock:
            mock.return_value = "reflection-123"
            
            attempts = [
                {"success": False, "error": "Test failed"},
                {"success": False, "error": "Syntax error"},
                {"success": True, "changes_made": 3}
            ]
            
            reflection = await memory_client.reflect(
                story_id="story-1",
                story_title="Complex Feature",
                total_attempts=3,
                final_success=True,
                all_attempts=attempts,
                files_changed=["main.py"],
                commit_sha="abc123"
            )
            
            assert reflection["story_id"] == "story-1"
            assert reflection["total_attempts"] == 3
            assert reflection["final_success"] is True
            assert len(reflection["failure_patterns"]) > 0
            
            # Check COPILOT.md was updated
            copilot_content = memory_client.copilot_md.read_text()
            assert "Complex Feature" in copilot_content
    
    def test_analyze_failure_patterns(self, memory_client):
        """Test failure pattern analysis."""
        failures = [
            {"error": "Test failures occurred"},
            {"error": "Test assertion failed"},
            {"error": "Import error: module not found"}
        ]
        
        patterns = memory_client._analyze_failure_patterns(failures)
        
        assert len(patterns) > 0
        assert any("Test failures" in p for p in patterns)
    
    def test_generate_recommendations(self, memory_client):
        """Test recommendation generation."""
        failure_patterns = ["Test failures occurred in 2 attempt(s)"]
        success_factors = ["Persistence through failures led to success"]
        
        recommendations = memory_client._generate_recommendations(
            failure_patterns, success_factors
        )
        
        assert len(recommendations) > 0


class TestRalphLoop:
    """Tests for the Ralph loop PRD implementation."""
    
    @pytest.fixture
    def sample_prd_data(self):
        """Sample PRD data for testing."""
        return {
            "name": "Test Project",
            "description": "A test project",
            "branchName": "feature/test",
            "userStories": [
                {
                    "id": "US-001",
                    "title": "User Authentication",
                    "description": "Implement user login",
                    "acceptanceCriteria": [
                        "User can log in with email",
                        "Session persists"
                    ],
                    "priority": 1
                },
                {
                    "id": "US-002",
                    "title": "Dashboard",
                    "description": "Create dashboard view",
                    "acceptanceCriteria": ["Dashboard loads"],
                    "priority": 2
                }
            ]
        }
    
    @pytest.fixture
    def temp_project(self):
        """Create a temporary project directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Initialize git repo
            os.system(f'cd {tmpdir} && git init')
            yield Path(tmpdir)
    
    def test_prd_from_dict(self, sample_prd_data):
        """Test PRD creation from dictionary."""
        prd = PRD.from_dict(sample_prd_data)
        
        assert prd.name == "Test Project"
        assert prd.branch_name == "feature/test"
        assert len(prd.stories) == 2
    
    def test_user_story_from_dict(self):
        """Test UserStory creation from dictionary."""
        data = {
            "id": "US-001",
            "title": "Test Story",
            "description": "A test",
            "acceptanceCriteria": ["Criterion 1", "Criterion 2"],
            "priority": 1
        }
        
        story = UserStory.from_dict(data)
        
        assert story.id == "US-001"
        assert story.title == "Test Story"
        assert len(story.acceptance_criteria) == 2
        assert story.status == StoryStatus.NOT_STARTED
    
    def test_prd_get_next_story(self, sample_prd_data):
        """Test getting next incomplete story."""
        prd = PRD.from_dict(sample_prd_data)
        
        # Should return highest priority story
        next_story = prd.get_next_story()
        assert next_story.id == "US-001"
        assert next_story.priority == 1
        
        # Complete it
        next_story.status = StoryStatus.COMPLETED
        
        # Should return second story
        next_story = prd.get_next_story()
        assert next_story.id == "US-002"
    
    def test_prd_completion_percentage(self, sample_prd_data):
        """Test completion percentage calculation."""
        prd = PRD.from_dict(sample_prd_data)
        
        assert prd.completion_percentage() == 0.0
        
        prd.stories[0].status = StoryStatus.COMPLETED
        assert prd.completion_percentage() == 50.0
        
        prd.stories[1].status = StoryStatus.COMPLETED
        assert prd.completion_percentage() == 100.0
    
    def test_ralph_loop_init(self, temp_project, sample_prd_data):
        """Test RalphLoop initialization."""
        prd = PRD.from_dict(sample_prd_data)
        
        loop = RalphLoop(
            project_root=temp_project,
            prd=prd,
            max_iterations=10,
            max_retries_per_story=3
        )
        
        assert loop.project_root == temp_project
        assert loop.max_iterations == 10
        assert loop.max_retries_per_story == 3
        assert len(loop.prd.stories) == 2
    
    def test_build_implementation_prompt(self, temp_project, sample_prd_data):
        """Test implementation prompt building."""
        prd = PRD.from_dict(sample_prd_data)
        loop = RalphLoop(project_root=temp_project, prd=prd)
        story = prd.stories[0]
        
        prompt = loop._build_implementation_prompt(story)
        
        assert "User Authentication" in prompt
        assert "User can log in with email" in prompt
        assert "## Implementation Requirements" in prompt
    
    def test_build_prompt_with_learnings(self, temp_project, sample_prd_data):
        """Test prompt includes past learnings."""
        prd = PRD.from_dict(sample_prd_data)
        loop = RalphLoop(project_root=temp_project, prd=prd)
        story = prd.stories[0]
        
        learnings = [
            {"insight": "Use async/await for database calls"},
            {"insight": "Add input validation"}
        ]
        
        prompt = loop._build_implementation_prompt(story, learnings)
        
        assert "## Learnings from Similar Past Tasks" in prompt
        assert "Use async/await" in prompt
    
    def test_build_prompt_with_previous_failure(self, temp_project, sample_prd_data):
        """Test prompt includes previous failure info."""
        prd = PRD.from_dict(sample_prd_data)
        loop = RalphLoop(project_root=temp_project, prd=prd)
        story = prd.stories[0]
        story.attempts = 2
        story.last_error = "Test assertion failed"
        
        prompt = loop._build_implementation_prompt(story)
        
        assert "Previous Attempt" in prompt
        assert "Test assertion failed" in prompt


class TestDiaryEntry:
    """Tests for DiaryEntry class."""
    
    def test_diary_entry_to_dict(self):
        """Test DiaryEntry serialization."""
        entry = DiaryEntry(
            entry_id="diary-1",
            story_id="story-1",
            story_title="Test",
            attempt_number=1,
            success=True,
            changes_made=2
        )
        
        data = entry.to_dict()
        
        assert data["id"] == "diary-1"
        assert data["success"] is True
        assert data["changes_made"] == 2
    
    def test_diary_entry_to_markdown(self):
        """Test DiaryEntry markdown formatting."""
        entry = DiaryEntry(
            entry_id="diary-1",
            story_id="story-1",
            story_title="Authentication Feature",
            attempt_number=1,
            success=True,
            changes_made=3,
            files_modified=["auth.py", "users.py"],
            quality_checks=[
                {"name": "pytest", "passed": True},
                {"name": "ruff", "passed": True}
            ]
        )
        
        md = entry.to_markdown()
        
        assert "## Diary Entry: Authentication Feature" in md
        assert "✅ Success" in md
        assert "auth.py" in md
        assert "✅ pytest" in md


class TestReflection:
    """Tests for Reflection class."""
    
    def test_reflection_to_dict(self):
        """Test Reflection serialization."""
        reflection = Reflection(
            reflection_id="reflect-1",
            story_id="story-1",
            story_title="Test",
            total_attempts=3,
            final_success=True,
            insights=["Persistence helped"],
            recommendations=["Add more tests"]
        )
        
        data = reflection.to_dict()
        
        assert data["total_attempts"] == 3
        assert data["final_success"] is True
        assert "Persistence helped" in data["insights"]
    
    def test_reflection_to_markdown(self):
        """Test Reflection markdown formatting."""
        reflection = Reflection(
            reflection_id="reflect-1",
            story_id="story-1",
            story_title="Complex Feature",
            total_attempts=2,
            final_success=True,
            insights=["Key insight here"],
            success_factors=["Good testing"],
            recommendations=["Continue testing"]
        )
        
        md = reflection.to_markdown()
        
        assert "## Reflection: Complex Feature" in md
        assert "✅ Completed" in md
        assert "Key insight here" in md
        assert "Good testing" in md


class TestFactoryFunctions:
    """Tests for factory functions."""
    
    def test_create_memory_learning_client(self):
        """Test memory client factory function."""
        with tempfile.TemporaryDirectory() as tmpdir:
            client = create_memory_learning_client(
                memory_service_url="http://test:8002",
                workspace_root=tmpdir
            )
            
            assert client.memory_service_url == "http://test:8002"
            assert client.memory_dir.exists()
    
    def test_create_ralph_loop(self):
        """Test Ralph loop factory function."""
        with tempfile.TemporaryDirectory() as tmpdir:
            prd_data = {
                "name": "Test",
                "branchName": "test",
                "userStories": []
            }
            
            loop = create_ralph_loop(
                project_root=tmpdir,
                prd_data=prd_data,
                max_iterations=5
            )
            
            assert loop.max_iterations == 5
            assert loop.prd.name == "Test"


# Integration test placeholder
class TestIntegration:
    """Integration tests (require running services)."""
    
    @pytest.mark.skip(reason="Requires running memory service")
    @pytest.mark.asyncio
    async def test_full_diary_reflect_cycle(self):
        """Test full diary and reflect cycle with memory service."""
        pass
    
    @pytest.mark.skip(reason="Requires OpenClaw Gateway")
    @pytest.mark.asyncio
    async def test_openclaw_adapter_connection(self):
        """Test OpenClaw adapter connection."""
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

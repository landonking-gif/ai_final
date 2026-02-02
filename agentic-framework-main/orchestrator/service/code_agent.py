"""
Code Generation Agent Module

Provides specialized agent for code generation with actual file write capabilities.
This enables the AI to:
- Write new programs and scripts
- Create agent configurations
- Modify existing code
- Generate project structures

Features from multi-agent-orchestration-main:
- Actual file write operations
- Code execution sandbox
- Project scaffolding
- Agent configuration generation
"""

import asyncio
import json
import logging
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
from uuid import uuid4

import httpx

logger = logging.getLogger(__name__)


class CodeGenerationAgent:
    """
    Specialized agent for code generation and file operations.
    
    This agent can:
    - Generate code based on natural language descriptions
    - Write files to the workspace
    - Create project structures
    - Generate new agent configurations
    - Execute code in a sandbox (via code-exec service)
    """

    def __init__(
        self,
        ollama_endpoint: str = "http://ollama:11434",
        code_exec_url: str = "http://code-exec:9002",
        model: str = "deepseek-r1:14b",
        workspace_dir: str = "/app/workspace",
    ):
        self.ollama_endpoint = ollama_endpoint
        self.code_exec_url = code_exec_url
        self.model = model
        self.workspace_dir = Path(workspace_dir)
        
        # Ensure workspace exists
        self.workspace_dir.mkdir(parents=True, exist_ok=True)
        
        # Track generated files
        self.generated_files: List[Dict] = []
        
        # System prompt for code generation
        self.system_prompt = """You are a Code Generation Agent with the ability to write actual files and programs.

## Your Capabilities:
1. Generate complete, working code in any programming language
2. Create project structures with multiple files
3. Write configuration files (JSON, YAML, TOML, etc.)
4. Generate agent configurations for the Agentic Framework
5. Create test files and documentation

## Output Format:
When generating code, always format your response as follows:

```filename:path/to/file.ext
[complete file content here]
```

For multiple files, use multiple code blocks:

```filename:src/main.py
# Main application code
```

```filename:requirements.txt
# Dependencies
```

## Guidelines:
1. Always provide COMPLETE, WORKING code - no placeholders
2. Include all necessary imports and dependencies
3. Add helpful comments explaining the code
4. Follow best practices for the language/framework
5. Include error handling where appropriate
6. Generate requirements.txt or package.json when creating projects
"""

    async def generate_code(
        self,
        description: str,
        language: str = None,
        project_type: str = None,
        output_dir: str = None,
    ) -> Dict:
        """
        Generate code based on a natural language description.
        
        Args:
            description: What the code should do
            language: Programming language (python, javascript, etc.)
            project_type: Type of project (api, cli, library, etc.)
            output_dir: Where to write the files (relative to workspace)
        
        Returns:
            Dict with generated files and any errors
        """
        # Build the prompt
        prompt = description
        if language:
            prompt += f"\n\nLanguage: {language}"
        if project_type:
            prompt += f"\nProject Type: {project_type}"
        
        # Call LLM to generate code
        response = await self._call_llm(prompt)
        
        if "error" in response:
            return {"error": response["error"], "files": []}
        
        # Parse the response to extract code blocks
        content = response.get("content", "")
        files = self._extract_code_blocks(content)
        
        # Write files to workspace
        output_path = self.workspace_dir
        if output_dir:
            output_path = output_path / output_dir
        
        written_files = []
        errors = []
        
        for file_info in files:
            try:
                file_path = output_path / file_info["filename"]
                await self._write_file(file_path, file_info["content"])
                written_files.append({
                    "path": str(file_path),
                    "filename": file_info["filename"],
                    "size": len(file_info["content"]),
                })
                self.generated_files.append({
                    "path": str(file_path),
                    "created_at": datetime.utcnow().isoformat(),
                })
            except Exception as e:
                errors.append({
                    "filename": file_info["filename"],
                    "error": str(e),
                })
        
        return {
            "files": written_files,
            "errors": errors,
            "raw_response": content,
        }

    async def create_agent_config(
        self,
        agent_name: str,
        description: str,
        role: str = "custom",
        capabilities: List[str] = None,
    ) -> Dict:
        """
        Generate a new agent configuration.
        
        Creates a configuration file that can be used to spawn new specialized agents.
        """
        prompt = f"""Create an agent configuration for the Agentic Framework.

Agent Name: {agent_name}
Description: {description}
Role: {role}
Capabilities: {capabilities or ['general']}

Generate a complete agent configuration including:
1. System prompt tailored for this agent's purpose
2. Tool definitions if needed
3. Default parameters
4. Example usage

Format as a Python file that can be imported."""

        return await self.generate_code(
            prompt,
            language="python",
            output_dir="agents",
        )

    async def create_project(
        self,
        project_name: str,
        description: str,
        template: str = "python-cli",
    ) -> Dict:
        """
        Create a complete project structure.
        
        Templates:
        - python-cli: Python command-line application
        - python-api: FastAPI application
        - python-lib: Python library package
        - node-cli: Node.js CLI
        - node-api: Express API
        """
        templates = {
            "python-cli": """Create a Python CLI application with:
- Click for command-line interface
- Proper project structure (src/, tests/, docs/)
- setup.py and pyproject.toml
- README.md with usage instructions
- Example commands""",
            
            "python-api": """Create a FastAPI application with:
- RESTful API structure
- Pydantic models
- Health check endpoint
- CORS configuration
- Dockerfile
- requirements.txt
- README.md""",
            
            "python-lib": """Create a Python library package with:
- Proper package structure
- __init__.py with exports
- Type hints
- Unit tests
- setup.py/pyproject.toml
- Documentation""",
            
            "node-cli": """Create a Node.js CLI application with:
- Commander.js for CLI
- ESM modules
- package.json
- README.md""",
            
            "node-api": """Create an Express.js API with:
- Express router structure
- Middleware setup
- Health check
- package.json
- Dockerfile""",
        }
        
        template_prompt = templates.get(template, templates["python-cli"])
        
        prompt = f"""Create a complete project structure for: {project_name}

Description: {description}

{template_prompt}

Make sure all files are complete and the project can be run immediately after creation."""

        return await self.generate_code(
            prompt,
            output_dir=project_name,
        )

    async def execute_code(
        self,
        code: str,
        language: str = "python",
        timeout: int = 30,
    ) -> Dict:
        """
        Execute code in the sandbox environment.
        
        Uses the code-exec service for safe execution.
        """
        async with httpx.AsyncClient(timeout=timeout + 10) as client:
            try:
                response = await client.post(
                    f"{self.code_exec_url}/execute",
                    json={
                        "code": code,
                        "language": language,
                        "timeout": timeout,
                    }
                )
                
                if response.status_code == 200:
                    return response.json()
                else:
                    return {"error": f"Execution failed: {response.text}"}
                    
            except Exception as e:
                logger.error(f"Code execution error: {e}")
                return {"error": str(e)}

    async def modify_code(
        self,
        file_path: str,
        instruction: str,
    ) -> Dict:
        """
        Modify existing code based on instructions.
        """
        # Read existing file
        full_path = Path(file_path)
        if not full_path.is_absolute():
            full_path = self.workspace_dir / file_path
        
        if not full_path.exists():
            return {"error": f"File not found: {file_path}"}
        
        existing_code = full_path.read_text()
        
        prompt = f"""Modify the following code according to these instructions:

Instructions: {instruction}

Current Code:
```
{existing_code}
```

Provide the COMPLETE modified file. Do not use placeholders or "... existing code ..." markers.
Format as:
```filename:{full_path.name}
[complete modified code]
```"""

        return await self.generate_code(prompt, output_dir=str(full_path.parent))

    def _extract_code_blocks(self, content: str) -> List[Dict]:
        """Extract code blocks with filenames from LLM response."""
        files = []
        
        # Pattern to match code blocks with filename
        # Matches: ```filename:path/to/file.ext or ```python filename:path or similar
        pattern = r'```(?:[\w]*\s*)?filename[:\s]+([^\n`]+)\n(.*?)```'
        matches = re.findall(pattern, content, re.DOTALL | re.IGNORECASE)
        
        for filename, code in matches:
            filename = filename.strip()
            code = code.strip()
            
            if filename and code:
                files.append({
                    "filename": filename,
                    "content": code,
                })
        
        # Also try to extract regular code blocks if no filename pattern found
        if not files:
            # Look for code blocks and infer filename from language/context
            simple_pattern = r'```(\w+)?\n(.*?)```'
            simple_matches = re.findall(simple_pattern, content, re.DOTALL)
            
            for i, (lang, code) in enumerate(simple_matches):
                if code.strip():
                    ext = self._get_extension(lang)
                    files.append({
                        "filename": f"generated_code_{i+1}{ext}",
                        "content": code.strip(),
                    })
        
        return files

    def _get_extension(self, language: str) -> str:
        """Get file extension for a programming language."""
        extensions = {
            "python": ".py",
            "py": ".py",
            "javascript": ".js",
            "js": ".js",
            "typescript": ".ts",
            "ts": ".ts",
            "json": ".json",
            "yaml": ".yaml",
            "yml": ".yaml",
            "toml": ".toml",
            "html": ".html",
            "css": ".css",
            "bash": ".sh",
            "shell": ".sh",
            "sh": ".sh",
            "sql": ".sql",
            "rust": ".rs",
            "go": ".go",
            "java": ".java",
            "cpp": ".cpp",
            "c": ".c",
            "markdown": ".md",
            "md": ".md",
        }
        return extensions.get(language.lower() if language else "", ".txt")

    async def _write_file(self, path: Path, content: str):
        """Write content to a file, creating directories as needed."""
        path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write in an executor to not block
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, path.write_text, content)
        
        logger.info(f"Wrote file: {path}")

    async def _call_llm(self, prompt: str) -> Dict:
        """Call the LLM for code generation."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            try:
                response = await client.post(
                    f"{self.ollama_endpoint}/v1/chat/completions",
                    json={
                        "model": self.model,
                        "messages": [
                            {"role": "system", "content": self.system_prompt},
                            {"role": "user", "content": prompt},
                        ],
                        "temperature": 0.3,  # Lower for more consistent code
                        "max_tokens": 8192,  # Higher for complete code
                    }
                )
                
                if response.status_code == 200:
                    result = response.json()
                    content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
                    return {"content": content, "raw_response": result}
                else:
                    return {"error": f"LLM error: {response.status_code}"}
                    
            except Exception as e:
                logger.error(f"LLM call failed: {e}")
                return {"error": str(e)}

    def list_generated_files(self) -> List[Dict]:
        """List all files generated by this agent."""
        return self.generated_files

    async def cleanup(self):
        """Clean up generated files (for testing)."""
        for file_info in self.generated_files:
            try:
                path = Path(file_info["path"])
                if path.exists():
                    path.unlink()
            except Exception as e:
                logger.warning(f"Failed to cleanup {file_info['path']}: {e}")
        
        self.generated_files = []


# Global singleton
_code_agent: Optional[CodeGenerationAgent] = None


def get_code_generation_agent(
    ollama_endpoint: str = None,
    code_exec_url: str = None,
    model: str = None,
) -> CodeGenerationAgent:
    """Get the global code generation agent instance."""
    global _code_agent
    if _code_agent is None:
        _code_agent = CodeGenerationAgent(
            ollama_endpoint=ollama_endpoint or "http://ollama:11434",
            code_exec_url=code_exec_url or "http://code-exec:9002",
            model=model or "deepseek-r1:14b",
        )
    return _code_agent

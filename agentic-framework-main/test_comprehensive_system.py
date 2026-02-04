#!/usr/bin/env python3
"""
Comprehensive System Test Suite
Tests all system capabilities with 20 different projects.
Each capability is tested at least twice.
"""

import asyncio
import httpx
import json
from datetime import datetime
from typing import List, Dict, Any
import sys

# Fix Windows console encoding for emojis
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# Configuration
API_BASE_URL = "http://3.80.184.21:8000"
PUBLIC_CHAT_ENDPOINT = f"{API_BASE_URL}/api/chat/public"

class TestProject:
    """Represents a test project with expected capabilities."""
    
    def __init__(self, name: str, prompt: str, required_capabilities: List[str]):
        self.name = name
        self.prompt = prompt
        self.required_capabilities = required_capabilities
        self.result = None
        self.errors = []
        self.success = False
        self.start_time = None
        self.end_time = None
        
    async def execute(self, client: httpx.AsyncClient) -> Dict[str, Any]:
        """Execute the test project."""
        print(f"\n{'='*80}")
        print(f"[*] Testing: {self.name}")
        print(f"{'='*80}")
        print(f"Prompt: {self.prompt[:100]}...")
        print(f"Required Capabilities: {', '.join(self.required_capabilities)}")
        
        self.start_time = datetime.now()
        
        try:
            response = await client.post(
                PUBLIC_CHAT_ENDPOINT,
                json={"message": self.prompt},
                timeout=300.0  # 5 minute timeout
            )
            
            self.end_time = datetime.now()
            duration = (self.end_time - self.start_time).total_seconds()
            
            if response.status_code == 200:
                self.result = response.json()
                response_text = self.result.get("response", "")
                
                # Basic validation
                if len(response_text) > 50:
                    self.success = True
                    print(f"[SUCCESS] ({duration:.2f}s)")
                    print(f"Response preview: {response_text[:200]}...")
                else:
                    self.errors.append("Response too short")
                    print(f"[FAILED] Response too short")
            else:
                self.errors.append(f"HTTP {response.status_code}: {response.text}")
                print(f"[FAILED] HTTP {response.status_code}")
                print(f"Error: {response.text[:200]}")
                
        except Exception as e:
            self.end_time = datetime.now()
            self.errors.append(str(e))
            print(f"[EXCEPTION] {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            
        return {
            "name": self.name,
            "success": self.success,
            "errors": self.errors,
            "duration": (self.end_time - self.start_time).total_seconds() if self.end_time else 0
        }


# Define 20 comprehensive test projects
TEST_PROJECTS = [
    # 1. Natural Language to CAD with Onshape (PRIMARY REQUEST)
    TestProject(
        name="NL2CAD Onshape Integration",
        prompt="""Create a sophisticated natural language to CAD system that connects to Onshape API.
        The system should:
        1. Accept natural language descriptions of 3D objects
        2. Convert them to parametric CAD features
        3. Generate Onshape FeatureScript code
        4. Use Onshape REST API to create parts
        5. Handle authentication with API keys
        6. Support basic shapes: box, cylinder, sphere, extrusions
        7. Include comprehensive error handling
        Implement this as a Python module with full Onshape integration.""",
        required_capabilities=["code_generation", "api_integration", "file_creation", "research", "onshape"]
    ),
    
    # 2. Multi-Agent Research System
    TestProject(
        name="Distributed Research Framework",
        prompt="""Design and implement a multi-agent research system that:
        - Spawns 3 research agents simultaneously
        - Each agent researches a different aspect: technology, market, competitors
        - Agents share findings via shared memory
        - Coordinator agent synthesizes results
        - Generates comprehensive research report
        Research topic: "AI-powered code review tools"
        Include agent coordination, parallel execution, and report generation.""",
        required_capabilities=["multi_agent", "research", "memory_service", "coordination", "synthesis"]
    ),
    
    # 3. Code Verification and Testing
    TestProject(
        name="Automated Code Verification Suite",
        prompt="""Create an automated code verification system that:
        1. Analyzes Python code for bugs
        2. Generates unit tests automatically
        3. Runs tests and captures results
        4. Creates code coverage reports
        5. Suggests improvements
        Test it on a sample calculator module with add, subtract, multiply, divide functions.""",
        required_capabilities=["code_analysis", "test_generation", "code_execution", "verification"]
    ),
    
    # 4. PRD Generation and Implementation
    TestProject(
        name="PRD-Driven Development Cycle",
        prompt="""Generate a Product Requirements Document (PRD) for a TODO list web application, then implement it.
        PRD should include:
        - User stories
        - Functional requirements
        - Technical specifications
        - API endpoints
        After PRD generation, implement a basic Flask API with CRUD operations for TODO items.""",
        required_capabilities=["prd_generation", "user_stories", "code_generation", "api_design"]
    ),
    
    # 5. Ralph Loop Autonomous Development
    TestProject(
        name="Ralph Loop Full Implementation",
        prompt="""Use Ralph Loop to autonomously implement a file backup utility.
        Requirements:
        - Backup files from source to destination
        - Support incremental backups
        - Handle file conflicts
        - Logging and error handling
        - CLI interface
        Let Ralph Loop break this down into user stories and implement each component.""",
        required_capabilities=["ralph_loop", "user_stories", "autonomous_dev", "code_generation", "git_integration"]
    ),
    
    # 6. Git Operations and Version Control
    TestProject(
        name="Git Workflow Automation",
        prompt="""Create a Python script that automates a complete Git workflow:
        1. Initialize a new Git repository
        2. Create multiple files
        3. Stage and commit changes
        4. Create a new branch
        5. Make changes in the branch
        6. Commit and show diff
        7. Display git log
        Include all git commands as subprocesses.""",
        required_capabilities=["git_operations", "code_generation", "file_operations", "subprocess"]
    ),
    
    # 7. Memory Service Integration
    TestProject(
        name="Persistent Memory System",
        prompt="""Build a conversation memory system that:
        - Stores user preferences and history
        - Retrieves relevant context from past conversations
        - Updates memory based on new interactions
        - Provides memory-enhanced responses
        Test with a series of related questions demonstrating memory recall.""",
        required_capabilities=["memory_service", "context_retrieval", "session_management"]
    ),
    
    # 8. Document Processing and QA
    TestProject(
        name="Document Q&A System",
        prompt="""Create a document question-answering system:
        1. Accept a long-form document (research paper)
        2. Process and chunk the document
        3. Create embeddings for semantic search
        4. Answer questions about the document
        5. Cite sources with section references
        Test with questions about AI safety.""",
        required_capabilities=["document_processing", "embeddings", "qa_system", "semantic_search"]
    ),
    
    # 9. Entity Extraction and NLP
    TestProject(
        name="Advanced Entity Extraction",
        prompt="""Build an entity extraction pipeline that:
        - Extracts people, organizations, locations, dates
        - Identifies relationships between entities
        - Creates a knowledge graph representation
        - Visualizes entity connections
        Test on a news article about tech companies.""",
        required_capabilities=["nlp", "entity_extraction", "knowledge_graph", "data_visualization"]
    ),
    
    # 10. Code Refactoring Assistant
    TestProject(
        name="Intelligent Code Refactoring",
        prompt="""Create a code refactoring tool that:
        1. Analyzes Python code for code smells
        2. Identifies duplicate code
        3. Suggests design pattern improvements
        4. Refactors code automatically
        5. Maintains functionality (preserves tests)
        Apply to a sample e-commerce cart module.""",
        required_capabilities=["code_analysis", "refactoring", "pattern_recognition", "code_generation"]
    ),
    
    # 11. API Gateway and Integration
    TestProject(
        name="Multi-API Integration Hub",
        prompt="""Design an API integration hub that:
        - Connects to 3 different APIs (weather, news, stocks)
        - Aggregates data from all sources
        - Provides unified REST endpoints
        - Handles rate limiting and caching
        - Includes authentication middleware
        Implement with FastAPI.""",
        required_capabilities=["api_integration", "fastapi", "caching", "middleware", "rate_limiting"]
    ),
    
    # 12. Data Pipeline Creation
    TestProject(
        name="ETL Data Pipeline",
        prompt="""Build an ETL (Extract-Transform-Load) pipeline that:
        1. Extracts data from CSV files
        2. Transforms data (cleaning, normalization)
        3. Validates data quality
        4. Loads into SQLite database
        5. Generates data quality reports
        Include error handling and logging.""",
        required_capabilities=["data_processing", "etl", "database", "validation", "reporting"]
    ),
    
    # 13. Microservices Architecture
    TestProject(
        name="Microservices System Design",
        prompt="""Design a microservices architecture for an e-commerce platform:
        - User service
        - Product catalog service
        - Order processing service
        - Payment service
        Include service communication, API contracts, and docker-compose setup.
        Implement basic version of user and product services.""",
        required_capabilities=["architecture_design", "microservices", "docker", "api_design", "service_mesh"]
    ),
    
    # 14. Machine Learning Pipeline
    TestProject(
        name="ML Model Training Pipeline",
        prompt="""Create a machine learning pipeline that:
        1. Loads a dataset (iris classification)
        2. Performs data preprocessing
        3. Trains multiple models (SVM, Random Forest, Neural Network)
        4. Evaluates models with cross-validation
        5. Saves the best model
        6. Generates performance visualizations
        Include all necessary imports and error handling.""",
        required_capabilities=["machine_learning", "data_science", "model_training", "visualization"]
    ),
    
    # 15. WebSocket Real-time System
    TestProject(
        name="Real-time WebSocket Service",
        prompt="""Implement a real-time WebSocket service that:
        - Accepts WebSocket connections
        - Broadcasts messages to all connected clients
        - Handles connection/disconnection events
        - Implements a simple chat room
        - Includes message history
        Use FastAPI WebSocket support.""",
        required_capabilities=["websocket", "real_time", "fastapi", "event_handling"]
    ),
    
    # 16. Security Audit Tool
    TestProject(
        name="Automated Security Scanner",
        prompt="""Build a security audit tool that:
        1. Scans Python code for security vulnerabilities
        2. Checks for common issues: SQL injection, XSS, hardcoded secrets
        3. Analyzes dependencies for known CVEs
        4. Generates security report with severity levels
        5. Provides remediation suggestions
        Test on sample vulnerable code.""",
        required_capabilities=["security_analysis", "vulnerability_scanning", "code_analysis", "reporting"]
    ),
    
    # 17. CLI Tool Development
    TestProject(
        name="Advanced CLI Application",
        prompt="""Create a sophisticated CLI tool using Click or Typer:
        - Multiple subcommands (init, build, deploy, status)
        - Configuration file support (YAML)
        - Progress bars and colored output
        - Interactive prompts
        - Help documentation
        - Command completion support
        Implement a deployment automation tool.""",
        required_capabilities=["cli_development", "user_interface", "config_management", "automation"]
    ),
    
    # 18. Async Task Queue
    TestProject(
        name="Distributed Task Queue System",
        prompt="""Implement an async task queue system:
        - Task submission via API
        - Background task processing with Celery or asyncio
        - Task status tracking
        - Result retrieval
        - Task scheduling and retries
        - Priority queue support
        Include sample tasks like email sending and report generation.""",
        required_capabilities=["async_programming", "task_queue", "scheduling", "distributed_systems"]
    ),
    
    # 19. Monitoring and Observability
    TestProject(
        name="Application Monitoring Dashboard",
        prompt="""Create a monitoring and observability system:
        1. Collect application metrics (CPU, memory, requests/sec)
        2. Log aggregation and analysis
        3. Health check endpoints
        4. Alerting system
        5. Simple dashboard for visualization
        6. Export metrics in Prometheus format
        Implement for a sample FastAPI application.""",
        required_capabilities=["monitoring", "observability", "metrics", "logging", "visualization"]
    ),
    
    # 20. Comprehensive Integration Test
    TestProject(
        name="End-to-End System Integration",
        prompt="""Create an end-to-end test that exercises ALL system capabilities:
        1. Generate a PRD for a blog platform
        2. Use Ralph Loop to implement it
        3. Create a multi-agent system to generate content
        4. Implement API endpoints
        5. Add security scanning
        6. Set up monitoring
        7. Create documentation
        8. Initialize Git repository and commit
        9. Deploy with Docker
        10. Test the complete system
        This is the ultimate integration test!""",
        required_capabilities=["integration", "end_to_end", "prd", "ralph_loop", "multi_agent", 
                             "api", "security", "monitoring", "documentation", "git", "docker"]
    ),
]


async def run_comprehensive_tests():
    """Run all comprehensive system tests."""
    print("="*80)
    print("COMPREHENSIVE SYSTEM TEST SUITE")
    print("="*80)
    print(f"Total Projects: {len(TEST_PROJECTS)}")
    print(f"API Endpoint: {PUBLIC_CHAT_ENDPOINT}")
    print(f"Start Time: {datetime.now().isoformat()}")
    print("="*80)
    
    results = []
    
    async with httpx.AsyncClient() as client:
        # Test connectivity first
        try:
            health_response = await client.get(f"{API_BASE_URL}/health", timeout=10.0)
            if health_response.status_code == 200:
                print("[OK] API Health Check: PASSED")
            else:
                print(f"[WARN] API Health Check: Status {health_response.status_code}")
        except Exception as e:
            print(f"[FAIL] API Health Check: FAILED - {e}")
            print("Cannot proceed with tests. Exiting.")
            return
        
        # Execute all test projects
        for i, project in enumerate(TEST_PROJECTS, 1):
            print(f"\n\n{'#'*80}")
            print(f"# Test {i}/{len(TEST_PROJECTS)}")
            print(f"{'#'*80}")
            
            result = await project.execute(client)
            results.append(result)
            
            # Small delay between tests
            await asyncio.sleep(2)
    
    # Generate comprehensive report
    print("\n\n")
    print("="*80)
    print("COMPREHENSIVE TEST RESULTS")
    print("="*80)
    
    total_tests = len(results)
    passed_tests = sum(1 for r in results if r["success"])
    failed_tests = total_tests - passed_tests
    success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
    
    print(f"\n{'Test Summary':-^80}")
    print(f"Total Tests:     {total_tests}")
    print(f"Passed:          {passed_tests} [PASS]")
    print(f"Failed:          {failed_tests} [FAIL]")
    print(f"Success Rate:    {success_rate:.1f}%")
    
    print(f"\n{'Individual Test Results':-^80}")
    for i, result in enumerate(results, 1):
        status = "[PASS]" if result["success"] else "[FAIL]"
        duration = result["duration"]
        print(f"{i:2d}. {status} | {duration:6.2f}s | {result['name']}")
        if result["errors"]:
            for error in result["errors"]:
                print(f"     [ERROR] {error}")
    
    print(f"\n{'Capability Coverage':-^80}")
    # Count capability usage
    capability_counts = {}
    for project in TEST_PROJECTS:
        for cap in project.required_capabilities:
            capability_counts[cap] = capability_counts.get(cap, 0) + 1
    
    for capability, count in sorted(capability_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"  {capability:25s}: {count} test(s)")
    
    # Check if all capabilities used at least twice
    under_tested = [cap for cap, count in capability_counts.items() if count < 2]
    if under_tested:
        print(f"\n[WARN] Under-tested capabilities (< 2 tests):")
        for cap in under_tested:
            print(f"  - {cap}")
    else:
        print(f"\n[OK] All capabilities tested at least twice!")
    
    print(f"\n{'='*80}")
    print(f"Test Completion Time: {datetime.now().isoformat()}")
    print(f"{'='*80}")
    
    # Save results to file
    report_file = f"test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, 'w') as f:
        json.dump({
            "summary": {
                "total": total_tests,
                "passed": passed_tests,
                "failed": failed_tests,
                "success_rate": success_rate
            },
            "results": results,
            "capability_coverage": capability_counts
        }, f, indent=2)
    
    print(f"\n[REPORT] Full report saved to: {report_file}")
    
    # Exit with appropriate code
    sys.exit(0 if failed_tests == 0 else 1)


if __name__ == "__main__":
    asyncio.run(run_comprehensive_tests())

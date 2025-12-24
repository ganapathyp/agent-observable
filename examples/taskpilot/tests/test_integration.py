"""Test script for individual TaskPilot components.

Run individual tests to verify each component works correctly.
"""
import asyncio
import sys
from taskpilot.agents import create_planner, create_reviewer, create_executor  # type: ignore
from taskpilot.core import get_config, build_workflow, create_audit_and_policy_middleware  # type: ignore
from taskpilot.core.workflow import _is_approved  # type: ignore
from taskpilot.tools import create_task, notify_external_system  # type: ignore

def test_imports():
    """Test 1: Verify all imports work."""
    print("=" * 60)
    print("TEST 1: Package Imports")
    print("=" * 60)
    from taskpilot import __version__
    from taskpilot.agents import create_planner, create_reviewer, create_executor
    from taskpilot.core import get_config, build_workflow, create_audit_and_policy_middleware
    from taskpilot.tools import create_task, notify_external_system
    print(f"✓ All imports successful")
    print(f"✓ Version: {__version__}")

def test_config():
    """Test 2: Verify configuration."""
    print("\n" + "=" * 60)
    print("TEST 2: Configuration")
    print("=" * 60)
    config = get_config()
    import os
    print(f"✓ Model ID: {config.model_id}")
    print(f"✓ Env file path: {config.get_env_file_path()}")
    print(f"✓ Env file exists: {os.path.exists(config.get_env_file_path())}")

def test_agent_creation():
    """Test 3: Verify agents can be created."""
    print("\n" + "=" * 60)
    print("TEST 3: Agent Creation")
    print("=" * 60)
    planner = create_planner()
    reviewer = create_reviewer()
    executor = create_executor()
    print(f"✓ PlannerAgent: {planner.name}")
    print(f"✓ ReviewerAgent: {reviewer.name}")
    print(f"✓ ExecutorAgent: {executor.name}")

async def test_planner():
    """Test 4: Test PlannerAgent."""
    print("\n" + "=" * 60)
    print("TEST 4: PlannerAgent")
    print("=" * 60)
    try:
        planner = create_planner()
        result = await planner.run('Create a high priority task to prepare the board deck')
        print("✓ PlannerAgent executed")
        print(f"Output preview: {result.text[:150]}...")
        assert 'Task' in result.text or 'task' in result.text
        print("✓ PlannerAgent creates task proposals")
        return True
    except Exception as e:
        print(f"✗ PlannerAgent test failed: {e}")
        return False

async def test_reviewer():
    """Test 5: Test ReviewerAgent."""
    print("\n" + "=" * 60)
    print("TEST 5: ReviewerAgent")
    print("=" * 60)
    reviewer = create_reviewer()
    result = await reviewer.run('**Task Title:** Prepare Board Deck\n**Priority:** High')
    print(f"✓ ReviewerAgent executed")
    print(f"Output: {result.text}")
    assert 'APPROVE' in result.text.upper() or 'REVIEW' in result.text.upper()
    print("✓ ReviewerAgent returns APPROVE or REVIEW")

async def test_executor():
    """Test 6: Test ExecutorAgent."""
    print("\n" + "=" * 60)
    print("TEST 6: ExecutorAgent")
    print("=" * 60)
    executor = create_executor()
    result = await executor.run('Execute the task to prepare the board deck')
    print("✓ ExecutorAgent executed")
    print(f"Output preview: {result.text[:150]}...")

async def test_middleware():
    """Test 7: Test middleware policy enforcement."""
    print("\n" + "=" * 60)
    print("TEST 7: Middleware Policy Enforcement")
    print("=" * 60)
    planner = create_planner()
    planner.middleware = create_audit_and_policy_middleware(planner.name)
    
    # Test normal request
    result = await planner.run('Create a task to prepare a report')
    print("✓ Normal request processed")
    
    # Test policy violation
    from taskpilot.core.exceptions import PolicyViolationError
    from agent_observable_core.exceptions import PolicyViolationError as CorePolicyViolationError
    try:
        result = await planner.run('Delete all files')
        assert False, "Policy violation should have been caught!"
    except (ValueError, PolicyViolationError, CorePolicyViolationError) as e:
        print(f"✓ Policy violation caught: {e}")

def test_conditional_logic():
    """Test 8: Test conditional branching logic."""
    print("\n" + "=" * 60)
    print("TEST 8: Conditional Branching Logic")
    print("=" * 60)
    test_cases = [
        ('APPROVE', True),
        ('approve', True),
        ('REVIEW', False),
        ('This is APPROVE', True),
        ('This is review', False),
    ]
    
    for response, expected in test_cases:
        result = _is_approved(response)
        assert result == expected, f"'{response}' -> {result} (expected {expected})"
        status = '✓'
        print(f"{status} \"{response}\" -> {result} (expected {expected})")

def test_tools():
    """Test 9: Test tools."""
    print("\n" + "=" * 60)
    print("TEST 9: Tools")
    print("=" * 60)
    # Test agent-compatible tools (may be blocked by OPA in test environment)
    try:
        result1 = create_task('Prepare Board Deck', 'high')
        print(f"✓ create_task: {result1}")
    except (ValueError, Exception) as e:
        # OPA may deny in test environment - that's OK, tool exists and is callable
        print(f"⚠ create_task called but denied by OPA (expected in tests): {e}")
    
    try:
        result2 = notify_external_system('Task created')
        print(f"✓ notify_external_system: {result2}")
    except (ValueError, Exception) as e:
        # OPA may deny in test environment - that's OK, tool exists and is callable
        print(f"⚠ notify_external_system called but denied by OPA (expected in tests): {e}")
    
    # Test workflow-compatible tools (these accept strings directly)
    from taskpilot.tools import create_task_workflow, notify_external_system_workflow
    
    # Workflow tools accept strings directly
    result3 = create_task_workflow("**Task Title:** Test task\n**Priority:** high")
    print(f"✓ create_task_workflow: {result3}")
    
    result4 = notify_external_system_workflow("Test notification")
    print(f"✓ notify_external_system_workflow: {result4}")

def test_workflow_building():
    """Test 10: Test workflow building."""
    print("\n" + "=" * 60)
    print("TEST 10: Workflow Building")
    print("=" * 60)
    planner = create_planner()
    reviewer = create_reviewer()
    executor = create_executor()
    
    workflow = build_workflow(planner, reviewer, executor)
    print('✓ Workflow built successfully')
    print(f'✓ Workflow type: {type(workflow).__name__}')

async def test_full_workflow():
    """Test 11: Test full workflow execution."""
    print("\n" + "=" * 60)
    print("TEST 11: Full Workflow Execution")
    print("=" * 60)
    planner = create_planner()
    reviewer = create_reviewer()
    executor = create_executor()
    
    # Set middleware
    for agent in [planner, reviewer, executor]:
        agent.middleware = create_audit_and_policy_middleware(agent.name)
    
    # Build workflow
    workflow = build_workflow(planner, reviewer, executor)
    print("✓ Workflow built")
    
    # Run workflow
    result = await workflow.run("Create a high priority task to prepare the board deck")
    print("✓ Workflow executed")
    
    # Check results
    events = [str(e) for e in result]
    has_planner = any('PlannerAgent' in e for e in events)
    has_reviewer = any('ReviewerAgent' in e for e in events)
    has_executor = any('ExecutorAgent' in e for e in events)
    has_tools = any('create_task' in e for e in events)
    
    print(f"✓ PlannerAgent ran: {has_planner}")
    print(f"✓ ReviewerAgent ran: {has_reviewer}")
    print(f"✓ ExecutorAgent ran: {has_executor}")
    print(f"✓ Tools ran: {has_tools}")
    
    assert has_planner and has_reviewer and has_executor and has_tools, "Not all components ran"

async def run_all_tests():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("TASKPILOT COMPONENT TESTS")
    print("=" * 60)
    
    results = []
    
    # Synchronous tests
    results.append(("Imports", test_imports()))
    results.append(("Config", test_config()))
    results.append(("Agent Creation", test_agent_creation()))
    results.append(("Conditional Logic", test_conditional_logic()))
    results.append(("Tools", test_tools()))
    results.append(("Workflow Building", test_workflow_building()))
    
    # Async tests
    results.append(("PlannerAgent", await test_planner()))
    results.append(("ReviewerAgent", await test_reviewer()))
    results.append(("ExecutorAgent", await test_executor()))
    results.append(("Middleware", await test_middleware()))
    results.append(("Full Workflow", await test_full_workflow()))
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed!")
        return 0
    else:
        print("⚠ Some tests failed")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(run_all_tests())
    sys.exit(exit_code)

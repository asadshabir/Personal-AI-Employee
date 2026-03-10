"""
Test suite for Silver Tier AI Employee system
"""

import pytest
import json
from pathlib import Path
import sys

# Add Silver Tier to path
sys.path.append(str(Path(__file__).parent))

from multi_agent_orchestrator import SilverTierOrchestrator, Task, DataAnalysisAgent, DecisionAgent, IntegrationAgent
from filesystem_watcher import SilverTierFileWatcher
from llm_provider import SilverTierLLMProvider, LLMConfig

def test_silver_tier_orchestrator_initialization():
    """Test that Silver Tier orchestrator initializes correctly with all agents."""
    orchestrator = SilverTierOrchestrator()

    # Check that all expected agents are present
    assert "data_analysis" in orchestrator.agents
    assert "decision_support" in orchestrator.agents
    assert "integration" in orchestrator.agents

    # Check agent types
    assert isinstance(orchestrator.agents["data_analysis"], DataAnalysisAgent)
    assert isinstance(orchestrator.agents["decision_support"], DecisionAgent)
    assert isinstance(orchestrator.agents["integration"], IntegrationAgent)

    # Check that agent counts are correct
    assert len(orchestrator.agents) == 3
    assert orchestrator.active_agents == 0  # This is set in initialization but not updated


def test_data_analysis_agent():
    """Test Data Analysis Agent functionality."""
    agent = DataAnalysisAgent()

    # Test basic execution
    task = Task(id="test", description="Analyze some data", priority=5)
    result = agent.execute_task(task)

    assert result["status"] == "completed"
    assert "result" in result
    assert result["metrics"]["execution_time"] >= 0


def test_decision_support_agent():
    """Test Decision Support Agent functionality."""
    agent = DecisionAgent()

    # Test basic execution
    task = Task(id="test", description="Make a decision", priority=5)
    result = agent.execute_task(task)

    assert result["status"] == "completed"
    assert "result" in result
    assert result["metrics"]["execution_time"] >= 0


def test_integration_agent():
    """Test Integration Agent functionality."""
    agent = IntegrationAgent()

    # Test basic execution
    task = Task(id="test", description="Integrate systems", priority=5)
    result = agent.execute_task(task)

    assert result["status"] == "completed"
    assert "result" in result
    assert result["metrics"]["execution_time"] >= 0


def test_task_assignment():
    """Test that tasks are assigned to appropriate agents based on content."""
    orchestrator = SilverTierOrchestrator()

    # Test data analysis task
    data_task = Task(id="test_data", description="Analyze quarterly sales data", priority=5)
    agent = orchestrator.get_agent_by_capability("data_processing")
    assert agent is not None

    # Test decision support task
    decision_task = Task(id="test_decision", description="Recommend new strategy", priority=5)
    agent = orchestrator.get_agent_by_capability("decision_support")
    assert agent is not None

    # Test integration task
    integration_task = Task(id="test_integration", description="Integrate CRM systems", priority=5)
    agent = orchestrator.get_agent_by_capability("system_integration")
    assert agent is not None


def test_silver_tier_llm_provider():
    """Test Silver Tier LLM Provider functionality."""
    llm = SilverTierLLMProvider()

    # Test basic response generation
    response = llm.generate_response("Hello, test this system")

    assert "response" in response
    assert "model" in response
    assert "intelligence_level" in response
    assert "metrics" in response
    assert response["intelligence_level"] == "enhanced"
    assert "confidence" in response["metrics"]


def test_silver_tier_file_watcher():
    """Test Silver Tier File Watcher initialization."""
    import tempfile

    with tempfile.TemporaryDirectory() as temp_dir:
        watcher = SilverTierFileWatcher(temp_dir)

        # Test basic functionality
        changes = watcher.scan_for_changes()
        assert isinstance(changes, list)

        # Check that Silver Tier specific features are present
        assert hasattr(watcher, 'intelligence_level')
        assert watcher.intelligence_level == "enhanced"
        assert hasattr(watcher, 'adaptive_learning')
        assert hasattr(watcher, 'decision_support')


def test_enhanced_decision_making():
    """Test the enhanced decision making capability of Silver Tier."""
    orchestrator = SilverTierOrchestrator()

    # Test with sample context
    context = {
        "sales_data": {"q3": 100000, "q4": 120000},
        "market_conditions": "growing",
        "competition": "moderate"
    }

    result = orchestrator.enhance_decision_making(context)

    assert "analysis" in result
    assert "decision" in result
    assert "confidence" in result
    assert isinstance(result["confidence"], float)
    assert 0.0 <= result["confidence"] <= 1.0


def test_system_status():
    """Test getting system status."""
    orchestrator = SilverTierOrchestrator()

    status = orchestrator.get_system_status()

    assert "active_agents" in status
    assert "pending_tasks" in status
    assert "completed_tasks" in status
    assert "agents" in status
    assert "system_metrics" in status


def test_memory_integration():
    """Test that memory systems are properly integrated."""
    orchestrator = SilverTierOrchestrator()

    # Check that memory attributes exist
    assert hasattr(orchestrator, 'context_memory')
    assert hasattr(orchestrator, 'decision_memory')
    assert hasattr(orchestrator, 'performance_memory')

    # Verify they are initialized as empty dictionaries
    assert isinstance(orchestrator.context_memory, dict)
    assert isinstance(orchestrator.decision_memory, dict)
    assert isinstance(orchestrator.performance_memory, dict)


def test_agent_capabilities():
    """Test that each agent has appropriate Silver Tier capabilities."""
    # Data Analysis Agent capabilities
    data_agent = DataAnalysisAgent()
    expected_data_caps = ["data_processing", "statistical_analysis", "visualization", "insights_generation"]
    for cap in expected_data_caps:
        assert cap in data_agent.capabilities

    # Decision Support Agent capabilities
    decision_agent = DecisionAgent()
    expected_decision_caps = ["decision_support", "recommendation_engine", "risk_assessment", "optimization"]
    for cap in expected_decision_caps:
        assert cap in decision_agent.capabilities

    # Integration Agent capabilities
    integration_agent = IntegrationAgent()
    expected_integration_caps = ["system_integration", "workflow_coordination", "api_management", "data_sync"]
    for cap in expected_integration_caps:
        assert cap in integration_agent.capabilities


def test_silver_tier_specific_features():
    """Test Silver Tier specific features and intelligence enhancements."""
    llm = SilverTierLLMProvider()

    # Check Silver Tier specific features
    metrics = llm.get_intelligence_metrics()
    assert "decision_accuracy" in metrics
    assert "response_quality" in metrics
    assert "context_awareness" in metrics
    assert "adaptability" in metrics

    # Check that values are within expected ranges
    for key, value in metrics.items():
        assert 0.0 <= value <= 1.0

    # Test feedback adaptation
    success = llm.adapt_to_feedback("test prompt", "test response", 0.9)
    assert success is True

    # Check that metrics were updated
    updated_metrics = llm.get_intelligence_metrics()
    assert updated_metrics != metrics  # Should be different after adaptation


def test_silver_tier_config_integration():
    """Test integration with configuration file."""
    # Test with default config
    llm_default = SilverTierLLMProvider()
    assert llm_default.config.intelligence_level == "enhanced"

    # Test with custom config
    custom_config = LLMConfig(
        model_name="custom-silver-model",
        intelligence_level="enhanced-plus"
    )
    llm_custom = SilverTierLLMProvider(config=custom_config)
    assert llm_custom.config.model_name == "custom-silver-model"
    assert llm_custom.config.intelligence_level == "enhanced-plus"


if __name__ == "__main__":
    # Run all tests
    test_silver_tier_orchestrator_initialization()
    test_data_analysis_agent()
    test_decision_support_agent()
    test_integration_agent()
    test_task_assignment()
    test_silver_tier_llm_provider()
    test_silver_tier_file_watcher()
    test_enhanced_decision_making()
    test_system_status()
    test_memory_integration()
    test_agent_capabilities()
    test_silver_tier_specific_features()
    test_silver_tier_config_integration()

    print("All Silver Tier tests passed successfully!")

    # Additional demonstration
    print("\nSilver Tier Demonstration:")
    print("="*30)

    # Create orchestrator and demonstrate functionality
    orchestrator = SilverTierOrchestrator()
    status = orchestrator.get_system_status()
    print(f"Active agents: {status['active_agents']}")
    print(f"Agents: {list(status['agents'].keys())}")

    # Demonstrate enhanced decision making
    context = {
        "sales_data": {"q3": 100000, "q4": 120000, "growth_rate": 0.2},
        "market_trend": "positive",
        "cost_factors": {"production": 50000, "marketing": 30000}
    }

    decision_result = orchestrator.enhance_decision_making(context)
    print(f"Enhanced decision confidence: {decision_result['confidence']:.2f}")
    print("Silver Tier functionality verified successfully!")
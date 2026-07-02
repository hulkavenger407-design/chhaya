"""
Tests for Chhaya Project Planner.
"""

from typing import Any
import pytest

from chhaya.core.planner import ProjectPlanner
from chhaya.interfaces.llm_provider import LLMProvider


class MockLLMProvider(LLMProvider):
    def __init__(self, json_response: str):
        self.json_response = json_response

    def generate(self, prompt: str, model_tier: str, **kwargs: Any) -> str:
        return self.json_response


def test_planner_create_plan_success():
    valid_json = '''
    {
        "project_goal": "Build a website",
        "sub_tasks": [
            {
                "id": 1,
                "description": "Create index.html",
                "required_capabilities": ["file_writer"]
            },
            {
                "id": 2,
                "description": "Create style.css",
                "required_capabilities": ["file_writer"]
            }
        ]
    }
    '''

    llm = MockLLMProvider(json_response=valid_json)
    planner = ProjectPlanner(llm_provider=llm)

    plan = planner.create_plan("Build a website")

    assert plan.project_goal == "Build a website"
    assert len(plan.sub_tasks) == 2
    assert plan.sub_tasks[0].id == 1
    assert "index.html" in plan.sub_tasks[0].description
    assert plan.sub_tasks[1].required_capabilities == ["file_writer"]


def test_planner_create_plan_cleans_markdown():
    markdown_json = '''```json
    {
        "project_goal": "Test goal",
        "sub_tasks": [
            {
                "id": 1,
                "description": "Test task",
                "required_capabilities": []
            }
        ]
    }
    ```'''

    llm = MockLLMProvider(json_response=markdown_json)
    planner = ProjectPlanner(llm_provider=llm)

    plan = planner.create_plan("Test goal")
    assert len(plan.sub_tasks) == 1
    assert plan.sub_tasks[0].description == "Test task"


def test_planner_create_plan_invalid_json():
    bad_json = "I am not JSON."

    llm = MockLLMProvider(json_response=bad_json)
    planner = ProjectPlanner(llm_provider=llm)

    with pytest.raises(ValueError, match="Failed to generate valid project plan"):
        planner.create_plan("Test goal")

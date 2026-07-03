"""
Project Planner for Chhaya.
Uses the Reasoning LLM to decompose large goals into structured sub-tasks.
"""

import json
from typing import Any, Dict, List
from pydantic import BaseModel
import structlog

from chhaya_v1.interfaces.llm_provider import LLMProvider
from chhaya_v1.domain.models import ModelTier

logger = structlog.get_logger(__name__)


class SubTask(BaseModel):
    """A discrete, actionable piece of a larger project."""
    id: int
    description: str
    required_capabilities: List[str]


class ProjectPlan(BaseModel):
    """The full execution plan for a large project."""
    project_goal: str
    sub_tasks: List[SubTask]


class ProjectPlanner:
    """
    Decomposes large goals into an ordered list of tasks.
    """

    def __init__(self, llm_provider: LLMProvider):
        self.llm = llm_provider

    def _build_planning_prompt(self, project_goal: str) -> str:
        """
        Constructs the prompt for the 14b reasoning model to output a valid JSON task list.
        """
        prompt = f"""You are the Chhaya Project Planner. Your job is to break down a massive, complex project into a sequence of small, highly actionable, independent sub-tasks.

Project Goal:
"{project_goal}"

Rules for sub-tasks:
1. They must be strictly ordered. Task 2 assumes Task 1 is complete.
2. They must be discrete and testable.
3. For 'required_capabilities', guess what tools an agent might need (e.g., 'file_writer', 'internet_search', 'ask_jules').

Output ONLY a raw JSON object matching this schema perfectly (do not use markdown blocks like ```json):
{{
    "project_goal": "{project_goal}",
    "sub_tasks": [
        {{
            "id": 1,
            "description": "Initialize the project directory and create the README.",
            "required_capabilities": ["file_writer"]
        }}
    ]
}}
"""
        return prompt

    def create_plan(self, project_goal: str) -> ProjectPlan:
        """
        Designs a project plan using the LLM.

        Args:
            project_goal: The high-level description of what needs to be done.

        Returns:
            A structured ProjectPlan containing the sub-tasks.
        """
        logger.info("Planner starting project breakdown", goal=project_goal)

        prompt = self._build_planning_prompt(project_goal)

        try:
            # Force the reasoning model tier (14b) for planning tasks
            response_text = self.llm.generate(
                prompt=prompt,
                model_tier=ModelTier.REASONING_14B.value,
                format="json"
            )

            # Clean up the response in case the LLM wrapped it in markdown
            if response_text.strip().startswith("```json"):
                response_text = response_text.strip().strip("`").removeprefix("json").strip()

            plan_data: Dict[str, Any] = json.loads(response_text)

            plan = ProjectPlan(**plan_data)
            logger.info("Planner successfully broke down project", task_count=len(plan.sub_tasks))

            return plan

        except json.JSONDecodeError as e:
            logger.error("Planner failed to parse LLM JSON output", error=str(e), response=response_text)
            raise ValueError(f"Failed to generate valid project plan: {e}") from e

        except Exception as e:
            logger.error("Planner encountered an error", error=str(e))
            raise

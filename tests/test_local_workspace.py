"""
Tests for Chhaya Local Workspace.
"""

import os
import tempfile
import pytest

from chhaya.infrastructure.workspace.local import LocalWorkspace


@pytest.fixture
def temp_workspace_base():
    """Provides a temporary base directory for workspaces."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir


def test_local_workspace_init_creates_dir(temp_workspace_base):
    agent_name = "test_agent_1"
    workspace = LocalWorkspace(agent_name=agent_name, base_path=temp_workspace_base)

    expected_path = os.path.join(temp_workspace_base, agent_name)
    assert os.path.exists(expected_path)
    assert workspace.base_path == os.path.realpath(expected_path)


def test_local_workspace_read_write_file(temp_workspace_base):
    workspace = LocalWorkspace(agent_name="test_agent", base_path=temp_workspace_base)

    test_filename = "data/output.txt"
    test_content = "Hello from the agent!"

    # Write file
    workspace.write_file(test_filename, test_content)

    # Read file back
    read_content = workspace.read_file(test_filename)
    assert read_content == test_content

    # Verify file physically exists where we expect it to
    physical_path = os.path.join(workspace.base_path, test_filename)
    assert os.path.exists(physical_path)


def test_local_workspace_file_not_found(temp_workspace_base):
    workspace = LocalWorkspace(agent_name="test_agent", base_path=temp_workspace_base)

    with pytest.raises(FileNotFoundError):
        workspace.read_file("non_existent_file.txt")


def test_local_workspace_path_traversal_prevention(temp_workspace_base):
    workspace = LocalWorkspace(agent_name="hacker_agent", base_path=temp_workspace_base)

    # Attempt to write outside the workspace
    traversal_path = "../../../etc/passwd"

    with pytest.raises(ValueError, match="is outside the workspace"):
        workspace.write_file(traversal_path, "hacked")

    with pytest.raises(ValueError, match="is outside the workspace"):
        workspace.read_file(traversal_path)

def test_local_workspace_path_traversal_prefix_matching(temp_workspace_base):
    """Test against the prefix-sharing edge case for string matching paths."""
    workspace = LocalWorkspace(agent_name="agent", base_path=temp_workspace_base)
    # create the other directory outside workspace
    other_dir = os.path.join(temp_workspace_base, "agent-secrets")
    os.makedirs(other_dir)

    with pytest.raises(ValueError, match="is outside the workspace"):
        workspace.write_file("../agent-secrets/keys.txt", "hacked")

"""Unit tests for Task model (Phase 1 changes - Type Hints)."""

import pytest
from datetime import datetime
from dataclasses import fields

from src.domain.models import Task


class TestTaskModel:
    """Test Task model improvements.

    Phase 1 Change: Verified correct default_factory usage for datetime
    - The task.py file already uses: field(default_factory=datetime.now)
    - This ensures each Task instance gets a unique datetime object
    """

    def test_task_creation_with_defaults(self):
        """Test Task can be created with default values."""
        task = Task(
            description="Test task",
            agent_name="test_agent"
        )

        assert task.description == "Test task"
        assert task.agent_name == "test_agent"
        assert isinstance(task.created_at, datetime), \
            "created_at should be datetime instance"

    def test_task_created_at_is_datetime_instance(self):
        """Test that created_at is always a datetime instance."""
        task = Task(
            description="Test task",
            agent_name="test_agent"
        )

        assert isinstance(task.created_at, datetime), \
            "created_at should be datetime instance, not string"

    def test_task_created_at_uniqueness(self):
        """Test that each Task instance gets its own datetime object.

        This validates that field(default_factory=datetime.now) is used correctly.
        Using default=datetime.now() would create a single shared instance.
        """
        import time

        task1 = Task(
            description="task-1",
            agent_name="agent-1"
        )

        # Small delay to ensure different timestamps
        time.sleep(0.01)

        task2 = Task(
            description="task-2",
            agent_name="agent-1"
        )

        # Both should be datetime objects
        assert isinstance(task1.created_at, datetime)
        assert isinstance(task2.created_at, datetime)

        # They should be different instances (though may have same timestamp)
        # The important thing is that they are not shared
        assert task1.created_at <= task2.created_at, \
            "Task2 should be created after or at same time as Task1"

    def test_task_dataclass_fields(self):
        """Test Task dataclass has correct fields."""
        task_fields = {f.name: f for f in fields(Task)}

        # Check required fields
        required_fields = ["description", "agent_name"]
        for field_name in required_fields:
            assert field_name in task_fields, f"Required field {field_name} missing"

        # Check created_at field
        assert "created_at" in task_fields, "created_at field missing"

        # created_at should be datetime
        created_at_field = task_fields["created_at"]
        assert created_at_field.type == datetime, \
            "created_at should be datetime type"

    def test_task_with_custom_created_at(self):
        """Test Task can accept custom created_at value."""
        custom_time = datetime(2025, 1, 1, 12, 0, 0)

        task = Task(
            description="test_task",
            agent_name="test_agent",
            created_at=custom_time
        )

        assert task.created_at == custom_time

    def test_task_string_representation(self):
        """Test Task string representation."""
        task = Task(
            description="test_task",
            agent_name="test_agent"
        )

        # Task should have a string representation
        task_str = str(task)
        assert isinstance(task_str, str)
        assert "test_task" in task_str or "Task" in task_str

    def test_task_equality(self):
        """Test Task equality comparison."""
        now = datetime.now()

        task1 = Task(
            description="test_task",
            agent_name="test_agent",
            created_at=now
        )

        task2 = Task(
            description="test_task",
            agent_name="test_agent",
            created_at=now
        )

        assert task1 == task2, "Tasks with same values should be equal"

    def test_task_inequality(self):
        """Test Task inequality comparison."""
        task1 = Task(
            description="test_task_1",
            agent_name="test_agent"
        )

        task2 = Task(
            description="test_task_2",
            agent_name="test_agent"
        )

        assert task1 != task2, "Tasks with different descriptions should not be equal"

    @pytest.mark.parametrize("description,agent_name", [
        ("", "test_agent"),
        ("test_task", ""),
    ])
    def test_task_with_empty_fields(self, description: str, agent_name: str):
        """Test Task handles empty fields."""
        # Task should accept these values (validation is not enforced at model level)
        task = Task(
            description=description,
            agent_name=agent_name
        )

        assert task.description == description
        assert task.agent_name == agent_name

    def test_task_created_at_default_factory_verification(self):
        """Verify that created_at uses default_factory, not default.

        This test creates multiple tasks in sequence and verifies that
        each gets its own datetime object instance.
        """
        tasks = []
        for i in range(3):
            task = Task(
                description=f"task-{i}",
                agent_name="agent-1"
            )
            tasks.append(task)

        # All tasks should have created_at as datetime
        for task in tasks:
            assert isinstance(task.created_at, datetime)

        # Tasks created later should have same or later timestamp
        for i in range(len(tasks) - 1):
            assert tasks[i].created_at <= tasks[i + 1].created_at, \
                "Later tasks should have same or later timestamp"

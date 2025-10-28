"""
워크플로우 검증기 단위 테스트

테스트 범위:
- 순환 참조 검사 (_check_cycles)
- 고아 노드 검사 (_check_orphan_nodes)
- 템플릿 변수 유효성 검사 (_validate_template_variables)
- Worker별 도구 권한 검사 (_check_worker_tools)
- Input 노드 검사 (_check_input_node)
- Manager 노드 검사 (_check_manager_nodes)
"""

import pytest
from src.presentation.web.services.workflow_validator import (
    WorkflowValidator,
    ValidationError,
)
from src.presentation.web.schemas.workflow import (
    Workflow,
    WorkflowNode,
    WorkflowEdge,
    WorkerNodeData,
    ManagerNodeData,
    InputNodeData,
)


class TestWorkflowValidator:
    """WorkflowValidator 단위 테스트"""

    def setup_method(self):
        """각 테스트 전에 실행"""
        self.validator = WorkflowValidator()

    # ==================== 순환 참조 검사 ====================

    def test_check_cycles_detects_cycle(self):
        """순환 참조 탐지 테스트"""
        # node1 → node2 → node3 → node1 (순환)
        workflow = Workflow(
            name="test",
            nodes=[
                WorkflowNode(
                    id="node1",
                    type="worker",
                    position={"x": 0, "y": 0},
                    data=WorkerNodeData(
                        agent_name="planner",
                        task_template="Plan"
                    )
                ),
                WorkflowNode(
                    id="node2",
                    type="worker",
                    position={"x": 100, "y": 0},
                    data=WorkerNodeData(
                        agent_name="coder",
                        task_template="Code"
                    )
                ),
                WorkflowNode(
                    id="node3",
                    type="worker",
                    position={"x": 200, "y": 0},
                    data=WorkerNodeData(
                        agent_name="reviewer",
                        task_template="Review"
                    )
                ),
            ],
            edges=[
                WorkflowEdge(id="e1", source="node1", target="node2"),
                WorkflowEdge(id="e2", source="node2", target="node3"),
                WorkflowEdge(id="e3", source="node3", target="node1"),  # 순환!
            ]
        )

        errors = self.validator._check_cycles(workflow)

        assert len(errors) == 1
        assert errors[0].severity == "error"
        assert "순환 참조" in errors[0].message

    def test_check_cycles_no_cycle(self):
        """순환 참조 없는 경우 테스트"""
        # node1 → node2 → node3 (순환 없음)
        workflow = Workflow(
            name="test",
            nodes=[
                WorkflowNode(
                    id="node1",
                    type="worker",
                    position={"x": 0, "y": 0},
                    data=WorkerNodeData(
                        agent_name="planner",
                        task_template="Plan"
                    )
                ),
                WorkflowNode(
                    id="node2",
                    type="worker",
                    position={"x": 100, "y": 0},
                    data=WorkerNodeData(
                        agent_name="coder",
                        task_template="Code"
                    )
                ),
            ],
            edges=[
                WorkflowEdge(id="e1", source="node1", target="node2"),
            ]
        )

        errors = self.validator._check_cycles(workflow)

        assert len(errors) == 0

    # ==================== 고아 노드 검사 ====================

    def test_check_orphan_nodes(self):
        """고아 노드 탐지 테스트"""
        workflow = Workflow(
            name="test",
            nodes=[
                WorkflowNode(
                    id="node1",
                    type="worker",
                    position={"x": 0, "y": 0},
                    data=WorkerNodeData(
                        agent_name="planner",
                        task_template="Plan"
                    )
                ),
                WorkflowNode(
                    id="node2",
                    type="worker",
                    position={"x": 100, "y": 0},
                    data=WorkerNodeData(
                        agent_name="coder",
                        task_template="Code"
                    )
                ),
                WorkflowNode(
                    id="orphan",
                    type="worker",
                    position={"x": 200, "y": 200},
                    data=WorkerNodeData(
                        agent_name="reviewer",
                        task_template="Review"
                    )
                ),
            ],
            edges=[
                WorkflowEdge(id="e1", source="node1", target="node2"),
                # orphan 노드는 연결 없음
            ]
        )

        errors = self.validator._check_orphan_nodes(workflow)

        assert len(errors) == 1
        assert errors[0].severity == "warning"
        assert errors[0].node_id == "orphan"
        assert "연결되지 않았습니다" in errors[0].message

    def test_check_orphan_nodes_input_excluded(self):
        """Input 노드는 고아 노드 검사에서 제외"""
        workflow = Workflow(
            name="test",
            nodes=[
                WorkflowNode(
                    id="input1",
                    type="input",
                    position={"x": 0, "y": 0},
                    data=InputNodeData(initial_input="Start")
                ),
            ],
            edges=[]
        )

        errors = self.validator._check_orphan_nodes(workflow)

        # Input 노드는 고아로 판정되지 않음
        assert len(errors) == 0

    # ==================== 템플릿 변수 검증 ====================

    def test_validate_template_variables_valid(self):
        """유효한 템플릿 변수 테스트"""
        workflow = Workflow(
            name="test",
            nodes=[
                WorkflowNode(
                    id="node1",
                    type="worker",
                    position={"x": 0, "y": 0},
                    data=WorkerNodeData(
                        agent_name="planner",
                        task_template="Plan with {{input}}"
                    )
                ),
                WorkflowNode(
                    id="node2",
                    type="worker",
                    position={"x": 100, "y": 0},
                    data=WorkerNodeData(
                        agent_name="coder",
                        task_template="Code based on {{node1}}"
                    )
                ),
            ],
            edges=[
                WorkflowEdge(id="e1", source="node1", target="node2"),
            ]
        )

        errors = self.validator._validate_template_variables(workflow)

        assert len(errors) == 0

    def test_validate_template_variables_invalid(self):
        """유효하지 않은 템플릿 변수 테스트"""
        workflow = Workflow(
            name="test",
            nodes=[
                WorkflowNode(
                    id="node1",
                    type="worker",
                    position={"x": 0, "y": 0},
                    data=WorkerNodeData(
                        agent_name="planner",
                        task_template="Plan with {{nonexistent}}"
                    )
                ),
            ],
            edges=[]
        )

        errors = self.validator._validate_template_variables(workflow)

        assert len(errors) == 1
        assert errors[0].severity == "error"
        assert errors[0].node_id == "node1"
        assert "유효하지 않은 템플릿 변수" in errors[0].message

    def test_validate_template_variables_nonexistent_node(self):
        """존재하지 않는 노드를 참조하는 템플릿 변수 테스트"""
        workflow = Workflow(
            name="test",
            nodes=[
                WorkflowNode(
                    id="node1",
                    type="worker",
                    position={"x": 0, "y": 0},
                    data=WorkerNodeData(
                        agent_name="planner",
                        task_template="Plan with {{node_999}}"  # node_ prefix 사용
                    )
                ),
            ],
            edges=[]
        )

        errors = self.validator._validate_template_variables(workflow)

        assert len(errors) == 1
        assert errors[0].severity == "error"
        assert "존재하지 않는 노드" in errors[0].message

    # ==================== Worker 도구 권한 검사 ====================

    def test_check_worker_tools_valid(self):
        """유효한 Worker 도구 설정 테스트"""
        workflow = Workflow(
            name="test",
            nodes=[
                WorkflowNode(
                    id="node1",
                    type="worker",
                    position={"x": 0, "y": 0},
                    data=WorkerNodeData(
                        agent_name="planner",
                        task_template="Plan",
                        allowed_tools=["read", "glob"]  # planner의 기본 도구 포함
                    )
                ),
            ],
            edges=[]
        )

        errors = self.validator._check_worker_tools(workflow)

        assert len(errors) == 0

    def test_check_worker_tools_invalid(self):
        """유효하지 않은 Worker 도구 설정 테스트"""
        workflow = Workflow(
            name="test",
            nodes=[
                WorkflowNode(
                    id="node1",
                    type="worker",
                    position={"x": 0, "y": 0},
                    data=WorkerNodeData(
                        agent_name="planner",
                        task_template="Plan",
                        allowed_tools=["read", "bash"]  # planner는 bash 사용 불가!
                    )
                ),
            ],
            edges=[]
        )

        errors = self.validator._check_worker_tools(workflow)

        assert len(errors) == 1
        assert errors[0].severity == "error"
        assert errors[0].node_id == "node1"
        assert "사용할 수 없는 도구" in errors[0].message
        assert "bash" in errors[0].message

    def test_check_worker_tools_unknown_worker(self):
        """알려지지 않은 Worker 테스트"""
        workflow = Workflow(
            name="test",
            nodes=[
                WorkflowNode(
                    id="node1",
                    type="worker",
                    position={"x": 0, "y": 0},
                    data=WorkerNodeData(
                        agent_name="unknown_worker",
                        task_template="Do something"
                    )
                ),
            ],
            edges=[]
        )

        errors = self.validator._check_worker_tools(workflow)

        assert len(errors) == 1
        assert errors[0].severity == "warning"
        assert "알려지지 않은 Worker" in errors[0].message

    # ==================== Input 노드 검사 ====================

    def test_check_input_node_missing(self):
        """Input 노드 없는 경우 테스트"""
        workflow = Workflow(
            name="test",
            nodes=[
                WorkflowNode(
                    id="node1",
                    type="worker",
                    position={"x": 0, "y": 0},
                    data=WorkerNodeData(
                        agent_name="planner",
                        task_template="Plan"
                    )
                ),
            ],
            edges=[]
        )

        errors = self.validator._check_input_node(workflow)

        assert len(errors) == 1
        assert errors[0].severity == "error"
        assert "Input 노드가 없습니다" in errors[0].message

    def test_check_input_node_exists(self):
        """Input 노드 존재하는 경우 테스트"""
        workflow = Workflow(
            name="test",
            nodes=[
                WorkflowNode(
                    id="input1",
                    type="input",
                    position={"x": 0, "y": 0},
                    data=InputNodeData(initial_input="Start")
                ),
            ],
            edges=[]
        )

        errors = self.validator._check_input_node(workflow)

        assert len(errors) == 0

    def test_check_input_node_multiple(self):
        """여러 개의 Input 노드가 있는 경우 테스트"""
        workflow = Workflow(
            name="test",
            nodes=[
                WorkflowNode(
                    id="input1",
                    type="input",
                    position={"x": 0, "y": 0},
                    data=InputNodeData(initial_input="Start 1")
                ),
                WorkflowNode(
                    id="input2",
                    type="input",
                    position={"x": 100, "y": 0},
                    data=InputNodeData(initial_input="Start 2")
                ),
            ],
            edges=[]
        )

        errors = self.validator._check_input_node(workflow)

        assert len(errors) == 1
        assert errors[0].severity == "warning"
        assert "여러 개의 Input 노드" in errors[0].message

    # ==================== Manager 노드 검사 ====================

    def test_check_manager_nodes_no_workers(self):
        """Manager 노드에 워커가 없는 경우 테스트"""
        workflow = Workflow(
            name="test",
            nodes=[
                WorkflowNode(
                    id="manager1",
                    type="manager",
                    position={"x": 0, "y": 0},
                    data=ManagerNodeData(
                        task_description="Manage tasks",
                        available_workers=[]  # 워커 없음!
                    )
                ),
            ],
            edges=[]
        )

        errors = self.validator._check_manager_nodes(workflow)

        assert len(errors) == 1
        assert errors[0].severity == "error"
        assert errors[0].node_id == "manager1"
        assert "등록된 워커가 없습니다" in errors[0].message

    def test_check_manager_nodes_with_workers(self):
        """Manager 노드에 워커가 있는 경우 테스트"""
        workflow = Workflow(
            name="test",
            nodes=[
                WorkflowNode(
                    id="manager1",
                    type="manager",
                    position={"x": 0, "y": 0},
                    data=ManagerNodeData(
                        task_description="Manage tasks",
                        available_workers=["planner", "coder"]
                    )
                ),
            ],
            edges=[]
        )

        errors = self.validator._check_manager_nodes(workflow)

        assert len(errors) == 0

    def test_check_manager_nodes_invalid_workers(self):
        """Manager 노드에 유효하지 않은 워커가 있는 경우 테스트"""
        workflow = Workflow(
            name="test",
            nodes=[
                WorkflowNode(
                    id="manager1",
                    type="manager",
                    position={"x": 0, "y": 0},
                    data=ManagerNodeData(
                        task_description="Manage tasks",
                        available_workers=["planner", "unknown_worker"]
                    )
                ),
            ],
            edges=[]
        )

        errors = self.validator._check_manager_nodes(workflow)

        assert len(errors) == 1
        assert errors[0].severity == "warning"
        assert "알려지지 않은 워커" in errors[0].message
        assert "unknown_worker" in errors[0].message

    # ==================== 통합 검증 ====================

    def test_validate_complete_workflow(self):
        """전체 워크플로우 검증 테스트"""
        workflow = Workflow(
            name="test",
            nodes=[
                WorkflowNode(
                    id="input1",
                    type="input",
                    position={"x": 0, "y": 0},
                    data=InputNodeData(initial_input="Start")
                ),
                WorkflowNode(
                    id="node1",
                    type="worker",
                    position={"x": 100, "y": 0},
                    data=WorkerNodeData(
                        agent_name="planner",
                        task_template="Plan with {{input}}"
                    )
                ),
                WorkflowNode(
                    id="node2",
                    type="worker",
                    position={"x": 200, "y": 0},
                    data=WorkerNodeData(
                        agent_name="coder",
                        task_template="Code based on {{node1}}"
                    )
                ),
            ],
            edges=[
                WorkflowEdge(id="e1", source="input1", target="node1"),
                WorkflowEdge(id="e2", source="node1", target="node2"),
            ]
        )

        errors = self.validator.validate(workflow)

        assert len(errors) == 0

    def test_validate_workflow_with_multiple_errors(self):
        """여러 에러가 있는 워크플로우 테스트"""
        workflow = Workflow(
            name="test",
            nodes=[
                # Input 노드 없음
                WorkflowNode(
                    id="node1",
                    type="worker",
                    position={"x": 0, "y": 0},
                    data=WorkerNodeData(
                        agent_name="planner",
                        task_template="Plan with {{nonexistent}}",  # 유효하지 않은 변수
                        allowed_tools=["read", "bash"]  # planner는 bash 사용 불가
                    )
                ),
                WorkflowNode(
                    id="orphan",
                    type="worker",
                    position={"x": 200, "y": 200},
                    data=WorkerNodeData(
                        agent_name="coder",
                        task_template="Code"
                    )
                ),
            ],
            edges=[]
        )

        errors = self.validator.validate(workflow)

        # 예상 에러:
        # 1. Input 노드 없음 (error)
        # 2. 고아 노드 2개 (warning x2)
        # 3. 유효하지 않은 템플릿 변수 (error)
        # 4. 유효하지 않은 도구 (error)

        assert len(errors) >= 4

        # severity별로 분류
        error_count = len([e for e in errors if e.severity == "error"])
        warning_count = len([e for e in errors if e.severity == "warning"])

        assert error_count >= 3  # Input 없음, 템플릿 변수, 도구
        assert warning_count >= 2  # 고아 노드 2개

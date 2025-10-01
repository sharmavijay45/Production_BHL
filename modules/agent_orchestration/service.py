"""
BHIV Core Agent Orchestration Microservice
==========================================

Coordinates AI agents and workflows for intelligent automation:
- Agent lifecycle management
- Workflow orchestration
- Task routing and scheduling
- Agent communication
- Performance monitoring
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from fastapi import HTTPException, Depends, Query, BackgroundTasks
from pydantic import BaseModel, Field
from enum import Enum
import json
import uuid
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from modules.shared.base_service import BaseService
from security.auth import get_current_user
from security.rbac import require_permission, Permission
from security.audit import audit_log

logger = logging.getLogger(__name__)

# Enums
class AgentStatus(str, Enum):
    IDLE = "idle"
    BUSY = "busy"
    OFFLINE = "offline"
    ERROR = "error"

class TaskStatus(str, Enum):
    PENDING = "pending"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class TaskPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class WorkflowStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"

# Pydantic Models
class Agent(BaseModel):
    """AI Agent model"""
    id: Optional[str] = None
    name: str = Field(..., description="Agent name")
    type: str = Field(..., description="Agent type (llm, analytics, etc.)")
    description: Optional[str] = None
    capabilities: List[str] = Field(default_factory=list, description="Agent capabilities")
    status: AgentStatus = Field(default=AgentStatus.OFFLINE)
    endpoint: Optional[str] = None
    config: Dict[str, Any] = Field(default_factory=dict)
    performance_metrics: Dict[str, float] = Field(default_factory=dict)
    created_at: Optional[datetime] = None
    last_active: Optional[datetime] = None

class Task(BaseModel):
    """Task model"""
    id: Optional[str] = None
    workflow_id: Optional[str] = None
    agent_id: Optional[str] = None
    task_type: str = Field(..., description="Type of task")
    priority: TaskPriority = Field(default=TaskPriority.MEDIUM)
    status: TaskStatus = Field(default=TaskStatus.PENDING)
    input_data: Dict[str, Any] = Field(..., description="Task input data")
    output_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    retry_count: int = Field(default=0)
    max_retries: int = Field(default=3)
    timeout_seconds: int = Field(default=300)
    created_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

class Workflow(BaseModel):
    """Workflow model"""
    id: Optional[str] = None
    name: str = Field(..., description="Workflow name")
    description: Optional[str] = None
    status: WorkflowStatus = Field(default=WorkflowStatus.DRAFT)
    steps: List[Dict[str, Any]] = Field(..., description="Workflow steps")
    trigger_conditions: Dict[str, Any] = Field(default_factory=dict)
    created_by: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class WorkflowExecution(BaseModel):
    """Workflow execution instance"""
    id: Optional[str] = None
    workflow_id: str = Field(..., description="Workflow ID")
    status: WorkflowStatus = Field(default=WorkflowStatus.ACTIVE)
    current_step: int = Field(default=0)
    input_data: Dict[str, Any] = Field(default_factory=dict)
    output_data: Optional[Dict[str, Any]] = None
    step_results: List[Dict[str, Any]] = Field(default_factory=list)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

class AgentOrchestrationService(BaseService):
    """Agent Orchestration microservice"""
    
    def __init__(self):
        super().__init__(
            service_name="AgentOrchestration",
            service_version="1.0.0",
            port=8003
        )
        
        # In-memory storage (replace with database in production)
        self.agents: Dict[str, Agent] = {}
        self.tasks: Dict[str, Task] = {}
        self.workflows: Dict[str, Workflow] = {}
        self.executions: Dict[str, WorkflowExecution] = {}
        
        # Task queue and processing
        self.task_queue: asyncio.Queue = asyncio.Queue()
        self.processing_tasks = set()
        
        self._setup_routes()
        self._initialize_sample_data()
    
    def _get_service_capabilities(self) -> List[str]:
        """Get agent orchestration service capabilities"""
        return super()._get_service_capabilities() + [
            "agent_management",
            "task_orchestration",
            "workflow_execution",
            "agent_communication",
            "performance_monitoring",
            "intelligent_routing"
        ]
    
    def _get_service_dependencies(self) -> List[str]:
        """Get service dependencies"""
        return ["llm_query_service", "integrations_service"]
    
    def _setup_routes(self):
        """Setup agent orchestration routes"""
        
        # Agent Management Routes
        @self.app.get("/agents", tags=["agents"])
        async def list_agents(
            status: Optional[AgentStatus] = Query(None, description="Filter by status"),
            agent_type: Optional[str] = Query(None, description="Filter by type"),
            current_user: dict = Depends(get_current_user)
        ):
            """List registered agents"""
            if not require_permission(current_user, Permission.AGENT_READ):
                raise HTTPException(status_code=403, detail="Agent read permission required")
            
            agents = list(self.agents.values())
            
            if status:
                agents = [a for a in agents if a.status == status]
            
            if agent_type:
                agents = [a for a in agents if a.type.lower() == agent_type.lower()]
            
            return {
                "agents": agents,
                "total_count": len(agents),
                "active_count": len([a for a in self.agents.values() if a.status != AgentStatus.OFFLINE])
            }
        
        @self.app.post("/agents", tags=["agents"])
        async def register_agent(
            agent: Agent,
            current_user: dict = Depends(get_current_user)
        ):
            """Register new agent"""
            if not require_permission(current_user, Permission.AGENT_WRITE):
                raise HTTPException(status_code=403, detail="Agent write permission required")
            
            agent.id = f"agent_{len(self.agents) + 1:06d}"
            agent.created_at = datetime.now()
            agent.last_active = datetime.now()
            
            self.agents[agent.id] = agent
            
            await audit_log(
                action="agent_register",
                resource="agents",
                user_id=current_user.get("user_id"),
                details={"agent_id": agent.id, "agent_type": agent.type}
            )
            
            return {"success": True, "agent": agent}
        
        @self.app.put("/agents/{agent_id}/status", tags=["agents"])
        async def update_agent_status(
            agent_id: str,
            status: AgentStatus,
            current_user: dict = Depends(get_current_user)
        ):
            """Update agent status"""
            if not require_permission(current_user, Permission.AGENT_WRITE):
                raise HTTPException(status_code=403, detail="Agent write permission required")
            
            if agent_id not in self.agents:
                raise HTTPException(status_code=404, detail="Agent not found")
            
            old_status = self.agents[agent_id].status
            self.agents[agent_id].status = status
            self.agents[agent_id].last_active = datetime.now()
            
            await audit_log(
                action="agent_status_update",
                resource="agents",
                user_id=current_user.get("user_id"),
                details={"agent_id": agent_id, "old_status": old_status, "new_status": status}
            )
            
            return {"success": True, "agent": self.agents[agent_id]}
        
        # Task Management Routes
        @self.app.get("/tasks", tags=["tasks"])
        async def list_tasks(
            status: Optional[TaskStatus] = Query(None, description="Filter by status"),
            agent_id: Optional[str] = Query(None, description="Filter by agent"),
            priority: Optional[TaskPriority] = Query(None, description="Filter by priority"),
            current_user: dict = Depends(get_current_user)
        ):
            """List tasks"""
            if not require_permission(current_user, Permission.AGENT_READ):
                raise HTTPException(status_code=403, detail="Agent read permission required")
            
            tasks = list(self.tasks.values())
            
            if status:
                tasks = [t for t in tasks if t.status == status]
            
            if agent_id:
                tasks = [t for t in tasks if t.agent_id == agent_id]
            
            if priority:
                tasks = [t for t in tasks if t.priority == priority]
            
            return {
                "tasks": tasks,
                "total_count": len(tasks),
                "pending_count": len([t for t in self.tasks.values() if t.status == TaskStatus.PENDING]),
                "in_progress_count": len([t for t in self.tasks.values() if t.status == TaskStatus.IN_PROGRESS])
            }
        
        @self.app.post("/tasks", tags=["tasks"])
        async def create_task(
            task: Task,
            background_tasks: BackgroundTasks,
            current_user: dict = Depends(get_current_user)
        ):
            """Create and queue new task"""
            if not require_permission(current_user, Permission.AGENT_WRITE):
                raise HTTPException(status_code=403, detail="Agent write permission required")
            
            task.id = f"task_{len(self.tasks) + 1:06d}"
            task.created_at = datetime.now()
            
            self.tasks[task.id] = task
            
            # Add to processing queue
            background_tasks.add_task(self._queue_task, task.id)
            
            await audit_log(
                action="task_create",
                resource="tasks",
                user_id=current_user.get("user_id"),
                details={"task_id": task.id, "task_type": task.task_type, "priority": task.priority}
            )
            
            return {"success": True, "task": task}
        
        @self.app.get("/tasks/{task_id}", tags=["tasks"])
        async def get_task(
            task_id: str,
            current_user: dict = Depends(get_current_user)
        ):
            """Get specific task"""
            if not require_permission(current_user, Permission.AGENT_READ):
                raise HTTPException(status_code=403, detail="Agent read permission required")
            
            if task_id not in self.tasks:
                raise HTTPException(status_code=404, detail="Task not found")
            
            task = self.tasks[task_id]
            
            # Get assigned agent info if available
            agent_info = None
            if task.agent_id and task.agent_id in self.agents:
                agent_info = self.agents[task.agent_id]
            
            return {
                "task": task,
                "assigned_agent": agent_info,
                "execution_time": self._calculate_execution_time(task)
            }
        
        # Workflow Management Routes
        @self.app.get("/workflows", tags=["workflows"])
        async def list_workflows(
            status: Optional[WorkflowStatus] = Query(None, description="Filter by status"),
            current_user: dict = Depends(get_current_user)
        ):
            """List workflows"""
            if not require_permission(current_user, Permission.AGENT_READ):
                raise HTTPException(status_code=403, detail="Agent read permission required")
            
            workflows = list(self.workflows.values())
            
            if status:
                workflows = [w for w in workflows if w.status == status]
            
            return {
                "workflows": workflows,
                "total_count": len(workflows),
                "active_count": len([w for w in self.workflows.values() if w.status == WorkflowStatus.ACTIVE])
            }
        
        @self.app.post("/workflows", tags=["workflows"])
        async def create_workflow(
            workflow: Workflow,
            current_user: dict = Depends(get_current_user)
        ):
            """Create new workflow"""
            if not require_permission(current_user, Permission.AGENT_WRITE):
                raise HTTPException(status_code=403, detail="Agent write permission required")
            
            workflow.id = f"wf_{len(self.workflows) + 1:06d}"
            workflow.created_by = current_user.get("user_id")
            workflow.created_at = datetime.now()
            workflow.updated_at = datetime.now()
            
            self.workflows[workflow.id] = workflow
            
            await audit_log(
                action="workflow_create",
                resource="workflows",
                user_id=current_user.get("user_id"),
                details={"workflow_id": workflow.id, "name": workflow.name}
            )
            
            return {"success": True, "workflow": workflow}
        
        @self.app.post("/workflows/{workflow_id}/execute", tags=["workflows"])
        async def execute_workflow(
            workflow_id: str,
            input_data: Dict[str, Any],
            background_tasks: BackgroundTasks,
            current_user: dict = Depends(get_current_user)
        ):
            """Execute workflow"""
            if not require_permission(current_user, Permission.AGENT_WRITE):
                raise HTTPException(status_code=403, detail="Agent write permission required")
            
            if workflow_id not in self.workflows:
                raise HTTPException(status_code=404, detail="Workflow not found")
            
            workflow = self.workflows[workflow_id]
            
            if workflow.status != WorkflowStatus.ACTIVE:
                raise HTTPException(status_code=400, detail="Workflow is not active")
            
            # Create execution instance
            execution = WorkflowExecution(
                id=f"exec_{len(self.executions) + 1:06d}",
                workflow_id=workflow_id,
                input_data=input_data,
                started_at=datetime.now()
            )
            
            self.executions[execution.id] = execution
            
            # Start workflow execution in background
            background_tasks.add_task(self._execute_workflow, execution.id)
            
            await audit_log(
                action="workflow_execute",
                resource="workflows",
                user_id=current_user.get("user_id"),
                details={"workflow_id": workflow_id, "execution_id": execution.id}
            )
            
            return {"success": True, "execution": execution}
        
        # Analytics and Monitoring Routes
        @self.app.get("/analytics/dashboard", tags=["analytics"])
        async def orchestration_dashboard(
            current_user: dict = Depends(get_current_user)
        ):
            """Get orchestration analytics dashboard"""
            if not require_permission(current_user, Permission.AGENT_READ):
                raise HTTPException(status_code=403, detail="Agent read permission required")
            
            # Agent metrics
            total_agents = len(self.agents)
            active_agents = len([a for a in self.agents.values() if a.status != AgentStatus.OFFLINE])
            
            # Task metrics
            total_tasks = len(self.tasks)
            pending_tasks = len([t for t in self.tasks.values() if t.status == TaskStatus.PENDING])
            completed_tasks = len([t for t in self.tasks.values() if t.status == TaskStatus.COMPLETED])
            failed_tasks = len([t for t in self.tasks.values() if t.status == TaskStatus.FAILED])
            
            # Workflow metrics
            total_workflows = len(self.workflows)
            active_workflows = len([w for w in self.workflows.values() if w.status == WorkflowStatus.ACTIVE])
            
            # Performance metrics
            avg_task_time = self._calculate_average_task_time()
            success_rate = (completed_tasks / max(total_tasks, 1)) * 100
            
            return {
                "agents": {
                    "total": total_agents,
                    "active": active_agents,
                    "offline": total_agents - active_agents
                },
                "tasks": {
                    "total": total_tasks,
                    "pending": pending_tasks,
                    "completed": completed_tasks,
                    "failed": failed_tasks,
                    "success_rate": success_rate
                },
                "workflows": {
                    "total": total_workflows,
                    "active": active_workflows
                },
                "performance": {
                    "avg_task_time_seconds": avg_task_time,
                    "tasks_per_hour": self._calculate_tasks_per_hour(),
                    "agent_utilization": (active_agents / max(total_agents, 1)) * 100
                }
            }
        
        @self.app.get("/agents/{agent_id}/performance", tags=["analytics"])
        async def agent_performance(
            agent_id: str,
            current_user: dict = Depends(get_current_user)
        ):
            """Get agent performance metrics"""
            if not require_permission(current_user, Permission.AGENT_READ):
                raise HTTPException(status_code=403, detail="Agent read permission required")
            
            if agent_id not in self.agents:
                raise HTTPException(status_code=404, detail="Agent not found")
            
            agent = self.agents[agent_id]
            agent_tasks = [t for t in self.tasks.values() if t.agent_id == agent_id]
            
            completed_tasks = [t for t in agent_tasks if t.status == TaskStatus.COMPLETED]
            failed_tasks = [t for t in agent_tasks if t.status == TaskStatus.FAILED]
            
            avg_execution_time = 0
            if completed_tasks:
                execution_times = [
                    (t.completed_at - t.started_at).total_seconds()
                    for t in completed_tasks
                    if t.started_at and t.completed_at
                ]
                if execution_times:
                    avg_execution_time = sum(execution_times) / len(execution_times)
            
            return {
                "agent": agent,
                "performance": {
                    "total_tasks": len(agent_tasks),
                    "completed_tasks": len(completed_tasks),
                    "failed_tasks": len(failed_tasks),
                    "success_rate": (len(completed_tasks) / max(len(agent_tasks), 1)) * 100,
                    "avg_execution_time_seconds": avg_execution_time,
                    "uptime_percentage": self._calculate_agent_uptime(agent_id)
                }
            }
    
    async def _queue_task(self, task_id: str):
        """Add task to processing queue"""
        await self.task_queue.put(task_id)
        asyncio.create_task(self._process_task_queue())
    
    async def _process_task_queue(self):
        """Process tasks from queue"""
        while not self.task_queue.empty():
            try:
                task_id = await asyncio.wait_for(self.task_queue.get(), timeout=1.0)
                
                if task_id not in self.processing_tasks:
                    self.processing_tasks.add(task_id)
                    asyncio.create_task(self._execute_task(task_id))
                    
            except asyncio.TimeoutError:
                break
    
    async def _execute_task(self, task_id: str):
        """Execute individual task"""
        try:
            if task_id not in self.tasks:
                return
            
            task = self.tasks[task_id]
            
            # Find suitable agent
            suitable_agent = self._find_suitable_agent(task)
            
            if not suitable_agent:
                task.status = TaskStatus.FAILED
                task.error_message = "No suitable agent available"
                return
            
            # Assign task to agent
            task.agent_id = suitable_agent.id
            task.status = TaskStatus.ASSIGNED
            task.started_at = datetime.now()
            
            # Update agent status
            suitable_agent.status = AgentStatus.BUSY
            suitable_agent.last_active = datetime.now()
            
            # Simulate task execution
            await asyncio.sleep(2)  # Simulate processing time
            
            # Mock task completion
            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.now()
            task.output_data = {
                "result": f"Task {task.task_type} completed successfully",
                "processed_by": suitable_agent.name,
                "execution_time": (task.completed_at - task.started_at).total_seconds()
            }
            
            # Update agent status back to idle
            suitable_agent.status = AgentStatus.IDLE
            
            logger.info(f"✅ Task {task_id} completed by agent {suitable_agent.id}")
            
        except Exception as e:
            if task_id in self.tasks:
                task = self.tasks[task_id]
                task.status = TaskStatus.FAILED
                task.error_message = str(e)
                task.retry_count += 1
                
                # Retry if under limit
                if task.retry_count < task.max_retries:
                    await asyncio.sleep(5)  # Wait before retry
                    await self._queue_task(task_id)
            
            logger.error(f"❌ Task {task_id} failed: {e}")
        
        finally:
            if task_id in self.processing_tasks:
                self.processing_tasks.remove(task_id)
    
    def _find_suitable_agent(self, task: Task) -> Optional[Agent]:
        """Find suitable agent for task"""
        available_agents = [
            agent for agent in self.agents.values()
            if agent.status == AgentStatus.IDLE
        ]
        
        # Simple matching based on task type and agent capabilities
        for agent in available_agents:
            if task.task_type in agent.capabilities or "general" in agent.capabilities:
                return agent
        
        return available_agents[0] if available_agents else None
    
    async def _execute_workflow(self, execution_id: str):
        """Execute workflow steps"""
        try:
            if execution_id not in self.executions:
                return
            
            execution = self.executions[execution_id]
            workflow = self.workflows[execution.workflow_id]
            
            for i, step in enumerate(workflow.steps):
                execution.current_step = i
                
                # Create task for workflow step
                step_task = Task(
                    workflow_id=execution.workflow_id,
                    task_type=step.get("type", "general"),
                    priority=TaskPriority.MEDIUM,
                    input_data=step.get("input", {}),
                    timeout_seconds=step.get("timeout", 300)
                )
                
                step_task.id = f"wf_task_{execution_id}_{i}"
                step_task.created_at = datetime.now()
                
                self.tasks[step_task.id] = step_task
                
                # Execute step task
                await self._execute_task(step_task.id)
                
                # Wait for completion
                while step_task.status in [TaskStatus.PENDING, TaskStatus.ASSIGNED, TaskStatus.IN_PROGRESS]:
                    await asyncio.sleep(1)
                
                if step_task.status == TaskStatus.FAILED:
                    execution.status = WorkflowStatus.FAILED
                    return
                
                # Store step result
                execution.step_results.append({
                    "step": i,
                    "task_id": step_task.id,
                    "output": step_task.output_data
                })
            
            execution.status = WorkflowStatus.COMPLETED
            execution.completed_at = datetime.now()
            execution.output_data = {"step_results": execution.step_results}
            
            logger.info(f"✅ Workflow execution {execution_id} completed")
            
        except Exception as e:
            if execution_id in self.executions:
                self.executions[execution_id].status = WorkflowStatus.FAILED
            logger.error(f"❌ Workflow execution {execution_id} failed: {e}")
    
    def _calculate_execution_time(self, task: Task) -> Optional[float]:
        """Calculate task execution time"""
        if task.started_at and task.completed_at:
            return (task.completed_at - task.started_at).total_seconds()
        return None
    
    def _calculate_average_task_time(self) -> float:
        """Calculate average task execution time"""
        completed_tasks = [t for t in self.tasks.values() if t.status == TaskStatus.COMPLETED]
        
        if not completed_tasks:
            return 0.0
        
        execution_times = [
            self._calculate_execution_time(t)
            for t in completed_tasks
            if self._calculate_execution_time(t) is not None
        ]
        
        return sum(execution_times) / len(execution_times) if execution_times else 0.0
    
    def _calculate_tasks_per_hour(self) -> float:
        """Calculate tasks completed per hour"""
        completed_tasks = [
            t for t in self.tasks.values()
            if t.status == TaskStatus.COMPLETED and t.completed_at
        ]
        
        if not completed_tasks:
            return 0.0
        
        # Count tasks completed in last hour
        one_hour_ago = datetime.now() - timedelta(hours=1)
        recent_tasks = [t for t in completed_tasks if t.completed_at > one_hour_ago]
        
        return len(recent_tasks)
    
    def _calculate_agent_uptime(self, agent_id: str) -> float:
        """Calculate agent uptime percentage"""
        if agent_id not in self.agents:
            return 0.0
        
        agent = self.agents[agent_id]
        
        # Simple uptime calculation based on status
        if agent.status == AgentStatus.OFFLINE:
            return 0.0
        elif agent.status == AgentStatus.ERROR:
            return 25.0
        elif agent.status == AgentStatus.IDLE:
            return 90.0
        else:  # BUSY
            return 100.0
    
    def _initialize_sample_data(self):
        """Initialize with sample data"""
        # Sample agents
        sample_agents = [
            Agent(
                id="agent_000001",
                name="LLM Assistant",
                type="llm",
                description="General purpose language model agent",
                capabilities=["text_generation", "analysis", "general"],
                status=AgentStatus.IDLE,
                endpoint="http://localhost:8004/llm/process",
                config={"model": "gpt-3.5-turbo", "max_tokens": 1000},
                created_at=datetime.now()
            ),
            Agent(
                id="agent_000002",
                name="Data Analyzer",
                type="analytics",
                description="Data analysis and reporting agent",
                capabilities=["data_analysis", "reporting", "visualization"],
                status=AgentStatus.IDLE,
                config={"analysis_type": "statistical"},
                created_at=datetime.now()
            )
        ]
        
        for agent in sample_agents:
            self.agents[agent.id] = agent
        
        # Sample workflow
        sample_workflow = Workflow(
            id="wf_000001",
            name="Customer Onboarding",
            description="Automated customer onboarding workflow",
            status=WorkflowStatus.ACTIVE,
            steps=[
                {
                    "type": "data_validation",
                    "input": {"validate": "customer_data"},
                    "timeout": 60
                },
                {
                    "type": "account_creation", 
                    "input": {"create": "customer_account"},
                    "timeout": 120
                },
                {
                    "type": "welcome_email",
                    "input": {"send": "welcome_message"},
                    "timeout": 30
                }
            ],
            created_at=datetime.now()
        )
        
        self.workflows[sample_workflow.id] = sample_workflow
        
        logger.info("✅ Agent Orchestration service initialized with sample data")

# Create service instance
agent_orchestration_service = AgentOrchestrationService()

if __name__ == "__main__":
    agent_orchestration_service.run(debug=True)

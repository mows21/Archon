from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from archon.archon_graph import agentic_flow
from archon.archon_graph_enhanced import (
    run_knowledge_workflow,
    run_simple_knowledge_workflow,
    run_task_execution_workflow,
    run_project_planning_workflow
)
from archon.integrated_workflow import run_integrated_workflow
from langgraph.types import Command
from utils.utils import write_to_log

app = FastAPI()

class InvokeRequest(BaseModel):
    message: str
    thread_id: str
    is_first_message: bool = False
    config: Optional[Dict[str, Any]] = None

class KnowledgeWorkflowRequest(BaseModel):
    project_description: str
    project_name: str = "New Project"
    min_coverage: float = 0.4
    thread_id: str = "default"

class SimpleKnowledgeRequest(BaseModel):
    task_id: str
    thread_id: str = "default"

class TaskExecutionRequest(BaseModel):
    task_id: str
    min_coverage: float = 0.4
    thread_id: str = "default"

class ProjectPlanningRequest(BaseModel):
    project_id: str
    min_coverage: float = 0.4
    thread_id: str = "default"

class CheckCoverageRequest(BaseModel):
    tags: List[str]
    frameworks: List[str]
    min_coverage: float = 0.4

class LinkTaskRequest(BaseModel):
    task_id: str
    refresh: bool = False

class IntegratedWorkflowRequest(BaseModel):
    user_message: str
    workflow_type: str = "conditional"  # sequential | parallel | conditional
    thread_id: str = "default"

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "ok"}    

@app.post("/invoke")
async def invoke_agent(request: InvokeRequest):
    """Process a message through the agentic flow and return the complete response.

    The agent streams the response but this API endpoint waits for the full output
    before returning so it's a synchronous operation for MCP.
    Another endpoint will be made later to fully stream the response from the API.
    
    Args:
        request: The InvokeRequest containing message and thread info
        
    Returns:
        dict: Contains the complete response from the agent
    """
    try:
        config = request.config or {
            "configurable": {
                "thread_id": request.thread_id
            }
        }

        response = ""
        if request.is_first_message:
            write_to_log(f"Processing first message for thread {request.thread_id}")
            async for msg in agentic_flow.astream(
                {"latest_user_message": request.message}, 
                config,
                stream_mode="custom"
            ):
                response += str(msg)
        else:
            write_to_log(f"Processing continuation for thread {request.thread_id}")
            async for msg in agentic_flow.astream(
                Command(resume=request.message),
                config,
                stream_mode="custom"
            ):
                response += str(msg)

        write_to_log(f"Final response for thread {request.thread_id}: {response}")
        return {"response": response}
        
    except Exception as e:
        print(f"Exception invoking Archon for thread {request.thread_id}: {str(e)}")
        write_to_log(f"Error processing message for thread {request.thread_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/knowledge/invoke")
async def invoke_knowledge_workflow(request: KnowledgeWorkflowRequest):
    """
    Run the complete knowledge workflow for a project.

    This endpoint:
    1. Checks knowledge coverage
    2. Acquires missing knowledge if needed
    3. Decomposes project into tasks
    4. Links knowledge to tasks
    5. Schedules tasks

    Returns the final workflow state with tasks and schedule.
    """
    try:
        write_to_log(f"Running knowledge workflow for: {request.project_name}")

        result = await run_knowledge_workflow(
            project_description=request.project_description,
            project_name=request.project_name,
            min_coverage=request.min_coverage,
            thread_id=request.thread_id
        )

        return {
            "status": "success",
            "workflow_stage": result.get('workflow_stage'),
            "coverage_score": result.get('coverage_score'),
            "task_ids": result.get('task_ids', []),
            "schedule": result.get('schedule', []),
            "crawl_status": result.get('crawl_status'),
            "error_message": result.get('error_message')
        }

    except Exception as e:
        write_to_log(f"Error in knowledge workflow: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/knowledge/link-task")
async def link_task_knowledge(request: LinkTaskRequest):
    """
    Link knowledge to an existing task using semantic search.

    This is a quick operation that doesn't trigger crawling,
    just links existing knowledge chunks to the task.
    """
    try:
        write_to_log(f"Linking knowledge to task: {request.task_id}")

        result = await run_simple_knowledge_workflow(
            task_id=request.task_id,
            thread_id=f"link-{request.task_id}"
        )

        return {
            "status": "success",
            "linked_knowledge": result.get('linked_knowledge', []),
            "coverage_score": result.get('coverage_score', 0.0),
            "knowledge_chunks": len(result.get('linked_knowledge', []))
        }

    except Exception as e:
        write_to_log(f"Error linking task knowledge: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/knowledge/execute-task")
async def execute_task_with_knowledge(request: TaskExecutionRequest):
    """
    Execute a task with knowledge context injected.

    This endpoint:
    1. Checks knowledge coverage for the task
    2. Acquires knowledge if needed
    3. Links relevant knowledge to the task
    4. Executes the task with knowledge in context
    """
    try:
        write_to_log(f"Executing task with knowledge: {request.task_id}")

        result = await run_task_execution_workflow(
            task_id=request.task_id,
            min_coverage=request.min_coverage,
            thread_id=request.thread_id
        )

        return {
            "status": "success",
            "execution_result": result.get('execution_result'),
            "agent_output": result.get('agent_output'),
            "coverage_score": result.get('coverage_score'),
            "workflow_stage": result.get('workflow_stage')
        }

    except Exception as e:
        write_to_log(f"Error executing task: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/knowledge/plan-project")
async def plan_project(request: ProjectPlanningRequest):
    """
    Plan a project by creating and scheduling tasks.

    This endpoint:
    1. Checks knowledge coverage
    2. Acquires knowledge if needed
    3. Decomposes project into tasks
    4. Links knowledge to tasks
    5. Schedules tasks based on dependencies
    """
    try:
        write_to_log(f"Planning project: {request.project_id}")

        result = await run_project_planning_workflow(
            project_id=request.project_id,
            min_coverage=request.min_coverage,
            thread_id=request.thread_id
        )

        return {
            "status": "success",
            "project_id": request.project_id,
            "task_ids": result.get('task_ids', []),
            "schedule": result.get('schedule', []),
            "coverage_score": result.get('coverage_score'),
            "workflow_stage": result.get('workflow_stage')
        }

    except Exception as e:
        write_to_log(f"Error planning project: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/knowledge/check-coverage")
async def check_knowledge_coverage(request: CheckCoverageRequest):
    """
    Check knowledge coverage for given tags and frameworks.

    Returns coverage score and whether scraping is needed.
    """
    try:
        from archon.knowledge_manager import KnowledgeManager

        km = KnowledgeManager()
        coverage = await km.check_and_acquire_knowledge(
            tags=request.tags,
            frameworks=request.frameworks,
            min_coverage=request.min_coverage
        )

        return {
            "status": "success",
            "coverage_score": coverage.coverage_score,
            "total_chunks": coverage.total_chunks,
            "needs_scraping": coverage.needs_scraping,
            "missing_tags": coverage.missing_tags,
            "available_frameworks": coverage.available_frameworks
        }

    except Exception as e:
        write_to_log(f"Error checking coverage: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/integrated/invoke")
async def invoke_integrated_workflow(request: IntegratedWorkflowRequest):
    """
    Run integrated workflow that combines agent creation with knowledge management.

    The workflow automatically detects user intent and routes appropriately:
    - Agent creation only
    - Project planning only
    - Both agent creation and project planning
    """
    try:
        write_to_log(f"Running integrated workflow: {request.workflow_type}")

        result = await run_integrated_workflow(
            user_message=request.user_message,
            workflow_type=request.workflow_type,
            thread_id=request.thread_id
        )

        return {
            "status": "success",
            "workflow_mode": result.get('workflow_mode'),
            "agent_created": result.get('agent_created', False),
            "project_created": result.get('project_created', False),
            "project_id": result.get('project_id'),
            "task_ids": result.get('task_ids', [])
        }

    except Exception as e:
        write_to_log(f"Error in integrated workflow: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8100)

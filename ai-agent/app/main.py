from fastapi import FastAPI, BackgroundTasks, HTTPException
from pydantic import BaseModel
from app.agent import AIHealingAgent
import os
import logging

# Setup Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="AI Healing Agent")

# Initialize Agent
# In a real app, we might want to do this lazily or with dependency injection
agent = AIHealingAgent(
    github_token=os.getenv("AIDEVOPS_TOKEN"),
    openai_key=os.getenv("OPENAI_API_KEY"),
    slack_webhook=os.getenv("SLACK_WEBHOOK_URL")
)

class HealingRequest(BaseModel):
    repo: str
    run_id: str
    job: str
    branch: str
    failure_type: str = "unknown"

@app.post("/heal")
async def trigger_healing(request: HealingRequest, background_tasks: BackgroundTasks):
    logger.info(f"Received healing request for run {request.run_id}")
    background_tasks.add_task(agent.heal_pipeline, request.model_dump())
    return {"status": "healing initiated", "run_id": request.run_id}

@app.get("/health")
async def health():
    return {"status": "healthy"}

@app.get("/stats")
async def stats():
    return agent.get_stats()

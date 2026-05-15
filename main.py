import os
from uuid import uuid4
from datetime import datetime
from typing import Dict, Any

from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from pydantic import BaseModel

# Import from enhanced agents
from agents import process_patient_case, TriageReport

# -----------------------------------
# FASTAPI APP
# -----------------------------------

app = FastAPI(
    title="Medi-Sync AI Triage",
    description="Intelligent Medical Triage System with Multi-Agent Pipeline",
    version="1.0.0"
)

# -----------------------------------
# CORS (for React Frontend)
# -----------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Simple in-memory task store (for demo - replace with Redis/DB later)
tasks_db: Dict[str, Dict] = {}

# -----------------------------------
# REQUEST MODEL
# -----------------------------------

class PatientEmail(BaseModel):
    email_body: str


# -----------------------------------
# BACKGROUND TASK (Enhanced)
# -----------------------------------

def alert_doctor(task_id: str, urgency: str, report: TriageReport):
    """Background task - can later become email, SMS, WhatsApp, or push notification"""
    print("\n" + "="*60)
    print(f"🚨 DOCTOR ALERT - Task ID: {task_id}")
    print(f"URGENCY: {urgency.upper()}")
    print(f"Symptoms: {report.symptoms_list}")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60 + "\n")


# -----------------------------------
# MAIN PIPELINE ENDPOINT
# -----------------------------------

@app.post("/api/incoming-patient")
async def process_patient(
    request: PatientEmail,
    background_tasks: BackgroundTasks
):
    task_id = str(uuid4())[:8]   # Short unique ID for tracking

    try:
        print(f"\n[Task {task_id}] Received new patient case")

        # Store initial task status
        tasks_db[task_id] = {
            "status": "processing",
            "timestamp": datetime.now(),
            "email_body": request.email_body[:500] + "..." if len(request.email_body) > 500 else request.email_body
        }

        # ======================
        # FULL AUTONOMOUS PIPELINE
        # ======================
        result = process_patient_case(request.email_body)

        triage_report: TriageReport = result["triage_report"]

        # Update task status
        tasks_db[task_id].update({
            "status": "completed",
            "triage_report": triage_report.model_dump(),
            "research_summary": result["research_facts"][:500] + "..." if len(result["research_facts"]) > 500 else result["research_facts"],
            "completed_at": datetime.now()
        })

        # Trigger background alert
        background_tasks.add_task(
            alert_doctor,
            task_id,
            triage_report.urgency,
            triage_report
        )

        print(f"[Task {task_id}] Pipeline completed successfully - Urgency: {triage_report.urgency}")

        # Return rich response
        return {
            "task_id": task_id,
            "status": "success",
            "message": "Triage completed",
            "triage_report": triage_report.model_dump(),
            "research_facts": result["research_facts"],
            "reflection": result.get("reflection", ""),
            "processed_at": datetime.now().isoformat()
        }

    except Exception as e:
        print(f"[Task {task_id}] Error: {e}")
        tasks_db[task_id] = {
            "status": "failed",
            "error": str(e),
            "timestamp": datetime.now()
        }
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")


# -----------------------------------
# ADDITIONAL ENDPOINTS
# -----------------------------------

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "service": "Medi-Sync",
        "timestamp": datetime.now().isoformat()
    }


@app.get("/tasks/{task_id}")
async def get_task_status(task_id: str):
    """Check status of a task (useful for long-running workflows)"""
    if task_id not in tasks_db:
        raise HTTPException(status_code=404, detail="Task not found")
    return tasks_db[task_id]


# -----------------------------------
# RUN SERVER
# -----------------------------------

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
import os
import json
import asyncio
from uuid import uuid4
from datetime import datetime
from typing import Dict, Any

from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from pydantic import BaseModel

# Import from enhanced agents
from agents import process_patient_case, TriageReport, logs_queue, set_main_loop

# -----------------------------------
# FASTAPI APP
# -----------------------------------

app = FastAPI(
    title="Medi-Sync AI Triage",
    description="Intelligent Medical Triage System with Multi-Agent Pipeline",
    version="1.0.0"
)

@app.on_event("startup")
async def startup_event():
    # Set the main loop for thread-safe logging
    set_main_loop(asyncio.get_running_loop())
    print("🚀 System initialized with thread-safe logging")

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

@app.get("/api/incoming-patient")
async def get_all_patients():
    """Retrieve all patient triage cases"""
    return {
        "total_tasks": len(tasks_db),
        "tasks": tasks_db
    }

@app.get("/api/ai-logs")
async def stream_logs():
    """Stream AI agent logs using Server-Sent Events (SSE)"""
    async def log_generator():
        while True:
            log = await logs_queue.get()
            yield f"data: {json.dumps(log)}\n\n"
            
    return StreamingResponse(
        log_generator(), 
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

@app.post("/api/incoming-patient")
async def process_patient(
    request: PatientEmail,
    background_tasks: BackgroundTasks
):
    task_id = str(uuid4())[:8]   # Short unique ID for tracking

    try:
        print(f"\n[Task {task_id}] Received new patient case")

        # Store initial task status with ID included for easier frontend access
        tasks_db[task_id] = {
            "task_id": task_id,
            "status": "processing",
            "timestamp": datetime.now(),
            "email_body": request.email_body[:500] + "..." if len(request.email_body) > 500 else request.email_body
        }

        # ======================
        # FULL AUTONOMOUS PIPELINE
        # ======================
        # Run in a thread to avoid blocking the event loop, 
        # allowing logs to be streamed while processing
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(None, process_patient_case, request.email_body)

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
        error_msg = f"Processing failed: {str(e)}"
        print(f"[Task {task_id}] Error: {error_msg}")
        
        if task_id in tasks_db:
            tasks_db[task_id].update({
                "status": "failed",
                "error": error_msg,
                "timestamp": datetime.now()
            })
            
        raise HTTPException(status_code=500, detail=error_msg)


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

@app.get("/api/reports/{task_id}")
async def generate_report(task_id: str):
    """Generate a formatted medical report for a specific task"""
    if task_id not in tasks_db:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task = tasks_db[task_id]
    
    if task["status"] != "completed":
        return {
            "task_id": task_id,
            "status": task["status"],
            "message": "Report not ready yet."
        }
    
    report_data = task["triage_report"]
    
    # Create a structured, professional format
    formatted_report = {
        "header": {
            "report_id": f"REP-{task_id.upper()}",
            "generated_at": datetime.now().isoformat(),
            "patient_case_ref": task_id
        },
        "clinical_summary": {
            "urgency_level": report_data["urgency"],
            "identified_symptoms": report_data["symptoms_list"],
            "initial_assessment": report_data["doctor_notes"]
        },
        "medical_guidance": report_data["medical_guidance"],
        "research_background": task.get("research_summary", "No research data available."),
        "disclaimer": "This report is AI-generated for clinical support and should be reviewed by a qualified medical professional."
    }
    
    return formatted_report


# -----------------------------------
# RUN SERVER
# -----------------------------------

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=True,
        log_level="info"
    )

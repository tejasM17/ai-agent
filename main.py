from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from pydantic import BaseModel

from agents import (
    run_research_agent,
    run_triage_agent
)

import uvicorn

# -----------------------------------
# FASTAPI APP
# -----------------------------------

app = FastAPI(
    title="Medi-Sync AI Backend"
)

# -----------------------------------
# CORS
# -----------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------------
# REQUEST MODEL
# -----------------------------------

class PatientEmail(BaseModel):
    email_body: str

# -----------------------------------
# BACKGROUND TASK
# -----------------------------------

def alert_doctor(urgency: str):
    """
    Dummy background task.
    """

    print("\n" + "=" * 50)
    print(f"🚨 ALERT: Doctor notified for {urgency.upper()} urgency patient")
    print("=" * 50 + "\n")

# -----------------------------------
# ROUTE
# -----------------------------------

@app.post("/api/incoming-patient")
async def process_patient(
    request: PatientEmail,
    background_tasks: BackgroundTasks
):
    try:

        print(f"\n--> Received patient email:")
        print(request.email_body)

        # -----------------------------------
        # STEP 1 — RESEARCH AGENT
        # -----------------------------------

        print("\n--> Running Research Agent...")

        research_facts = run_research_agent(
            request.email_body
        )

        # -----------------------------------
        # STEP 2 — TRIAGE AGENT
        # -----------------------------------

        print("\n--> Running Triage Agent...")

        triage_result = run_triage_agent(
            request.email_body,
            research_facts
        )

        # -----------------------------------
        # STEP 3 — BACKGROUND TASK
        # -----------------------------------

        background_tasks.add_task(
            alert_doctor,
            triage_result.urgency
        )

        # -----------------------------------
        # STEP 4 — RETURN JSON
        # -----------------------------------

        print("\n--> Pipeline completed successfully.\n")

        return triage_result.model_dump()

    except Exception as e:

        print(f"Pipeline Error: {e}")

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

# -----------------------------------
# MAIN
# -----------------------------------

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
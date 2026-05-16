import os
import json
import asyncio
from datetime import datetime
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Callable

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.messages import HumanMessage, SystemMessage

from tools import medical_web_search

load_dotenv()

my_google_key = os.getenv("GOOGLE_API_KEY")
if not my_google_key:
    raise ValueError("🚨 ERROR: GOOGLE_API_KEY not found in .env file!")

print("✅ Google API Key loaded successfully")

# ====================== GLOBAL LOG QUEUE ======================
# This will be used by FastAPI to stream logs
logs_queue = asyncio.Queue()
main_loop = None

def set_main_loop(loop):
    global main_loop
    main_loop = loop

def log_activity(agent_name: str, message: str, data: Any = None):
    """Helper to push logs to the queue safely from any thread"""
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "agent": agent_name,
        "message": message,
        "data": data
    }
    print(f"[{agent_name}] {message}")
    
    if main_loop:
        # Use call_soon_threadsafe to put item in queue from a different thread
        main_loop.call_soon_threadsafe(logs_queue.put_nowait, log_entry)
    else:
        # Fallback if loop isn't set yet
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(logs_queue.put(log_entry))
        except RuntimeError:
            pass

# ====================== OUTPUT SCHEMA ======================
class TriageReport(BaseModel):
    urgency: str = Field(..., description="Must be exactly 'High', 'Medium', or 'Low'")
    symptoms_list: List[str] = Field(..., description="List of extracted symptoms")
    medical_guidance: str = Field(..., description="Evidence-based medical guidelines summary")
    doctor_notes: str = Field(default="", description="Additional observations for doctor")


# ====================== LLM ======================
llm = ChatGoogleGenerativeAI(
    model="gemini-3.1-flash-lite-preview",   # Switching to 2.0 Flash for fresh quota
    temperature=0.1,
    api_key=my_google_key,
    convert_system_message_to_human=True,
    max_tokens=2048,
)


# ====================== AGENT 1 — RESEARCHER (with Tool + Reasoning) ======================
research_system_prompt = SystemMessage(content="""You are an expert Clinical Medical Researcher.
Your job is to gather reliable, up-to-date medical information only.
Rules:
- Use the web search tool effectively.
- Focus on standard guidelines (WHO, Mayo Clinic, CDC, NICE, etc.)
- Never diagnose the patient.
- Be concise, factual, and cite sources when possible.
- Think step-by-step before giving final answer.""")

def run_research_agent(patient_text: str) -> str:
    """Researcher Agent with tool calling simulation"""
    try:
        log_activity("Researcher", f"Starting research for: {patient_text[:50]}...")
        
        tool_query = f"Current medical guidelines for: {patient_text}"
        web_results = medical_web_search(tool_query)
        
        log_activity("Researcher", "Web search completed. Analyzing results...")

        response = llm.invoke([
            research_system_prompt,
            HumanMessage(content=f"""Patient: {patient_text}

Web Search Results:
{web_results}

Now analyze and summarize only the relevant medical facts and guidelines.""")
        ])
        
        log_activity("Researcher", "Fact summary generated.")
        return response.content
    
    except Exception as e:
        log_activity("Researcher", f"Error: {str(e)}")
        return f"Web search failed. Basic symptoms: {patient_text}"


# ====================== REFLECTION / CRITIQUE STEP ======================
reflection_prompt = ChatPromptTemplate.from_messages([
    ("system", """You are a senior medical reviewer. 
Critically evaluate the research provided and suggest improvements or missing information.
Be strict and objective."""),
    ("human", "Research Output:\n{research_facts}\n\nPatient: {patient_text}")
])

def run_reflection(research_facts: str, patient_text: str) -> str:
    """Adds deep reasoning through reflection"""
    try:
        log_activity("Reviewer", "Critically evaluating research findings...")
        reflection = llm.invoke(reflection_prompt.format_messages(
            research_facts=research_facts,
            patient_text=patient_text
        ))
        log_activity("Reviewer", "Reflection completed.")
        return reflection.content
    except Exception as e:
        log_activity("Reviewer", f"Error during reflection: {str(e)}")
        return "No additional reflection available."


# ====================== AGENT 2 — TRIAGE OFFICER (Final Decision) ======================
parser = PydanticOutputParser(pydantic_object=TriageReport)

triage_system_prompt = """You are an experienced Medical Triage Officer.
Analyze the patient's symptoms and the provided research facts.
Determine urgency level carefully.
You must output ONLY valid JSON matching the schema. No explanations."""

triage_prompt = ChatPromptTemplate.from_messages([
    ("system", triage_system_prompt),
    ("human", """Patient Description:
{patient_text}

Research + Guidelines:
{research_facts}

Reflection:
{reflection}

{format_instructions}""")
]).partial(format_instructions=parser.get_format_instructions())

triage_chain = triage_prompt | llm | parser

def run_triage_agent(patient_text: str, research_facts: str, reflection: str = "") -> TriageReport:
    """Triage Officer with structured output"""
    try:
        log_activity("TriageOfficer", "Synthesizing final triage decision...")
        report = triage_chain.invoke({
            "patient_text": patient_text,
            "research_facts": research_facts,
            "reflection": reflection
        })
        log_activity("TriageOfficer", f"Triage complete. Urgency: {report.urgency}")
        return report
    except Exception as e:
        log_activity("TriageOfficer", f"Error: {str(e)}")
        # Fallback
        return TriageReport(
            urgency="Medium",
            symptoms_list=["Unknown symptoms"],
            medical_guidance="Unable to process request properly. Please consult a doctor.",
            doctor_notes="Error occurred during triage processing."
        )


# ====================== MAIN PIPELINE ======================
def process_patient_case(patient_text: str) -> Dict[str, Any]:
    """
    Full autonomous pipeline with multi-agent collaboration + reflection
    """
    log_activity("System", "Initializing Multi-Agent Pipeline")
    
    research_facts = run_research_agent(patient_text)
    reflection = run_reflection(research_facts, patient_text)
    triage_report = run_triage_agent(patient_text, research_facts, reflection)
    
    log_activity("System", "Pipeline execution finished")
    
    return {
        "triage_report": triage_report,
        "research_facts": research_facts,
        "reflection": reflection
    }

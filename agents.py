import os
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from typing import List, Dict, Any

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


# ====================== OUTPUT SCHEMA ======================
class TriageReport(BaseModel):
    urgency: str = Field(..., description="Must be exactly 'High', 'Medium', or 'Low'")
    symptoms_list: List[str] = Field(..., description="List of extracted symptoms")
    medical_guidance: str = Field(..., description="Evidence-based medical guidelines summary")
    doctor_notes: str = Field(default="", description="Additional observations for doctor")


# ====================== LLM ======================
llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash-lite",   # Change to "gemini-2.5-flash" if needed
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

research_prompt = ChatPromptTemplate.from_messages([
    research_system_prompt,
    ("human", """Patient Symptoms: {patient_text}

Use the available search tool to find relevant medical guidelines.
Then provide a detailed factual summary.""")
])

def run_research_agent(patient_text: str) -> str:
    """Researcher Agent with tool calling simulation"""
    try:
        # First call with tool instruction
        tool_query = f"Current medical guidelines for: {patient_text}"
        web_results = medical_web_search(tool_query)
        
        response = llm.invoke([
            research_system_prompt,
            HumanMessage(content=f"""Patient: {patient_text}

Web Search Results:
{web_results}

Now analyze and summarize only the relevant medical facts and guidelines.""")
        ])
        
        return response.content
    
    except Exception as e:
        print(f"Research Agent Error: {e}")
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
        reflection = llm.invoke(reflection_prompt.format_messages(
            research_facts=research_facts,
            patient_text=patient_text
        ))
        return reflection.content
    except:
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
        return triage_chain.invoke({
            "patient_text": patient_text,
            "research_facts": research_facts,
            "reflection": reflection
        })
    except Exception as e:
        print(f"Triage Agent Error: {e}")
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
    print("🔍 Starting Research Phase...")
    research_facts = run_research_agent(patient_text)
    
    print("🤔 Running Reflection & Critique...")
    reflection = run_reflection(research_facts, patient_text)
    
    print("⚕️ Running Triage Decision...")
    triage_report = run_triage_agent(patient_text, research_facts, reflection)
    
    return {
        "triage_report": triage_report,
        "research_facts": research_facts,
        "reflection": reflection
    }
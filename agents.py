import os
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from typing import List

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser

from tools import medical_web_search

# ====================== LOAD ENVIRONMENT ======================
load_dotenv()

my_google_key = os.getenv("GOOGLE_API_KEY")

if not my_google_key:
    raise ValueError("🚨 ERROR: GOOGLE_API_KEY not found in .env file!")

print("✅ Google API Key loaded successfully")

# ====================== OUTPUT SCHEMA ======================
class TriageReport(BaseModel):
    urgency: str = Field(description="Must be exactly High, Medium, or Low")
    symptoms_list: List[str] = Field(description="List of extracted symptoms")
    medical_guidance: str = Field(description="Summary of standard medical guidelines")
    doctor_notes: str = Field(description="Leave empty for now", default="")


# ====================== LLM ======================
llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash-lite",      # Try "gemini-1.5-flash" if 2.5 doesn't work
    temperature=0,
    api_key=my_google_key,         # ← This was missing!
    convert_system_message_to_human=True  # Helps with some Gemini versions
)

# ====================== AGENT 1 — RESEARCHER ======================
research_prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a clinical medical researcher.\n"
               "1. Analyze the patient's symptoms.\n"
               "2. Search for standard medical guidelines.\n"
               "3. Return ONLY factual medical guidance.\n"
               "4. Do NOT diagnose the patient.\n"
               "5. Keep the response concise and medically grounded."),
    ("human", "Patient Symptoms:\n{patient_text}")
])

research_chain = research_prompt | llm

def run_research_agent(patient_text: str) -> str:
    web_results = medical_web_search(f"Medical guidelines for symptoms: {patient_text}")
    research_response = research_chain.invoke({
        "patient_text": f"{patient_text}\n\nWeb Search Results:\n{web_results}"
    })
    return research_response.content


# ====================== AGENT 2 — TRIAGE OFFICER ======================
parser = PydanticOutputParser(pydantic_object=TriageReport)

triage_prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a medical triage officer.\n"
               "Analyze patient symptoms and medical research facts.\n"
               "Determine urgency: High, Medium, or Low.\n"
               "Return output EXACTLY matching the required JSON schema.\n"
               "{format_instructions}"),
    ("human", "Patient Symptoms:\n{patient_text}\n\nMedical Research:\n{research_facts}")
]).partial(format_instructions=parser.get_format_instructions())

triage_chain = triage_prompt | llm | parser

def run_triage_agent(patient_text: str, research_facts: str):
    return triage_chain.invoke({
        "patient_text": patient_text,
        "research_facts": research_facts
    })
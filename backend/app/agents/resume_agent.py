import logging
from typing import TypedDict

import fitz  # PyMuPDF
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, END

from app.config import settings
from app.schemas.profile import ResumeProfile

logger = logging.getLogger(__name__)

# State definition
class ResumeState(TypedDict):
    file_path: str
    raw_text: str
    parsed_profile: ResumeProfile | None
    error: str | None


def extract_text_node(state: ResumeState) -> ResumeState:
    """Extracts text from the PDF file using PyMuPDF."""
    logger.info(f"Extracting text from {state['file_path']}")
    text = ""
    try:
        with fitz.open(state["file_path"]) as doc:
            for page in doc:
                text += page.get_text()
        
        if not text.strip():
            return {**state, "error": "Could not extract text from PDF."}
            
        return {**state, "raw_text": text}
    except Exception as e:
        logger.error(f"Error extracting text: {e}")
        return {**state, "error": f"Failed to extract text: {str(e)}"}


def parse_with_llm_node(state: ResumeState) -> ResumeState:
    """Parses the raw text into a structured profile using Gemini 2.0 Flash."""
    logger.info("Parsing text with Gemini 2.0 Flash")
    
    # Initialize the LLM (temperature 0 for consistent extraction)
    llm = ChatGoogleGenerativeAI(
        model="gemini-3.6-flash",
        temperature=0,
        google_api_key=settings.google_api_key,
    )
    
    # Bind the target Pydantic schema
    structured_llm = llm.with_structured_output(ResumeProfile)
    
    system_prompt = (
        "You are an expert ATS (Applicant Tracking System) parser. "
        "Your task is to extract information from the provided resume text and format it exactly "
        "according to the schema. Extract all relevant details, skills, experiences, and education. "
        "If some information is missing, leave the optional fields empty. Do not invent information."
    )
    
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"Resume Text:\n\n{state['raw_text']}")
    ]
    
    try:
        parsed_profile = structured_llm.invoke(messages)
        return {**state, "parsed_profile": parsed_profile}
    except Exception as e:
        logger.error(f"Error parsing with LLM: {e}")
        return {**state, "error": f"Failed to parse resume with AI: {str(e)}"}


def router(state: ResumeState) -> str:
    """Routes the graph based on the presence of errors."""
    if state.get("error"):
        return END
    if not state.get("raw_text"):
        return END
    return "parse_with_llm"


# Build the Graph
workflow = StateGraph(ResumeState)

workflow.add_node("extract_text", extract_text_node)
workflow.add_node("parse_with_llm", parse_with_llm_node)

workflow.set_entry_point("extract_text")
workflow.add_conditional_edges("extract_text", router, {"parse_with_llm": "parse_with_llm", END: END})
workflow.add_edge("parse_with_llm", END)

resume_parser_app = workflow.compile()


async def process_resume(file_path: str) -> dict:
    """Helper function to run the graph and return the result."""
    initial_state = {"file_path": file_path, "raw_text": "", "parsed_profile": None, "error": None}
    
    # Run the graph synchronously as PyMuPDF is sync and langchain invoke is blocking by default here,
    # though we could use ainvoke if we updated the node to be async.
    # For now, we'll just run it with standard invoke.
    final_state = resume_parser_app.invoke(initial_state)
    
    return {
        "raw_text": final_state.get("raw_text"),
        "profile": final_state.get("parsed_profile"),
        "error": final_state.get("error")
    }

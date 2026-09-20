import logging
from typing import TypedDict

from langchain_core.messages import SystemMessage, HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, END

from app.config import settings
from app.schemas.profile import ProfileResponse
from app.schemas.cv import CVGenerateRequest, TailoredCV, JobRequirements

logger = logging.getLogger(__name__)

class CVState(TypedDict):
    profile: ProfileResponse
    request: CVGenerateRequest
    job_requirements: JobRequirements | None
    tailored_cv: TailoredCV | None
    error: str | None


def analyze_job_node(state: CVState) -> CVState:
    """Extracts structured requirements from the job description."""
    logger.info("Analyzing Job Description")
    llm = ChatGoogleGenerativeAI(
        model="gemini-3.6-flash",
        temperature=0,
        google_api_key=settings.google_api_key,
    )
    structured_llm = llm.with_structured_output(JobRequirements)
    
    prompt = (
        "You are an expert technical recruiter and ATS specialist. "
        "Analyze the following job description and extract the key requirements, skills, "
        "responsibilities, and ATS keywords needed to pass the screening."
    )
    
    messages = [
        SystemMessage(content=prompt),
        HumanMessage(content=f"Job Description:\n\n{state['request'].job_description}")
    ]
    
    try:
        job_reqs = structured_llm.invoke(messages)
        return {**state, "job_requirements": job_reqs}
    except Exception as e:
        logger.error(f"Error analyzing job description: {e}")
        return {**state, "error": f"Failed to analyze job description: {str(e)}"}


def generate_cv_node(state: CVState) -> CVState:
    """Generates the tailored CV based on the profile and job requirements."""
    logger.info("Generating Tailored CV")
    llm = ChatGoogleGenerativeAI(
        model="gemini-3.6-flash",
        temperature=0.2,
        google_api_key=settings.google_api_key,
    )
    structured_llm = llm.with_structured_output(TailoredCV)
    
    reqs = state["job_requirements"]
    profile = state["profile"]
    
    target_job = state["request"].job_title or reqs.job_title or "the target role"
    target_company = state["request"].company_name or reqs.company or "the target company"
    
    system_prompt = (
        f"You are an elite executive resume writer. Your task is to tailor a candidate's resume "
        f"for the role of '{target_job}' at '{target_company}'. "
        "You must rewrite the professional summary and work experience bullets to highly align "
        "with the job requirements and seamlessly integrate ATS keywords. "
        "CRITICAL RULES: "
        "1. DO NOT lie or invent experience/data the candidate does not have. You can change wording but cannot add new hallucinated data. "
        "2. Only output sections that have provided data. If the profile lacks data (e.g., no projects), omit the section entirely and DO NOT hallucinate it. "
        "3. For detailed job titles, use a hyphen '-' instead of parentheses '()'. (e.g., 'Software Engineer - DevOps', NOT 'Software Engineer (DevOps)'). "
        "4. You may logically reorder sections (e.g., placing Education before Experience if the candidate is a fresh graduate). "
        "Prioritize the most relevant skills. Estimate a realistic ATS match score (0-100) based on the match."
    )
    
    human_content = (
        f"CANDIDATE PROFILE:\n{profile.model_dump_json(indent=2)}\n\n"
        f"JOB REQUIREMENTS & ATS KEYWORDS:\n{reqs.model_dump_json(indent=2)}\n\n"
        "Generate the highly tailored CV content adhering to the schema."
    )
    
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=human_content)
    ]
    
    try:
        tailored_cv = structured_llm.invoke(messages)
        return {**state, "tailored_cv": tailored_cv}
    except Exception as e:
        logger.error(f"Error generating CV: {e}")
        return {**state, "error": f"Failed to generate CV: {str(e)}"}


def router(state: CVState) -> str:
    if state.get("error"):
        return END
    return "generate_cv"

# Build the Graph
workflow = StateGraph(CVState)

workflow.add_node("analyze_job", analyze_job_node)
workflow.add_node("generate_cv", generate_cv_node)

workflow.set_entry_point("analyze_job")
workflow.add_conditional_edges("analyze_job", router, {"generate_cv": "generate_cv", END: END})
workflow.add_edge("generate_cv", END)

cv_generator_app = workflow.compile()


async def process_cv_generation(profile: ProfileResponse, request: CVGenerateRequest) -> dict:
    """Helper function to run the graph and return the tailored CV."""
    initial_state = {
        "profile": profile,
        "request": request,
        "job_requirements": None,
        "tailored_cv": None,
        "error": None
    }
    
    final_state = cv_generator_app.invoke(initial_state)
    
    return {
        "tailored_cv": final_state.get("tailored_cv"),
        "error": final_state.get("error")
    }

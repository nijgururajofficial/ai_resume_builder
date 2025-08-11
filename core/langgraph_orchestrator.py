import logging
from typing import TypedDict, Dict, Any

from langgraph.graph import StateGraph, END

# Import the agents and the Gemini client
from agents import JobDescriptionAnalysisAgent, ResumeContentSelectionAgent, MarkdownFormattingAgent
from .gemini_client import GeminiClient

class GraphState(TypedDict):
    """
    Defines the state that flows through the LangGraph.
    Each key represents a piece of data managed by the graph.
    """
    user_profile: Dict[str, Any]
    job_description: str
    job_analysis: Dict[str, Any]
    tailored_content: Dict[str, Any]
    markdown_resume: str

class LangGraphOrchestrator:
    """
    Orchestrates the resume generation workflow using a stateful graph (LangGraph).

    This class wires together the different AI and deterministic agents into a
    sequential pipeline, managing the state at each step.
    """

    def __init__(self, gemini_client: GeminiClient):
        """
        Initializes the orchestrator and the agents it manages.
        """
        self.gemini_client = gemini_client
        self.workflow = self._build_graph()

    def _build_graph(self):
        """
        Constructs the computational graph defining the agent workflow.
        """
        # Instantiate agents, injecting the Gemini client where needed
        analysis_agent = JobDescriptionAnalysisAgent(self.gemini_client)
        selection_agent = ResumeContentSelectionAgent(self.gemini_client)
        formatting_agent = MarkdownFormattingAgent() # This agent is deterministic

        # Define graph nodes corresponding to each agent's task
        def analyze_job_description(state: GraphState) -> GraphState:
            logging.info("Node: Analyzing Job Description")
            job_analysis = analysis_agent.run(state['job_description'])
            return {**state, "job_analysis": job_analysis}

        def select_resume_content(state: GraphState) -> GraphState:
            logging.info("Node: Selecting and Tailoring Resume Content")
            tailored_content = selection_agent.run(state['user_profile'], state['job_analysis'])
            return {**state, "tailored_content": tailored_content}

        def format_markdown_resume(state: GraphState) -> GraphState:
            logging.info("Node: Formatting Final Markdown Resume")
            markdown_resume = formatting_agent.run(state['user_profile'], state['tailored_content'])
            return {**state, "markdown_resume": markdown_resume}

        # Build the state machine
        graph_builder = StateGraph(GraphState)
        graph_builder.add_node("analyze_job", analyze_job_description)
        graph_builder.add_node("select_content", select_resume_content)
        graph_builder.add_node("format_resume", format_markdown_resume)

        # Define the workflow edges
        graph_builder.set_entry_point("analyze_job")
        graph_builder.add_edge("analyze_job", "select_content")
        graph_builder.add_edge("select_content", "format_resume")
        graph_builder.add_edge("format_resume", END)

        logging.info("LangGraph workflow compiled.")
        return graph_builder.compile()

    def run(self, user_profile: Dict, job_description: str) -> Dict:
        """
        Executes the entire resume generation pipeline.

        Args:
            user_profile: The user's profile data.
            job_description: The target job description text.

        Returns:
            The final state of the graph, containing all intermediate and final results.
        """
        initial_state = {
            "user_profile": user_profile,
            "job_description": job_description,
            "job_analysis": {},
            "tailored_content": {},
            "markdown_resume": ""
        }
        logging.info("Invoking LangGraph workflow...")
        final_state = self.workflow.invoke(initial_state)
        logging.info("Workflow finished.")
        return final_state
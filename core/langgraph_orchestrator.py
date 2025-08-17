import logging
from typing import TypedDict, Dict, Any
from datetime import datetime

from langgraph.graph import StateGraph, END
from IPython.display import Image, display


# Import the agents and the Gemini client
from agents import JobDescriptionAnalysisAgent, ResumeContentSelectionAgent, MarkdownFormattingAgent
from .gemini_client import GeminiClient

class AgentResponse(TypedDict):
    """Stores detailed information about an agent's execution."""
    timestamp: str
    agent_name: str
    input_data: Dict[str, Any]
    output_data: Dict[str, Any]
    execution_time_ms: float
    status: str  # "success", "error"
    error_message: str
    raw_llm_response: str  # For LLM-based agents
    prompt_used: str  # For LLM-based agents

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
    # New fields for storing agent responses
    agent_responses: Dict[str, AgentResponse]
    workflow_metadata: Dict[str, Any]

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
            start_time = datetime.now()
            
            try:
                # Capture input data
                input_data = {"job_description": state['job_description']}
                
                # Execute agent
                job_analysis = analysis_agent.run(state['job_description'])
                
                # Calculate execution time
                execution_time = (datetime.now() - start_time).total_seconds() * 1000
                
                # Store agent response
                agent_response = AgentResponse(
                    timestamp=datetime.now().isoformat(),
                    agent_name="JobDescriptionAnalysisAgent",
                    input_data=input_data,
                    output_data=job_analysis,
                    execution_time_ms=execution_time,
                    status="success" if job_analysis else "error",
                    error_message="" if job_analysis else "Failed to generate job analysis",
                    raw_llm_response=getattr(analysis_agent, 'last_response', ''),
                    prompt_used=getattr(analysis_agent, 'last_prompt', '')
                )
                
                # Update state
                new_state = {**state, "job_analysis": job_analysis}
                new_state["agent_responses"]["job_analysis"] = agent_response
                
                return new_state
                
            except Exception as e:
                execution_time = (datetime.now() - start_time).total_seconds() * 1000
                error_response = AgentResponse(
                    timestamp=datetime.now().isoformat(),
                    agent_name="JobDescriptionAnalysisAgent",
                    input_data=input_data,
                    output_data={},
                    execution_time_ms=execution_time,
                    status="error",
                    error_message=str(e),
                    raw_llm_response="",
                    prompt_used=""
                )
                
                new_state = {**state, "job_analysis": {}}
                new_state["agent_responses"]["job_analysis"] = error_response
                return new_state

        def select_resume_content(state: GraphState) -> GraphState:
            logging.info("Node: Selecting and Tailoring Resume Content")
            start_time = datetime.now()
            
            try:
                # Capture input data
                input_data = {
                    "user_profile": state['user_profile'],
                    "job_analysis": state['job_analysis']
                }
                
                # Execute agent
                tailored_content = selection_agent.run(state['user_profile'], state['job_analysis'])
                
                # Calculate execution time
                execution_time = (datetime.now() - start_time).total_seconds() * 1000
                
                # Store agent response
                agent_response = AgentResponse(
                    timestamp=datetime.now().isoformat(),
                    agent_name="ResumeContentSelectionAgent",
                    input_data=input_data,
                    output_data=tailored_content,
                    execution_time_ms=execution_time,
                    status="success" if tailored_content else "error",
                    error_message="" if tailored_content else "Failed to generate tailored content",
                    raw_llm_response=getattr(selection_agent, 'last_response', ''),
                    prompt_used=getattr(selection_agent, 'last_prompt', '')
                )
                
                # Update state
                new_state = {**state, "tailored_content": tailored_content}
                new_state["agent_responses"]["content_selection"] = agent_response
                
                return new_state
                
            except Exception as e:
                execution_time = (datetime.now() - start_time).total_seconds() * 1000
                error_response = AgentResponse(
                    timestamp=datetime.now().isoformat(),
                    agent_name="ResumeContentSelectionAgent",
                    input_data=input_data,
                    output_data={},
                    execution_time_ms=execution_time,
                    status="error",
                    error_message=str(e),
                    raw_llm_response="",
                    prompt_used=""
                )
                
                new_state = {**state, "tailored_content": {}}
                new_state["agent_responses"]["content_selection"] = error_response
                return new_state

        def format_markdown_resume(state: GraphState) -> GraphState:
            logging.info("Node: Formatting Final Markdown Resume")
            start_time = datetime.now()
            
            try:
                # Capture input data
                input_data = {
                    "user_profile": state['user_profile'],
                    "tailored_content": state['tailored_content']
                }
                
                # Execute agent
                markdown_resume = formatting_agent.run(state['user_profile'], state['tailored_content'])
                
                # Calculate execution time
                execution_time = (datetime.now() - start_time).total_seconds() * 1000
                
                # Store agent response
                agent_response = AgentResponse(
                    timestamp=datetime.now().isoformat(),
                    agent_name="MarkdownFormattingAgent",
                    input_data=input_data,
                    output_data={"markdown_resume": markdown_resume},
                    execution_time_ms=execution_time,
                    status="success",
                    error_message="",
                    raw_llm_response="",  # This agent doesn't use LLM
                    prompt_used=""  # This agent doesn't use prompts
                )
                
                # Update state
                new_state = {**state, "markdown_resume": markdown_resume}
                new_state["agent_responses"]["markdown_formatting"] = agent_response
                
                return new_state
                
            except Exception as e:
                execution_time = (datetime.now() - start_time).total_seconds() * 1000
                error_response = AgentResponse(
                    timestamp=datetime.now().isoformat(),
                    agent_name="MarkdownFormattingAgent",
                    input_data=input_data,
                    output_data={},
                    execution_time_ms=execution_time,
                    status="error",
                    error_message=str(e),
                    raw_llm_response="",
                    prompt_used=""
                )
                
                new_state = {**state, "markdown_resume": ""}
                new_state["agent_responses"]["markdown_formatting"] = error_response
                return new_state

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
        graph = graph_builder.compile()
        
        # Save the Mermaid diagram as a PNG image
        # try:
        #     png_data = graph.get_graph().draw_mermaid_png()
        #     print("Saving workflow diagram...")
        #     with open("output/workflow_diagram.png", "wb") as f:
        #         f.write(png_data)
        #     logging.info("Workflow diagram saved as 'output/workflow_diagram.png'")
        # except Exception as e:
        #     logging.warning(f"Could not save workflow diagram: {e}")
        
        return graph

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
            "markdown_resume": "",
            "agent_responses": {},
            "workflow_metadata": {
                "workflow_start_time": datetime.now().isoformat(),
                "total_agents": 3,
                "version": "1.0"
            }
        }
        logging.info("Invoking LangGraph workflow...")
        final_state = self.workflow.invoke(initial_state)
        
        # Add workflow completion metadata
        final_state["workflow_metadata"]["workflow_end_time"] = datetime.now().isoformat()
        final_state["workflow_metadata"]["total_execution_time_ms"] = sum(
            response.get("execution_time_ms", 0) 
            for response in final_state["agent_responses"].values()
        )
        
        logging.info("Workflow finished.")
        return final_state
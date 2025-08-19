import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List
import pandas as pd

class ResponseLogger:
    """
    Utility class for logging, storing, and analyzing agent responses.
    Provides methods to save responses to files, analyze performance, and generate reports.
    """
    
    def __init__(self, output_dir: str = "output"):
        """
        Initialize the response logger.
        
        Args:
            output_dir: Directory to store response logs and reports
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        # Create subdirectories
        (self.output_dir / "agent_responses").mkdir(exist_ok=True)
        (self.output_dir / "reports").mkdir(exist_ok=True)
        
        logging.basicConfig(level=logging.INFO)
    
    def save_workflow_responses(self, final_state: Dict[str, Any], filename: str = None) -> str:
        """
        Save the complete workflow state including all agent responses to a JSON file.
        
        Args:
            final_state: The final state from the LangGraph orchestrator
            filename: Optional custom filename, defaults to timestamp-based name
            
        Returns:
            Path to the saved file
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"workflow_responses_{timestamp}.json"
        
        filepath = self.output_dir / "agent_responses" / filename
        
        # Create a clean copy for saving (remove any non-serializable objects)
        save_data = {
            "workflow_metadata": final_state.get("workflow_metadata", {}),
            "agent_responses": final_state.get("agent_responses", {}),
            "final_outputs": {
                "job_analysis": final_state.get("job_analysis", {}),
                "tailored_content": final_state.get("tailored_content", {}),
                "markdown_resume": final_state.get("markdown_resume", "")
            }
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(save_data, f, indent=2, ensure_ascii=False)
        
        logging.info(f"Workflow responses saved to: {filepath}")
        return str(filepath)
    
    def save_individual_agent_response(self, agent_response: Dict[str, Any], agent_name: str) -> str:
        """
        Save an individual agent's response to a separate file.
        
        Args:
            agent_response: The agent response data
            agent_name: Name of the agent
            
        Returns:
            Path to the saved file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{agent_name}_{timestamp}.json"
        filepath = self.output_dir / "agent_responses" / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(agent_response, f, indent=2, ensure_ascii=False)
        
        logging.info(f"Agent response saved to: {filepath}")
        return str(filepath)
    
    def generate_performance_report(self, final_state: Dict[str, Any]) -> str:
        """
        Generate a performance report from the workflow execution.
        
        Args:
            final_state: The final state from the LangGraph orchestrator
            
        Returns:
            Path to the generated report
        """
        agent_responses = final_state.get("agent_responses", {})
        workflow_metadata = final_state.get("workflow_metadata", {})
        
        # Create performance summary
        performance_data = []
        total_time = 0
        
        for agent_key, response in agent_responses.items():
            agent_name = response.get("agent_name", agent_key)
            execution_time = response.get("execution_time_ms", 0)
            status = response.get("status", "unknown")
            error_message = response.get("error_message", "")
            
            performance_data.append({
                "Agent": agent_name,
                "Status": status,
                "Execution Time (ms)": execution_time,
                "Error Message": error_message
            })
            
            total_time += execution_time
        
        # Create DataFrame for easy analysis
        df = pd.DataFrame(performance_data)
        
        # Generate report
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_filename = f"performance_report_{timestamp}.html"
        report_path = self.output_dir / "reports" / report_filename
        
        html_report = f"""
        <html>
        <head>
            <title>AI Resume Builder - Performance Report</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .header {{ background-color: #f0f0f0; padding: 20px; border-radius: 5px; }}
                .summary {{ margin: 20px 0; }}
                table {{ border-collapse: collapse; width: 100%; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
                .success {{ color: green; }}
                .error {{ color: red; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>AI Resume Builder - Performance Report</h1>
                <p>Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
            </div>
            
            <div class="summary">
                <h2>Workflow Summary</h2>
                <p><strong>Total Execution Time:</strong> {total_time:.2f} ms</p>
                <p><strong>Workflow Start:</strong> {workflow_metadata.get('workflow_start_time', 'N/A')}</p>
                <p><strong>Workflow End:</strong> {workflow_metadata.get('workflow_end_time', 'N/A')}</p>
                <p><strong>Total Agents:</strong> {workflow_metadata.get('total_agents', 'N/A')}</p>
            </div>
            
            <h2>Agent Performance Details</h2>
            {df.to_html(index=False, classes='dataframe')}
        </body>
        </html>
        """
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(html_report)
        
        logging.info(f"Performance report generated: {report_path}")
        return str(report_path)
    
    def analyze_agent_responses(self, final_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze agent responses and return insights.
        
        Args:
            final_state: The final state from the LangGraph orchestrator
            
        Returns:
            Dictionary containing analysis results
        """
        agent_responses = final_state.get("agent_responses", {})
        
        analysis = {
            "total_agents": len(agent_responses),
            "successful_agents": 0,
            "failed_agents": 0,
            "total_execution_time_ms": 0,
            "agent_performance": {},
            "errors": []
        }
        
        for agent_key, response in agent_responses.items():
            agent_name = response.get("agent_name", agent_key)
            status = response.get("status", "unknown")
            execution_time = response.get("execution_time_ms", 0)
            error_message = response.get("error_message", "")
            
            analysis["total_execution_time_ms"] += execution_time
            
            if status == "success":
                analysis["successful_agents"] += 1
            else:
                analysis["failed_agents"] += 1
                if error_message:
                    analysis["errors"].append(f"{agent_name}: {error_message}")
            
            analysis["agent_performance"][agent_name] = {
                "status": status,
                "execution_time_ms": execution_time,
                "has_llm_response": bool(response.get("raw_llm_response")),
                "has_prompt": bool(response.get("prompt_used"))
            }
        
        return analysis
    
    def get_agent_response_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent agent response history from saved files.
        
        Args:
            limit: Maximum number of recent responses to return
            
        Returns:
            List of recent agent responses
        """
        response_dir = self.output_dir / "agent_responses"
        response_files = sorted(response_dir.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True)
        
        history = []
        for filepath in response_files[:limit]:
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    data["_filename"] = filepath.name
                    data["_filepath"] = str(filepath)
                    history.append(data)
            except Exception as e:
                logging.warning(f"Could not read response file {filepath}: {e}")
        
        return history

import json
import logging
from typing import Dict

# The GeminiClient would be a wrapper around the Google Gemini API SDK.
# from core.gemini_client import GeminiClient

class JobDescriptionAnalysisAgent:
    """
    Analyzes a job description using the Gemini LLM to extract structured data.

    This agent's primary function is to parse unstructured job description text
    and convert it into a machine-readable JSON format, identifying the exact
    terminology and skills required for the role. This is the foundation for
    ATS keyword matching.
    """

    def __init__(self, gemini_client):
        """
        Initializes the agent with a client to communicate with the Gemini API.
        
        Args:
            gemini_client: An instance of a client configured to handle Gemini API calls.
        """
        self.llm = gemini_client
        self.last_response = ""
        self.last_prompt = ""
        logging.basicConfig(level=logging.INFO)

    def _create_prompt(self, job_description: str) -> str:
        """
        Constructs a precise, zero-shot prompt for the LLM, instructing it to
        act as an ATS analyst and return a structured JSON object.
        """
        return f"""
        Analyze the following job description with the expertise of an ATS (Applicant Tracking System) analyst.
        Your task is to extract key information and structure it as a valid JSON object.
        The output must only be the JSON object, with no additional text or explanations.

        **Extraction Rules:**
        1.  `job_title`: Extract the exact job title.
        2.  `company_name`: Extract the hiring company's name.
        3.  `required_skills`: Create a comprehensive list of all technical and soft skills.
            -   Crucially, if an acronym is present, include both the full term and the acronym (e.g., "Natural Language Processing", "NLP").
            -   This list must be flat, containing only strings.
        4.  `responsibilities`: List the core duties and qualifications mentioned.

        **Job Description Text:**
        ---
        {job_description}
        ---

        **JSON Output:**
        """

    def run(self, job_description: str) -> Dict:
        """
        Executes the analysis pipeline for a given job description.

        Args:
            job_description: The raw text of the job description.

        Returns:
            A dictionary with the extracted job details. Returns an empty dict on failure.
        """
        prompt = self._create_prompt(job_description)
        self.last_prompt = prompt
        
        try:
            # This makes the actual call to the Gemini API.
            response_text = self.llm.generate_text(prompt)
            self.last_response = response_text
            
            # The response from the LLM is often enclosed in markdown backticks.
            # This cleans the response before parsing.
            clean_response = response_text.strip().replace("```json", "").replace("```", "")
            
            analysis_result = json.loads(clean_response)
            logging.info("Successfully analyzed job description.")
            return analysis_result
            
        except json.JSONDecodeError:
            logging.error("Critical Error: Failed to decode JSON from the LLM response.")
            # A fallback mechanism is crucial for production stability.
            return {}
        except Exception as e:
            logging.error(f"An unexpected error occurred during job analysis: {e}")
            return {}
import json
import logging
import re
from typing import Dict, Any
import requests

# The GeminiClient would be a wrapper around the Google Gemini API SDK.
# from core.gemini_client import GeminiClient

class JobProspectorAgent:
    """
    A unified agent that scrapes a job posting URL and performs a detailed
    analysis of its content in a single, streamlined step.

    This agent fetches the raw HTML from a URL and uses a powerful prompt to
    extract a structured JSON object containing the job title, company,
    required skills, and responsibilities, optimized for ATS matching.
    """

    def __init__(self, gemini_client: Any):
        """
        Initializes the agent with a client to communicate with the Gemini API.
        
        Args:
            gemini_client: An instance of a client configured to handle Gemini API calls.
        """
        self.llm = gemini_client
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    def _fetch_html(self, url: str) -> str:
        """
        Fetches the HTML content from a given URL.
        """
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            resp = requests.get(url, timeout=15, headers=headers)
            resp.raise_for_status()
            return resp.text
        except requests.exceptions.RequestException as e:
            logging.error(f"Error fetching URL '{url}': {e}")
            return ""

    def _create_unified_analysis_prompt(self, html_content: str) -> str:
        """
        Constructs a unified prompt for the LLM to scrape and analyze a job posting
        from raw HTML into the final desired JSON structure.
        """
        return f"""
        Analyze the following raw HTML content from a job posting web page with the
        expertise of an ATS (Applicant Tracking System) analyst. Your task is to extract
        key information and structure it as a single, valid JSON object.
        The output must only be the JSON object, with no additional text or explanations.

        **Extraction Rules:**
        1.  `job_title`: Find and extract the exact job title.
        2.  `company_name`: Find and extract the hiring company's name.
        3.  `required_skills`: From the job description text, create a comprehensive list
            of all technical and soft skills.
            -   If an acronym is present, you must include both the full term and the
                acronym (e.g., "Natural Language Processing", "NLP").
            -   This list must be a flat array of strings.
        4.  `responsibilities`: From the job description text, list the core duties,
            qualifications, and requirements mentioned.

        **Raw HTML Content:**
        ---
        {html_content}
        ---

        **JSON Output:**
        """

    def _clean_response_to_json(self, response_text: str) -> Dict[str, Any]:
        """
        Cleans the LLM's response to isolate and parse the JSON object.
        Handles responses that might be enclosed in markdown code blocks.
        """
        # Search for a JSON object within the text, potentially enclosed in ```json ... ```
        match = re.search(r"\{[\s\S]*\}", response_text)
        if not match:
            logging.error("Could not find a JSON object in the LLM response.")
            raise json.JSONDecodeError("No JSON object found", response_text, 0)
        
        return json.loads(match.group(0))

    def run(self, url: str) -> Dict[str, Any]:
        """
        Executes the full, integrated pipeline from URL to detailed job analysis.

        Args:
            url: The URL of the job posting to analyze.

        Returns:
            A dictionary with the detailed, ATS-optimized job analysis. 
            Returns an empty dictionary on failure.
        """
        html_content = self._fetch_html(url)
        if not html_content:
            return {}

        # Create the single prompt for scraping and analysis
        analysis_prompt = self._create_unified_analysis_prompt(html_content)
        
        try:
            # Make a single call to the LLM
            analysis_response_text = self.llm.generate_text(analysis_prompt)
            if not analysis_response_text:
                logging.error("Received an empty response from the LLM during analysis.")
                return {}

            # Clean and parse the final result
            analysis_result = self._clean_response_to_json(analysis_response_text)
            
            logging.info("Successfully scraped and analyzed job description from URL.")
            return analysis_result

        except (json.JSONDecodeError, Exception) as e:
            logging.error(f"An error occurred during the analysis phase: {e}")
            return {}

# --- Example Usage ---
# if __name__ == '__main__':
#     # This is a mock GeminiClient for demonstration purposes.
#     # It simulates a single API call that performs both scraping and analysis.
#     class MockGeminiClient:
#         def generate_text(self, prompt: str) -> str:
#             # This simulation now responds to the new unified prompt
#             if "Raw HTML Content" in prompt:
#                 logging.info("Simulating unified analysis API call...")
#                 return """
#                 ```json
#                 {
#                   "job_title": "Senior AI Engineer (NLP)",
#                   "company_name": "FutureTech Solutions",
#                   "required_skills": [
#                     "Natural Language Processing",
#                     "NLP",
#                     "Python",
#                     "PyTorch",
#                     "TensorFlow",
#                     "Deep Learning",
#                     "Large Language Models",
#                     "LLMs",
#                     "Text Classification",
#                     "Sentiment Analysis",
#                     "Named Entity Recognition"
#                   ],
#                   "responsibilities": [
#                     "Developing and deploying advanced NLP models",
#                     "Text classification, sentiment analysis, and named entity recognition",
#                     "Must have 5+ years of experience with Python",
#                     "Proficiency in deep learning frameworks like PyTorch and TensorFlow is required",
#                     "Experience with Large Language Models (LLMs) is a huge plus"
#                   ]
#                 }
#                 ```
#                 """
#             return ""

#     # Initialize the agent with the mock client
#     mock_gemini_client = MockGeminiClient()
#     agent = JobProspectorAgent(gemini_client=mock_gemini_client)

#     # The only input the user needs to provide is the URL
#     job_posting_url = "http://example.com/job/senior-ai-engineer" 
    
#     # Run the complete end-to-end process
#     final_job_analysis = agent.run(job_posting_url)

#     # Print the final, detailed analysis
#     if final_job_analysis:
#         print(json.dumps(final_job_analysis, indent=2))
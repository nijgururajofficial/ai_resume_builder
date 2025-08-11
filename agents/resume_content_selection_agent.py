import json
import logging
from typing import Dict

# from core.gemini_client import GeminiClient

class ResumeContentSelectionAgent:
    """
    Selects and tailors content from a user's profile to align with the
    requirements extracted from a job description.

    This agent uses the Gemini LLM to perform a creative and strategic task:
    rewriting and prioritizing the user's experience to maximize its relevance
    and impact for a specific job application, focusing on keyword alignment
    and quantifiable achievements.
    """

    def __init__(self, gemini_client):
        """
        Initializes the agent with a client to communicate with the Gemini API.
        
        Args:
            gemini_client: An instance of a client for Gemini API calls.
        """
        self.llm = gemini_client
        logging.basicConfig(level=logging.INFO)

    def _create_prompt(self, user_profile: Dict, job_analysis: Dict) -> str:
        """
        Constructs a detailed prompt that provides the LLM with context (profile, job needs)
        and strict instructions for generating tailored resume content.
        """
        # Serialize the structured data to be included in the prompt.
        user_profile_str = json.dumps(user_profile, indent=2)
        job_analysis_str = json.dumps(job_analysis, indent=2)

        return f"""
        You are an expert career coach and resume writer crafting a resume for a high-stakes job application.
        Your goal is to create highly tailored resume content that will score exceptionally well with ATS systems
        like Taleo and Workday by aligning a User Profile with a specific Job Analysis.

        **Input Data:**

        1.  **User Profile:**
            ---
            {user_profile_str}
            ---

        2.  **Job Analysis:**
            ---
            {job_analysis_str}
            ---

        **Your Task:**
        Generate a JSON object containing the tailored resume content based on the following rules:

        1.  `headline`: Create a compelling headline that includes the exact `job_title` from the Job Analysis.
        2.  `tailored_experience`: Select the most relevant work experience. For each responsibility, rewrite it to naturally incorporate keywords from the `required_skills` and `responsibilities` in the Job Analysis. Emphasize quantifiable results (e.g., "reduced costs by 30%").
        3.  `tailored_projects`: Select only the projects whose technologies and descriptions align with the job's requirements.
        4.  `tailored_skills`: From the User Profile's skills, create a new skills object that only includes skills relevant to the `required_skills` in the Job Analysis. Maintain the original skill categories.

        The output must be a single, valid JSON object and nothing else.

        **Tailored Content JSON Output:**
        """

    def run(self, user_profile: Dict, job_analysis: Dict) -> Dict:
        """
        Executes the content selection and tailoring process.

        Args:
            user_profile: The user's complete professional data as a dictionary.
            job_analysis: The structured analysis of the target job description.

        Returns:
            A dictionary containing the tailored resume content. Returns an empty dict on failure.
        """
        prompt = self._create_prompt(user_profile, job_analysis)

        try:
            response_text = self.llm.generate_text(prompt)
            clean_response = response_text.strip().replace("```json", "").replace("```", "")
            
            tailored_content = json.loads(clean_response)
            logging.info("Successfully generated tailored resume content.")
            return tailored_content

        except json.JSONDecodeError:
            logging.error("Critical Error: Failed to decode JSON from the LLM response during content selection.")
            return {}
        except Exception as e:
            logging.error(f"An unexpected error occurred during content selection: {e}")
            return {}
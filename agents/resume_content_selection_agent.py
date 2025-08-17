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
        self.last_response = ""
        self.last_prompt = ""
        logging.basicConfig(level=logging.INFO)

    def _create_prompt(self, user_profile: Dict, job_analysis: Dict) -> str:
        """
        Constructs a detailed prompt that provides the LLM with context (profile, job needs)
        and strict instructions for generating tailored resume content.
        """
        user_profile_str = json.dumps(user_profile, indent=2)
        job_analysis_str = json.dumps(job_analysis, indent=2)

        return f"""
        You are an expert career coach and resume writer crafting a resume for a high-stakes job application.
        Your goal is to create highly tailored resume content that will score exceptionally well with ATS systems
        and impress hiring managers by aligning a User Profile with a specific Job Analysis.

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
        Generate a JSON object containing the tailored resume content based on the following strict rules. Adhere to all constraints precisely.

        **Rules:**

        1.  **`headline`**: Create a compelling, professional headline that includes the exact `job_title` from the Job Analysis. Do not add any other text.

        2.  **`tailored_experience`**: 
            - Select the most relevant work experiences from the User Profile that align with the Job Analysis.
            - For each job, rewrite the responsibilities to create a list of high-impact bullet points.
            - **Constraint**: Each job entry must have a **maximum of 5 bullet points**.
            - **Quantification**: Rewrite every bullet point to start with a strong action verb and include quantifiable metrics wherever possible to demonstrate impact (e.g., "Optimized database queries, reducing latency by 40%," or "Led a team of 5 engineers to deliver the project 2 weeks ahead of schedule.").
            - **Keyword Integration**: Naturally incorporate keywords from the `required_skills` and `responsibilities` in the Job Analysis.

        3.  **`tailored_projects`**: 
            - Select only the projects whose technologies and descriptions strongly align with the job's requirements.
            - For each project, rewrite the description into a concise list of achievements.
            - **Constraint**: Each project must have a **maximum of 4 bullet points**. The project **name** must be rewritten to be concise and professional, ideally **under 30 characters**.
            - **Quantification**: As with experience, quantify the outcomes of the project work (e.g., "Achieved 95% test coverage using Pytest," or "Handled 1,000 concurrent users with minimal performance degradation.").

        4.  **`tailored_skills`**: 
            - **CRITICAL:** You must create a new skills object by filtering the User Profile's skills.
            - First, carefully review the `required_skills` list in the Job Analysis.
            - Then, for each skill in the User Profile, you must decide whether to keep or discard it.
            - A skill should only be kept if it **directly matches or is a very close equivalent** to a skill listed in the `required_skills`.
            - For example, if the job requires "Kubernetes," the user's "Docker" skill is relevant and should be kept. If the job requires "Python," the user's "Python" skill should be kept. If the job does not mention anything about data visualization, the user's "Power BI" skill **must be discarded**.
            - Maintain the original skill categories from the User Profile. If a category becomes empty after filtering, omit the entire category from the output.

        5.  **`education`**:
            - Copy the `education` section from the User Profile into the output **verbatim**. Do not change, rewrite, or tailor this section in any way. It must be carried over exactly as it appears in the input.

        The output must be a single, valid JSON object and nothing else. Do not add explanations or surrounding text.

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
        self.last_prompt = prompt

        try:
            response_text = self.llm.generate_text(prompt)
            self.last_response = response_text
            # Clean up potential markdown formatting from the LLM response
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
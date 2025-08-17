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
        You are an expert career coach and resume writer. Your task is to generate highly tailored resume content designed to fit on a single, high-impact page. The content must be professional, concise, and action-oriented to impress hiring managers and score exceptionally well with ATS systems.

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

        1.  **`professional_title`**: Craft a professional title, not a conversational headline. It should prominently feature the `job_title` from the Job Analysis and may optionally include a key specialization if highly relevant (e.g., "Senior Software Engineer | Cloud Infrastructure").

        2.  **`tailored_experience`**:
            - Select the most relevant work experiences from the User Profile that align with the Job Analysis.
            - **Framework**: Rewrite each responsibility using the STAR method (Situation, Task, Action, Result), focusing heavily on the **Action** (what you did) and the **Result** (the outcome).
            - **Constraint**: Each job entry must have a **maximum of 5 bullet points**. Prioritize the most impactful achievements. **must be between 110 and 120 characters strictly**.
            - **Quantification**: Every bullet point must start with a strong action verb and include a quantifiable metric to demonstrate impact (e.g., "Reduced server costs by 30%," "Increased user engagement by 15%").
            - **Conciseness**: Each bullet point **must be a single, concise line of text**.
            - **Keyword Integration**: Naturally incorporate keywords from the `required_skills` and `responsibilities` in the Job Analysis.

        3.  **`tailored_projects`**:
            - Select only projects whose technologies and descriptions strongly align with the job's requirements.
            - **Focus**: Rewrite descriptions to highlight the project's **outcome** and the **problem it solved**.
            - **Constraint**: Each project must have a **maximum of 4 bullet points**. **must be between 110 and 120 characters strictly**.
            - **Project Naming**: The project `name` must be rewritten to be concise and professional, ideally **under 25 characters**.
            - **Quantification**: As with experience, quantify outcomes (e.g., "Achieved 95% test coverage," "Processed 10,000 records per second").
            - **Conciseness**: Each bullet point **must be a single, concise line of text**.

        4.  **`tailored_skills`**:
            - **CRITICAL**: Create a new skills object by filtering the User Profile's skills against the `required_skills` from the Job Analysis.
            - A skill should only be kept if it **directly matches or is a very close equivalent** to a required skill. For example, if the job requires "Kubernetes," the user's "Docker" is relevant and should be kept. If the job does not mention data visualization, "Power BI" **must be discarded**.
            - Maintain the original skill categories. Omit any category that becomes empty after filtering.

        5.  **`education`**:
            - Copy the `education` section from the User Profile into the output **verbatim**. Do not alter this section.

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
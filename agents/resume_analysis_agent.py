import os
import sys
import json
import re
import logging
import threading
import time
import traceback
from typing import Dict, Any
from dotenv import load_dotenv

class ResumeAnalysisAgent:
    """
    Analyzes text extracted from a resume using a Gemini LLM to produce structured JSON data.

    This agent's primary function is to convert the unstructured text of a resume
    into a machine-readable JSON format, identifying key sections like contact information,
    work experience, education, and skills.
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
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    def _create_prompt(self, resume_text: str) -> str:
        """
        Constructs a precise, zero-shot prompt for the LLM, instructing it to
        act as an expert HR analyst and return a structured JSON object.
        """
        self.last_prompt = f"""
        You are an expert HR analyst specializing in parsing resumes. Your task is to analyze the
        following resume text and convert it into a structured, valid JSON object.
        The output must ONLY be the JSON object, with no additional text, explanations, or markdown.

        **Required JSON Structure:**
        {{
            "name": "Full Name",
            "contact": {{
                "phone": "Phone number",
                "github": "GitHub URL",
                "linkedin": "LinkedIn URL", 
                "email": "Email address"
            }},
            "skills": {{
                "Languages": ["skill1", "skill2"],
                "Data Engineering": ["skill1", "skill2"],
                "Machine Learning/AI": ["skill1", "skill2"],
                "Cloud Platforms": ["skill1", "skill2"],
                "Tools": ["skill1", "skill2"],
                "Certifications": ["cert1", "cert2"]
            }},
            "experience": [
                {{
                    "title": "Job Title",
                    "company": "Company Name",
                    "location": "City, State",
                    "dates": "Start Date - End Date",
                    "responsibilities": [
                        "Responsibility 1",
                        "Responsibility 2"
                    ]
                }}
            ],
            "projects": [
                {{
                    "name": "Project Name",
                    "technologies": "Tech1, Tech2, Tech3",
                    "description": [
                        "Description point 1",
                        "Description point 2"
                    ]
                }}
            ],
            "education": [
                {{
                    "degree": "Degree Type, Field of Study",
                    "institution": "Institution Name, Location",
                    "dates": "Start Date - End Date",
                    "coursework": "Relevant coursework (optional)"
                }}
            ]
        }}

        **Extraction Rules:**
        1. `name`: Extract the full name from the resume
        2. `contact`: Extract phone, email, GitHub URL, and LinkedIn URL
        3. `skills`: Categorize skills into the exact categories shown above:
           - Languages: Programming languages
           - Data Engineering: Data processing and ETL tools
           - Machine Learning/AI: ML frameworks, AI tools, and related technologies
           - Cloud Platforms: AWS, Azure, Google Cloud, etc.
           - Tools: Development tools, version control, databases, etc.
           - Certifications: Any professional certifications
        4. `experience`: Extract work experience with exact field names:
           - `title`: Job title
           - `company`: Company name
           - `location`: City, State format
           - `dates`: Date range
           - `responsibilities`: Array of responsibility descriptions
        5. `projects`: Extract projects with:
           - `name`: Project name
           - `technologies`: Comma-separated string of technologies used
           - `description`: Array of project description points
        6. `education`: Extract education with:
           - `degree`: Degree type and field of study
           - `institution`: School name and location
           - `dates`: Date range
           - `coursework`: Relevant coursework (optional field)

        **Resume Text:**
        ---
        {resume_text}
        ---

        **JSON Output:**
        """
        return self.last_prompt

    def _parse_ai_json(self, ai_text: str) -> Dict[str, Any]:
        """
        Robustly parses a string to extract a JSON object, even if it's embedded in markdown.
        """
        # Use regex to find the JSON block, which is more reliable
        match = re.search(r"\{[\s\S]*\}", ai_text)
        if match:
            json_str = match.group(0)
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                logging.error("Failed to decode JSON even after regex extraction.")
                return {}
        return {}

    def run(self, resume_text: str) -> Dict[str, Any]:
        """
        Executes the analysis pipeline for the given resume text.

        This method serves as the primary entry point or "node" for the agent.

        Args:
            resume_text: The raw text extracted from a resume PDF.

        Returns:
            A dictionary with the extracted resume details. Returns an empty dict on failure.
        """
        if not resume_text or not resume_text.strip():
            logging.warning("Resume text is empty. Aborting analysis.")
            return {}

        prompt = self._create_prompt(resume_text)

        try:
            response_text = self.llm.generate_text(prompt)
            self.last_response = response_text

            if not response_text:
                logging.error("Received an empty response from the LLM.")
                return {}

            analysis_result = self._parse_ai_json(response_text)
            if analysis_result:
                logging.info("Successfully extracted and parsed resume details.")
            else:
                logging.error("Could not parse a valid JSON object from the LLM response.")
                logging.debug(f"Raw response was: {self.last_response}")

            return analysis_result

        except Exception as e:
            logging.error(f"An unexpected error occurred during resume analysis: {e}")
            return {}

def loading_animation(stop_event: threading.Event):
    """Displays a simple loading animation in the console."""
    animation = ['   ', '.  ', '.. ', '...']
    idx = 0
    while not stop_event.is_set():
        print(f'\r🤖 Analyzing Resume{animation[idx]}', end='', flush=True)
        idx = (idx + 1) % len(animation)
        time.sleep(0.5)
    print('\r🤖 Analysis complete!          ')

# if __name__ == "__main__":
#     load_dotenv()

#     if len(sys.argv) < 2:
#         print("Usage: python your_script_name.py <path_to_pdf.pdf>")
#         sys.exit(1)

#     pdf_path = sys.argv[1]
#     print(f"📄 Extracting text from: {pdf_path}")
#     resume_text = extract_pdf_text(pdf_path)

#     if not resume_text:
#         print("❌ Text extraction failed. Exiting.")
#         sys.exit(1)
#     print("✅ Text extraction complete.")

#     try:
#         # Initialize the client and agent
#         gemini_api_key = os.getenv("GOOGLE_API_KEY")
#         client = GeminiClient(api_key=gemini_api_key)
#         resume_agent = ResumeAnalysisAgent(gemini_client=client)

#         # Start loading animation in a separate thread
#         stop_event = threading.Event()
#         animation_thread = threading.Thread(target=loading_animation, args=(stop_event,))
#         animation_thread.start()

#         # Run the agent's main logic
#         parsed_resume = resume_agent.run(resume_text=resume_text)

#         # Stop the animation
#         stop_event.set()
#         animation_thread.join()

#         if parsed_resume:
#             print("\n✅ Resume Parsed Successfully:\n")
#             print(json.dumps(parsed_resume, indent=2, ensure_ascii=False))
#             # Save parsed JSON to file
#             with open("parsed_resume.json", "w", encoding="utf-8") as f:
#                 json.dump(parsed_resume, f, indent=2, ensure_ascii=False)
#             print("\n✅ Saved summary to parsed_resume.json")
#         else:
#             print("\n❌ Agent failed to parse the resume.")

#     except (ValueError, RuntimeError) as e:
#         logging.error(f"❌ Initialization or runtime error: {e}")
#     except Exception:
#         print("\nAn unexpected error occurred:")
#         traceback.print_exc()
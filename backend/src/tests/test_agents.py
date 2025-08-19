import unittest
import json
from unittest.mock import MagicMock

# Import the agents to be tested
from agents.job_description_analysis_agent import JobDescriptionAnalysisAgent
from agents.resume_content_selection_agent import ResumeContentSelectionAgent
from agents.markdown_formatting_agent import MarkdownFormattingAgent

class TestResumeAgents(unittest.TestCase):
    """Unit tests for the AI Resume Builder agents."""

    @classmethod
    def setUpClass(cls):
        """Set up mock data that will be used across all tests."""
        cls.mock_user_profile = {
            "name": "Nijgururaj Ashtagi",
            "contact": {"email": "test@example.com", "linkedin": "linkedin.com/in/test"},
            "experience": [{
                "title": "AI Engineer", "company": "S3CURA", "dates": "2025-Present",
                "responsibilities": ["Architected a system using AWS Lambda and DynamoDB."]
            }],
            "skills": {"Languages": ["Python", "SQL"], "Cloud": ["AWS"]}
        }
        
        cls.mock_job_description = "We are hiring an AI Engineer at Google. Must know Python, AWS, and Docker."

    def test_job_description_analysis_agent(self):
        """
        Tests that the analysis agent correctly parses a job description
        based on a mocked LLM response.
        """
        # 1. Setup: Mock the Gemini client and its response
        mock_gemini_client = MagicMock()
        expected_response = {
            "job_title": "AI Engineer",
            "company_name": "Google",
            "required_skills": ["Python", "AWS", "Docker"]
        }
        mock_gemini_client.generate_text.return_value = json.dumps(expected_response)

        # 2. Execution: Run the agent
        agent = JobDescriptionAnalysisAgent(mock_gemini_client)
        result = agent.run(self.mock_job_description)

        # 3. Assertion: Verify the output
        self.assertIsNotNone(result)
        self.assertEqual(result["job_title"], "AI Engineer")
        self.assertEqual(result["company_name"], "Google")
        self.assertIn("Python", result["required_skills"])

    def test_resume_content_selection_agent(self):
        """
        Tests that the selection agent correctly tailors user content
        based on the job analysis from a mocked LLM response.
        """
        # 1. Setup
        mock_gemini_client = MagicMock()
        job_analysis = {"job_title": "AI Engineer", "required_skills": ["Python", "AWS"]}
        expected_response = {
            "headline": "AI Engineer | Cloud & Python Specialist",
            "tailored_experience": [{
                "title": "AI Engineer", "responsibilities": ["Architected a system using AWS Lambda..."]
            }],
            "tailored_skills": {"Languages": ["Python"], "Cloud": ["AWS"]}
        }
        mock_gemini_client.generate_text.return_value = json.dumps(expected_response)

        # 2. Execution
        agent = ResumeContentSelectionAgent(mock_gemini_client)
        result = agent.run(self.mock_user_profile, job_analysis)

        # 3. Assertion
        self.assertIn("AI Engineer", result["headline"])
        self.assertEqual(len(result["tailored_experience"]), 1)
        self.assertIn("Python", result["tailored_skills"]["Languages"])
        self.assertIn("AWS", result["tailored_skills"]["Cloud"])

    def test_markdown_formatting_agent(self):
        """
        Tests the deterministic formatting agent to ensure it produces
        ATS-compliant Markdown without an LLM.
        """
        # 1. Setup: This agent needs no mock client.
        tailored_content = {
            "headline": "AI Engineer",
            "tailored_experience": [{
                "title": "AI Engineer", "company": "S3CURA", "location": "Chicago, IL", "dates": "2025 – Present",
                "responsibilities": ["Used AWS to build a thing."]
            }],
            "tailored_skills": {"Languages": ["Python"]}
        }

        # 2. Execution
        agent = MarkdownFormattingAgent()
        result = agent.run(self.mock_user_profile, tailored_content)

        # 3. Assertion
        self.assertIn("# Nijgururaj Ashtagi", result)
        self.assertIn("### AI Engineer", result)
        self.assertIn("linkedin.com/in/test | test@example.com", result)
        self.assertIn("## Work Experience", result)
        self.assertIn("**AI Engineer** | S3CURA", result)
        self.assertIn("- Used AWS to build a thing.", result)
        self.assertIn("## Skills", result)
        self.assertIn("**Languages**: Python", result)
        self.assertIsInstance(result, str)

if __name__ == '__main__':
    unittest.main()
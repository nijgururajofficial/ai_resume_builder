import os
import json
import logging
import argparse
from datetime import datetime
from dotenv import load_dotenv
from utils import extract_pdf_text # We no longer need load_json_file

from core.langgraph_orchestrator import LangGraphOrchestrator
from core.pdf_docx_generator import PdfDocxGenerator
from core.gemini_client import GeminiClient 
from core.response_logger import ResponseLogger

# --- Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
load_dotenv()


def main():
    """
    Main function to run the AI Resume Builder pipeline.
    """
    parser = argparse.ArgumentParser(description="AI Resume Builder CLI")
    parser.add_argument(
        "--resume",
        type=str,
        default="data/resume.pdf",
        help="Path to the user's resume PDF file."
    )
    parser.add_argument(
        "--job-desc-url", # --- CHANGED: Renamed for clarity
        type=str,
        required=True,
        # default="https://paypal.eightfold.ai/careers?domain=paypal.com&Codes=W-LINKEDIN&query=R0129930&start=0&location=Chicago%2C+Illinois%2C+US&pid=274908696559&sort_by=timestamp",
        help="URL of the job description."
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="output",
        help="Directory to save the generated resume files."
    )
    parser.add_argument(
        "--log-responses",
        action="store_true",
        help="Enable detailed response logging for all agents."
    )
    args = parser.parse_args()

    # --- 1. Load Inputs ---
    # --- CHANGED: Simplified input loading process ---
    logging.info("Loading inputs...")
    
    resume_text = extract_pdf_text(args.resume)
    if not resume_text:
        logging.error(f"Could not extract text from resume PDF: {args.resume}")
        return

    # The job description is now just the URL string
    job_description_url = args.job_desc_url
    logging.info(f"Resume loaded. Job URL: {job_description_url}")

    # --- 2. Initialize Services ---
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        logging.error("GEMINI_API_KEY environment variable not set.")
        return

    gemini_client = GeminiClient(api_key=api_key)
    orchestrator = LangGraphOrchestrator(gemini_client)
    
    response_logger = None
    if args.log_responses:
        response_logger = ResponseLogger(output_dir=args.output_dir)
        logging.info("Response logging enabled.")

    # --- 3. Run Orchestration Pipeline ---
    logging.info("Starting resume generation pipeline...")
    # --- CHANGED: Call the orchestrator with the correct inputs ---
    final_content = orchestrator.run(
        resume_txt=resume_text, 
        job_description_url=job_description_url
    )

    if not final_content or 'markdown_resume' not in final_content or not final_content['markdown_resume']:
        logging.error("Pipeline failed to generate resume content. Exiting.")
        # Log the partial failure if possible
        if response_logger and args.log_responses and final_content:
            response_logger.save_workflow_responses(final_content, "FAILED_")
        return

    # --- 4. Log Agent Responses (if enabled) ---
    # This section remains the same and should work correctly.
    if response_logger and args.log_responses:
        try:
            response_file = response_logger.save_workflow_responses(final_content)
            logging.info(f"Complete workflow responses saved to: {response_file}")
            report_file = response_logger.generate_performance_report(final_content)
            logging.info(f"Performance report generated: {report_file}")
            analysis = response_logger.analyze_agent_responses(final_content)
            logging.info(f"Agent Analysis: {analysis['successful_agents']}/{analysis['total_agents']} agents succeeded")
            if analysis['errors']:
                logging.warning(f"Agent errors encountered: {analysis['errors']}")
        except Exception as e:
            logging.error(f"Error during response logging: {e}")

    # --- 5. Generate and Save Final Documents ---
    # --- CHANGED: Extract user_name and company_name from the final_content dictionary ---
    markdown_resume = final_content['markdown_resume']
    
    # Safely get company name from the job_analysis part of the state
    company_name = final_content.get('job_analysis', {}).get('company_name', 'Company').replace(' ', '')
    
    # Safely get user name from the user_profile part of the state
    user_name = final_content.get('user_profile', {}).get('name', 'User').replace(' ', '')

    os.makedirs(args.output_dir, exist_ok=True)

    date_str = datetime.now().strftime("%d%m")
    base_filename = f"{user_name}-{company_name}-{date_str}"

    logging.info(f"Generating DOCX and PDF files for base name: {base_filename}")
    generator = PdfDocxGenerator(markdown_content=markdown_resume)

    docx_path = os.path.join(args.output_dir, f"{base_filename}.docx")
    generator.to_docx(docx_path)

    pdf_path = os.path.join(args.output_dir, f"{base_filename}.pdf")
    generator.to_pdf(pdf_path)

    logging.info(f"Successfully created resumes at {docx_path} and {pdf_path}")
    
    # --- 6. Display Summary (if response logging enabled) ---
    # This section remains the same.
    if response_logger and args.log_responses:
        try:
            history = response_logger.get_agent_response_history(limit=3)
            if history:
                logging.info(f"Recent response history: {len(history)} files available")
                for item in history:
                    logging.info(f"  - {item['_filename']}")
        except Exception as e:
            logging.error(f"Error retrieving response history: {e}")

if __name__ == "__main__":
    main()
import os
import json
import logging
import argparse
from datetime import datetime
from dotenv import load_dotenv

from core.langgraph_orchestrator import LangGraphOrchestrator
from core.pdf_docx_generator import PdfDocxGenerator
from core.gemini_client import GeminiClient 
from core.response_logger import ResponseLogger

# --- Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
load_dotenv()

def load_json_file(file_path: str):
    """Safely loads a JSON file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        logging.error(f"File not found: {file_path}")
        return None
    except json.JSONDecodeError:
        logging.error(f"Error decoding JSON from {file_path}")
        return None
    except UnicodeDecodeError:
        logging.error(f"Encoding error reading file: {file_path}. Please ensure the file is saved with UTF-8 encoding.")
        return None

def main():
    """
    Main function to run the AI Resume Builder pipeline.
    """
    parser = argparse.ArgumentParser(description="AI Resume Builder CLI")
    parser.add_argument(
        "--profile",
        type=str,
        default="data/user_profile.json",
        help="Path to the user's profile JSON file."
    )
    parser.add_argument(
        "--job-desc",
        type=str,
        required=True,
        default="data/job_description.txt",
        help="Path to a text file containing the job description."
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
    logging.info("Loading user profile and job description...")
    user_profile = load_json_file(args.profile)
    if not user_profile:
        return # Exit if profile loading fails

    try:
        with open(args.job_desc, 'r', encoding='utf-8') as f:
            job_description = f.read()
    except FileNotFoundError:
        logging.error(f"Job description file not found: {args.job_desc}")
        return
    except UnicodeDecodeError:
        logging.error(f"Encoding error reading job description file: {args.job_desc}. Please ensure the file is saved with UTF-8 encoding.")
        return

    # --- 2. Initialize Services ---
    # The API key should be loaded from environment variables for security
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        logging.error("GEMINI_API_KEY environment variable not set.")
        return

    gemini_client = GeminiClient(api_key=api_key)
    orchestrator = LangGraphOrchestrator(gemini_client)
    
    # Initialize response logger if enabled
    response_logger = None
    if args.log_responses:
        response_logger = ResponseLogger(output_dir=args.output_dir)
        logging.info("Response logging enabled. Agent responses will be saved and analyzed.")

    # --- 3. Run Orchestration Pipeline ---
    logging.info("Starting resume generation pipeline...")
    # The orchestrator runs the agents and returns the final tailored content and analysis
    final_content = orchestrator.run(user_profile, job_description)

    if not final_content or 'markdown_resume' not in final_content:
        logging.error("Pipeline failed to generate resume content. Exiting.")
        return

    # --- 4. Log Agent Responses (if enabled) ---
    if response_logger and args.log_responses:
        try:
            # Save complete workflow responses
            response_file = response_logger.save_workflow_responses(final_content)
            logging.info(f"Complete workflow responses saved to: {response_file}")
            
            # Generate performance report
            report_file = response_logger.generate_performance_report(final_content)
            logging.info(f"Performance report generated: {report_file}")
            
            # Analyze agent responses
            analysis = response_logger.analyze_agent_responses(final_content)
            logging.info(f"Agent Analysis: {analysis['successful_agents']}/{analysis['total_agents']} agents succeeded")
            
            if analysis['errors']:
                logging.warning(f"Agent errors encountered: {analysis['errors']}")
                
        except Exception as e:
            logging.error(f"Error during response logging: {e}")

    markdown_resume = final_content['markdown_resume']
    company_name = final_content.get('job_analysis', {}).get('company_name', 'Company')
    user_name = user_profile.get('name', 'User').replace(' ', '')
    
    # --- 5. Generate and Save Final Documents ---
    os.makedirs(args.output_dir, exist_ok=True)

    # Format: UserName-CompanyName-DDMM
    date_str = datetime.now().strftime("%d%m")
    base_filename = f"{user_name}-{company_name}-{date_str}"

    logging.info(f"Generating DOCX and PDF files for base name: {base_filename}")
    generator = PdfDocxGenerator(markdown_content=markdown_resume)

    # Generate DOCX
    docx_path = os.path.join(args.output_dir, f"{base_filename}.docx")
    generator.to_docx(docx_path)

    # Generate PDF (This runs the DOCX generation logic again internally)
    pdf_path = os.path.join(args.output_dir, f"{base_filename}.pdf")
    generator.to_pdf(pdf_path)

    logging.info(f"Successfully created resumes at {docx_path} and {pdf_path}")
    
    # --- 6. Display Summary (if response logging enabled) ---
    if response_logger and args.log_responses:
        try:
            # Show recent response history
            history = response_logger.get_agent_response_history(limit=3)
            if history:
                logging.info(f"Recent response history: {len(history)} files available")
                for item in history:
                    logging.info(f"  - {item['_filename']}")
        except Exception as e:
            logging.error(f"Error retrieving response history: {e}")

if __name__ == "__main__":
    main()
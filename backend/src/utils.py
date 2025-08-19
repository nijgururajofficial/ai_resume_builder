import logging
import json
from PyPDF2 import PdfReader

def extract_pdf_text(filepath: str) -> str:
    """Extracts text from all pages of a PDF file."""
    try:
        with open(filepath, "rb") as f:
            reader = PdfReader(f)
            full_text = "".join(page.extract_text() for page in reader.pages if page.extract_text())
        return full_text
    except FileNotFoundError:
        logging.error(f"The file was not found at path: {filepath}")
        return ""
    except Exception as e:
        logging.error(f"An error occurred while reading the PDF file: {e}")
        return ""

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
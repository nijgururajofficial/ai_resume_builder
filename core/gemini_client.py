import os
import logging
import google.genai as genai
from google.api_core import exceptions
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

class GeminiClient:
    """
    A robust client for interacting with the Google Gemini API.

    This class encapsulates API key management, model configuration, and resilient
    API calls with exponential backoff for retries. It is designed to be a
    singleton or a shared instance across the application.
    """

    def __init__(self, api_key: str, model_name: str = "gemini-1.5-pro"):
        """
        Initializes and configures the Gemini client.

        Args:
            api_key: The Google AI API key.
            model_name: The specific Gemini model to use (e.g., "gemini-1.5-pro").
        """
        if not api_key:
            raise ValueError("API key for Gemini client cannot be None or empty.")
        
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model_name)
        logging.info(f"GeminiClient initialized with model: {model_name}")

    @retry(
        wait=wait_exponential(multiplier=1, min=4, max=10),
        stop=stop_after_attempt(3),
        retry=(retry_if_exception_type(exceptions.ResourceExhausted) | retry_if_exception_type(exceptions.ServiceUnavailable)),
        before_sleep=lambda retry_state: logging.warning(f"Retrying Gemini API call... Attempt #{retry_state.attempt_number}")
    )
    def generate_text(self, prompt: str) -> str:
        """
        Generates text using the configured Gemini model with retry logic.

        Args:
            prompt: The text prompt to send to the model.

        Returns:
            The generated text from the model as a string.

        Raises:
            google.api_core.exceptions.GoogleAPICallError: If a non-retriable API error occurs.
            Exception: For other unexpected errors.
        """
        try:
            logging.info("Sending prompt to Gemini API...")
            response = self.model.generate_content(prompt)
            
            # Accessing the text safely, handling cases where the response might be empty or blocked.
            if response.text:
                return response.text
            else:
                logging.warning("Gemini API returned an empty or blocked response.")
                return ""

        except (exceptions.ResourceExhausted, exceptions.ServiceUnavailable) as e:
            logging.error(f"A retriable Gemini API error occurred: {e}")
            raise  # Re-raise to trigger tenacity's retry mechanism
        except exceptions.GoogleAPICallError as e:
            logging.error(f"A non-retriable Gemini API error occurred: {e}")
            raise
        except Exception as e:
            logging.error(f"An unexpected error occurred in GeminiClient: {e}")
            raise
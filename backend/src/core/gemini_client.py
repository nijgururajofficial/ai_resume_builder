import os
import logging
# The new SDK is imported from the top-level 'google' package
from google import genai
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type


class GeminiClient:
    """
    A robust client for interacting with the Google Gemini API using the updated Google GenAI SDK.

    This class encapsulates API key management, model configuration, and resilient
    API calls with exponential backoff for retries. It is designed to be a
    singleton or a shared instance across the application.
    """

    def __init__(self, api_key: str, model_name: str = "gemini-2.5-flash"):
        """
        Initializes and configures the Gemini client with the new SDK.

        Args:
            api_key: The Google AI API key.
            model_name: The specific Gemini model to use (e.g., "gemini-2.5-pro").
        """
        if not api_key:
            raise ValueError("API key for Gemini client cannot be None or empty.")
        
        # The new SDK uses a central client object for authentication and API access.
        # It can also automatically use the GEMINI_API_KEY environment variable if set.
        self.client = genai.Client(api_key=api_key)
        self.model_name = model_name
        logging.info(f"GeminiClient initialized with model: {self.model_name}")

    @retry(
        wait=wait_exponential(multiplier=1, min=4, max=10),
        stop=stop_after_attempt(3),
        retry=(retry_if_exception_type(Exception)),
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
            # The API call now goes through the client.models service.
            # The model name and prompt (contents) are passed as arguments.
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt
            )
            
            # Accessing the response text remains the same.
            if response.text:
                return response.text
            else:
                logging.warning("Gemini API returned an empty or blocked response.")
                return ""

        except Exception as e:
            logging.error(f"An error occurred in GeminiClient: {e}")
            raise

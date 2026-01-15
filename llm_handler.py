"""
OpenAI API handler for generating email responses.
"""
import logging
from typing import Optional
from openai import OpenAI, OpenAIError, RateLimitError, APITimeoutError

from config import Config

logger = logging.getLogger(__name__)

PROMPT_TEMPLATE = """You are an email assistant helping to craft professional email responses.

Original Email:
From: {sender}
Subject: {subject}
Body: {email_body}

Generate a professional, friendly response that:
- Addresses the key points in the email
- Matches the tone of the sender
- Is concise (2-3 paragraphs maximum)
- Ends with appropriate sign-off

Response:"""

class LLMHandler:
    """Handles OpenAI API operations for email response generation."""
    
    def __init__(self):
        """Initialize OpenAI client."""
        try:
            self.client = OpenAI(
                api_key=Config.OPENAI_API_KEY,
                organization=Config.OPENAI_ORG_ID
            )
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI client: {e}")
            raise

    def generate_response(self, email_data: dict, user_email: Optional[str] = None) -> str:
        """
        Generate email response using OpenAI.
        
        Args:
           email_data: Dictionary containing email details (sender, subject, body, date)
           user_email: The authenticated user's email address (for perspective)
        
        Returns:
            Suggested response text
        """
        # Build email context
        email_context = f"""
Email from: {email_data.get('sender', 'Unknown')}
Subject: {email_data.get('subject', 'No Subject')}
Date: {email_data.get('date', 'Unknown')}

Email content:
{email_data.get('body', '')}
"""

        # Build system message with proper perspective
        if user_email:
            system_message = f"""You are an AI email assistant.

The user ({user_email}) received this email from {email_data.get('sender')}.
Generate a professional reply FROM {user_email} TO {email_data.get('sender')}.

Keep the response professional, concise, and contextually relevant to the email content.
Sign the email appropriately for the user."""
        else:
            system_message = "You are an AI email assistant generating professional email responses."

        try:
            # Call OpenAI API
            # Note: We use the configured client. If org ID logic was needed per call, it's not in this snippet.
            # But I should preserve the basic error handling.
            
            response = self.client.chat.completions.create(
                model=Config.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": email_context}
                ],
                temperature=Config.TEMPERATURE,
                max_tokens=Config.MAX_TOKENS
            )
            return response.choices[0].message.content.strip()
            
        except RateLimitError:
            logger.error("Rate limit exceeded")
            raise Exception("Rate limit exceeded. Please try again later.")
        except APITimeoutError:
            logger.error("Network timeout")
            raise Exception("Network error. Request timed out.")
        except OpenAIError as e:
            logger.error(f"OpenAI API error: {e}")
            raise Exception(f"OpenAI API error: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            raise Exception(f"An unexpected error occurred: {str(e)}")

"""
Gmail API handler for searching, reading, and sending emails.
"""
import os
import base64
import logging
from typing import List, Optional, Dict, Any, TypedDict
from datetime import datetime
from email.mime.text import MIMEText

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build, Resource
from googleapiclient.errors import HttpError
from bs4 import BeautifulSoup

from config import Config

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class EmailDict(TypedDict):
    """Type definition for email dictionary."""
    id: str
    threadId: str
    sender: str
    subject: str
    body: str
    date: str

class GmailHandler:
    """Handles Gmail API operations."""
    
    def __init__(self):
        """Initialize Gmail handler."""
        self.service: Optional[Resource] = None
        
    def authenticate(self) -> Resource:
        """
        Authenticate with Gmail API using OAuth 2.0.
        
        Returns:
            Gmail API service instance
            
        Raises:
            Exception: If authentication fails
        """
        try:
            creds = None
            
            # Load existing token
            if os.path.exists(Config.GMAIL_TOKEN_PATH):
                creds = Credentials.from_authorized_user_file(
                    Config.GMAIL_TOKEN_PATH, 
                    Config.GMAIL_SCOPES
                )
            
            # Refresh or create new credentials
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    if not os.path.exists(Config.GMAIL_CREDENTIALS_PATH):
                        raise FileNotFoundError(f"Credentials file not found at {Config.GMAIL_CREDENTIALS_PATH}")
                        
                    flow = InstalledAppFlow.from_client_secrets_file(
                        Config.GMAIL_CREDENTIALS_PATH, 
                        Config.GMAIL_SCOPES
                    )
                    creds = flow.run_local_server(port=0)
                
                # Save credentials for next run
                with open(Config.GMAIL_TOKEN_PATH, 'w') as token:
                    token.write(creds.to_json())
            
            self.service = build('gmail', 'v1', credentials=creds)
            return self.service
            
        except Exception as e:
            logger.error(f"Authentication failed: {str(e)}")
            raise Exception(f"Authentication failed: {str(e)}")
    
    def search_emails(self, subject: str, max_results: int = 10) -> tuple[list[str], int]:
        """
        Search for emails by subject.
        
        Args:
            subject: Email subject to search for
            max_results: Maximum number of results to return
            
        Returns:
            Tuple containing (list of email_ids, total_count)
            
        Raises:
            Exception: If search fails
        """
        if not self.service:
            self.authenticate()
            
        try:
            # Search in both subject and from fields
            query = f'(subject:{subject} OR from:{subject})'
            results = self.service.users().messages().list(
                userId='me',
                q=query,
                maxResults=max_results
            ).execute()
            
            messages = results.get('messages', [])
            
            if messages:
                email_ids = [msg['id'] for msg in messages]
                return email_ids, len(messages)
            return [], 0
            
        except HttpError as error:
            logger.error(f"Gmail search failed: {error}")
            raise Exception(f"Search failed: {error}")

    def get_email_preview(self, message_id: str) -> Optional[Dict[str, str]]:
        """
        Get email preview (from, subject, date) without full body.
        
        Args:
            message_id: Gmail message ID
            
        Returns:
            Dictionary with preview info or None if failed
        """
        if not self.service:
            self.authenticate()
            
        try:
            message = self.service.users().messages().get(
                userId='me', 
                id=message_id,
                format='metadata',
                metadataHeaders=['From', 'Subject', 'Date']
            ).execute()
            
            headers = message['payload']['headers']
            header_dict = {h['name']: h['value'] for h in headers}
            
            return {
                'id': message_id,
                'from': header_dict.get('From', 'Unknown'),
                'subject': header_dict.get('Subject', 'No Subject'),
                'date': header_dict.get('Date', 'Unknown Date')
            }
        except Exception as e:
            logger.error(f"Failed to get email preview: {e}")
            return None

    def get_user_email(self) -> Optional[str]:
        """Get the authenticated user's email address."""
        if not self.service:
            self.authenticate()
            
        try:
            profile = self.service.users().getProfile(userId='me').execute()
            return profile['emailAddress']
        except Exception as e:
            logger.error(f"Failed to get user email: {e}")
            return None

    def get_email_content(self, message_id: str) -> EmailDict:
        """
        Get full email content by message ID.
        
        Args:
            message_id: Gmail message ID
            
        Returns:
            Dictionary with email details
            
        Raises:
            Exception: If retrieval fails
        """
        if not self.service:
            self.authenticate()
            
        try:
            message = self.service.users().messages().get(
                userId='me', 
                id=message_id,
                format='full'
            ).execute()
            
            payload = message['payload']
            headers = {h['name']: h['value'] for h in payload['headers']}
            
            email_data: EmailDict = {
                'id': message['id'],
                'threadId': message['threadId'],
                'sender': headers.get('From', 'Unknown'),
                'subject': headers.get('Subject', 'No Subject'),
                'date': headers.get('Date', ''),
                'body': self._extract_body(payload)
            }
            
            return email_data
            
        except HttpError as error:
            logger.error(f"Failed to get email content: {error}")
            raise Exception(f"Email not found or access denied: {error}")

    def _extract_body(self, payload: Dict[str, Any]) -> str:
        """
        Extract plain text body from payload.
        
        Args:
            payload: Email payload
            
        Returns:
            Plain text body string
        """
        body = ""
        
        # Check if message has parts (multipart)
        if 'parts' in payload:
            for part in payload['parts']:
                if part['mimeType'] == 'text/plain':
                    data = part['body'].get('data', '')
                    if data:
                        body = base64.urlsafe_b64decode(data).decode('utf-8')
                        break
                elif part['mimeType'] == 'text/html' and not body:
                    # Fallback to HTML if no plain text found yet
                    data = part['body'].get('data', '')
                    if data:
                        html = base64.urlsafe_b64decode(data).decode('utf-8')
                        body = BeautifulSoup(html, 'html.parser').get_text()
        else:
            # Single part message
            data = payload['body'].get('data', '')
            if data:
                decoded = base64.urlsafe_b64decode(data).decode('utf-8')
                if payload['mimeType'] == 'text/html':
                    body = BeautifulSoup(decoded, 'html.parser').get_text()
                else:
                    body = decoded
        
        return body.strip()

    def send_reply(self, message_id: str, reply_text: str, thread_id: str) -> bool:
        """
        Send reply to an email.
        
        Args:
            message_id: Original message ID (for threading)
            reply_text: Response body
            thread_id: Thread ID
            
        Returns:
            True if sent successfully
            
        Raises:
            Exception: If send fails
        """
        if not self.service:
            self.authenticate()
            
        try:
            # Get original email headers to determine 'To' and 'Subject'
            original = self.service.users().messages().get(
                userId='me', id=message_id, format='metadata', 
                metadataHeaders=['From', 'Subject', 'Message-ID']
            ).execute()
            
            headers = {h['name']: h['value'] for h in original['payload']['headers']}
            sender = headers.get('From', '')
            subject = headers.get('Subject', '')
            original_msg_id = headers.get('Message-ID', '') # Use the actual Message-ID header if available, or the API ID
            
            if not subject.lower().startswith('re:'):
                subject = f"Re: {subject}"

            message = MIMEText(reply_text)
            message['to'] = sender
            message['subject'] = subject
            message['In-Reply-To'] = original_msg_id if original_msg_id else message_id
            message['References'] = original_msg_id if original_msg_id else message_id
            
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
            
            send_message = {
                'raw': raw_message,
                'threadId': thread_id
            }
            
            self.service.users().messages().send(
                userId='me',
                body=send_message
            ).execute()
            
            logger.info(f"Reply sent to thread {thread_id}")
            return True
            
        except HttpError as error:
            logger.error(f"Failed to send reply: {error}")
            raise Exception(f"Failed to send reply: {error}")

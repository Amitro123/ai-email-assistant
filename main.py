"""
Email Response Agent - Main CLI Interface
"""
import sys
import logging
from typing import Optional, Dict

from config import Config
from gmail_handler import GmailHandler
from llm_handler import LLMHandler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("agent.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class EmailResponseAgent:
    """Main application controller."""
    
    def __init__(self):
        """Initialize handlers."""
        self.gmail = GmailHandler()
        self.llm = LLMHandler()
        
    def run(self):
        """Run the main application loop."""
        print("\n==================================")
        print("📧 Email Response Agent")
        print("==================================")
        
        while True:
            try:
                # 1. Get Search Query
                print("\nWhat email subject or sender would you like to search for?")
                subject = input("> ").strip()
                
                if not subject:
                    print("⚠️  Subject cannot be empty. Please try again.")
                    continue
                    
                # 2. Search Gmail
                print("\n🔍 Searching Gmail...")
                email_ids, total_count = self.gmail.search_emails(subject)
                
                if not email_ids:
                    print(f"❌ No emails found with subject: '{subject}'")
                    if not self._should_continue():
                        break
                    continue
                
                # Inform user about search results
                if total_count > 1:
                    print(f"📊 Found {total_count} emails. Showing most recent.")
                    user_input = input("Would you like to see more results? (y/n): ").strip().lower()
                    if user_input == 'y':
                        print("ℹ️  Multiple email selection is not implemented yet. Continuing with most recent email.")
                else:
                    print(f"📊 Found 1 email.")
                
                # Get the first (most recent) email ID
                email_id = email_ids[0]
                
                # 3. Get Full Content
                print("📥 Fetching email content...")
                email_data = self.gmail.get_email_content(email_id)
                
                # 4. Display Email
                self._display_email(email_data)
                
                # 5. Generate Response
                print("\n🤖 Generating suggested response...")
                
                # Get user email for proper response context
                user_email = self.gmail.get_user_email()
                suggested_reply = self.llm.generate_response(email_data, user_email=user_email)
                
                # 6. User Review Loop
                while True:
                    print("\n" + "-"*50)
                    print("💡 SUGGESTED REPLY:")
                    print("-"*50)
                    print(suggested_reply)
                    print("-"*50)
                    
                    print("\nWould you like to (s)end, (m)odify, or (c)ancel?")
                    choice = input("> ").strip().lower()
                    
                    if choice in ['s', 'send']:
                        # Send
                        print("\n📤 Sending reply...")
                        if self.gmail.send_reply(
                            message_id=email_data['id'],
                            reply_text=suggested_reply,
                            thread_id=email_data['threadId']
                        ):
                            print("✅ Reply sent successfully!")
                        else:
                            print("❌ Failed to send reply.")
                        break
                        
                    elif choice in ['m', 'modify']:
                        # Modify
                        print("\n✏️  Enter your new response below (press Enter twice to finish):")
                        lines = []
                        while True:
                            line = input()
                            if not line and lines: # Stop on empty line if we have content
                                break
                            lines.append(line)
                        suggested_reply = "\n".join(lines).strip()
                        if not suggested_reply:
                             print("⚠️  Response cannot be empty.")
                             continue
                        # Loop back to show new draft and ask again
                        
                    elif choice in ['c', 'cancel']:
                        # Cancel
                        print("\n🚫 Operation cancelled.")
                        break
                        
                    else:
                        print("⚠️  Invalid choice. Please try again.")
                
                # 7. Next?
                if not self._should_continue("process another email"):
                    break
                    
            except KeyboardInterrupt:
                print("\n\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"\n❌ Error: {str(e)}")
                logger.error(f"Runtime error: {e}")
                if not self._should_continue():
                    break

    def _display_email(self, email: Dict[str, str]):
        """Display email details."""
        print("\n" + "="*50)
        print(f"📨 From:    {email['sender']}")
        print(f"📋 Subject: {email['subject']}")
        print(f"📅 Date:    {email['date']}")
        print("="*50)
        
        body_preview = email.get('body', '')
        # Truncate if excessively long for display
        if len(body_preview) > 2000:
            body_preview = body_preview[:2000] + "... (truncated)"
            
        print(f"\n{body_preview}\n")
        print("="*50)

    def _should_continue(self, action: str = "continue") -> bool:
        """Ask user if they want to continue."""
        print(f"\nWould you like to {action}? (y/n)")
        choice = input("> ").strip().lower()
        return choice in ['y', 'yes']

if __name__ == "__main__":
    try:
        agent = EmailResponseAgent()
        agent.run()
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        logger.critical(f"Fatal error: {e}")

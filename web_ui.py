"""
Email Response Agent - Web UI using Reflex
"""
import reflex as rx
from typing import Optional, Any
import asyncio

from gmail_handler import GmailHandler
from llm_handler import LLMHandler
from config import Config

class State(rx.State):
    """Application state"""
    
    # UI State
    subject: str = ""
    is_searching: bool = False
    is_generating: bool = False
    is_sending: bool = False
    
    # Email data
    email_found: bool = False
    email_id: str = ""
    email_thread_id: str = ""
    email_from: str = ""
    email_subject: str = ""
    email_date: str = ""
    email_body: str = ""
    total_count: int = 0
    
    # Multiple results handling
    all_email_ids: list[str] = []
    all_email_previews: list[dict] = []  # List of {id, from, subject, date}
    show_results_list: bool = False
    selected_email_index: int = 0
    is_loading_email: bool = False
    
    # Response data
    suggested_reply: str = ""
    modified_reply: str = ""
    is_modifying: bool = False
    
    # Status messages
    status_message: str = ""
    status_type: str = "info"
    
    # Handlers - initialized lazily
    
    def set_status(self, message: str, status_type: str = "info"):
        """Set status message"""
        self.status_message = message
        self.status_type = status_type
    
    async def search_email(self):
        """Search for email by subject"""
        if not self.subject.strip():
            self.set_status("Please enter a subject to search", "error")
            return
        
        self.is_searching = True
        self.email_found = False
        self.suggested_reply = ""
        self.show_results_list = False
        self.all_email_ids = []
        self.all_email_previews = []
        self.set_status(f"🔍 Searching for emails with subject: '{self.subject}'...", "info")
        
        # Small delay to ensure loading state is visible
        await asyncio.sleep(0.3)
        
        try:
            gmail = GmailHandler()
            email_ids, total_count = gmail.search_emails(self.subject, max_results=10)
            
            if not email_ids:
                self.set_status(f"❌ No emails found with subject: '{self.subject}'", "error")
                self.is_searching = False
                return
            
            # Store all email IDs
            self.all_email_ids = email_ids
            
            # Get previews for all results
            previews = []
            for email_id in email_ids:
                preview = gmail.get_email_preview(email_id)
                if preview:
                    previews.append(preview)
            
            self.all_email_previews = previews
            
            # If multiple results, show selection UI
            if total_count > 1:
                self.show_results_list = True
                self.set_status(f"📊 Found {total_count} emails. Select one to respond to:", "success")
            else:
                # Single result - load it directly
                await self.load_email(0)
        
        except Exception as e:
            self.set_status(f"❌ Error: {str(e)}", "error")
        
        finally:
            self.is_searching = False
    
    async def load_email(self, index: int):
        """Load full email content for selected email"""
        self.selected_email_index = index
        self.is_loading_email = True
        self.set_status("📥 Loading email content...", "info")
        
        try:
            gmail = GmailHandler()
            email_id = self.all_email_ids[index]
            
            email_data = gmail.get_email_content(email_id)
            
            if email_data:
                self.email_found = True
                self.email_id = email_data['id']
                self.email_thread_id = email_data['threadId']
                self.email_from = email_data['sender']
                self.email_subject = email_data['subject']
                self.email_date = email_data['date']
                self.email_body = email_data['body']
                self.show_results_list = False
                
                self.set_status(f"✅ Email loaded successfully", "success")
                
                # Auto-generate response
                await self.generate_response_action()
            else:
                self.set_status("❌ Failed to fetch email content", "error")
        
        except Exception as e:
            self.set_status(f"❌ Error loading email: {str(e)}", "error")
        
        finally:
            self.is_loading_email = False
    
    async def generate_response_action(self):
        """Generate AI response"""
        self.is_generating = True
        self.set_status("🤖 Generating suggested response...", "info")
        
        # Small delay to ensure loading state is visible
        await asyncio.sleep(0.3)
        
        try:
            gmail = GmailHandler()
            llm = LLMHandler()
            
            user_email = gmail.get_user_email()
            
            email_data = {
                'sender': self.email_from,
                'subject': self.email_subject,
                'date': self.email_date,
                'body': self.email_body
            }
            
            # Using generate_response(email_data, user_email) signature
            reply = llm.generate_response(email_data, user_email=user_email)
            self.suggested_reply = reply
            self.modified_reply = reply
            self.set_status("✅ Response generated successfully!", "success")
        
        except Exception as e:
            self.set_status(f"❌ Error generating response: {str(e)}", "error")
        
        finally:
            self.is_generating = False
    
    def toggle_modify(self):
        """Toggle modification mode"""
        if self.is_modifying:
            # Exiting modify mode - keep the changes (user is "saving")
            self.is_modifying = False
            self.set_status("✅ Changes saved. Ready to send.", "success")
        else:
            # Entering modify mode - initialize modified_reply with current suggested_reply
            self.modified_reply = self.suggested_reply
            self.is_modifying = True
            self.set_status("✏️ Modification mode enabled. Edit the response below.", "info")
    
    def cancel_modify(self):
        """Cancel modifications and revert to original"""
        self.modified_reply = self.suggested_reply
        self.is_modifying = False
        self.set_status("Modification cancelled. Reverted to original response.", "info")
    
    async def send_reply_action(self):
        """Send the email reply"""
        self.is_sending = True
        self.set_status("📤 Sending email...", "info")
        
        try:
            gmail = GmailHandler()
            
            # Use modified_reply if it exists and has content, otherwise use suggested_reply
            final_reply = self.modified_reply if self.modified_reply else self.suggested_reply
            
            # Use correct signature: message_id, reply_text, thread_id
            success = gmail.send_reply(
                message_id=self.email_id,
                reply_text=final_reply,
                thread_id=self.email_thread_id
            )
            
            if success:
                self.set_status("✅ Email sent successfully!", "success")
                self.email_found = False
                self.suggested_reply = ""
                self.modified_reply = ""
                self.subject = ""
                self.is_modifying = False
            else:
                self.set_status("❌ Failed to send email", "error")
        
        except Exception as e:
            self.set_status(f"❌ Error sending email: {str(e)}", "error")
        
        finally:
            self.is_sending = False
    
    def cancel(self):
        """Cancel and reset"""
        self.email_found = False
        self.suggested_reply = ""
        self.is_modifying = False
        self.subject = ""
        self.set_status("Operation cancelled", "info")


def status_badge() -> rx.Component:
    """Status message badge"""
    return rx.cond(
        State.status_message != "",
        rx.callout(
            State.status_message,
            icon="info",
            color_scheme=rx.cond(
                State.status_type == "success", "green",
                rx.cond(
                    State.status_type == "error", "red",
                    rx.cond(
                        State.status_type == "warning", "yellow",
                        "blue"
                    )
                )
            ),
            size="3",
            margin_bottom="1em"
        )
    )


def search_section() -> rx.Component:
    """Email search input section with loading state"""
    return rx.vstack(
        rx.heading("📧 Email Response Agent", size="8"),
        rx.text("Search for emails by subject or sender and generate AI-powered responses", color="gray"),
        rx.divider(),
        rx.hstack(
            rx.input(
                placeholder="Enter subject or sender name to search...",
                value=State.subject,
                on_change=State.set_subject,
                size="3",
                width="100%",
                disabled=State.is_searching
            ),
            rx.button(
                rx.cond(
                    State.is_searching,
                    rx.hstack(
                        rx.spinner(size="3"),
                        rx.text("Searching..."),
                        spacing="2"
                    ),
                    rx.hstack(
                        rx.icon("search", size=20),
                        rx.text("Search"),
                        spacing="2"
                    )
                ),
                on_click=State.search_email,
                loading=State.is_searching,
                size="3",
                color_scheme="blue",
                min_width="140px"
            ),
            width="100%"
        ),
        # Loading skeleton while searching
        rx.cond(
            State.is_searching,
            rx.card(
                rx.vstack(
                    rx.hstack(
                        rx.spinner(size="3", color="blue"),
                        rx.heading("🔍 Searching Gmail...", size="5", color="gray"),
                        spacing="3"
                    ),
                    rx.skeleton(height="20px", width="100%"),
                    rx.skeleton(height="20px", width="80%"),
                    rx.skeleton(height="20px", width="60%"),
                    spacing="3",
                    width="100%"
                ),
                margin_top="1em",
                background="var(--gray-2)"
            )
        ),
        width="100%",
        spacing="4"
    )


def results_list() -> rx.Component:
    """Display list of search results for selection"""
    return rx.cond(
        State.show_results_list,
        rx.card(
            rx.vstack(
                rx.heading("📋 Select an Email", size="6"),
                rx.text(
                    f"Found {State.all_email_previews.length()} email(s). Click on one to view and respond:",
                    color="gray"
                ),
                rx.divider(),
                rx.foreach(
                    State.all_email_previews,
                    lambda preview, idx: rx.card(
                        rx.vstack(
                            rx.hstack(
                                rx.text("From:", weight="bold", width="60px"),
                                rx.text(preview["from"]),
                                width="100%"
                            ),
                            rx.hstack(
                                rx.text("Subject:", weight="bold", width="60px"),
                                rx.text(preview["subject"]),
                                width="100%"
                            ),
                            rx.hstack(
                                rx.text("Date:", weight="bold", width="60px"),
                                rx.text(preview["date"]),
                                width="100%"
                            ),
                            rx.button(
                                "Select This Email",
                                on_click=lambda: State.load_email(idx),
                                size="2",
                                color_scheme="blue",
                                width="100%"
                            ),
                            width="100%",
                            spacing="2"
                        ),
                        margin_bottom="0.5em",
                        _hover={"background": "var(--gray-3)"}
                    )
                ),
                width="100%",
                spacing="3"
            ),
            margin_top="1em",
            margin_bottom="1em"
        )
    )


def email_display() -> rx.Component:
    """Display found email"""
    return rx.cond(
        State.email_found,
        rx.card(
            rx.vstack(
                rx.heading("📨 Email Found", size="6"),
                rx.divider(),
                rx.hstack(
                    rx.text("From:", weight="bold", width="80px"),
                    rx.text(State.email_from),
                    width="100%"
                ),
                rx.hstack(
                    rx.text("Subject:", weight="bold", width="80px"),
                    rx.text(State.email_subject),
                    width="100%"
                ),
                rx.hstack(
                    rx.text("Date:", weight="bold", width="80px"),
                    rx.text(State.email_date),
                    width="100%"
                ),
                rx.divider(),
                rx.text("Email Content:", weight="bold"),
                rx.text_area(
                    value=State.email_body,
                    read_only=True,
                    height="200px",
                    width="100%"
                ),
                width="100%",
                spacing="3"
            ),
            margin_top="1em"
        )
    )


def response_section() -> rx.Component:
    """AI response section with loading state"""
    return rx.cond(
        State.is_generating | (State.suggested_reply != ""),
        rx.card(
            rx.vstack(
                rx.heading("🤖 Suggested Response", size="6"),
                rx.divider(),
                # Show loading state while generating
                rx.cond(
                    State.is_generating,
                    rx.vstack(
                        rx.hstack(
                            rx.spinner(size="3", color="blue"),
                            rx.text("Generating AI response...", color="gray", size="4"),
                            spacing="3"
                        ),
                        rx.skeleton(height="300px", width="100%"),
                        spacing="3",
                        width="100%"
                    ),
                    # Show actual response when ready
                    rx.vstack(
                        rx.cond(
                            State.is_modifying,
                            rx.text_area(
                                value=State.modified_reply,
                                on_change=State.set_modified_reply,
                                height="300px",
                                width="100%",
                                placeholder="Edit your response here..."
                            ),
                            rx.text_area(
                                value=rx.cond(
                                    State.modified_reply != "",
                                    State.modified_reply,
                                    State.suggested_reply
                                ),
                                read_only=True,
                                height="300px",
                                width="100%"
                            )
                        ),
                        rx.hstack(
                            # Send button (always visible)
                            rx.button(
                                rx.cond(
                                    State.is_sending,
                                    rx.hstack(
                                        rx.spinner(size="2"),
                                        rx.text("Sending..."),
                                        spacing="2"
                                    ),
                                    rx.hstack(
                                        rx.icon("send", size=16),
                                        rx.text("Send"),
                                        spacing="2"
                                    )
                                ),
                                on_click=State.send_reply_action,
                                loading=State.is_sending,
                                color_scheme="green",
                                size="3"
                            ),
                            # Modify/Save Edit button
                            rx.cond(
                                State.is_modifying,
                                # When modifying: Show "Save Edit" button
                                rx.button(
                                    rx.hstack(
                                        rx.icon("check", size=16),
                                        rx.text("Save Edit"),
                                        spacing="2"
                                    ),
                                    on_click=State.toggle_modify,
                                    color_scheme="blue",
                                    size="3"
                                ),
                                # When not modifying: Show "Modify" button
                                rx.button(
                                    rx.hstack(
                                        rx.icon("edit", size=16),
                                        rx.text("Modify"),
                                        spacing="2"
                                    ),
                                    on_click=State.toggle_modify,
                                    color_scheme="blue",
                                    size="3"
                                )
                            ),
                            # Cancel Edit button (only when modifying)
                            rx.cond(
                                State.is_modifying,
                                rx.button(
                                    rx.hstack(
                                        rx.icon("x-circle", size=16),
                                        rx.text("Cancel Edit"),
                                        spacing="2"
                                    ),
                                    on_click=State.cancel_modify,
                                    color_scheme="orange",
                                    size="3"
                                )
                            ),
                            # Regenerate button (only when NOT modifying)
                            rx.cond(
                                ~State.is_modifying,
                                rx.button(
                                    rx.hstack(
                                        rx.icon("refresh-cw", size=16),
                                        rx.text("Regenerate"),
                                        spacing="2"
                                    ),
                                    on_click=State.generate_response_action,
                                    loading=State.is_generating,
                                    color_scheme="gray",
                                    size="3"
                                )
                            ),
                            # Cancel All button (only when NOT modifying)
                            rx.cond(
                                ~State.is_modifying,
                                rx.button(
                                    rx.hstack(
                                        rx.icon("x", size=16),
                                        rx.text("Cancel"),
                                        spacing="2"
                                    ),
                                    on_click=State.cancel,
                                    color_scheme="red",
                                    size="3"
                                )
                            ),
                            spacing="4",
                            wrap="wrap"
                        ),
                        width="100%",
                        spacing="4"
                    )
                ),
                width="100%",
                spacing="4"
            ),
            margin_top="1em"
        )
    )


def index() -> rx.Component:
    """Main page"""
    return rx.container(
        rx.vstack(
            status_badge(),
            search_section(),
            results_list(),
            email_display(),
            response_section(),
            spacing="5",
            padding_top="2em",
            padding_bottom="2em"
        ),
        max_width="1200px"
    )


app = rx.App(
    theme=rx.theme(
        appearance="light",
        accent_color="blue"
    )
)
app.add_page(index, title="Email Response Agent")

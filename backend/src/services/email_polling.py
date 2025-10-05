import threading
import time
from typing import Optional, Set, Tuple, Any
from dataclasses import asdict
from datetime import datetime

from ..action_registry import ActionRegistry
from ..emails import EmailAccounts

class EmailPoller:
    """
    Polls email accounts periodically and logs received emails
    to an ActionRegistry.
    """

    def __init__(
        self,
        email_accounts: EmailAccounts,
        action_registry: ActionRegistry,
        interval: int = 15
    ):
        """
        Initializes the EmailPoller.

        Args:
            email_accounts: An EmailAccounts instance with configured accounts.
            action_registry: An ActionRegistry instance to log actions.
            interval: The polling interval in seconds.
        """
        self.email_accounts = email_accounts
        self.action_registry = action_registry
        self.interval = interval
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._seen_uids: Set[Tuple[str, Any]] = set()

    def _poll_and_register(self):
        """
        The core polling loop that runs in a separate thread.
        """
        print(f"Email poller started. Will check for new mail every {self.interval} seconds.")
        while not self._stop_event.is_set():
            try:
                # Fetch recent emails from all accounts
                messages = self.email_accounts.fetch_aggregated_recent(limit=25)

                new_messages_found = 0
                for msg in messages:
                    source_account_id = "email_aggregated"
                    for acc in self.email_accounts.accounts:
                         if acc.identifier in msg.from_addr or acc.identifier in msg.to_addr:
                              source_account_id = acc.identifier
                              break
                    
                    message_uid = (source_account_id, msg.uid)

                    if message_uid not in self._seen_uids:
                        # --- MODIFICATION START ---
                        # Create a dictionary with specific, important email details.
                        # This assumes the 'msg' object has attributes like 'from_addr',
                        # 'to_addr', 'subject'. No 'body' as email summary doesn't have it.
                        action_details = {
                            "sender": msg.from_addr,
                            "recipient": msg.to_addr,
                            "subject": msg.subject,
                            "description": f"From {msg.from_addr} to {msg.to_addr}, with subject: \"{msg.subject}\"."
                        }
                        
                        self.action_registry.register_action(
                            action_type="email_sent" if msg.from_addr == source_account_id else "email_received",
                            details=action_details, # Use the new, structured dictionary
                            source=source_account_id,
                            metadata={"email_uid": str(msg.uid)}
                        )
                        # --- MODIFICATION END ---
                        
                        self._seen_uids.add(message_uid)
                        new_messages_found += 1
                
                if new_messages_found > 0:
                    print(f"[EmailPoller] Registered {new_messages_found} new email(s) in the action registry.")

            except Exception as e:
                print(f"[EmailPoller] Error during email polling: {e}")

            self._stop_event.wait(self.interval)
        
        print("Email poller has stopped.")

    def start(self):
        """Starts the background polling thread."""
        if self._thread and self._thread.is_alive():
            print("Poller is already running.")
            return

        self._stop_event.clear()
        
        # --- MODIFICATION START ---
        
        # 1. Populate from Action Registry for persistence
        print("Populating seen UIDs from historical actions in the registry...")
        
        # Get all previously registered email actions
        received_actions = self.action_registry.get_actions(action_type="email_received")
        sent_actions = self.action_registry.get_actions(action_type="email_sent")
        all_email_actions = received_actions + sent_actions
        
        for action in all_email_actions:
            # Ensure metadata exists and contains the email_uid
            if action.metadata and "email_uid" in action.metadata:
                source_account = action.source
                email_uid = action.metadata["email_uid"]
                self._seen_uids.add((source_account, email_uid))

        print(f"Loaded {len(self._seen_uids)} UIDs from the action registry.")
        
        # 2. Initial scan of live mailboxes to catch anything new since last run
        print("Performing live scan to populate initial list of seen emails...")
        initial_messages = self.email_accounts.fetch_aggregated_recent(limit=100)
        initial_scan_count = 0
        for msg in initial_messages:
            source_account_id = "unknown_account"
            for acc in self.email_accounts.accounts:
                 if acc.identifier in msg.from_addr or acc.identifier in msg.to_addr:
                      source_account_id = acc.identifier
                      break
            
            # The add method of a set returns None if item is new, so we count additions
            if self._seen_uids.add((source_account_id, msg.uid)) is None:
                initial_scan_count += 1

        # --- MODIFICATION END ---
        
        print(f"Live scan added {initial_scan_count} new UIDs.")
        print(f"Initialization complete. {len(self._seen_uids)} total existing emails will be ignored.")
        
        self._thread = threading.Thread(target=self._poll_and_register, daemon=True)
        self._thread.start()

    def stop(self):
        """Stops the background polling thread gracefully."""
        print("Stopping email poller...")
        self._stop_event.set()
        if self._thread:
            self._thread.join()

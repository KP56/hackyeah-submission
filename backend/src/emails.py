from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple
import imapclient
import email
from email.header import decode_header
from email.utils import parsedate_to_datetime
import smtplib
from email.mime.text import MIMEText
import poplib
import dns.resolver


@dataclass
class EmailMessageSummary:
    subject: str
    from_addr: str
    to_addr: str
    date: datetime
    uid: Optional[int] = None


def discover_email_servers(email_address: str) -> Tuple[Optional[str], Optional[str], Optional[str], Optional[str]]:
    """Discover IMAP, POP3, and SMTP servers for an email address via DNS MX lookup."""
    try:
        domain = email_address.split('@')[1]
        
        # Common server patterns to try
        imap_candidates = [f"imap.{domain}", f"mail.{domain}", f"imap4.{domain}"]
        pop3_candidates = [f"pop.{domain}", f"pop3.{domain}", f"mail.{domain}"]
        smtp_candidates = [f"smtp.{domain}", f"mail.{domain}", f"outgoing.{domain}"]
        
        # Try to resolve MX record for domain validation
        try:
            dns.resolver.resolve(domain, 'MX')
        except Exception:
            pass  # Continue even if MX lookup fails
        
        # Return first three candidates for each service
        return (
            imap_candidates[0] if imap_candidates else None,
            pop3_candidates[0] if pop3_candidates else None, 
            smtp_candidates[0] if smtp_candidates else None,
            domain
        )
    except Exception:
        return None, None, None, None


class EmailAccount:
    def __init__(self, identifier: str, verbose: bool = False):
        self.identifier = identifier
        self._verbose = verbose

    def fetch_recent_emails(self, limit: int = -1) -> List[EmailMessageSummary]:
        raise NotImplementedError

    def send_email(self, to_addr: str, subject: str, body: str) -> None:
        raise NotImplementedError


class ImapEmailAccount(EmailAccount):
    def __init__(self, host: str, username: str, password: str, ssl: bool = True, mailbox: str = "INBOX", smtp_host: Optional[str] = None, smtp_port: int = 587, verbose: bool = False):
        super().__init__(identifier=f"imap:{username}@{host}", verbose=verbose)
        self.host = host
        self.username = username
        self.password = password
        self.ssl = ssl
        self.mailbox = mailbox
        self.smtp_host = smtp_host or (f"smtp.{host}" if not host.startswith("smtp.") else host)
        self.smtp_port = smtp_port

    def fetch_recent_emails(self, limit: int = -1) -> List[EmailMessageSummary]:
        client = imapclient.IMAPClient(self.host, ssl=self.ssl)
        client.login(self.username, self.password)
        try:
            client.select_folder(self.mailbox, readonly=True)
            uids = client.search(["ALL"])  # list of ints
            uids_sorted = sorted(uids, reverse=True)
            if limit > 0:
                uids_sorted = uids_sorted[:limit]
            if not uids_sorted:
                return []
            messages = client.fetch(uids_sorted, [b"RFC822"])
            summaries: List[EmailMessageSummary] = []
            for uid in uids_sorted:
                msg_bytes = messages[uid][b"RFC822"]
                msg = email.message_from_bytes(msg_bytes)
                subject_hdr = msg.get("Subject", "")
                subject_parts = decode_header(subject_hdr)
                subject_decoded = "".join(
                    [(part.decode(enc or "utf-8") if isinstance(part, bytes) else part) for part, enc in subject_parts]
                )
                from_addr = msg.get("From", "")
                to_addr = msg.get("To", "")
                date_hdr = msg.get("Date")
                try:
                    dt = parsedate_to_datetime(date_hdr) if date_hdr else datetime.utcnow()
                except Exception:
                    dt = datetime.utcnow()
                summaries.append(EmailMessageSummary(
                    subject=subject_decoded,
                    from_addr=from_addr,
                    to_addr=to_addr,
                    date=dt,
                    uid=uid,
                ))
            if self._verbose:
                print(f"[email] IMAP fetched {len(summaries)} messages from {self.identifier}")
            return summaries
        finally:
            client.logout()

    def send_email(self, to_addr: str, subject: str, body: str) -> None:
        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = self.username
        msg["To"] = to_addr
        with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
            server.starttls()
            server.login(self.username, self.password)
            server.sendmail(self.username, [to_addr], msg.as_string())
        if self._verbose:
            print(f"[email] IMAP SMTP sent to {to_addr} from {self.identifier}: {subject}")


class Pop3EmailAccount(EmailAccount):
    def __init__(self, host: str, username: str, password: str, ssl: bool = True, smtp_host: Optional[str] = None, smtp_port: int = 587, verbose: bool = False):
        super().__init__(identifier=f"pop3:{username}@{host}", verbose=verbose)
        self.host = host
        self.username = username
        self.password = password
        self.ssl = ssl
        self.smtp_host = smtp_host or (f"smtp.{host}" if not host.startswith("smtp.") else host)
        self.smtp_port = smtp_port

    def fetch_recent_emails(self, limit: int = -1) -> List[EmailMessageSummary]:
        if self.ssl:
            server = poplib.POP3_SSL(self.host)
        else:
            server = poplib.POP3(self.host)
        server.user(self.username)
        server.pass_(self.password)
        try:
            count, _ = server.stat()
            indices = list(range(1, count + 1))
            if limit > 0:
                indices = indices[-limit:]
            summaries: List[EmailMessageSummary] = []
            for i in reversed(indices):
                try:
                    resp, lines, octets = server.top(i, 0)
                except Exception:
                    resp, lines, octets = server.retr(i)
                headers = b"\n".join(lines).decode(errors="ignore")
                msg = email.message_from_string(headers)
                subject_hdr = msg.get("Subject", "")
                subject_parts = decode_header(subject_hdr)
                subject_decoded = "".join(
                    [(part.decode(enc or "utf-8") if isinstance(part, bytes) else part) for part, enc in subject_parts]
                )
                from_addr = msg.get("From", "")
                to_addr = msg.get("To", "")
                date_hdr = msg.get("Date")
                try:
                    dt = parsedate_to_datetime(date_hdr) if date_hdr else datetime.utcnow()
                except Exception:
                    dt = datetime.utcnow()
                summaries.append(EmailMessageSummary(
                    subject=subject_decoded,
                    from_addr=from_addr,
                    to_addr=to_addr,
                    date=dt,
                    uid=i,
                ))
            if self._verbose:
                print(f"[email] POP3 fetched {len(summaries)} messages from {self.identifier}")
            return summaries
        finally:
            server.quit()

    def send_email(self, to_addr: str, subject: str, body: str) -> None:
        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = self.username
        msg["To"] = to_addr
        with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
            server.starttls()
            server.login(self.username, self.password)
            server.sendmail(self.username, [to_addr], msg.as_string())
        if self._verbose:
            print(f"[email] POP3 SMTP sent to {to_addr} from {self.identifier}: {subject}")


class NylasEmailAccount(EmailAccount):
    def __init__(self, nylas_client: Any, grant_id: str, email_address: str, verbose: bool = False):
        super().__init__(identifier=f"nylas:{email_address}", verbose=verbose)
        self._nylas = nylas_client
        self._grant_id = grant_id
        self._email = email_address

    def fetch_recent_emails(self, limit: int = -1) -> List[EmailMessageSummary]:
        try:
            query = {"limit": limit if limit > 0 else 50}
            resp = self._nylas.messages.list(self._grant_id, query_params=query)
            data = getattr(resp, "data", resp)
            summaries: List[EmailMessageSummary] = []
            for m in data:
                subject = m.get("subject") if isinstance(m, dict) else getattr(m, "subject", "")
                from_val = m.get("from") if isinstance(m, dict) else getattr(m, "from_", "")
                to_val = m.get("to") if isinstance(m, dict) else getattr(m, "to", "")
                try:
                    if isinstance(from_val, list) and from_val:
                        from_addr = from_val[0].get("email", "")
                    else:
                        from_addr = str(from_val or "")
                except Exception:
                    from_addr = str(from_val or "")
                try:
                    if isinstance(to_val, list):
                        to_addr = ", ".join([x.get("email", "") for x in to_val])
                    else:
                        to_addr = str(to_val or "")
                except Exception:
                    to_addr = str(to_val or "")
                ts = m.get("received_at") if isinstance(m, dict) else getattr(m, "received_at", None)
                if ts is None:
                    ts = m.get("date") if isinstance(m, dict) else getattr(m, "date", None)
                if isinstance(ts, (int, float)):
                    date_val = datetime.fromtimestamp(ts)
                else:
                    date_val = datetime.utcnow()
                uid = m.get("id") if isinstance(m, dict) else getattr(m, "id", None)
                summaries.append(EmailMessageSummary(
                    subject=subject or "",
                    from_addr=from_addr,
                    to_addr=to_addr,
                    date=date_val,
                    uid=uid,
                ))
            if self._verbose:
                print(f"[email] Nylas fetched {len(summaries)} messages from {self.identifier}")
            return summaries
        except Exception:
            return []

    def send_email(self, to_addr: str, subject: str, body: str) -> None:
        draft = {
            "to": [{"email": to_addr}],
            "subject": subject,
            "body": body,
        }
        if hasattr(self._nylas, "drafts") and hasattr(self._nylas.drafts, "send"):
            self._nylas.drafts.send(self._grant_id, draft)
        else:
            self._nylas.messages.send(self._grant_id, draft)
        if self._verbose:
            print(f"[email] Nylas sent to {to_addr} from {self.identifier}: {subject}")


@dataclass
class EmailAccounts:
    accounts: List[EmailAccount] = field(default_factory=list)

    def add(self, account: EmailAccount) -> None:
        self.accounts.append(account)

    def remove(self, identifier: str) -> None:
        self.accounts = [a for a in self.accounts if a.identifier != identifier]

    def list_identifiers(self) -> List[str]:
        return [a.identifier for a in self.accounts]

    def fetch_aggregated_recent(self, limit: int = -1) -> List[EmailMessageSummary]:
        per_account_limit = 1000 if limit < 0 else min(limit, 1000)
        all_msgs: List[EmailMessageSummary] = []
        for acc in self.accounts:
            msgs = acc.fetch_recent_emails(limit=per_account_limit)
            all_msgs.extend(msgs)
        all_msgs.sort(key=lambda m: m.date, reverse=True)
        if limit > 0:
            return all_msgs[:limit]
        return all_msgs

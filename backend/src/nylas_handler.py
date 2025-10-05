from __future__ import annotations
from typing import Optional, Any, List, Tuple
from dataclasses import dataclass

from .emails import EmailAccount, ImapEmailAccount, NylasEmailAccount, EmailMessageSummary, Pop3EmailAccount


@dataclass
class OAuthResult:
    grant_id: str
    email_address: str


class NylasHandler:
    def __init__(self, nylas_client: Optional[Any] = None):
        self._nylas = nylas_client

    def is_configured(self) -> bool:
        return self._nylas is not None

    # OAuth helpers (v3: use client_id + redirect_uri, no client secret)
    def get_oauth_url(self, client_id: str, redirect_uri: str, scope: Optional[str] = None) -> Optional[str]:
        if not self._nylas:
            return None
        try:
            params = {"client_id": client_id, "redirect_uri": redirect_uri}
            if scope:
                params["scope"] = scope
            return self._nylas.auth.url_for_oauth2(params)
        except Exception:
            return None

    def exchange_code_for_grant(self, code: str, client_id: str, redirect_uri: str) -> Optional[OAuthResult]:
        if not self._nylas:
            print("Nylas handler: no self._nylas")
            return None
        try:
            payload = {"code": code, "client_id": client_id, "redirect_uri": redirect_uri}
            print("1")
            exchange = self._nylas.auth.exchange_code_for_token(payload)
            print("2")
            grant_id = exchange.get("grant_id") if isinstance(exchange, dict) else getattr(exchange, "grant_id", None)
            print("3")
            email_address = exchange.get("email") if isinstance(exchange, dict) else getattr(exchange, "email", None)
            if not grant_id:
                print("Nylas handler: no grant_id")
                return None
            print("4")
            return OAuthResult(grant_id=grant_id, email_address=email_address or "")
        except Exception as e:
            print("Nylas handler exception:", e)
            return None

    def sign_in_oauth(self) -> Optional[EmailAccount]:
        if self._nylas is None:
            return None
        try:
            grants = self._nylas.grants.list(limit=1)
            if not grants:
                return None
            grant = grants[0]
            grant_id = grant["id"] if isinstance(grant, dict) else getattr(grant, "id", None)
            email_address = grant.get("email") if isinstance(grant, dict) else getattr(grant, "email", None)
            if not grant_id:
                return None
            return NylasEmailAccount(self._nylas, grant_id=grant_id, email_address=email_address or "")
        except Exception:
            return None

    def sign_in_imap(self, host: str, username: str, password: str, ssl: bool = True) -> EmailAccount:
        return ImapEmailAccount(host=host, username=username, password=password, ssl=ssl)

    def sign_in_pop3(self, host: str, username: str, password: str, ssl: bool = True) -> EmailAccount:
        return Pop3EmailAccount(host=host, username=username, password=password, ssl=ssl)

    def fetch_recent_via_grant(self, grant_id: str, limit: int = -1) -> List[EmailMessageSummary]:
        if self._nylas is None:
            return []
        q = {"limit": limit if limit > 0 else 50}
        try:
            msgs = self._nylas.messages.list(grant_id, query_params=q)
            results: List[EmailMessageSummary] = []
            data = getattr(msgs, "data", msgs)
            for m in data:
                subject = m.get("subject") if isinstance(m, dict) else getattr(m, "subject", "")
                from_val = m.get("from") if isinstance(m, dict) else getattr(m, "from_", "")
                to_val = m.get("to") if isinstance(m, dict) else getattr(m, "to", "")
                ts = m.get("received_at") if isinstance(m, dict) else getattr(m, "received_at", None)
                if ts is None:
                    ts = m.get("date") if isinstance(m, dict) else getattr(m, "date", None)
                from datetime import datetime
                dt = datetime.fromtimestamp(ts) if isinstance(ts, (int, float)) else datetime.utcnow()
                results.append(EmailMessageSummary(subject=subject or "", from_addr=str(from_val or ""), to_addr=str(to_val or ""), date=dt, uid=(m.get("id") if isinstance(m, dict) else getattr(m, "id", None))))
            return results
        except Exception:
            return []

    def send_via_grant(self, grant_id: str, to_addr: str, subject: str, body: str) -> bool:
        if self._nylas is None:
            return False
        try:
            draft = {"to": [{"email": to_addr}], "subject": subject, "body": body}
            if hasattr(self._nylas, "drafts") and hasattr(self._nylas.drafts, "send"):
                self._nylas.drafts.send(grant_id, draft)
            else:
                self._nylas.messages.send(grant_id, draft)
            return True
        except Exception:
            return False

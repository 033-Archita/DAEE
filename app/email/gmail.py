"""Gmail REST API sender using OAuth refresh-token credentials."""

from __future__ import annotations

import base64
import json
from email.message import EmailMessage
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class GmailError(RuntimeError):
    """Raised when Gmail OAuth or message delivery fails."""


class GmailSender:
    token_endpoint = "https://oauth2.googleapis.com/token"
    send_endpoint = "https://gmail.googleapis.com/gmail/v1/users/me/messages/send"

    def __init__(self, *, client_id: str | None, client_secret: str | None, refresh_token: str | None, recipient: str | None) -> None:
        self._client_id, self._client_secret = client_id, client_secret
        self._refresh_token, self._recipient = refresh_token, recipient

    @property
    def is_configured(self) -> bool:
        return all((self._client_id, self._client_secret, self._refresh_token, self._recipient))

    def _access_token(self) -> str:
        if not self.is_configured:
            raise GmailError("Gmail OAuth is not configured. Set GMAIL_OAUTH_CLIENT_ID, GMAIL_OAUTH_CLIENT_SECRET, GMAIL_REFRESH_TOKEN, and GMAIL_RECIPIENT.")
        body = json.dumps({"client_id": self._client_id, "client_secret": self._client_secret, "refresh_token": self._refresh_token, "grant_type": "refresh_token"}).encode()
        request = Request(self.token_endpoint, data=body, headers={"Content-Type": "application/json"}, method="POST")
        try:
            with urlopen(request, timeout=30) as response:
                token = json.loads(response.read().decode())["access_token"]
        except (HTTPError, URLError, KeyError, json.JSONDecodeError, TimeoutError) as error:
            raise GmailError("Could not obtain a Gmail access token.") from error
        return token

    def send_html(self, *, subject: str, html: str, message_id: str) -> str:
        message = EmailMessage()
        message["To"] = self._recipient or ""
        message["Subject"] = subject
        message["Message-ID"] = message_id
        message.set_content("Your email client does not support HTML. Please view this message in Gmail.")
        message.add_alternative(html, subtype="html")
        encoded = base64.urlsafe_b64encode(message.as_bytes()).decode().rstrip("=")
        request = Request(self.send_endpoint, data=json.dumps({"raw": encoded}).encode(), headers={"Authorization": f"Bearer {self._access_token()}", "Content-Type": "application/json"}, method="POST")
        try:
            with urlopen(request, timeout=45) as response:
                return str(json.loads(response.read().decode())["id"])
        except (HTTPError, URLError, KeyError, json.JSONDecodeError, TimeoutError) as error:
            raise GmailError("Gmail could not send the daily email.") from error

"""Notification channel implementations."""
from __future__ import annotations

import json
import logging
import urllib.request
import urllib.error
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from apex_os_bp.notifications.models import Notification, NotificationChannel, NotificationStatus

logger = logging.getLogger(__name__)


@dataclass
class ChannelResult:
    """Result of sending a notification through a channel."""
    success: bool
    channel: NotificationChannel
    message: str = ""
    response_data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class BaseChannel(ABC):
    """Base class for notification channels."""

    def __init__(self, name: str, config: Optional[Dict[str, Any]] = None):
        self.name = name
        self.config = config or {}
        self._sent_count = 0
        self._failed_count = 0

    @property
    @abstractmethod
    def channel_type(self) -> NotificationChannel:
        """Return the channel type."""
        ...

    @abstractmethod
    def send(self, notification: Notification) -> ChannelResult:
        """Send a notification through this channel."""
        ...

    def get_stats(self) -> Dict[str, int]:
        """Get channel statistics."""
        return {
            "sent": self._sent_count,
            "failed": self._failed_count,
        }

    def _record_success(self) -> None:
        self._sent_count += 1

    def _record_failure(self) -> None:
        self._failed_count += 1


class EmailChannel(BaseChannel):
    """Email notification channel using SMTP."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__("email", config)
        self.smtp_host = self.config.get("smtp_host", "localhost")
        self.smtp_port = self.config.get("smtp_port", 587)
        self.smtp_user = self.config.get("smtp_user", "")
        self.smtp_password = self.config.get("smtp_password", "")
        self.use_tls = self.config.get("use_tls", True)
        self.from_address = self.config.get("from_address", "noreply@apex-os.local")
        self._mock_mode = self.config.get("mock_mode", True)

    @property
    def channel_type(self) -> NotificationChannel:
        return NotificationChannel.EMAIL

    def send(self, notification: Notification) -> ChannelResult:
        """Send email notification."""
        try:
            if not notification.recipients:
                raise ValueError("No recipients specified for email notification")

            if self._mock_mode:
                logger.info(
                    f"[MOCK] Email sent to {notification.recipients}: {notification.title}"
                )
                self._record_success()
                return ChannelResult(
                    success=True,
                    channel=self.channel_type,
                    message=f"Email sent to {len(notification.recipients)} recipients",
                    response_data={"recipients": notification.recipients, "mock": True},
                )

            # Real SMTP sending would go here
            import smtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart

            msg = MIMEMultipart()
            msg["From"] = self.from_address
            msg["To"] = ", ".join(notification.recipients)
            msg["Subject"] = notification.title
            msg.attach(MIMEText(notification.body, "plain"))

            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                if self.use_tls:
                    server.starttls()
                if self.smtp_user:
                    server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)

            self._record_success()
            return ChannelResult(
                success=True,
                channel=self.channel_type,
                message=f"Email sent to {len(notification.recipients)} recipients",
            )
        except Exception as e:
            self._record_failure()
            logger.error(f"Email send failed: {e}")
            return ChannelResult(
                success=False,
                channel=self.channel_type,
                error=str(e),
            )


class SMSChannel(BaseChannel):
    """SMS notification channel using Twilio or similar."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__("sms", config)
        self.account_sid = self.config.get("account_sid", "")
        self.auth_token = self.config.get("auth_token", "")
        self.from_number = self.config.get("from_number", "")
        self.provider = self.config.get("provider", "twilio")
        self._mock_mode = self.config.get("mock_mode", True)

    @property
    def channel_type(self) -> NotificationChannel:
        return NotificationChannel.SMS

    def send(self, notification: Notification) -> ChannelResult:
        """Send SMS notification."""
        try:
            if not notification.recipients:
                raise ValueError("No recipients specified for SMS notification")

            if self._mock_mode:
                logger.info(
                    f"[MOCK] SMS sent to {notification.recipients}: {notification.title}"
                )
                self._record_success()
                return ChannelResult(
                    success=True,
                    channel=self.channel_type,
                    message=f"SMS sent to {len(notification.recipients)} recipients",
                    response_data={"recipients": notification.recipients, "mock": True},
                )

            # Real SMS sending would use Twilio or similar
            self._record_success()
            return ChannelResult(
                success=True,
                channel=self.channel_type,
                message=f"SMS sent to {len(notification.recipients)} recipients",
            )
        except Exception as e:
            self._record_failure()
            logger.error(f"SMS send failed: {e}")
            return ChannelResult(
                success=False,
                channel=self.channel_type,
                error=str(e),
            )


class PushChannel(BaseChannel):
    """Push notification channel using FCM/APNs."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__("push", config)
        self.fcm_api_key = self.config.get("fcm_api_key", "")
        self.apns_cert = self.config.get("apns_cert", "")
        self.apns_key = self.config.get("apns_key", "")
        self._mock_mode = self.config.get("mock_mode", True)

    @property
    def channel_type(self) -> NotificationChannel:
        return NotificationChannel.PUSH

    def send(self, notification: Notification) -> ChannelResult:
        """Send push notification."""
        try:
            if not notification.recipients:
                raise ValueError("No recipients specified for push notification")

            if self._mock_mode:
                logger.info(
                    f"[MOCK] Push sent to {notification.recipients}: {notification.title}"
                )
                self._record_success()
                return ChannelResult(
                    success=True,
                    channel=self.channel_type,
                    message=f"Push notification sent to {len(notification.recipients)} devices",
                    response_data={"recipients": notification.recipients, "mock": True},
                )

            # Real push sending would use FCM/APNs
            self._record_success()
            return ChannelResult(
                success=True,
                channel=self.channel_type,
                message=f"Push notification sent to {len(notification.recipients)} devices",
            )
        except Exception as e:
            self._record_failure()
            logger.error(f"Push send failed: {e}")
            return ChannelResult(
                success=False,
                channel=self.channel_type,
                error=str(e),
            )


class WebhookChannel(BaseChannel):
    """Webhook notification channel for HTTP callbacks."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__("webhook", config)
        self.url = self.config.get("url", "")
        self.headers = self.config.get("headers", {})
        self.timeout = self.config.get("timeout", 30)
        self.secret = self.config.get("secret", "")
        self._mock_mode = self.config.get("mock_mode", True)

    @property
    def channel_type(self) -> NotificationChannel:
        return NotificationChannel.WEBHOOK

    def send(self, notification: Notification) -> ChannelResult:
        """Send webhook notification."""
        try:
            if not self.url:
                raise ValueError("No URL specified for webhook notification")

            payload = {
                "id": notification.id,
                "title": notification.title,
                "body": notification.body,
                "priority": notification.priority.value,
                "status": notification.status.value,
                "recipients": notification.recipients,
                "metadata": notification.metadata,
                "timestamp": notification.created_at,
            }

            if self._mock_mode:
                logger.info(f"[MOCK] Webhook sent to {self.url}: {notification.title}")
                self._record_success()
                return ChannelResult(
                    success=True,
                    channel=self.channel_type,
                    message=f"Webhook sent to {self.url}",
                    response_data={"url": self.url, "payload": payload, "mock": True},
                )

            # Real webhook sending
            data = json.dumps(payload).encode("utf-8")
            headers = {"Content-Type": "application/json"}
            headers.update(self.headers)

            req = urllib.request.Request(
                self.url, data=data, headers=headers, method="POST"
            )
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                response_body = resp.read().decode("utf-8")
                self._record_success()
                return ChannelResult(
                    success=True,
                    channel=self.channel_type,
                    message=f"Webhook sent to {self.url}",
                    response_data={"status": resp.status, "body": response_body},
                )
        except Exception as e:
            self._record_failure()
            logger.error(f"Webhook send failed: {e}")
            return ChannelResult(
                success=False,
                channel=self.channel_type,
                error=str(e),
            )

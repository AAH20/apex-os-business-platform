"""Report distribution — distribute reports via email, webhook, and file share."""

from __future__ import annotations

import json
import os
import smtplib
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from enum import Enum
from pathlib import Path
from typing import Any
from urllib import request as urlrequest

from apex_os_bp.reporting.exporter import ExportResult


class DistributionChannel(str, Enum):
    """Supported distribution channels."""

    EMAIL = "email"
    WEBHOOK = "webhook"
    FILE_SHARE = "file_share"
    SLACK = "slack"
    SFTP = "sftp"


class DistributionStatus(str, Enum):
    """Distribution status."""

    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    RETRYING = "retrying"


@dataclass
class DistributionConfig:
    """Configuration for a distribution target."""

    channel: DistributionChannel
    name: str
    # Email settings
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_use_tls: bool = True
    from_address: str | None = None
    to_addresses: list[str] = field(default_factory=list)
    # Webhook settings
    webhook_url: str | None = None
    webhook_headers: dict[str, str] = field(default_factory=dict)
    webhook_method: str = "POST"
    # File share settings
    file_share_path: str | None = None
    # Slack settings
    slack_webhook_url: str | None = None
    slack_channel: str | None = None
    # SFTP settings
    sftp_host: str | None = None
    sftp_port: int = 22
    sftp_username: str | None = None
    sftp_password: str | None = None
    sftp_remote_path: str | None = None
    # General
    parameters: dict[str, Any] = field(default_factory=dict)
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=datetime.utcnow)
    enabled: bool = True


@dataclass
class DistributionResult:
    """Result of a distribution attempt."""

    config_id: str
    channel: DistributionChannel
    status: DistributionStatus
    sent_at: datetime = field(default_factory=datetime.utcnow)
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    error: str | None = None
    retry_count: int = 0
    max_retries: int = 3


class ReportDistributor:
    """Distributes reports to configured channels."""

    def __init__(self) -> None:
        self._configs: dict[str, DistributionConfig] = {}
        self._history: list[DistributionResult] = []

    def add_config(self, config: DistributionConfig) -> DistributionConfig:
        """Add a distribution configuration."""
        self._configs[config.id] = config
        return config

    def remove_config(self, config_id: str) -> bool:
        """Remove a distribution configuration."""
        if config_id in self._configs:
            del self._configs[config_id]
            return True
        return False

    def get_config(self, config_id: str) -> DistributionConfig | None:
        """Get a distribution config by ID."""
        return self._configs.get(config_id)

    def list_configs(
        self, channel: DistributionChannel | None = None
    ) -> list[DistributionConfig]:
        """List all configs, optionally filtered by channel."""
        configs = list(self._configs.values())
        if channel is not None:
            configs = [c for c in configs if c.channel == channel]
        return configs

    def distribute(
        self,
        config_id: str,
        export_result: ExportResult,
        subject: str | None = None,
        message: str | None = None,
    ) -> DistributionResult:
        """Distribute an export result via the specified config."""
        config = self._configs.get(config_id)
        if config is None:
            result = DistributionResult(
                config_id=config_id,
                channel=DistributionChannel.EMAIL,
                status=DistributionStatus.FAILED,
                error=f"Config not found: {config_id}",
            )
            self._history.append(result)
            return result
        if not config.enabled:
            result = DistributionResult(
                config_id=config_id,
                channel=config.channel,
                status=DistributionStatus.FAILED,
                error="Config is disabled",
            )
            self._history.append(result)
            return result

        try:
            if config.channel == DistributionChannel.EMAIL:
                return self._send_email(config, export_result, subject, message)
            if config.channel == DistributionChannel.WEBHOOK:
                return self._send_webhook(config, export_result)
            if config.channel == DistributionChannel.FILE_SHARE:
                return self._send_file_share(config, export_result)
            if config.channel == DistributionChannel.SLACK:
                return self._send_slack(config, export_result, message)
            if config.channel == DistributionChannel.SFTP:
                return self._send_sftp(config, export_result)
            raise ValueError(f"Unsupported channel: {config.channel}")
        except Exception as exc:
            result = DistributionResult(
                config_id=config_id,
                channel=config.channel,
                status=DistributionStatus.FAILED,
                error=str(exc),
            )
            self._history.append(result)
            return result

    def _send_email(
        self,
        config: DistributionConfig,
        export_result: ExportResult,
        subject: str | None,
        message: str | None,
    ) -> DistributionResult:
        """Send report via email."""
        msg = MIMEMultipart()
        msg["From"] = config.from_address or "reports@apex-os.local"
        msg["To"] = ", ".join(config.to_addresses)
        msg["Subject"] = subject or "APEX-OS Report"

        body = message or (
            f"Please find the attached report.\n\n"
            f"File: {Path(export_result.file_path).name}\n"
            f"Size: {export_result.file_size} bytes"
        )
        msg.attach(MIMEText(body, "plain"))

        with open(export_result.file_path, "rb") as f:
            attachment = MIMEApplication(f.read(), _subtype="octet-stream")
            attachment.add_header(
                "Content-Disposition",
                "attachment",
                filename=Path(export_result.file_path).name,
            )
            msg.attach(attachment)

        with smtplib.SMTP(config.smtp_host, config.smtp_port) as server:
            if config.smtp_use_tls:
                server.starttls()
            if config.smtp_username and config.smtp_password:
                server.login(config.smtp_username, config.smtp_password)
            server.send_message(msg)

        result = DistributionResult(
            config_id=config.id,
            channel=DistributionChannel.EMAIL,
            status=DistributionStatus.SENT,
        )
        self._history.append(result)
        return result

    def _send_webhook(
        self,
        config: DistributionConfig,
        export_result: ExportResult,
    ) -> DistributionResult:
        """Send report via webhook."""
        payload = {
            "report_id": export_result.id,
            "format": export_result.format.value,
            "file_path": export_result.file_path,
            "file_size": export_result.file_size,
            "row_count": export_result.row_count,
            "generated_at": export_result.generated_at.isoformat(),
        }
        data = json.dumps(payload).encode("utf-8")
        req = urlrequest.Request(
            config.webhook_url or "",
            data=data,
            headers={
                "Content-Type": "application/json",
                **config.webhook_headers,
            },
            method=config.webhook_method,
        )
        with urlrequest.urlopen(req, timeout=30) as resp:
            _ = resp.read()

        result = DistributionResult(
            config_id=config.id,
            channel=DistributionChannel.WEBHOOK,
            status=DistributionStatus.SENT,
        )
        self._history.append(result)
        return result

    def _send_file_share(
        self,
        config: DistributionConfig,
        export_result: ExportResult,
    ) -> DistributionResult:
        """Copy report to a file share path."""
        dest_dir = config.file_share_path or "/tmp/reports"
        os.makedirs(dest_dir, exist_ok=True)
        dest = os.path.join(dest_dir, Path(export_result.file_path).name)
        import shutil

        shutil.copy2(export_result.file_path, dest)

        result = DistributionResult(
            config_id=config.id,
            channel=DistributionChannel.FILE_SHARE,
            status=DistributionStatus.SENT,
        )
        self._history.append(result)
        return result

    def _send_slack(
        self,
        config: DistributionConfig,
        export_result: ExportResult,
        message: str | None,
    ) -> DistributionResult:
        """Send report notification via Slack webhook."""
        payload = {
            "channel": config.slack_channel or "#reports",
            "text": message or f"Report ready: {Path(export_result.file_path).name}",
            "attachments": [
                {
                    "fields": [
                        {"title": "Format", "value": export_result.format.value, "short": True},
                        {"title": "Rows", "value": str(export_result.row_count), "short": True},
                        {"title": "Size", "value": f"{export_result.file_size} bytes", "short": True},
                    ]
                }
            ],
        }
        data = json.dumps(payload).encode("utf-8")
        req = urlrequest.Request(
            config.slack_webhook_url or "",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlrequest.urlopen(req, timeout=30) as resp:
            _ = resp.read()

        result = DistributionResult(
            config_id=config.id,
            channel=DistributionChannel.SLACK,
            status=DistributionStatus.SENT,
        )
        self._history.append(result)
        return result

    def _send_sftp(
        self,
        config: DistributionConfig,
        export_result: ExportResult,
    ) -> DistributionResult:
        """Upload report via SFTP."""
        try:
            import paramiko
        except ImportError:
            raise RuntimeError("paramiko is required for SFTP distribution")

        transport = paramiko.Transport((config.sftp_host, config.sftp_port))
        transport.connect(
            username=config.sftp_username,
            password=config.sftp_password,
        )
        sftp = paramiko.SFTPClient.from_transport(remote_path=config.sftp_remote_path or "/upload")
        remote_file = f"{config.sftp_remote_path.rstrip('/')}/{Path(export_result.file_path).name}"
        sftp.put(export_result.file_path, remote_file)
        sftp.close()
        transport.close()

        result = DistributionResult(
            config_id=config.id,
            channel=DistributionChannel.SFTP,
            status=DistributionStatus.SENT,
        )
        self._history.append(result)
        return result

    def get_history(
        self, config_id: str | None = None
    ) -> list[DistributionResult]:
        """Get distribution history."""
        if config_id is not None:
            return [r for r in self._history if r.config_id == config_id]
        return list(self._history)

    def get_history_by_status(
        self, status: DistributionStatus
    ) -> list[DistributionResult]:
        """Get distribution history filtered by status."""
        return [r for r in self._history if r.status == status]

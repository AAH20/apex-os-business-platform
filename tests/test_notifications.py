"""Tests for notification system."""
import pytest
from apex_os_bp.notifications import (
    Notification,
    NotificationChannel,
    NotificationManager,
    NotificationPriority,
    NotificationStatus,
    NotificationTemplate,
    TemplateRegistry,
)
from apex_os_bp.notifications.channels import (
    ChannelResult,
    EmailChannel,
    PushChannel,
    SMSChannel,
    WebhookChannel,
)


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class TestNotification:
    """Test Notification data model."""

    def test_create_notification(self):
        n = Notification(title="Test", body="Body")
        assert n.title == "Test"
        assert n.body == "Body"
        assert n.status == NotificationStatus.PENDING
        assert n.id is not None

    def test_notification_with_channels(self):
        n = Notification(
            title="Test",
            body="Body",
            channels=[NotificationChannel.EMAIL, NotificationChannel.SMS],
            recipients=["a@b.com"],
        )
        assert len(n.channels) == 2
        assert NotificationChannel.EMAIL in n.channels

    def test_notification_priority(self):
        n = Notification(priority=NotificationPriority.HIGH)
        assert n.priority == NotificationPriority.HIGH

    def test_mark_sent(self):
        n = Notification()
        n.mark_sent()
        assert n.status == NotificationStatus.SENT
        assert n.sent_at is not None

    def test_mark_delivered(self):
        n = Notification()
        n.mark_delivered()
        assert n.status == NotificationStatus.DELIVERED
        assert n.delivered_at is not None

    def test_mark_failed(self):
        n = Notification()
        n.mark_failed("error")
        assert n.status == NotificationStatus.FAILED
        assert n.error_message == "error"

    def test_mark_retrying(self):
        n = Notification()
        n.mark_retrying()
        assert n.status == NotificationStatus.RETRYING
        assert n.retry_count == 1

    def test_can_retry(self):
        n = Notification(max_retries=3)
        assert n.can_retry() is True
        n.retry_count = 3
        assert n.can_retry() is False

    def test_to_dict(self):
        n = Notification(title="Test", body="Body")
        d = n.to_dict()
        assert d["title"] == "Test"
        assert d["status"] == "pending"
        assert "id" in d

    def test_from_dict(self):
        n = Notification(title="Test", body="Body")
        d = n.to_dict()
        n2 = Notification.from_dict(d)
        assert n2.title == "Test"
        assert n2.body == "Body"
        assert n2.id == n.id

    def test_from_dict_with_channels(self):
        d = {
            "title": "Test",
            "body": "Body",
            "channels": ["email", "sms"],
            "recipients": ["a@b.com"],
            "priority": "high",
        }
        n = Notification.from_dict(d)
        assert NotificationChannel.EMAIL in n.channels
        assert NotificationChannel.SMS in n.channels
        assert n.priority == NotificationPriority.HIGH


class TestNotificationStatus:
    """Test NotificationStatus enum."""

    def test_status_values(self):
        assert NotificationStatus.PENDING.value == "pending"
        assert NotificationStatus.SENT.value == "sent"
        assert NotificationStatus.DELIVERED.value == "delivered"
        assert NotificationStatus.FAILED.value == "failed"
        assert NotificationStatus.RETRYING.value == "retrying"
        assert NotificationStatus.CANCELLED.value == "cancelled"


class TestNotificationPriority:
    """Test NotificationPriority enum."""

    def test_priority_values(self):
        assert NotificationPriority.LOW.value == "low"
        assert NotificationPriority.NORMAL.value == "normal"
        assert NotificationPriority.HIGH.value == "high"
        assert NotificationPriority.CRITICAL.value == "critical"


class TestNotificationChannel:
    """Test NotificationChannel enum."""

    def test_channel_values(self):
        assert NotificationChannel.EMAIL.value == "email"
        assert NotificationChannel.SMS.value == "sms"
        assert NotificationChannel.PUSH.value == "push"
        assert NotificationChannel.WEBHOOK.value == "webhook"


# ---------------------------------------------------------------------------
# Channels
# ---------------------------------------------------------------------------

class TestEmailChannel:
    """Test email notification channel."""

    def test_channel_type(self):
        ch = EmailChannel()
        assert ch.channel_type == NotificationChannel.EMAIL

    def test_send_mock(self):
        ch = EmailChannel({"mock_mode": True})
        n = Notification(
            title="Test Email",
            body="Test body",
            recipients=["user@example.com"],
            channels=[NotificationChannel.EMAIL],
        )
        result = ch.send(n)
        assert result.success is True
        assert result.channel == NotificationChannel.EMAIL

    def test_send_no_recipients(self):
        ch = EmailChannel({"mock_mode": True})
        n = Notification(
            title="Test",
            body="Body",
            recipients=[],
            channels=[NotificationChannel.EMAIL],
        )
        result = ch.send(n)
        assert result.success is False
        assert "No recipients" in result.error

    def test_get_stats(self):
        ch = EmailChannel({"mock_mode": True})
        n = Notification(
            title="Test",
            body="Body",
            recipients=["a@b.com"],
            channels=[NotificationChannel.EMAIL],
        )
        ch.send(n)
        stats = ch.get_stats()
        assert stats["sent"] == 1
        assert stats["failed"] == 0

    def test_stats_after_failure(self):
        ch = EmailChannel({"mock_mode": True})
        n = Notification(
            title="Test",
            body="Body",
            recipients=[],
            channels=[NotificationChannel.EMAIL],
        )
        ch.send(n)
        stats = ch.get_stats()
        assert stats["failed"] == 1


class TestSMSChannel:
    """Test SMS notification channel."""

    def test_channel_type(self):
        ch = SMSChannel()
        assert ch.channel_type == NotificationChannel.SMS

    def test_send_mock(self):
        ch = SMSChannel({"mock_mode": True})
        n = Notification(
            title="Test SMS",
            body="Test body",
            recipients=["+1234567890"],
            channels=[NotificationChannel.SMS],
        )
        result = ch.send(n)
        assert result.success is True
        assert result.channel == NotificationChannel.SMS

    def test_send_no_recipients(self):
        ch = SMSChannel({"mock_mode": True})
        n = Notification(
            title="Test",
            body="Body",
            recipients=[],
            channels=[NotificationChannel.SMS],
        )
        result = ch.send(n)
        assert result.success is False

    def test_get_stats(self):
        ch = SMSChannel({"mock_mode": True})
        n = Notification(
            title="Test",
            body="Body",
            recipients=["+1234567890"],
            channels=[NotificationChannel.SMS],
        )
        ch.send(n)
        stats = ch.get_stats()
        assert stats["sent"] == 1


class TestPushChannel:
    """Test push notification channel."""

    def test_channel_type(self):
        ch = PushChannel()
        assert ch.channel_type == NotificationChannel.PUSH

    def test_send_mock(self):
        ch = PushChannel({"mock_mode": True})
        n = Notification(
            title="Test Push",
            body="Test body",
            recipients=["device_token_123"],
            channels=[NotificationChannel.PUSH],
        )
        result = ch.send(n)
        assert result.success is True
        assert result.channel == NotificationChannel.PUSH

    def test_send_no_recipients(self):
        ch = PushChannel({"mock_mode": True})
        n = Notification(
            title="Test",
            body="Body",
            recipients=[],
            channels=[NotificationChannel.PUSH],
        )
        result = ch.send(n)
        assert result.success is False

    def test_get_stats(self):
        ch = PushChannel({"mock_mode": True})
        n = Notification(
            title="Test",
            body="Body",
            recipients=["token"],
            channels=[NotificationChannel.PUSH],
        )
        ch.send(n)
        stats = ch.get_stats()
        assert stats["sent"] == 1


class TestWebhookChannel:
    """Test webhook notification channel."""

    def test_channel_type(self):
        ch = WebhookChannel()
        assert ch.channel_type == NotificationChannel.WEBHOOK

    def test_send_mock(self):
        ch = WebhookChannel({"mock_mode": True, "url": "https://example.com/hook"})
        n = Notification(
            title="Test Webhook",
            body="Test body",
            channels=[NotificationChannel.WEBHOOK],
        )
        result = ch.send(n)
        assert result.success is True
        assert result.channel == NotificationChannel.WEBHOOK

    def test_send_no_url(self):
        ch = WebhookChannel({"mock_mode": True})
        n = Notification(
            title="Test",
            body="Body",
            channels=[NotificationChannel.WEBHOOK],
        )
        result = ch.send(n)
        assert result.success is False
        assert "No URL" in result.error

    def test_get_stats(self):
        ch = WebhookChannel({"mock_mode": True, "url": "https://example.com/hook"})
        n = Notification(
            title="Test",
            body="Body",
            channels=[NotificationChannel.WEBHOOK],
        )
        ch.send(n)
        stats = ch.get_stats()
        assert stats["sent"] == 1


class TestChannelResult:
    """Test ChannelResult data class."""

    def test_success_result(self):
        r = ChannelResult(success=True, channel=NotificationChannel.EMAIL)
        assert r.success is True
        assert r.channel == NotificationChannel.EMAIL

    def test_failure_result(self):
        r = ChannelResult(
            success=False,
            channel=NotificationChannel.EMAIL,
            error="timeout",
        )
        assert r.success is False
        assert r.error == "timeout"


# ---------------------------------------------------------------------------
# Templates
# ---------------------------------------------------------------------------

class TestNotificationTemplate:
    """Test notification template."""

    def test_render(self):
        t = NotificationTemplate(
            id="test",
            name="Test",
            title_template="Hello {{name}}",
            body_template="Your order #{{order_id}} is ready",
        )
        result = t.render({"name": "Alice", "order_id": "123"})
        assert result["title"] == "Hello Alice"
        assert result["body"] == "Your order #123 is ready"

    def test_render_missing_var(self):
        t = NotificationTemplate(
            id="test",
            name="Test",
            title_template="Hello {{name}}",
            body_template="Body",
        )
        result = t.render({})
        assert result["title"] == "Hello {{name}}"

    def test_template_with_channels(self):
        t = NotificationTemplate(
            id="test",
            name="Test",
            title_template="Title",
            body_template="Body",
            channels=["email", "push"],
        )
        assert "email" in t.channels
        assert "push" in t.channels


class TestTemplateRegistry:
    """Test template registry."""

    def test_register_and_get(self):
        reg = TemplateRegistry()
        t = NotificationTemplate(
            id="custom",
            name="Custom",
            title_template="Title",
            body_template="Body",
        )
        reg.register(t)
        assert reg.get("custom") is t

    def test_get_nonexistent(self):
        reg = TemplateRegistry()
        assert reg.get("nonexistent") is None

    def test_list_templates(self):
        reg = TemplateRegistry()
        templates = reg.list_templates()
        assert len(templates) > 0

    def test_remove_template(self):
        reg = TemplateRegistry()
        assert reg.remove("welcome") is True
        assert reg.get("welcome") is None

    def test_remove_nonexistent(self):
        reg = TemplateRegistry()
        assert reg.remove("nonexistent") is False

    def test_render_by_id(self):
        reg = TemplateRegistry()
        result = reg.render("welcome", {"name": "Bob"})
        assert result is not None
        assert "Bob" in result["title"]

    def test_render_nonexistent(self):
        reg = TemplateRegistry()
        result = reg.render("nonexistent", {})
        assert result is None

    def test_default_templates_exist(self):
        reg = TemplateRegistry()
        expected = [
            "welcome",
            "password_reset",
            "order_confirmation",
            "payment_received",
            "alert",
            "task_assigned",
            "meeting_reminder",
            "invoice_overdue",
            "system_maintenance",
            "security_alert",
        ]
        for tid in expected:
            assert reg.get(tid) is not None, f"Template {tid} not found"


# ---------------------------------------------------------------------------
# Manager
# ---------------------------------------------------------------------------

class TestNotificationManager:
    """Test notification manager."""

    def test_register_channel(self):
        mgr = NotificationManager()
        ch = EmailChannel({"mock_mode": True})
        mgr.register_channel(ch)
        assert mgr.get_channel(NotificationChannel.EMAIL) is ch

    def test_unregister_channel(self):
        mgr = NotificationManager()
        ch = EmailChannel({"mock_mode": True})
        mgr.register_channel(ch)
        assert mgr.unregister_channel(NotificationChannel.EMAIL) is True
        assert mgr.get_channel(NotificationChannel.EMAIL) is None

    def test_unregister_nonexistent(self):
        mgr = NotificationManager()
        assert mgr.unregister_channel(NotificationChannel.EMAIL) is False

    def test_create_notification(self):
        mgr = NotificationManager()
        n = mgr.create_notification(
            title="Test",
            body="Body",
            channels=[NotificationChannel.EMAIL],
            recipients=["a@b.com"],
        )
        assert n.title == "Test"
        assert n.id in mgr._notifications

    def test_create_from_template(self):
        mgr = NotificationManager()
        n = mgr.create_from_template(
            "welcome",
            {"name": "Alice"},
            recipients=["alice@example.com"],
        )
        assert n is not None
        assert "Alice" in n.title
        assert n.template_id == "welcome"

    def test_create_from_nonexistent_template(self):
        mgr = NotificationManager()
        n = mgr.create_from_template("nonexistent", {}, [])
        assert n is None

    def test_send_notification(self):
        mgr = NotificationManager()
        mgr.register_channel(EmailChannel({"mock_mode": True}))
        n = mgr.create_notification(
            title="Test",
            body="Body",
            channels=[NotificationChannel.EMAIL],
            recipients=["a@b.com"],
        )
        results = mgr.send(n)
        assert NotificationChannel.EMAIL in results
        assert results[NotificationChannel.EMAIL].success is True

    def test_send_unregistered_channel(self):
        mgr = NotificationManager()
        n = mgr.create_notification(
            title="Test",
            body="Body",
            channels=[NotificationChannel.EMAIL],
            recipients=["a@b.com"],
        )
        results = mgr.send(n)
        assert results[NotificationChannel.EMAIL].success is False

    def test_send_by_id(self):
        mgr = NotificationManager()
        mgr.register_channel(EmailChannel({"mock_mode": True}))
        n = mgr.create_notification(
            title="Test",
            body="Body",
            channels=[NotificationChannel.EMAIL],
            recipients=["a@b.com"],
        )
        results = mgr.send_by_id(n.id)
        assert results is not None
        assert results[NotificationChannel.EMAIL].success is True

    def test_send_by_nonexistent_id(self):
        mgr = NotificationManager()
        results = mgr.send_by_id("nonexistent")
        assert results is None

    def test_retry(self):
        mgr = NotificationManager()
        mgr.register_channel(EmailChannel({"mock_mode": True}))
        n = mgr.create_notification(
            title="Test",
            body="Body",
            channels=[NotificationChannel.EMAIL],
            recipients=["a@b.com"],
        )
        n.mark_failed("error")
        results = mgr.retry(n)
        assert n.retry_count == 1
        assert NotificationChannel.EMAIL in results

    def test_retry_exceeded(self):
        mgr = NotificationManager()
        mgr.register_channel(EmailChannel({"mock_mode": True}))
        n = mgr.create_notification(
            title="Test",
            body="Body",
            channels=[NotificationChannel.EMAIL],
            recipients=["a@b.com"],
        )
        n.max_retries = 1
        n.retry_count = 1
        results = mgr.retry(n)
        assert results == {}

    def test_get_notification(self):
        mgr = NotificationManager()
        n = mgr.create_notification(
            title="Test",
            body="Body",
            channels=[NotificationChannel.EMAIL],
            recipients=["a@b.com"],
        )
        assert mgr.get_notification(n.id) is n

    def test_get_nonexistent_notification(self):
        mgr = NotificationManager()
        assert mgr.get_notification("nonexistent") is None

    def test_get_history(self):
        mgr = NotificationManager()
        mgr.register_channel(EmailChannel({"mock_mode": True}))
        n = mgr.create_notification(
            title="Test",
            body="Body",
            channels=[NotificationChannel.EMAIL],
            recipients=["a@b.com"],
        )
        mgr.send(n)
        history = mgr.get_history()
        assert len(history) >= 1

    def test_get_history_by_status(self):
        mgr = NotificationManager()
        mgr.register_channel(EmailChannel({"mock_mode": True}))
        n = mgr.create_notification(
            title="Test",
            body="Body",
            channels=[NotificationChannel.EMAIL],
            recipients=["a@b.com"],
        )
        mgr.send(n)
        history = mgr.get_history(status=NotificationStatus.SENT)
        assert len(history) >= 1

    def test_get_history_by_channel(self):
        mgr = NotificationManager()
        mgr.register_channel(EmailChannel({"mock_mode": True}))
        n = mgr.create_notification(
            title="Test",
            body="Body",
            channels=[NotificationChannel.EMAIL],
            recipients=["a@b.com"],
        )
        mgr.send(n)
        history = mgr.get_history(channel=NotificationChannel.EMAIL)
        assert len(history) >= 1

    def test_get_stats(self):
        mgr = NotificationManager()
        mgr.register_channel(EmailChannel({"mock_mode": True}))
        n = mgr.create_notification(
            title="Test",
            body="Body",
            channels=[NotificationChannel.EMAIL],
            recipients=["a@b.com"],
        )
        mgr.send(n)
        stats = mgr.get_stats()
        assert stats["total"] >= 1
        assert "by_status" in stats
        assert "by_channel" in stats
        assert "channels" in stats

    def test_clear_history(self):
        mgr = NotificationManager()
        mgr.register_channel(EmailChannel({"mock_mode": True}))
        n = mgr.create_notification(
            title="Test",
            body="Body",
            channels=[NotificationChannel.EMAIL],
            recipients=["a@b.com"],
        )
        mgr.send(n)
        mgr.clear_history()
        assert len(mgr.get_history()) == 0

    def test_template_registry_property(self):
        mgr = NotificationManager()
        assert mgr.template_registry is not None
        assert isinstance(mgr.template_registry, TemplateRegistry)

    def test_multi_channel_send(self):
        mgr = NotificationManager()
        mgr.register_channel(EmailChannel({"mock_mode": True}))
        mgr.register_channel(SMSChannel({"mock_mode": True}))
        n = mgr.create_notification(
            title="Test",
            body="Body",
            channels=[NotificationChannel.EMAIL, NotificationChannel.SMS],
            recipients=["a@b.com", "+1234567890"],
        )
        results = mgr.send(n)
        assert len(results) == 2
        assert results[NotificationChannel.EMAIL].success is True
        assert results[NotificationChannel.SMS].success is True

    def test_create_from_template_with_custom_channels(self):
        mgr = NotificationManager()
        n = mgr.create_from_template(
            "welcome",
            {"name": "Alice"},
            recipients=["alice@example.com"],
            channels=[NotificationChannel.EMAIL, NotificationChannel.PUSH],
        )
        assert n is not None
        assert NotificationChannel.PUSH in n.channels

    def test_create_from_template_with_custom_priority(self):
        mgr = NotificationManager()
        n = mgr.create_from_template(
            "welcome",
            {"name": "Alice"},
            recipients=["alice@example.com"],
            priority=NotificationPriority.HIGH,
        )
        assert n is not None
        assert n.priority == NotificationPriority.HIGH

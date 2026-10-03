"""Tests for deepened notification modules: push, in-app, preferences, templates, analytics."""
import pytest
from unittest.mock import MagicMock, patch, call


class TestPushNotifications:
    """Test push notification delivery."""

    def test_send_push(self):
        from apex_os_bp.notifications.deepened import PushNotifier
        notifier = PushNotifier()
        with patch.object(notifier, "_send_fcm") as mock_send:
            notifier.send(device_token="tok123", title="Hello", body="World")
            mock_send.assert_called_once()

    def test_push_with_data(self):
        from apex_os_bp.notifications.deepened import PushNotifier
        notifier = PushNotifier()
        with patch.object(notifier, "_send_fcm") as mock_send:
            notifier.send(device_token="t1", title="T", body="B", data={"order_id": 42})
            _, kwargs = mock_send.call_args
            assert kwargs.get("data", {}).get("order_id") == 42

    def test_push_batch(self):
        from apex_os_bp.notifications.deepened import PushNotifier
        notifier = PushNotifier()
        with patch.object(notifier, "_send_fcm") as mock_send:
            notifier.send_batch(tokens=["t1", "t2", "t3"], title="Hi", body="Msg")
            assert mock_send.call_count == 3

    def test_push_invalid_token(self):
        from apex_os_bp.notifications.deepened import PushNotifier
        notifier = PushNotifier()
        with patch.object(notifier, "_send_fcm", side_effect=Exception("invalid")):
            result = notifier.send(device_token="bad", title="T", body="B")
            assert result is False


class TestInAppNotifications:
    """Test in-app notifications."""

    def test_create_notification(self):
        from apex_os_bp.notifications.deepened import InAppNotifier
        notifier = InAppNotifier()
        notif = notifier.create(user_id=1, message="Welcome", type="info")
        assert notif["user_id"] == 1
        assert notif["message"] == "Welcome"
        assert notif["read"] is False

    def test_mark_as_read(self):
        from apex_os_bp.notifications.deepened import InAppNotifier
        notifier = InAppNotifier()
        notif = notifier.create(user_id=1, message="Test")
        notifier.mark_read(notif["id"])
        assert notifier.get(notif["id"])["read"] is True

    def test_list_unread(self):
        from apex_os_bp.notifications.deepened import InAppNotifier
        notifier = InAppNotifier()
        notifier.create(user_id=1, message="A")
        notifier.create(user_id=1, message="B")
        unread = notifier.list_unread(user_id=1)
        assert len(unread) == 2


class TestNotificationPreferences:
    """Test notification preferences."""

    def test_default_preferences(self):
        from apex_os_bp.notifications.deepened import PreferenceManager
        mgr = PreferenceManager()
        prefs = mgr.get(user_id=1)
        assert prefs["email"] is True
        assert prefs["push"] is True

    def test_update_preference(self):
        from apex_os_bp.notifications.deepened import PreferenceManager
        mgr = PreferenceManager()
        mgr.set(user_id=1, channel="email", enabled=False)
        assert mgr.get(user_id=1)["email"] is False

    def test_should_notify(self):
        from apex_os_bp.notifications.deepened import PreferenceManager
        mgr = PreferenceManager()
        mgr.set(user_id=1, channel="push", enabled=False)
        assert mgr.should_notify(user_id=1, channel="push") is False
        assert mgr.should_notify(user_id=1, channel="email") is True


class TestNotificationTemplates:
    """Test notification templates."""

    def test_render_template(self):
        from apex_os_bp.notifications.deepened import TemplateEngine
        engine = TemplateEngine()
        result = engine.render("welcome", {"name": "Alice"})
        assert "Alice" in result

    def test_template_with_missing_var(self):
        from apex_os_bp.notifications.deepened import TemplateEngine
        engine = TemplateEngine()
        result = engine.render("welcome", {})
        assert result is not None

    def test_register_template(self):
        from apex_os_bp.notifications.deepened import TemplateEngine
        engine = TemplateEngine()
        engine.register("custom", "Hello {{name}}!")
        assert engine.render("custom", {"name": "Bob"}) == "Hello Bob!"


class TestNotificationAnalytics:
    """Test notification analytics."""

    def test_track_sent(self):
        from apex_os_bp.notifications.deepened import NotificationAnalytics
        analytics = NotificationAnalytics()
        analytics.track_sent(channel="push", count=10)
        assert analytics.total_sent("push") == 10

    def test_track_delivered(self):
        from apex_os_bp.notifications.deepened import NotificationAnalytics
        analytics = NotificationAnalytics()
        analytics.track_delivered(channel="email", count=8)
        assert analytics.total_delivered("email") == 8

    def test_delivery_rate(self):
        from apex_os_bp.notifications.deepened import NotificationAnalytics
        analytics = NotificationAnalytics()
        analytics.track_sent(channel="push", count=10)
        analytics.track_delivered(channel="push", count=7)
        assert analytics.delivery_rate("push") == 0.7

"""Deepened notifications module: push, in-app, preferences, templates, analytics."""
from __future__ import annotations
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable


# ── Push Notifications (FCM / APNs) ────────────────────────────────────────

class PushProvider(Enum):
    FCM = "fcm"
    APNS = "apns"


@dataclass
class PushToken:
    token: str
    provider: PushProvider
    user_id: str
    device_id: str
    created_at: float = field(default_factory=time.time)


@dataclass
class PushResult:
    success: bool
    message_id: str
    error: str | None = None


class PushNotifier:
    """Sends push notifications via FCM or APNs."""

    def __init__(self) -> None:
        self._tokens: dict[str, PushToken] = {}
        self._handlers: dict[PushProvider, Callable] = {}

    def register_handler(self, provider: PushProvider, handler: Callable) -> None:
        self._handlers[provider] = handler

    def register_token(self, token: PushToken) -> None:
        self._tokens[token.user_id] = token

    def send(self, user_id: str, title: str, body: str,
             data: dict[str, Any] | None = None) -> PushResult:
        pt = self._tokens.get(user_id)
        if not pt:
            return PushResult(False, "", "no_token")
        handler = self._handlers.get(pt.provider)
        if not handler:
            return PushResult(False, "", "no_handler")
        msg_id = str(uuid.uuid4())
        try:
            handler(pt.token, title, body, data or {})
            return PushResult(True, msg_id)
        except Exception as exc:
            return PushResult(False, msg_id, str(exc))

    def send_multicast(self, user_ids: list[str], title: str, body: str,
                       data: dict[str, Any] | None = None) -> list[PushResult]:
        return [self.send(uid, title, body, data) for uid in user_ids]


# ── In-App Notifications (Real-Time) ───────────────────────────────────────

class NotificationPriority(Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


@dataclass
class InAppNotification:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = ""
    title: str = ""
    body: str = ""
    priority: NotificationPriority = NotificationPriority.NORMAL
    read: bool = False
    created_at: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)


class InAppNotifier:
    """Real-time in-app notification delivery."""

    def __init__(self) -> None:
        self._notifications: dict[str, list[InAppNotification]] = {}
        self._listeners: dict[str, list[Callable]] = {}

    def subscribe(self, user_id: str, callback: Callable) -> None:
        self._listeners.setdefault(user_id, []).append(callback)

    def unsubscribe(self, user_id: str, callback: Callable) -> None:
        if user_id in self._listeners:
            self._listeners[user_id] = [
                cb for cb in self._listeners[user_id] if cb is not callback
            ]

    def notify(self, user_id: str, title: str, body: str,
               priority: NotificationPriority = NotificationPriority.NORMAL,
               metadata: dict[str, Any] | None = None) -> InAppNotification:
        notif = InAppNotification(
            user_id=user_id, title=title, body=body,
            priority=priority, metadata=metadata or {},
        )
        self._notifications.setdefault(user_id, []).append(notif)
        for cb in self._listeners.get(user_id, []):
            cb(notif)
        return notif

    def get_unread(self, user_id: str) -> list[InAppNotification]:
        return [n for n in self._notifications.get(user_id, []) if not n.read]

    def mark_read(self, user_id: str, notif_id: str) -> bool:
        for n in self._notifications.get(user_id, []):
            if n.id == notif_id:
                n.read = True
                return True
        return False

    def mark_all_read(self, user_id: str) -> int:
        count = 0
        for n in self._notifications.get(user_id, []):
            if not n.read:
                n.read = True
                count += 1
        return count


# ── Notification Preferences ───────────────────────────────────────────────

class NotificationChannel(Enum):
    PUSH = "push"
    IN_APP = "in_app"
    EMAIL = "email"
    SMS = "sms"


@dataclass
class NotificationPreferences:
    user_id: str
    channels: dict[str, dict[str, bool]] = field(default_factory=dict)
    quiet_hours_start: int | None = None
    quiet_hours_end: int | None = None
    muted_categories: set[str] = field(default_factory=set)

    def __post_init__(self) -> None:
        if not self.channels:
            self.channels = {
                cat: {ch.value: True for ch in NotificationChannel}
                for cat in ("system", "marketing", "social", "billing", "security")
            }

    def is_enabled(self, category: str, channel: NotificationChannel) -> bool:
        if category in self.muted_categories:
            return False
        return self.channels.get(category, {}).get(channel.value, False)

    def set_channel(self, category: str, channel: NotificationChannel,
                    enabled: bool) -> None:
        self.channels.setdefault(category, {})[channel.value] = enabled

    def mute_category(self, category: str) -> None:
        self.muted_categories.add(category)

    def unmute_category(self, category: str) -> None:
        self.muted_categories.discard(category)

    def in_quiet_hours(self, hour: int | None = None) -> bool:
        if self.quiet_hours_start is None or self.quiet_hours_end is None:
            return False
        h = hour if hour is not None else int(time.strftime("%H"))
        if self.quiet_hours_start <= self.quiet_hours_end:
            return self.quiet_hours_start <= h < self.quiet_hours_end
        return h >= self.quiet_hours_start or h < self.quiet_hours_end


class PreferenceStore:
    """Stores and retrieves user notification preferences."""

    def __init__(self) -> None:
        self._prefs: dict[str, NotificationPreferences] = {}

    def get(self, user_id: str) -> NotificationPreferences:
        if user_id not in self._prefs:
            self._prefs[user_id] = NotificationPreferences(user_id=user_id)
        return self._prefs[user_id]

    def save(self, prefs: NotificationPreferences) -> None:
        self._prefs[prefs.user_id] = prefs


# ── Notification Templates ─────────────────────────────────────────────────

class TemplateEngine:
    """Renders notification templates with variable substitution."""

    def __init__(self) -> None:
        self._templates: dict[str, str] = {}

    def register(self, name: str, template: str) -> None:
        self._templates[name] = template

    def render(self, name: str, variables: dict[str, Any]) -> str:
        tmpl = self._templates.get(name, "")
        result = tmpl
        for key, val in variables.items():
            result = result.replace("{" + key + "}", str(val))
        return result

    def render_many(self, name: str,
                    variable_sets: list[dict[str, Any]]) -> list[str]:
        return [self.render(name, vs) for vs in variable_sets]


# ── Notification Analytics ─────────────────────────────────────────────────

@dataclass
class DeliveryRecord:
    notification_id: str
    user_id: str
    channel: str
    event: str  # sent, delivered, opened, failed
    timestamp: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)


class NotificationAnalytics:
    """Tracks notification delivery metrics."""

    def __init__(self) -> None:
        self._records: list[DeliveryRecord] = []

    def track(self, notification_id: str, user_id: str, channel: str,
              event: str, metadata: dict[str, Any] | None = None) -> None:
        self._records.append(DeliveryRecord(
            notification_id=notification_id, user_id=user_id,
            channel=channel, event=event, metadata=metadata or {},
        ))

    def get_stats(self, channel: str | None = None) -> dict[str, int]:
        records = self._records
        if channel:
            records = [r for r in records if r.channel == channel]
        stats: dict[str, int] = {}
        for r in records:
            stats[r.event] = stats.get(r.event, 0) + 1
        return stats

    def delivery_rate(self, channel: str | None = None) -> float:
        stats = self.get_stats(channel)
        sent = stats.get("sent", 0)
        if sent == 0:
            return 0.0
        return stats.get("delivered", 0) / sent

    def open_rate(self, channel: str | None = None) -> float:
        stats = self.get_stats(channel)
        delivered = stats.get("delivered", 0)
        if delivered == 0:
            return 0.0
        return stats.get("opened", 0) / delivered

    def events_for(self, notification_id: str) -> list[DeliveryRecord]:
        return [r for r in self._records if r.notification_id == notification_id]


# ── Unified Facade ─────────────────────────────────────────────────────────

class NotificationManager:
    """Unified facade combining all notification subsystems."""

    def __init__(self) -> None:
        self.push = PushNotifier()
        self.in_app = InAppNotifier()
        self.preferences = PreferenceStore()
        self.templates = TemplateEngine()
        self.analytics = NotificationAnalytics()

    def notify(self, user_id: str, category: str, template_name: str,
               variables: dict[str, Any], title: str = "",
               priority: NotificationPriority = NotificationPriority.NORMAL,
               channels: list[NotificationChannel] | None = None) -> dict[str, Any]:
        prefs = self.preferences.get(user_id)
        results: dict[str, Any] = {}
        target_channels = channels or list(NotificationChannel)
        body = self.templates.render(template_name, variables)
        notif_title = title or template_name
        for ch in target_channels:
            if not prefs.is_enabled(category, ch):
                continue
            if ch == NotificationChannel.PUSH:
                res = self.push.send(user_id, notif_title, body, variables)
                results["push"] = res
                self.analytics.track(res.message_id, user_id, "push",
                                     "sent" if res.success else "failed")
            elif ch == NotificationChannel.IN_APP:
                n = self.in_app.notify(user_id, notif_title, body, priority, variables)
                results["in_app"] = n
                self.analytics.track(n.id, user_id, "in_app", "sent")
        return results

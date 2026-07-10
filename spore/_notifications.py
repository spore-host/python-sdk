"""notifications — register/deregister a phone number for SMS lifecycle alerts."""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from .client import Client


class NotificationsClient:
    """Manage SMS notification registration (POST/DELETE /v1/notifications/register).

    A phone number is keyed by a chat-platform ``user_key`` — the same identity
    spore-bot uses — of the form ``"{platform}#{workspace_id}#{user_id}"`` (e.g.
    ``slack#T0ABC#U0XYZ``). It is NOT derived from your AWS credentials or API
    key, so you must supply it: either the three parts (``platform``,
    ``workspace_id``, ``user_id``) or a pre-built ``user_key``.
    """

    def __init__(self, client: "Client"):
        self._c = client

    def register(
        self,
        phone: str,
        *,
        platform: Optional[str] = None,
        workspace_id: Optional[str] = None,
        user_id: Optional[str] = None,
        user_key: Optional[str] = None,
    ) -> dict:
        """Register ``phone`` for SMS notifications.

        Provide either ``user_key`` directly, or all three of ``platform`` /
        ``workspace_id`` / ``user_id`` (from your Slack/Teams setup).

        Example:
            >>> spore.notifications.register(
            ...     "+15551234567", platform="slack",
            ...     workspace_id="T0ABC", user_id="U0XYZ",
            ... )
        """
        key = self._resolve_user_key(user_key, platform, workspace_id, user_id)
        return self._c.post(
            "/v1/notifications/register", {"phone": phone, "user_key": key}
        )

    def deregister(
        self,
        *,
        platform: Optional[str] = None,
        workspace_id: Optional[str] = None,
        user_id: Optional[str] = None,
        user_key: Optional[str] = None,
    ) -> dict:
        """Remove the SMS registration for a user (same identity args as register)."""
        key = self._resolve_user_key(user_key, platform, workspace_id, user_id)
        return self._c.delete("/v1/notifications/register", {"user_key": key})

    # ── Internal ──────────────────────────────────────────────────────────────

    @staticmethod
    def _resolve_user_key(
        user_key: Optional[str],
        platform: Optional[str],
        workspace_id: Optional[str],
        user_id: Optional[str],
    ) -> str:
        """Return an explicit ``user_key`` or build it from the identity triple.

        Mirrors spawn's registration key (spawn/cmd/bot.go):
        ``"{platform}#{workspace_id}#{user_id}"``.
        """
        if user_key:
            return user_key
        if platform and workspace_id and user_id:
            return f"{platform}#{workspace_id}#{user_id}"
        raise ValueError(
            "notifications require an identity: pass user_key=, or all of "
            "platform=, workspace_id=, and user_id= (from your Slack/Teams setup)."
        )

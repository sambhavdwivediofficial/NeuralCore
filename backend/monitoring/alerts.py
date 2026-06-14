# monitoring/alerts.py
from __future__ import annotations

import enum
import smtplib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from email.message import EmailMessage
from typing import Any

import httpx

from monitoring.logging import get_logger
from settings import Settings

logger = get_logger("neuralcore.alerts")


class AlertSeverity(str, enum.Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass(slots=True, frozen=True)
class AlertRule:
    name: str
    severity: AlertSeverity
    description: str
    metric: str
    threshold: float
    for_minutes: int


ALERT_RULES: tuple[AlertRule, ...] = (
    AlertRule("HighAPILatency", AlertSeverity.WARNING, "P95 API latency is above threshold", "neuralcore_http_request_duration_seconds", 2.0, 5),
    AlertRule("HighErrorRate", AlertSeverity.CRITICAL, "HTTP 5xx error rate is above threshold", "neuralcore_http_requests_total", 0.05, 5),
    AlertRule("PodCrashLooping", AlertSeverity.CRITICAL, "A pod is restarting repeatedly", "kube_pod_container_status_restarts_total", 3, 15),
    AlertRule("DatabaseConnectionsHigh", AlertSeverity.WARNING, "Database connection pool usage is high", "neuralcore_db_pool_connections_in_use", 0.9, 5),
    AlertRule("HighMemoryUsage", AlertSeverity.WARNING, "Node memory usage is above threshold", "node_memory_usage_percent", 90.0, 10),
    AlertRule("HighDiskUsage", AlertSeverity.WARNING, "Disk usage is above threshold", "node_disk_usage_percent", 90.0, 10),
    AlertRule("QuotaExceeded", AlertSeverity.WARNING, "A tenant exceeded its plan quota", "neuralcore_quota_usage_ratio", 1.0, 1),
    AlertRule("IngestionFailureRateHigh", AlertSeverity.CRITICAL, "Ingestion job failure rate is above threshold", "neuralcore_ingestion_documents_total", 0.1, 15),
    AlertRule("LLMProviderErrorRateHigh", AlertSeverity.CRITICAL, "LLM provider error rate is above threshold", "neuralcore_llm_call_duration_seconds", 0.1, 5),
)


@dataclass(slots=True, frozen=True)
class Alert:
    rule_name: str
    severity: AlertSeverity
    message: str
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


def get_rule(name: str) -> AlertRule | None:
    return next((rule for rule in ALERT_RULES if rule.name == name), None)


class AlertDispatcher:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def dispatch(self, alert: Alert) -> None:
        destinations = self.settings.monitoring.alert_destinations
        logger.warning(
            "alert_triggered",
            rule=alert.rule_name,
            severity=alert.severity.value,
            message=alert.message,
            metadata=alert.metadata,
        )

        if destinations.slack_webhook_url is not None:
            await self._send_slack(alert, destinations.slack_webhook_url.get_secret_value())

        if alert.severity == AlertSeverity.CRITICAL and destinations.pagerduty_routing_key is not None:
            await self._send_pagerduty(alert, destinations.pagerduty_routing_key.get_secret_value())

        if alert.severity == AlertSeverity.CRITICAL and destinations.alert_email:
            self._send_email(alert, destinations.alert_email)

    async def _send_slack(self, alert: Alert, webhook_url: str) -> None:
        payload = {
            "text": f"*[{alert.severity.value.upper()}] {alert.rule_name}*\n{alert.message}",
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": (
                            f"*[{alert.severity.value.upper()}] {alert.rule_name}*\n"
                            f"{alert.message}\n"
                            f"```{alert.metadata}```"
                        ),
                    },
                }
            ],
        }
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(webhook_url, json=payload)
                response.raise_for_status()
        except httpx.HTTPError:
            logger.error("slack_alert_dispatch_failed", rule=alert.rule_name, exc_info=True)

    async def _send_pagerduty(self, alert: Alert, routing_key: str) -> None:
        payload = {
            "routing_key": routing_key,
            "event_action": "trigger",
            "payload": {
                "summary": f"[{alert.rule_name}] {alert.message}",
                "source": self.settings.monitoring.otlp.service_name,
                "severity": "critical" if alert.severity == AlertSeverity.CRITICAL else "warning",
                "custom_details": alert.metadata,
            },
        }
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post("https://events.pagerduty.com/v2/enqueue", json=payload)
                response.raise_for_status()
        except httpx.HTTPError:
            logger.error("pagerduty_alert_dispatch_failed", rule=alert.rule_name, exc_info=True)

    def _send_email(self, alert: Alert, recipient: str) -> None:
        message = EmailMessage()
        message["Subject"] = f"[{alert.severity.value.upper()}] {alert.rule_name} - {self.settings.project_name}"
        message["From"] = f"alerts@{self.settings.project_name.lower()}.local"
        message["To"] = recipient
        message.set_content(
            f"{alert.message}\n\nMetadata:\n{alert.metadata}\n\nTimestamp: {alert.timestamp.isoformat()}"
        )
        try:
            with smtplib.SMTP("localhost", timeout=5) as smtp:
                smtp.send_message(message)
        except (OSError, smtplib.SMTPException):
            logger.error("email_alert_dispatch_failed", rule=alert.rule_name, exc_info=True)
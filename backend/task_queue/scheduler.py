# queue/scheduler.py
from __future__ import annotations

from celery.schedules import crontab


def build_beat_schedule() -> dict[str, dict]:
    return {
        "purge-expired-memories": {
            "task": "queue.tasks.cleanup.purge_expired_memories",
            "schedule": crontab(minute=0),
        },
        "unlock-expired-accounts": {
            "task": "queue.tasks.cleanup.unlock_expired_accounts",
            "schedule": crontab(minute="*/15"),
        },
        "cleanup-expired-invites": {
            "task": "queue.tasks.cleanup.cleanup_expired_invites",
            "schedule": crontab(hour=3, minute=0),
        },
        "purge-cancelled-organizations": {
            "task": "queue.tasks.cleanup.purge_cancelled_organizations",
            "schedule": crontab(hour=4, minute=0),
        },
    }
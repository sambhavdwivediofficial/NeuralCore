# auth/validators.py
from __future__ import annotations

import re

_EMAIL_PATTERN = re.compile(r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$")
_SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_NAME_PATTERN = re.compile(r"^[\w\s.,'\-]{1,255}$", re.UNICODE)


class ValidationError(ValueError):
    pass


def normalize_email(email: str) -> str:
    email = email.strip().lower()
    if not _EMAIL_PATTERN.match(email):
        raise ValidationError("Invalid email address format")
    return email


def validate_slug(slug: str) -> str:
    slug = slug.strip().lower()
    if not _SLUG_PATTERN.match(slug):
        raise ValidationError("Slug must be lowercase alphanumeric with single hyphens")
    if len(slug) < 3 or len(slug) > 63:
        raise ValidationError("Slug must be between 3 and 63 characters")
    return slug


def validate_display_name(name: str) -> str:
    name = name.strip()
    if not name:
        raise ValidationError("Name cannot be empty")
    if not _NAME_PATTERN.match(name):
        raise ValidationError("Name contains invalid characters")
    return name


def validate_organization_name(name: str) -> str:
    name = validate_display_name(name)
    if len(name) < 2:
        raise ValidationError("Organization name must be at least 2 characters")
    return name


def is_disposable_email_domain(email: str, blocked_domains: set[str]) -> bool:
    domain = email.rsplit("@", 1)[-1].lower()
    return domain in blocked_domains
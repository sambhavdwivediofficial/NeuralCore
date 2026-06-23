# backend/services/email_service.py
from __future__ import annotations

import asyncio
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

import aiosmtplib

from settings import settings

logger = logging.getLogger(__name__)


def _build_password_reset_html(reset_url: str, name: str) -> str:
    return f"""
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>Reset Password</title></head>
<body style="font-family:Arial,sans-serif;background:#f4f4f4;margin:0;padding:0;">
  <table width="100%" cellpadding="0" cellspacing="0">
    <tr><td align="center" style="padding:40px 0;">
      <table width="600" cellpadding="0" cellspacing="0" style="background:#fff;border-radius:8px;box-shadow:0 2px 8px rgba(0,0,0,.1);">
        <tr><td style="padding:40px;">
          <h1 style="color:#1a1a1a;font-size:24px;margin:0 0 16px;">Reset your password</h1>
          <p style="color:#555;font-size:16px;line-height:1.6;">Hi {name},</p>
          <p style="color:#555;font-size:16px;line-height:1.6;">
            We received a request to reset your NeuralCore password. Click the button below to choose a new one.
          </p>
          <table cellpadding="0" cellspacing="0" style="margin:32px 0;">
            <tr><td style="background:#6366f1;border-radius:6px;">
              <a href="{reset_url}" style="display:inline-block;padding:14px 32px;color:#fff;text-decoration:none;font-size:16px;font-weight:600;">
                Reset Password
              </a>
            </td></tr>
          </table>
          <p style="color:#888;font-size:14px;">This link expires in 1 hour. If you didn't request this, ignore this email.</p>
          <p style="color:#aaa;font-size:12px;margin-top:32px;border-top:1px solid #eee;padding-top:16px;">
            NeuralCore &mdash; Enterprise AI Platform
          </p>
        </td></tr>
      </table>
    </td></tr>
  </table>
</body>
</html>
"""


def _build_verify_email_html(verify_url: str, name: str) -> str:
    return f"""
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>Verify Email</title></head>
<body style="font-family:Arial,sans-serif;background:#f4f4f4;margin:0;padding:0;">
  <table width="100%" cellpadding="0" cellspacing="0">
    <tr><td align="center" style="padding:40px 0;">
      <table width="600" cellpadding="0" cellspacing="0" style="background:#fff;border-radius:8px;box-shadow:0 2px 8px rgba(0,0,0,.1);">
        <tr><td style="padding:40px;">
          <h1 style="color:#1a1a1a;font-size:24px;margin:0 0 16px;">Verify your email</h1>
          <p style="color:#555;font-size:16px;line-height:1.6;">Hi {name},</p>
          <p style="color:#555;font-size:16px;line-height:1.6;">
            Thanks for signing up for NeuralCore! Please verify your email address to get started.
          </p>
          <table cellpadding="0" cellspacing="0" style="margin:32px 0;">
            <tr><td style="background:#6366f1;border-radius:6px;">
              <a href="{verify_url}" style="display:inline-block;padding:14px 32px;color:#fff;text-decoration:none;font-size:16px;font-weight:600;">
                Verify Email
              </a>
            </td></tr>
          </table>
          <p style="color:#888;font-size:14px;">This link expires in 24 hours.</p>
          <p style="color:#aaa;font-size:12px;margin-top:32px;border-top:1px solid #eee;padding-top:16px;">
            NeuralCore &mdash; Enterprise AI Platform
          </p>
        </td></tr>
      </table>
    </td></tr>
  </table>
</body>
</html>
"""


def _build_invite_html(invite_url: str, inviter_name: str, org_name: str, role: str) -> str:
    return f"""
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>You're Invited</title></head>
<body style="font-family:Arial,sans-serif;background:#f4f4f4;margin:0;padding:0;">
  <table width="100%" cellpadding="0" cellspacing="0">
    <tr><td align="center" style="padding:40px 0;">
      <table width="600" cellpadding="0" cellspacing="0" style="background:#fff;border-radius:8px;box-shadow:0 2px 8px rgba(0,0,0,.1);">
        <tr><td style="padding:40px;">
          <h1 style="color:#1a1a1a;font-size:24px;margin:0 0 16px;">You've been invited to NeuralCore</h1>
          <p style="color:#555;font-size:16px;line-height:1.6;">
            <strong>{inviter_name}</strong> has invited you to join <strong>{org_name}</strong> as a <strong>{role}</strong>.
          </p>
          <table cellpadding="0" cellspacing="0" style="margin:32px 0;">
            <tr><td style="background:#6366f1;border-radius:6px;">
              <a href="{invite_url}" style="display:inline-block;padding:14px 32px;color:#fff;text-decoration:none;font-size:16px;font-weight:600;">
                Accept Invitation
              </a>
            </td></tr>
          </table>
          <p style="color:#888;font-size:14px;">This invitation expires in 72 hours.</p>
          <p style="color:#aaa;font-size:12px;margin-top:32px;border-top:1px solid #eee;padding-top:16px;">
            NeuralCore &mdash; Enterprise AI Platform
          </p>
        </td></tr>
      </table>
    </td></tr>
  </table>
</body>
</html>
"""


async def _send_email(to_email: str, subject: str, html_body: str, text_body: str) -> None:
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"NeuralCore <{settings.SMTP_FROM_EMAIL}>"
    msg["To"] = to_email
    msg.attach(MIMEText(text_body, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    try:
        await aiosmtplib.send(
            msg,
            hostname=settings.SMTP_HOST,
            port=settings.SMTP_PORT,
            username=settings.SMTP_USERNAME,
            password=settings.SMTP_PASSWORD,
            use_tls=settings.SMTP_USE_TLS,
            start_tls=settings.SMTP_START_TLS,
        )
    except Exception as exc:
        logger.error("Failed to send email to %s: %s", to_email, exc)
        raise


async def send_password_reset_email(
    to_email: str, name: str, raw_token: str
) -> None:
    reset_url = f"{settings.APP_URL}/reset-password/{raw_token}"
    html = _build_password_reset_html(reset_url, name)
    text = f"Hi {name},\n\nReset your password: {reset_url}\n\nThis link expires in 1 hour."
    await _send_email(to_email, "Reset your NeuralCore password", html, text)


async def send_verification_email(
    to_email: str, name: str, raw_token: str
) -> None:
    verify_url = f"{settings.APP_URL}/verify-email?token={raw_token}"
    html = _build_verify_email_html(verify_url, name)
    text = f"Hi {name},\n\nVerify your email: {verify_url}\n\nThis link expires in 24 hours."
    await _send_email(to_email, "Verify your NeuralCore email", html, text)


async def send_invite_email(
    to_email: str,
    inviter_name: str,
    org_name: str,
    role: str,
    invite_token: str,
) -> None:
    invite_url = f"{settings.APP_URL}/accept-invite/{invite_token}"
    html = _build_invite_html(invite_url, inviter_name, org_name, role)
    text = (
        f"{inviter_name} has invited you to join {org_name} on NeuralCore as {role}.\n\n"
        f"Accept invitation: {invite_url}\n\nThis link expires in 72 hours."
    )
    await _send_email(to_email, f"You've been invited to join {org_name} on NeuralCore", html, text)

"""
Notification Service
======================
Send notifications via WhatsApp and Telegram
when video processing is completed.
"""

import httpx
from typing import Optional

from app.config import settings


class Notifier:
    """Send notifications via WhatsApp Cloud API and Telegram Bot API."""

    def __init__(self):
        self.wa_api_url = settings.WHATSAPP_API_URL
        self.wa_phone_id = settings.WHATSAPP_PHONE_NUMBER_ID
        self.wa_token = settings.WHATSAPP_ACCESS_TOKEN
        self.tg_token = settings.TELEGRAM_BOT_TOKEN
        self.tg_chat_id = settings.TELEGRAM_CHAT_ID

    async def send_whatsapp(
        self,
        phone_number: str,
        message: str,
    ) -> bool:
        """
        Send a WhatsApp message via Meta Cloud API.

        Args:
            phone_number: Recipient phone number (with country code, e.g. +62xxx)
            message: Message text to send
        """
        if not self.wa_token or not self.wa_phone_id:
            print("⚠️ WhatsApp not configured, skipping notification")
            return False

        url = f"{self.wa_api_url}/{self.wa_phone_id}/messages"
        headers = {
            "Authorization": f"Bearer {self.wa_token}",
            "Content-Type": "application/json",
        }
        payload = {
            "messaging_product": "whatsapp",
            "to": phone_number,
            "type": "text",
            "text": {"body": message},
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                print(f"✅ WhatsApp sent to {phone_number}")
                return True
        except Exception as e:
            print(f"❌ WhatsApp failed: {e}")
            return False

    async def send_telegram(
        self,
        message: str,
        chat_id: Optional[str] = None,
        parse_mode: str = "HTML",
    ) -> bool:
        """
        Send a Telegram message via Bot API.

        Args:
            message: Message text (supports HTML formatting)
            chat_id: Target chat ID (defaults to configured TELEGRAM_CHAT_ID)
            parse_mode: "HTML" or "Markdown"
        """
        target_chat = chat_id or self.tg_chat_id

        if not self.tg_token or not target_chat:
            print("⚠️ Telegram not configured, skipping notification")
            return False

        url = f"https://api.telegram.org/bot{self.tg_token}/sendMessage"
        payload = {
            "chat_id": target_chat,
            "text": message,
            "parse_mode": parse_mode,
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                print(f"✅ Telegram sent to chat {target_chat}")
                return True
        except Exception as e:
            print(f"❌ Telegram failed: {e}")
            return False

    async def notify_job_completed(
        self,
        job_id: str,
        video_name: str,
        clips_count: int,
        notify_whatsapp: bool = False,
        notify_telegram: bool = True,
        whatsapp_number: Optional[str] = None,
    ):
        """
        Send job completion notification to configured channels.

        Args:
            job_id: Job ID for reference
            video_name: Original video filename
            clips_count: Number of clips generated
            notify_whatsapp: Send WhatsApp notification
            notify_telegram: Send Telegram notification
        """
        # Build message
        msg_plain = (
            f"🎬 Video Processing Complete!\n\n"
            f"📹 Video: {video_name}\n"
            f"✂️ Clips Generated: {clips_count}\n"
            f"🆔 Job: {job_id}\n\n"
            f"Your clips are ready for review in the dashboard."
        )

        msg_html = (
            f"🎬 <b>Video Processing Complete!</b>\n\n"
            f"📹 Video: <code>{video_name}</code>\n"
            f"✂️ Clips Generated: <b>{clips_count}</b>\n"
            f"🆔 Job: <code>{job_id}</code>\n\n"
            f"Your clips are ready for review in the dashboard."
        )

        if notify_telegram:
            await self.send_telegram(msg_html)

        if notify_whatsapp and whatsapp_number:
            await self.send_whatsapp(whatsapp_number, msg_plain)

    async def notify_job_failed(
        self,
        job_id: str,
        video_name: str,
        error: str,
        notify_telegram: bool = True,
    ):
        """Send job failure notification."""
        msg = (
            f"❌ <b>Video Processing Failed</b>\n\n"
            f"📹 Video: <code>{video_name}</code>\n"
            f"🆔 Job: <code>{job_id}</code>\n"
            f"🔥 Error: <code>{error[:200]}</code>\n\n"
            f"Please check the dashboard for details."
        )

        if notify_telegram:
            await self.send_telegram(msg)

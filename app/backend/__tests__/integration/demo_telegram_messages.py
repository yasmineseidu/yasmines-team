"""
Demo script to send visible Telegram messages for inspection.

Run with: uv run python __tests__/integration/demo_telegram_messages.py

Messages will remain in your Telegram chat for inspection.
"""

import asyncio
import os

from src.integrations.telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ParseMode,
    TelegramClient,
)


async def send_demo_messages() -> None:
    """Send demo messages that stay visible in Telegram."""
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "8566771806:AAG_DzGw5H6cSeK7RsHS2CQAP9qWAb2Iu9o")
    chat_id = int(os.getenv("TELEGRAM_CHAT_ID", "7233821403"))

    client = TelegramClient(bot_token=bot_token)

    try:
        print("🚀 Sending demo messages to Telegram...")
        print(f"   Chat ID: {chat_id}")
        print("-" * 50)

        # 1. Budget Approval Request
        budget_keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="✅ Approve", callback_data="approve_budget_demo"),
                    InlineKeyboardButton(text="❌ Reject", callback_data="reject_budget_demo"),
                ],
                [InlineKeyboardButton(text="✏️ Edit", callback_data="edit_budget_demo")],
            ]
        )

        budget_msg = await client.send_message(
            chat_id=chat_id,
            text="""<b>📊 BUDGET APPROVAL REQUEST</b>
══════════════════════════════

<b>Title:</b> Q4 Marketing Budget
<b>Amount:</b> $50,000.00
<b>Department:</b> Marketing
<b>Fiscal Year:</b> 2025

<b>Description:</b>
Budget allocation for Q4 marketing campaigns including digital advertising, content creation, and event sponsorships.

<i>🕐 Awaiting your decision...</i>""",
            parse_mode=ParseMode.HTML,
            reply_markup=budget_keyboard,
        )
        print(f"✅ Budget approval sent (ID: {budget_msg.message_id})")

        await asyncio.sleep(1)

        # 2. Document Approval Request
        doc_keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="✅ Approve", callback_data="approve_doc_demo"),
                    InlineKeyboardButton(text="❌ Reject", callback_data="reject_doc_demo"),
                ],
                [
                    InlineKeyboardButton(
                        text="📄 View Document",
                        url="https://example.com/contracts/partnership.pdf",
                    ),
                ],
            ]
        )

        doc_msg = await client.send_message(
            chat_id=chat_id,
            text="""<b>📄 DOCUMENT APPROVAL REQUEST</b>
══════════════════════════════

<b>Title:</b> Partnership Agreement
<b>Type:</b> Contract
<b>Partner:</b> TechCorp Inc.

<b>Description:</b>
Review partnership agreement with TechCorp Inc. for joint product development. Contract value: $250,000 over 2 years.

<b>Key Terms:</b>
• Revenue share: 60/40
• IP ownership: Shared
• Exclusivity: 12 months

<i>🕐 Awaiting your decision...</i>""",
            parse_mode=ParseMode.HTML,
            reply_markup=doc_keyboard,
        )
        print(f"✅ Document approval sent (ID: {doc_msg.message_id})")

        await asyncio.sleep(1)

        # 3. Content Approval Request
        content_keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="✅ Publish", callback_data="approve_content_demo"),
                    InlineKeyboardButton(text="❌ Reject", callback_data="reject_content_demo"),
                ],
                [InlineKeyboardButton(text="✏️ Edit", callback_data="edit_content_demo")],
            ]
        )

        content_msg = await client.send_message(
            chat_id=chat_id,
            text="""<b>📝 CONTENT APPROVAL REQUEST</b>
══════════════════════════════

<b>Title:</b> Blog Post: AI in Business
<b>Tags:</b> #ai #business #technology
<b>Author:</b> Content Team

<b>Preview:</b>
<pre>
Artificial intelligence is transforming
how businesses operate.

Key Benefits:
1. Automation of repetitive tasks
2. Data-driven decision making
3. Enhanced customer experience
</pre>

<i>🕐 Ready for publication review...</i>""",
            parse_mode=ParseMode.HTML,
            reply_markup=content_keyboard,
        )
        print(f"✅ Content approval sent (ID: {content_msg.message_id})")

        await asyncio.sleep(1)

        # 4. Custom Approval with Priority
        custom_keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="✅ Approve", callback_data="approve_custom_demo"),
                    InlineKeyboardButton(text="❌ Reject", callback_data="reject_custom_demo"),
                ],
            ]
        )

        custom_msg = await client.send_message(
            chat_id=chat_id,
            text="""<b>🚨 URGENT APPROVAL REQUEST</b>
══════════════════════════════

<b>Title:</b> Server Migration
<b>Priority:</b> 🔴 HIGH
<b>Category:</b> Operations
<b>Deadline:</b> Dec 25, 2025

<b>Request:</b>
Approval needed for emergency server migration to AWS. Current infrastructure experiencing capacity issues.

<b>Impact:</b>
• Estimated downtime: 2 hours
• Affected services: API, Dashboard
• Scheduled: Sunday 2am EST

<i>⚡ Requires immediate attention</i>""",
            parse_mode=ParseMode.HTML,
            reply_markup=custom_keyboard,
        )
        print(f"✅ Custom approval sent (ID: {custom_msg.message_id})")

        await asyncio.sleep(1)

        # 5. Photo with caption
        photo_msg = await client.send_photo(
            chat_id=chat_id,
            photo="https://www.google.com/images/branding/googlelogo/2x/googlelogo_color_272x92dp.png",
            caption="📸 <b>Sample Image Attachment</b>\n\nThis demonstrates photo sending capability.",
            parse_mode=ParseMode.HTML,
        )
        print(f"✅ Photo sent (ID: {photo_msg.message_id})")

        print("-" * 50)
        print("🎉 All demo messages sent!")
        print("   Check your Telegram chat to see them.")
        print("   Messages will stay visible for your inspection.")

    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(send_demo_messages())

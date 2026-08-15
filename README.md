# 🎬 Ultimate Netflix Bot - Premium Edition

A high-performance, premium Telegram store bot built with **aiogram v3** and **MongoDB (Motor)**. Featuring a high-end visual experience with Telegram Premium Custom Animated Emojis.

## 🚀 Key Features
- **Premium UI**: Integrated custom animated emojis in both messages and buttons for a high-end look.
- **Automated Delivery**: Support for Netflix accounts (Token Login & Email/Pass) with instant fulfillment.
- **Referral System**: Detailed referral tracking with custom sharing links.
- **Admin Dashboard**: Comprehensive panel for managing stock, balance, coupons, and broadcasting.
- **Force Join**: Mandatory channel subscription check with premium join UI.
- **Interactive Fulfillment**: Admin-centric workflow for delivering custom logins directly from logs.

## 🛠 Tech Stack
- **Framework**: `aiogram v3` (Asyncio)
- **Database**: `MongoDB` (Motor)
- **Logistics**: `BDFT` inspired environment wrapper for rapid development.
- **Aesthetics**: Custom Monkey Patched Pydantic models for `icon_custom_emoji_id` support.

## 📦 Deployment
1. Clone this repository.
2. Configure `.env` with your `BOT_TOKEN`, `MONGO_URL`, and `ADMINS`.
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Run the bot:
   ```bash
   python main.py
   ```

## 📜 License
Private Repository - All Rights Reserved.

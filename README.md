# Master Liquidity AI - Trading Bot

## Overview
Master Liquidity AI is an automated algorithmic trading bot designed to trade options on the Sensex using the Angel One SmartAPI. It features a modern, user-friendly Streamlit web interface for easy configuration, monitoring, and live status tracking.

## Features
- **1-Click Trading**: Easily start and stop the bot from the dashboard.
- **Auto Loss Protection**: Built-in maximum daily loss limits and dynamic risk management.
- **Telegram Alerts**: Get instant trade notifications directly on your mobile.
- **Live Activity Feed**: Monitor bot actions, entries, and exits in real-time through a clean terminal view.
- **Trade History**: Access your past trades, win rate, and net PnL right from the app.

---

## 1. Local Installation & Setup (Windows/Mac/Linux)

### Prerequisites
1. **Python 3.9+**: Make sure Python is installed on your system.
2. **Angel One Account**: You need an active Angel One demat account.
3. **SmartAPI Credentials**: Register an app on the [Angel One SmartAPI Developer Portal](https://smartapi.angelbroking.com/) to get your API Key.

### Step-by-Step Installation
1. Open your terminal or command prompt.
2. Navigate to the bot directory:
   ```bash
   cd "path/to/telegram-trading-bot"
   ```
3. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Run the application:
   ```bash
   streamlit run app.py
   ```
5. The dashboard will open automatically in your browser at `http://localhost:8501`.

---

## 2. Hosting on a VPS (Recommended for 24/7 Uptime)

To keep the bot running without keeping your personal computer on, you can host it on a VPS (Virtual Private Server) like AWS EC2, DigitalOcean, or Hostinger.

### Ubuntu VPS Setup Guide
1. Connect to your VPS via SSH:
   ```bash
   ssh root@your_server_ip
   ```
2. Update the system and install Python/pip:
   ```bash
   sudo apt update && sudo apt upgrade -y
   sudo apt install python3 python3-pip python3-venv git tmux -y
   ```
3. Upload the bot files to your VPS (via SFTP/FileZilla) or clone them from your repository.
4. Navigate into the bot folder:
   ```bash
   cd telegram-trading-bot
   ```
5. Create a virtual environment (optional but recommended):
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```
6. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
7. **Run Streamlit in the Background using `tmux`**:
   - Start a new tmux session:
     ```bash
     tmux new -s tradingbot
     ```
   - Run the bot:
     ```bash
     streamlit run app.py --server.port 8501 --server.address 0.0.0.0
     ```
   - Detach from the session by pressing `Ctrl+B`, then `D`.
   - Your bot is now running in the background! You can access it via `http://your_server_ip:8501`.

*(Note: Ensure that port 8501 is open in your VPS firewall settings).*

---

## 3. How to Use the Bot

1. **Login Page**:
   - The bot will first ask for your **Angel One Client ID** and **Trading Password (or MPIN)**.
   - Enter your real trading credentials. This page acts as a secure local setup that connects directly to the broker.

2. **Dashboard Overview**:
   - Once logged in, you will see the master control panel.
   - **Live Status & Activity**: View your current open positions, active safety measures, and live logs.
   - **Easy Settings**: Configure your API Key, TOTP Secret, risk per trade, max daily loss, and Telegram integration. *Ensure you save settings before starting the bot!*
   - **Past Trades**: Review your historical trading performance.

3. **Starting the Bot**:
   - Go to the **Live Status** tab.
   - Click the green **▶️ START TRADING BOT** button.
   - The bot will initialize, connect to Angel One, and begin scanning the market based on your configured risk parameters.
   - To pause trading, simply click the red **🛑 STOP TRADING** button.

### Note on Login Credentials
When you open the web interface for the first time, it will prompt you for a **Client ID** and **Password/MPIN**. These are **NOT** separate website accounts. You must enter your actual **Angel One Client ID (e.g., S123456)** and your **Angel One trading PIN/Password** to grant the bot access to your trading account.

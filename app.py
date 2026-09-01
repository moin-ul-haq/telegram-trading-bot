import streamlit as st
import threading
import logging
import queue
import time
import json
import os
from bot import BulletproofMasterLiquidityBot

CONFIG_FILE = "config.json"

st.set_page_config(page_title="Master Liquidity AI", layout="centered")

# Custom Logging Handler for Streamlit
class StreamlitQueueHandler(logging.Handler):
    def __init__(self, log_queue):
        super().__init__()
        self.log_queue = log_queue

    def emit(self, record):
        msg = self.format(record)
        self.log_queue.put(msg)

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            try:
                return json.load(f)
            except:
                pass
    return {
        "api_key": "",
        "client_id": "",
        "password": "",
        "totp_secret": "",
        "ce_token": "SENSEX_CE_TOKEN_HERE",
        "pe_token": "SENSEX_PE_TOKEN_HERE",
        "telegram_token": "",
        "telegram_chat_id": "",
        "total_capital": 50000,
        "risk_percent": 2.0,
        "max_daily_loss_pct": 5.0,
        "lot_size": 10,
        "max_trades_per_day": 5,
    }

def save_config(config):
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=4)

def run_bot(config):
    try:
        bot = BulletproofMasterLiquidityBot(config)
        bot.run_super_bot("BFO", config["lot_size"])
    except Exception as e:
        logging.error(f"Bot crashed: {e}")

# Initialize session state
if "bot_started" not in st.session_state:
    st.session_state.bot_started = False
if "log_queue" not in st.session_state:
    st.session_state.log_queue = queue.Queue()
if "logs" not in st.session_state:
    st.session_state.logs = []

# Configure root logger to output to queue safely without duplicating handlers
if not any(isinstance(h, StreamlitQueueHandler) for h in logging.getLogger().handlers):
    handler = StreamlitQueueHandler(st.session_state.log_queue)
    handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
    logging.getLogger().addHandler(handler)
    logging.getLogger().setLevel(logging.INFO)

config = load_config()

if not st.session_state.bot_started:
    # Logo
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if os.path.exists("logo.png"):
            st.image("logo.png", use_container_width=True)
        else:
            st.markdown("<h1 style='text-align: center;'>🤖 Master Liquidity AI</h1>", unsafe_allow_html=True)
    
    st.markdown("<h3 style='text-align: center;'>Login to Dashboard</h3>", unsafe_allow_html=True)
    
    with st.form("login_form"):
        client_id = st.text_input("Client ID", value=config.get("client_id", ""))
        password = st.text_input("Password / MPIN", type="password", value=config.get("password", ""))
        api_key = st.text_input("API Key", value=config.get("api_key", ""), type="password")
        
        submitted = st.form_submit_button("Submit & Start Bot", use_container_width=True)
        
        if submitted:
            if not client_id or not password or not api_key:
                st.error("Please fill in all fields.")
            else:
                config["client_id"] = client_id
                config["password"] = password
                config["api_key"] = api_key
                save_config(config)
                
                # Start bot thread
                bot_thread = threading.Thread(target=run_bot, args=(config,), daemon=True)
                bot_thread.start()
                
                st.session_state.bot_started = True
                st.rerun()

else:
    # Dashboard view
    col1, col2 = st.columns([1, 4])
    with col1:
        if os.path.exists("logo.png"):
            st.image("logo.png", width=80)
    with col2:
        st.title("Master Liquidity Dashboard")
    
    st.success("🟢 Bot is actively running in the background.")
    
    if st.button("Logout / Restart App"):
        st.session_state.bot_started = False
        st.rerun()
        
    st.subheader("Live Activity Logs")
    
    # Read from queue
    while not st.session_state.log_queue.empty():
        msg = st.session_state.log_queue.get()
        st.session_state.logs.append(msg)
        
    # Keep only last 200 logs
    if len(st.session_state.logs) > 200:
        st.session_state.logs = st.session_state.logs[-200:]
        
    log_text = "\n".join(st.session_state.logs)
    st.text_area("System Logs", value=log_text, height=500, disabled=True)
    
    # Auto refresh logic
    time.sleep(2)
    st.rerun()

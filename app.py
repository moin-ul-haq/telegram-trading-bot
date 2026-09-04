import streamlit as st
import threading
import logging
import queue
import time
import json
import os
import ctypes
import sqlite3
import datetime
import requests
import pandas as pd
from bot import BulletproofMasterLiquidityBot

CONFIG_FILE = "config.json"
DB_FILE = "trade_history.db"

# Page configuration
st.set_page_config(
    page_title="Master Liquidity AI • Easy Trading Bot",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# -------------------------------------------------------------
# High-Performance, Vibrant & Clutter-Free CSS (Fast Load)
# -------------------------------------------------------------
st.markdown("""
<style>
/* Fast system font stack with no external font-blocking network latency */
html, body, [class*="css"] {
    font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    color: #f1f5f9;
}

:root {
    --neon-green: #00f59b;
    --neon-cyan: #00f0ff;
    --neon-purple: #8b5cf6;
    --neon-amber: #f59e0b;
    --neon-rose: #ff3366;
    --card-bg: rgba(15, 23, 42, 0.85);
    --border-subtle: rgba(255, 255, 255, 0.1);
}

/* Base background */
.stApp {
    background-color: #070a13;
    background-image: 
        radial-gradient(circle at 10% 10%, rgba(0, 245, 155, 0.07) 0%, transparent 45%),
        radial-gradient(circle at 90% 15%, rgba(0, 240, 255, 0.06) 0%, transparent 45%),
        radial-gradient(circle at 50% 90%, rgba(139, 92, 246, 0.05) 0%, transparent 50%);
    background-attachment: fixed;
}

/* Style Streamlit Forms as unified luxury glass cards (Eliminates stray boxes) */
[data-testid="stForm"] {
    background: linear-gradient(145deg, rgba(16, 25, 46, 0.9) 0%, rgba(10, 16, 30, 0.95) 100%) !important;
    border: 1px solid rgba(0, 245, 155, 0.28) !important;
    border-radius: 20px !important;
    padding: 32px 28px !important;
    box-shadow: 0 20px 45px rgba(0, 0, 0, 0.6), 0 0 25px rgba(0, 245, 155, 0.08) !important;
}

/* Master Hero Control Banner */
.hero-banner-running {
    background: linear-gradient(135deg, rgba(0, 245, 155, 0.14) 0%, rgba(0, 240, 255, 0.08) 100%);
    border: 1px solid rgba(0, 245, 155, 0.4);
    border-radius: 16px;
    padding: 20px 24px;
    margin-bottom: 20px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    box-shadow: 0 8px 30px rgba(0, 245, 155, 0.12);
}

.hero-banner-stopped {
    background: linear-gradient(135deg, rgba(245, 158, 11, 0.12) 0%, rgba(239, 68, 68, 0.06) 100%);
    border: 1px solid rgba(245, 158, 11, 0.35);
    border-radius: 16px;
    padding: 20px 24px;
    margin-bottom: 20px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    box-shadow: 0 8px 30px rgba(0, 0, 0, 0.3);
}

/* Clean Metric Cards */
.simple-card {
    background: rgba(16, 25, 46, 0.85);
    border: 1px solid var(--border-subtle);
    border-radius: 14px;
    padding: 18px 20px;
    margin-bottom: 15px;
    transition: transform 0.2s ease, border-color 0.2s ease;
}

.simple-card:hover {
    border-color: rgba(0, 245, 155, 0.3);
    transform: translateY(-2px);
}

.simple-card-label {
    font-size: 0.82rem;
    font-weight: 600;
    color: #94a3b8;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-bottom: 6px;
}

.simple-card-value {
    font-size: 1.8rem;
    font-weight: 800;
    color: #ffffff;
    line-height: 1.2;
}

.simple-card-help {
    font-size: 0.8rem;
    color: #00f0ff;
    margin-top: 5px;
}

/* Pulsing radar indicator */
.pulse-indicator {
    display: inline-block;
    width: 10px;
    height: 10px;
    border-radius: 50%;
    margin-right: 8px;
    background-color: currentColor;
    box-shadow: 0 0 10px currentColor;
    animation: pulse-kf 1.8s infinite cubic-bezier(0.45, 0, 0.55, 1);
}

@keyframes pulse-kf {
    0% { transform: scale(0.9); opacity: 0.8; }
    50% { transform: scale(1.3); opacity: 1; filter: drop-shadow(0 0 8px currentColor); }
    100% { transform: scale(0.9); opacity: 0.8; }
}

/* Clean Terminal Window */
.clean-terminal {
    background: #060911;
    border: 1px solid rgba(0, 240, 255, 0.2);
    border-radius: 12px;
    padding: 16px;
    font-family: "JetBrains Mono", Consolas, Monaco, monospace;
    font-size: 0.82rem;
    line-height: 1.6;
    color: #cbd5e1;
    height: 380px;
    overflow-y: auto;
    white-space: pre-wrap;
    box-shadow: inset 0 2px 10px rgba(0,0,0,0.6);
}

/* Custom tabs styling */
.stTabs [data-baseweb="tab-list"] {
    gap: 10px;
    background: rgba(14, 22, 38, 0.7);
    padding: 6px;
    border-radius: 12px;
    border: 1px solid var(--border-subtle);
}

.stTabs [data-baseweb="tab"] {
    height: 46px;
    border-radius: 8px;
    color: #94a3b8;
    font-weight: 600;
    font-size: 0.92rem;
    padding: 0 20px;
    border: none !important;
    background: transparent;
}

.stTabs [aria-selected="true"] {
    background: linear-gradient(135deg, rgba(0, 245, 155, 0.18), rgba(0, 240, 255, 0.14)) !important;
    color: #ffffff !important;
    border: 1px solid rgba(0, 245, 155, 0.4) !important;
    box-shadow: 0 4px 14px rgba(0, 245, 155, 0.15);
}

/* Buttons */
.stButton > button {
    border-radius: 10px;
    font-weight: 700;
    transition: all 0.2s ease;
}

/* Clean modern scrollbars */
::-webkit-scrollbar {
    width: 6px;
    height: 6px;
}
::-webkit-scrollbar-track {
    background: #090e1a;
}
::-webkit-scrollbar-thumb {
    background: rgba(0, 240, 255, 0.25);
    border-radius: 4px;
}
</style>
""", unsafe_allow_html=True)


# -------------------------------------------------------------
# Fast Caching & Storage Helpers (Prevents reload lag)
# -------------------------------------------------------------
def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        except Exception:
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

def save_config(cfg):
    with open(CONFIG_FILE, "w") as f:
        json.dump(cfg, f, indent=4)
    # Clear any cached data so changes reflect immediately
    load_trade_history.clear()

@st.cache_data(ttl=15)
def load_trade_history():
    if not os.path.exists(DB_FILE):
        return pd.DataFrame()
    try:
        conn = sqlite3.connect(DB_FILE)
        df = pd.read_sql_query("SELECT * FROM trades ORDER BY id DESC LIMIT 50", conn)
        conn.close()
        return df
    except Exception:
        return pd.DataFrame()

def test_telegram_alert(token, chat_id):
    if not token or not chat_id:
        return False, "Please fill in both Telegram Bot Token and Chat ID."
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": "⚡ *Master Liquidity AI Alert*\nConnection verified successfully! Your trading alerts are active.",
            "parse_mode": "Markdown"
        }
        res = requests.post(url, json=payload, timeout=5)
        if res.status_code == 200:
            return True, "Alert sent successfully! Check your Telegram chat."
        else:
            return False, f"Telegram API error: {res.text}"
    except Exception as ex:
        return False, f"Connection error: {str(ex)}"


# -------------------------------------------------------------
# Background Thread & Bot Engine Manager
# -------------------------------------------------------------
def terminate_thread(thread):
    if not thread.is_alive():
        return
    exc = ctypes.py_object(SystemExit)
    res = ctypes.pythonapi.PyThreadState_SetAsyncExc(ctypes.c_long(thread.ident), exc)
    if res == 0:
        pass
    elif res > 1:
        ctypes.pythonapi.PyThreadState_SetAsyncExc(thread.ident, None)

class BotManager:
    def __init__(self):
        self.bot_thread = None
        self.bot_instance = None
        self.log_queue = queue.Queue()
        self.is_running = False
        self.start_time = None

    def start_bot(self, cfg):
        if self.is_running:
            return
        self.is_running = True
        self.start_time = datetime.datetime.now()
        self.bot_thread = threading.Thread(target=self._run_bot, args=(cfg,), daemon=True)
        self.bot_thread.start()

    def _run_bot(self, cfg):
        try:
            self.bot_instance = BulletproofMasterLiquidityBot(cfg)
            self.bot_instance.run_super_bot("BFO", cfg.get("lot_size", 10))
        except SystemExit:
            logging.info("Trading bot paused by user.")
        except Exception as e:
            logging.error(f"Bot error: {e}")
        finally:
            self.is_running = False
            self.bot_instance = None

    def stop_bot(self):
        if self.bot_instance:
            self.bot_instance.stop_requested = True
        if self.bot_thread and self.bot_thread.is_alive():
            self.bot_thread.join(timeout=1.0)
            if self.bot_thread.is_alive():
                terminate_thread(self.bot_thread)
        self.is_running = False
        self.bot_instance = None

@st.cache_resource
def get_bot_manager():
    return BotManager()

bot_manager = get_bot_manager()

# Global Queue Logger
class StreamlitQueueHandler(logging.Handler):
    def __init__(self, log_q):
        super().__init__()
        self.log_queue = log_q

    def emit(self, record):
        try:
            msg = self.format(record)
            self.log_queue.put(msg)
        except Exception:
            pass

if not any(isinstance(h, StreamlitQueueHandler) for h in logging.getLogger().handlers):
    handler = StreamlitQueueHandler(bot_manager.log_queue)
    handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s", datefmt="%H:%M:%S"))
    logging.getLogger().addHandler(handler)
    logging.getLogger().setLevel(logging.INFO)


# -------------------------------------------------------------
# Session State Initialization
# -------------------------------------------------------------
config = load_config()

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "logs" not in st.session_state:
    st.session_state.logs = [
        f"{datetime.datetime.now().strftime('%H:%M:%S')} | INFO | ⚡ Bot Dashboard ready. Welcome!"
    ]


# -------------------------------------------------------------
# SCREEN 1: Clean, Single-Card Login (Zero Stray Boxes)
# -------------------------------------------------------------
if not st.session_state.logged_in:
    st.markdown("<div style='height: 40px;'></div>", unsafe_allow_html=True)
    
    # Perfectly centered single column container
    _, login_col, _ = st.columns([1, 1.2, 1])
    
    with login_col:
        # ALL LOGIN CONTENT IS WRAPPED INSIDE THIS SINGLE FORM CARD
        # This guarantees NO stray boxes, NO broken divs, and instant clean rendering!
        with st.form("login_form"):
            # Centered Logo
            logo_l, logo_c, logo_r = st.columns([1, 1, 1])
            with logo_c:
                if os.path.exists("logo.png"):
                    st.image("logo.png", width=110)
                else:
                    st.markdown("<h1 style='text-align:center;'>⚡</h1>", unsafe_allow_html=True)

            # Title and Friendly Subtitle
            st.markdown("""
            <div style='text-align: center; margin-bottom: 22px;'>
                <h2 style='font-size: 1.75rem; font-weight: 800; margin: 4px 0 2px 0; background: linear-gradient(90deg, #00f59b, #00f0ff); -webkit-background-clip: text; -webkit-text-fill-color: transparent;'>
                    MASTER LIQUIDITY AI
                </h2>
                <p style='color: #94a3b8; font-size: 0.88rem; margin: 0 0 16px 0;'>
                    Simple & Automated Sensex Trading Bot
                </p>
                <div style='display: flex; justify-content: center; gap: 8px;'>
                    <span style='background: rgba(0, 245, 155, 0.1); border: 1px solid rgba(0, 245, 155, 0.25); color: #00f59b; padding: 3px 10px; border-radius: 9999px; font-size: 0.74rem; font-weight: 600;'>🛡️ Auto Loss Protection</span>
                    <span style='background: rgba(0, 240, 255, 0.1); border: 1px solid rgba(0, 240, 255, 0.25); color: #00f0ff; padding: 3px 10px; border-radius: 9999px; font-size: 0.74rem; font-weight: 600;'>⚡ 1-Click Trading</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

            # Friendly Input Fields
            st.markdown("<p style='font-weight: 600; color: #cbd5e1; font-size: 0.88rem; margin-bottom: 4px;'>👤 Angel One Client ID</p>", unsafe_allow_html=True)
            client_id = st.text_input("Client ID", value=config.get("client_id", ""), label_visibility="collapsed", placeholder="Enter your Client ID (e.g. S123456)")
            
            st.markdown("<p style='font-weight: 600; color: #cbd5e1; font-size: 0.88rem; margin-bottom: 4px; margin-top: 10px;'>🔒 Password / MPIN</p>", unsafe_allow_html=True)
            password = st.text_input("Password", type="password", value=config.get("password", ""), label_visibility="collapsed", placeholder="Enter your 4-digit MPIN or password")

            st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)
            
            # Big High-Contrast Login Button
            unlock_btn = st.form_submit_button("🚀 Open Trading Dashboard", width="stretch", type="primary")
            
            if unlock_btn:
                if not client_id or not password:
                    st.error("Please enter both Client ID and Password to continue.")
                else:
                    config["client_id"] = client_id
                    config["password"] = password
                    save_config(config)
                    st.session_state.logged_in = True
                    st.success("Welcome! Opening your dashboard...")
                    time.sleep(0.3)
                    st.rerun()

            st.markdown("""
            <div style='text-align: center; margin-top: 18px; color: #64748b; font-size: 0.76rem;'>
                🔒 Secure Local Session • Directly Connects to Angel One SmartAPI
            </div>
            """, unsafe_allow_html=True)


# -------------------------------------------------------------
# SCREEN 2: Intuitive Dashboard for Non-Technical Traders
# -------------------------------------------------------------
else:
    # 1. Top Brand & Quick Actions Header
    head_left, head_right = st.columns([2.5, 1], vertical_alignment="center")
    
    with head_left:
        st.markdown("""
        <div style="display: flex; align-items: center; gap: 14px;">
            <div style="font-size: 2.2rem; filter: drop-shadow(0 0 10px rgba(0, 245, 155, 0.4));">⚡</div>
            <div>
                <h2 style='font-weight: 800; margin: 0; font-size: 1.65rem; background: linear-gradient(90deg, #ffffff, #00f0ff); -webkit-background-clip: text; -webkit-text-fill-color: transparent;'>
                    MASTER LIQUIDITY AI
                </h2>
                <span style='font-size: 0.8rem; color: #94a3b8;'>
                    Simple & Safe Algorithmic Trading Center
                </span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
    with head_right:
        st.markdown("<div style='text-align: right;'>", unsafe_allow_html=True)
        if st.button("🚪 Logout & Exit", width="stretch"):
            if bot_manager.is_running:
                bot_manager.stop_bot()
            st.session_state.logged_in = False
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

    # 2. Master Control Hero Bar (HCI Principle: System Status & Big Clear Controls)
    # A non-technical user immediately knows if the bot is ON or OFF and how to switch it!
    bot_inst = bot_manager.bot_instance
    curr_pnl = bot_inst.daily_pnl if bot_inst else 0.0
    peak_pnl = bot_inst.max_peak_profit if bot_inst else 0.0
    trades_taken = bot_inst.trades_taken_today if bot_inst else 0

    if bot_manager.is_running:
        st.markdown("""
        <div class="hero-banner-running">
            <div>
                <div style="font-size: 1.25rem; font-weight: 800; color: #00f59b; display: flex; align-items: center;">
                    <span class="pulse-indicator" style="color: #00f59b;"></span>
                    BOT IS ACTIVELY RUNNING & MONITORING TRADES
                </div>
                <div style="font-size: 0.88rem; color: #cbd5e1; margin-top: 4px;">
                    The bot is scanning the market for high-probability setups with automated stop-loss and profit protection.
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Stop Button
        if st.button("🛑 STOP TRADING (PAUSE BOT)", width="stretch", type="primary"):
            bot_manager.stop_bot()
            st.rerun()

    else:
        st.markdown("""
        <div class="hero-banner-stopped">
            <div>
                <div style="font-size: 1.25rem; font-weight: 800; color: #f59e0b; display: flex; align-items: center;">
                    <span class="pulse-indicator" style="color: #f59e0b;"></span>
                    BOT IS CURRENTLY PAUSED (STANDBY)
                </div>
                <div style="font-size: 0.88rem; color: #cbd5e1; margin-top: 4px;">
                    No trades will be taken right now. Click the green button below whenever you are ready to start.
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Big Start Button
        if st.button("▶️ START TRADING BOT", width="stretch", type="primary"):
            bot_manager.start_bot(config)
            st.rerun()

    st.markdown("<div style='height: 14px;'></div>", unsafe_allow_html=True)

    # 3. Four Plain-Language Essential Metric Cards
    total_cap = float(config.get("total_capital", 50000))
    risk_pct = float(config.get("risk_percent", 2.0))
    max_loss_pct = float(config.get("max_daily_loss_pct", 5.0))
    lot_sz = int(config.get("lot_size", 10))
    max_trades = int(config.get("max_trades_per_day", 5))

    per_trade_risk = (total_cap * risk_pct) / 100.0
    daily_circuit_limit = (total_cap * max_loss_pct) / 100.0

    col_m1, col_m2, col_m3, col_m4 = st.columns(4)
    
    with col_m1:
        st.markdown(f"""
        <div class="simple-card">
            <div class="simple-card-label">💰 Trading Capital</div>
            <div class="simple-card-value">₹{total_cap:,.0f}</div>
            <div class="simple-card-help">Max risk: ₹{per_trade_risk:,.0f} ({risk_pct}%)</div>
        </div>
        """, unsafe_allow_html=True)

    with col_m2:
        pnl_color = "#00f59b" if curr_pnl >= 0 else "#ff3366"
        pnl_sign = "+" if curr_pnl > 0 else ""
        st.markdown(f"""
        <div class="simple-card">
            <div class="simple-card-label">📈 Today's Profit / Loss</div>
            <div class="simple-card-value" style="color: {pnl_color};">{pnl_sign}₹{curr_pnl:,.2f}</div>
            <div class="simple-card-help" style="color: #94a3b8;">Peak profit: ₹{peak_pnl:,.2f}</div>
        </div>
        """, unsafe_allow_html=True)

    with col_m3:
        st.markdown(f"""
        <div class="simple-card">
            <div class="simple-card-label">🛡️ Loss Safety Shield</div>
            <div class="simple-card-value" style="color: #ff3366;">-₹{daily_circuit_limit:,.0f}</div>
            <div class="simple-card-help" style="color: #94a3b8;">Auto-stops if daily loss reaches this limit</div>
        </div>
        """, unsafe_allow_html=True)

    with col_m4:
        st.markdown(f"""
        <div class="simple-card">
            <div class="simple-card-label">🔢 Trades Completed</div>
            <div class="simple-card-value">{trades_taken} <span style="font-size: 1.1rem; color: #94a3b8;">/ {max_trades}</span></div>
            <div class="simple-card-help">Fixed {lot_sz} lots per order</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)

    # 4. Intuitive 4 Tabs with Progressive Disclosure
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 Live Status & Activity",
        "⚙️ Easy Settings",
        "📜 Past Trades History",
        "❓ How It Works & Safety"
    ])

    # ---------------------------------------------------------
    # TAB 1: Live Status & Activity (Non-Technical Friendly)
    # ---------------------------------------------------------
    with tab1:
        st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)
        
        # Friendly Live Status Overview Card
        current_pos = bot_inst.position if bot_inst and bot_inst.position else "No open trade (Market is being scanned)"
        entry_pr = bot_inst.entry_price if bot_inst and bot_inst.position else 0.0
        active_sym = bot_inst.active_symbol_token if bot_inst and bot_inst.position else "Sensex Options"
        
        c_status1, c_status2 = st.columns([1.5, 1])
        with c_status1:
            st.markdown(f"""
            <div class="simple-card">
                <div style="font-weight: 700; color: #ffffff; font-size: 1.05rem; margin-bottom: 12px; display: flex; align-items: center; gap: 8px;">
                    <span>⚡ Current Position:</span>
                    <span style="color: {'#00f59b' if current_pos != 'No open trade (Market is being scanned)' else '#94a3b8'};">
                        {current_pos}
                    </span>
                </div>
                <div style="font-size: 0.88rem; color: #cbd5e1; line-height: 1.6;">
                    • <b>Contract:</b> {active_sym}<br>
                    • <b>Entry Price:</b> {'₹' + str(entry_pr) if entry_pr > 0 else 'Waiting for trade entry'}<br>
                    • <b>Automatic Protection:</b> Hard Stop-Loss and Trailing Profit locks are active automatically.
                </div>
            </div>
            """, unsafe_allow_html=True)

        with c_status2:
            st.markdown("""
            <div class="simple-card">
                <div style="font-weight: 700; color: #00f0ff; font-size: 1.05rem; margin-bottom: 10px;">
                    🛡️ Safety Highlights
                </div>
                <div style="font-size: 0.84rem; color: #cbd5e1; line-height: 1.6;">
                    ✅ <b>Max Daily Loss Protection:</b> Won't exceed your chosen limit.<br>
                    ✅ <b>3:15 PM Square-Off:</b> All positions closed before market ends.<br>
                    ✅ <b>Auto Profit Lock:</b> Locks profits when trade moves in your favor.
                </div>
            </div>
            """, unsafe_allow_html=True)

        # Non-Flicker Live Activity Section
        st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)
        st.markdown("<h4 style='color: #ffffff; margin-bottom: 8px;'>Live Bot Activity Feed</h4>", unsafe_allow_html=True)

        # Zero-flicker log fragment: updates logs without reloading or freezing the page!
        @st.fragment(run_every="2s" if bot_manager.is_running else None)
        def render_clean_logs_fragment():
            while not bot_manager.log_queue.empty():
                msg = bot_manager.log_queue.get()
                st.session_state.logs.append(msg)
                
            if len(st.session_state.logs) > 300:
                st.session_state.logs = st.session_state.logs[-300:]

            # Highlight key human-readable actions
            formatted_lines = []
            for line in st.session_state.logs:
                if "ERROR" in line or "CRITICAL" in line or "फेल" in line:
                    formatted_lines.append(f"<span style='color: #ff4d6d; font-weight: 600;'>{line}</span>")
                elif "WARNING" in line or "चेतावनी" in line:
                    formatted_lines.append(f"<span style='color: #f59e0b;'>{line}</span>")
                elif "🎯" in line or "BUY_CE" in line or "BUY_PE" in line or "सफल" in line:
                    formatted_lines.append(f"<span style='color: #00f59b; font-weight: 700;'>{line}</span>")
                elif "PnL" in line or "लाभ" in line:
                    formatted_lines.append(f"<span style='color: #00f0ff; font-weight: 600;'>{line}</span>")
                else:
                    formatted_lines.append(f"<span style='color: #94a3b8;'>{line}</span>")

            log_text_html = "\n".join(formatted_lines) if formatted_lines else "<span>Bot is ready. Waiting for events...</span>"

            st.markdown(f"""
            <div class="clean-terminal">
                {log_text_html}
            </div>
            """, unsafe_allow_html=True)

        render_clean_logs_fragment()

        # Terminal Actions Bar
        t_col1, t_col2, _ = st.columns([1, 1, 2])
        with t_col1:
            if st.button("🧹 Clear Feed", width="stretch"):
                st.session_state.logs = [
                    f"{datetime.datetime.now().strftime('%H:%M:%S')} | INFO | Feed cleared."
                ]
                st.rerun()
        with t_col2:
            all_logs_text = "\n".join(st.session_state.logs)
            st.download_button(
                "📥 Download Logs (.txt)",
                data=all_logs_text,
                file_name=f"trading_logs_{datetime.date.today()}.txt",
                mime="text/plain",
                width="stretch"
            )

    # ---------------------------------------------------------
    # TAB 2: Easy Settings (Friendly, Step-by-Step)
    # ---------------------------------------------------------
    with tab2:
        st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
        
        cfg_c1, cfg_c2 = st.columns(2)
        
        with cfg_c1:
            st.markdown("""
            <div class="simple-card">
                <div style="font-size: 1.1rem; font-weight: 700; color: #00f59b; margin-bottom: 4px;">
                    1️⃣ Angel One Broker Details
                </div>
                <div style="font-size: 0.8rem; color: #94a3b8; margin-bottom: 14px;">
                    Enter your Angel One SmartAPI login credentials here.
                </div>
            """, unsafe_allow_html=True)
            
            s_api_key = st.text_input("SmartAPI Key", value=config.get("api_key", ""), type="password", help="From your SmartAPI Developer Dashboard")
            s_client_id = st.text_input("Angel One Client ID", value=config.get("client_id", ""), help="Your trading username/account ID")
            s_password = st.text_input("Trading Password / MPIN", value=config.get("password", ""), type="password", help="Your login PIN or password")
            s_totp = st.text_input("TOTP Secret Key", value=config.get("totp_secret", ""), type="password", help="32-character TOTP secret code from Angel One security settings")
            
            st.markdown("</div>", unsafe_allow_html=True)

            st.markdown("""
            <div class="simple-card">
                <div style="font-size: 1.1rem; font-weight: 700; color: #8b5cf6; margin-bottom: 4px;">
                    2️⃣ Telegram Alerts (Optional)
                </div>
                <div style="font-size: 0.8rem; color: #94a3b8; margin-bottom: 14px;">
                    Receive instant alerts on your mobile phone whenever a trade is placed.
                </div>
            """, unsafe_allow_html=True)
            
            s_tele_token = st.text_input("Telegram Bot Token", value=config.get("telegram_token", ""), type="password", placeholder="e.g. 123456789:ABCDefgh...")
            s_tele_chat = st.text_input("Telegram Chat ID", value=config.get("telegram_chat_id", ""), placeholder="e.g. 987654321")
            
            if st.button("🔔 Send Test Telegram Message", width="stretch"):
                ok, res_msg = test_telegram_alert(s_tele_token, s_tele_chat)
                if ok:
                    st.success(f"✅ {res_msg}")
                else:
                    st.error(f"❌ {res_msg}")
                    
            st.markdown("</div>", unsafe_allow_html=True)

        with cfg_c2:
            st.markdown("""
            <div class="simple-card">
                <div style="font-size: 1.1rem; font-weight: 700; color: #00f0ff; margin-bottom: 4px;">
                    3️⃣ Capital & Risk Settings
                </div>
                <div style="font-size: 0.8rem; color: #94a3b8; margin-bottom: 14px;">
                    Configure how much money to use and how to protect your account.
                </div>
            """, unsafe_allow_html=True)
            
            s_cap = st.number_input("Total Trading Capital (₹)", value=int(config.get("total_capital", 50000)), step=5000, help="Amount of money in rupees you want this bot to trade with")
            s_risk = st.number_input("Risk Per Trade (%)", value=float(config.get("risk_percent", 2.0)), step=0.5, min_value=0.5, max_value=10.0, help="Recommended: 2% for balanced growth")
            s_max_loss = st.number_input("Max Daily Loss Limit (%)", value=float(config.get("max_daily_loss_pct", 5.0)), step=0.5, min_value=1.0, max_value=20.0, help="Bot automatically shuts down if this loss percentage is reached today")
            s_lot = st.number_input("Lot Size (Contracts)", value=int(config.get("lot_size", 10)), step=1, help="Fixed lot quantity per trade")
            s_max_t = st.number_input("Max Trades Per Day", value=int(config.get("max_trades_per_day", 5)), step=1, min_value=1, max_value=20, help="Prevents over-trading on choppy days")

            # Simple Live Math Preview
            calc_r = (s_cap * s_risk) / 100.0
            calc_l = (s_cap * s_max_loss) / 100.0
            
            st.markdown(f"""
            <div style="background: rgba(0, 240, 255, 0.08); border: 1px dashed rgba(0, 240, 255, 0.3); border-radius: 10px; padding: 14px; margin-top: 14px;">
                <div style="font-weight: 700; color: #00f0ff; font-size: 0.82rem; margin-bottom: 4px;">💡 WHAT THIS MEANS FOR YOU:</div>
                <div style="font-size: 0.85rem; color: #cbd5e1; line-height: 1.5;">
                    • <b>Max Risk per Trade:</b> <span style="color: #00f59b; font-weight: 700;">₹{calc_r:,.2f}</span><br>
                    • <b>Daily Stop Protection:</b> Bot will auto-stop if losses hit <span style="color: #ff3366; font-weight: 700;">₹{calc_l:,.2f}</span>.<br>
                    • <b>Trading Limit:</b> Bot will never take more than <b>{s_max_t} trades</b> per day.
                </div>
            </div>
            """, unsafe_allow_html=True)

            st.markdown("<div style='height: 15px;'></div>", unsafe_allow_html=True)

            with st.expander("🛠️ Advanced Option Token Settings (Optional)"):
                st.markdown("<div style='font-size: 0.8rem; color: #94a3b8;'>Only change these if you want to override automated Sensex tokens:</div>", unsafe_allow_html=True)
                s_ce = st.text_input("CE Symbol Token", value=config.get("ce_token", "SENSEX_CE_TOKEN_HERE"))
                s_pe = st.text_input("PE Symbol Token", value=config.get("pe_token", "SENSEX_PE_TOKEN_HERE"))

            st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)
            
            if st.button("💾 Save All Settings", width="stretch", type="primary"):
                config["api_key"] = s_api_key
                config["client_id"] = s_client_id
                config["password"] = s_password
                config["totp_secret"] = s_totp
                config["total_capital"] = s_cap
                config["risk_percent"] = s_risk
                config["max_daily_loss_pct"] = s_max_loss
                config["lot_size"] = s_lot
                config["max_trades_per_day"] = s_max_t
                if 's_ce' in locals():
                    config["ce_token"] = s_ce
                    config["pe_token"] = s_pe
                config["telegram_token"] = s_tele_token
                config["telegram_chat_id"] = s_tele_chat
                save_config(config)
                st.success("✅ Settings saved successfully! Ready for your next trading session.")

            st.markdown("</div>", unsafe_allow_html=True)

    # ---------------------------------------------------------
    # TAB 3: Past Trades & Performance Record
    # ---------------------------------------------------------
    with tab3:
        st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
        trades_df = load_trade_history()
        
        if not trades_df.empty:
            t_count = len(trades_df)
            wins = len(trades_df[trades_df["pnl"] > 0])
            losses = len(trades_df[trades_df["pnl"] < 0])
            win_rate = (wins / t_count * 100) if t_count > 0 else 0
            net_profit = trades_df["pnl"].sum()
            
            sc1, sc2, sc3 = st.columns(3)
            with sc1:
                st.metric("Total Completed Trades", t_count)
            with sc2:
                st.metric("Win Rate", f"{win_rate:.1f}%", delta=f"{wins} Wins / {losses} Losses")
            with sc3:
                st.metric("Total Realized Profit", f"₹{net_profit:,.2f}", delta=f"{net_profit:,.2f}")
                
            st.markdown("<div style='height: 14px;'></div>", unsafe_allow_html=True)
            st.dataframe(trades_df, width="stretch", hide_index=True)
        else:
            st.markdown("""
            <div class="simple-card" style="text-align: center; padding: 40px 20px;">
                <div style="font-size: 3rem; margin-bottom: 8px;">📊</div>
                <h3 style="color: #ffffff; margin-bottom: 6px;">No Trades Recorded Yet Today</h3>
                <p style="color: #94a3b8; max-width: 500px; margin: 0 auto 16px auto; font-size: 0.88rem;">
                    As soon as you launch the bot and it detects a trading opportunity, your executed orders and profit/loss results will appear here automatically.
                </p>
                <span style="background: rgba(0, 245, 155, 0.1); border: 1px solid rgba(0, 245, 155, 0.3); color: #00f59b; padding: 6px 16px; border-radius: 9999px; font-weight: 600; font-size: 0.82rem;">
                    ⚡ Database is active & connected
                </span>
            </div>
            """, unsafe_allow_html=True)

    # ---------------------------------------------------------
    # TAB 4: How It Works & Built-In Safety
    # ---------------------------------------------------------
    with tab4:
        st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
        
        st.markdown("""
        <div class="simple-card">
            <h3 style="color: #00f59b; margin-top: 0;">🚀 3 Simple Steps to Trade</h3>
            <div style="font-size: 0.9rem; color: #cbd5e1; line-height: 1.8;">
                <b>Step 1: Check Your Settings:</b> Go to the <i>Easy Settings</i> tab and verify your Angel One credentials and preferred capital.<br>
                <b>Step 2: Click Start Trading:</b> Click the big green <b>START TRADING BOT</b> button at the top.<br>
                <b>Step 3: Relax & Let the Bot Manage:</b> The bot will automatically scan Sensex contracts, enter high-probability setups, manage stop-loss, lock profits, and exit at 3:15 PM.
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        g1, g2 = st.columns(2)
        with g1:
            st.markdown("""
            <div class="simple-card">
                <h4 style="color: #00f0ff; margin-top: 0;">🎯 What the Bot Does for You</h4>
                <ul style="color: #cbd5e1; font-size: 0.86rem; line-height: 1.8; padding-left: 20px;">
                    <li><b>Scans Smart Money Moves:</b> Looks for market liquidity sweeps and momentum before entering.</li>
                    <li><b>Dynamic Option Expiry:</b> Automatically rolls over to active weekly and monthly Sensex contracts.</li>
                    <li><b>Afternoon Expansion:</b> Focuses on high-momentum periods (12:30 PM to 3:00 PM) for strong moves.</li>
                </ul>
            </div>
            """, unsafe_allow_html=True)

        with g2:
            st.markdown("""
            <div class="simple-card">
                <h4 style="color: #f59e0b; margin-top: 0;">🛡️ Built-in Capital Protection</h4>
                <ul style="color: #cbd5e1; font-size: 0.86rem; line-height: 1.8; padding-left: 20px;">
                    <li><b>Strict Stop-Loss:</b> Cuts losing trades immediately if the market reverses.</li>
                    <li><b>Trailing Profit Lock:</b> Once profits cross ₹1,000, the bot locks at least 50% gains so you don't give back profits.</li>
                    <li><b>Hard Daily Circuit:</b> Automatically shuts off if your maximum daily loss is reached.</li>
                    <li><b>3:15 PM Intraday Auto Exit:</b> Guarantees no positions remain open overnight.</li>
                </ul>
            </div>
            """, unsafe_allow_html=True)

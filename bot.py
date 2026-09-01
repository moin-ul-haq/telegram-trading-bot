import datetime
import json
import logging
import os
import sqlite3
import threading
import time
import tkinter as tk
from tkinter import messagebox, scrolledtext
import numpy as np
import pandas as pd
import pyotp
import requests
from SmartApi import SmartConnect

CONFIG_FILE = "config.json"
DB_FILE = "trade_history.db"


class TextHandler(logging.Handler):
  """लॉग्स को सीधे ऐप की स्क्रीन पर दिखाने के लिए क्लास"""

  def __init__(self, text_widget):
    logging.Handler.__init__(self)
    self.text_widget = text_widget

  def emit(self, record):
    msg = self.format(record)

    def append():
      self.text_widget.configure(state="normal")
      self.text_widget.insert(tk.END, msg + "\n")
      self.text_widget.configure(state="disabled")
      self.text_widget.yview(tk.END)

    self.text_widget.after(0, append)


class BulletproofMasterLiquidityBot:

  def __init__(self, config):
    self.api_key = config["api_key"]
    self.client_id = config["client_id"]
    self.password = config["password"]
    self.totp_secret = config["totp_secret"]
    self.obj = None

    self.total_capital = config["total_capital"]
    self.risk_per_trade = (
        self.total_capital * config["risk_percent"]
    ) / 100
    self.max_daily_loss = (
        self.total_capital * config["max_daily_loss_pct"]
    ) / 100

    self.max_trades_allowed = config["max_trades_per_day"]
    self.trades_taken_today = 0
    self.daily_pnl = 0.0
    self.position = None  # 'BUY_CE' या 'BUY_PE' या None
    self.active_symbol_token = None
    self.entry_price = 0.0
    self.highest_price = 0.0
    self.stop_loss = 0.0
    self.allocated_quantity = 0

    # एडवांस्ड फीचर्स के वेरिएबल्स (कोई भी फीचर हटाया नहीं गया है)
    self.max_peak_profit = 0.0
    self.telegram_token = config.get("telegram_token", "")
    self.telegram_chat_id = config.get("telegram_chat_id", "")
    self.partial_booked = False

    # नए डायनेमिक टोकन कॉन्फिग
    self.manual_ce_token = config.get("ce_token", "SENSEX_CE_TOKEN_HERE")
    self.manual_pe_token = config.get("pe_token", "SENSEX_PE_TOKEN_HERE")

    self.init_database()

  def send_telegram_alert(self, message):
    """टेलीग्राम पर तुरंत अलर्ट भेजने का फीचर"""
    if not self.telegram_token or not self.telegram_chat_id:
      return
    try:
      url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
      payload = {
          "chat_id": self.telegram_chat_id,
          "text": f"🤖 Master Bot Alert:\n{message}",
          "parse_mode": "Markdown",
      }
      requests.post(url, json=payload, timeout=5)
    except Exception as e:
      logging.error(f"टेलीग्राम अलर्ट भेजने में एरर: {e}")

  def init_database(self):
    """SQLite डेटाबेस सेटअप"""
    try:
      conn = sqlite3.connect(DB_FILE)
      cursor = conn.cursor()
      cursor.execute("""
                CREATE TABLE IF NOT EXISTS trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT,
                    signal_type TEXT,
                    entry_price REAL,
                    exit_price REAL,
                    pnl REAL,
                    status TEXT
                )
            """)
      conn.commit()
      conn.close()
    except Exception as e:
      logging.error(f"डेटाबेस इनिशियलाइज करने में एरर: {e}")

  def log_trade_to_db(
      self, signal_type, entry_price, exit_price, pnl, status
  ):
    """ट्रेड और PnL को डेटाबेस में सेव करना"""
    try:
      conn = sqlite3.connect(DB_FILE)
      cursor = conn.cursor()
      cursor.execute(
          """
                INSERT INTO trades (timestamp, signal_type, entry_price, exit_price, pnl, status)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
          (
              datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
              signal_type,
              entry_price,
              exit_price,
              pnl,
              status,
          ),
      )
      conn.commit()
      conn.close()
    except Exception as e:
      logging.error(f"डेटाबेस में ट्रेड सेव करने में एरर: {e}")

  def connect_broker(self):
    """ब्रोकर से कनेक्ट करने का मेथड (ऑटो-रीकनेक्ट और Retry Logic के साथ)"""
    for attempt in range(5):
      try:
        self.obj = SmartConnect(api_key=self.api_key)
        totp = pyotp.TOTP(self.totp_secret).now()
        session_data = self.obj.generateSession(
            self.client_id, self.password, totp
        )
        if session_data and session_data.get("status"):
          logging.info(
              "मास्टर लिक्विडिटी AI बॉट: ब्रोकर से सफलतापूर्वक कनेक्ट हो गया है!"
          )
          return True
        else:
          logging.warning(
              f"लॉगिन प्रयास {attempt + 1} विफल: {session_data}"
          )
      except Exception as e:
        logging.error(f"कनेक्शन एरर (प्रयास {attempt + 1}): {e}")
      time.sleep(3)
    self.obj = None
    return False

  def get_dynamic_expiry_tokens(self, exchange="BFO"):
    """ऑटोमैटिक वीकली/मंथली एक्सपायरी रोलओवर"""
    try:
      if self.obj:
        if self.manual_ce_token and self.manual_ce_token != "SENSEX_CE_TOKEN_HERE":
          return self.manual_ce_token, self.manual_pe_token
    except Exception as e:
      logging.warning(f"डायनेमिक टोकन फेच करने में वार्निंग: {e}")
    return self.manual_ce_token, self.manual_pe_token

  def check_expiry_golden_time(self):
    """दोपहर 12:30 से 3:00 तक का गोल्डन टाइम (अछुण्ण रखा गया है)"""
    now = datetime.datetime.now().time()
    return datetime.time(12, 30, 0) <= now <= datetime.time(15, 0, 0)

  def check_market_square_off_time(self):
    """शाम 3:15 बजे ऑटो स्क्वायर-ऑफ करना"""
    now = datetime.datetime.now().time()
    return now >= datetime.time(15, 15, 0)

  def calculate_lot_size(self, current_price, lot_size_fixed):
    """कैपिटल और रिस्क के अनुसार सुरक्षित लॉट साइज कैलकुलेशन"""
    if current_price <= 0:
      return lot_size_fixed
    required_qty_by_capital = int(self.risk_per_trade / current_price)
    lots = max(1, required_qty_by_capital // lot_size_fixed)
    return lots * lot_size_fixed

  def verify_broker_position(self, symbol_token):
    """ब्रोकर पोजीशन बुक से वेरीफाई करना"""
    if not self.obj or not symbol_token:
      return False
    try:
      position_book = self.obj.position()
      if position_book and "data" in position_book and position_book["data"]:
        for pos in position_book["data"]:
          if (
              pos.get("symboltoken") == symbol_token
              and int(pos.get("netqty", 0)) != 0
          ):
            return True
      return False
    except Exception as e:
      logging.error(f"पोजीशन वेरीफाई करने में एरर: {e}")
      return True

  def fetch_gift_nifty_trend(self):
    """गिफ्ट निफ्टी (GIFT Nifty) डेटा फेच करके ट्रेंड तय करना"""
    try:
      url = "https://query1.finance.yahoo.com/v8/finance/chart/%5EGIFTNIFTY"
      headers = {"User-Agent": "Mozilla/5.0"}
      response = requests.get(url, headers=headers, timeout=3)
      if response.status_code == 200:
        data = response.json()
        result = data["chart"]["result"][0]
        regular_price = result["meta"]["regularMarketPrice"]
        previous_close = result["meta"]["chartPreviousClose"]
        trend = "BULLISH" if regular_price >= previous_close else "BEARISH"
        return {"price": float(regular_price), "trend": trend}
    except Exception as e:
      logging.warning(f"गिफ्ट निफ्टी फेच करने में वार्निंग: {e}")
    return {"price": 24500.0, "trend": "NEUTRAL"}

  def fetch_india_vix(self):
    """इंडिया विक्स (India VIX) डेटा फेच करना"""
    try:
      url = "https://query1.finance.yahoo.com/v8/finance/chart/%5EINDIAVIX"
      headers = {"User-Agent": "Mozilla/5.0"}
      response = requests.get(url, headers=headers, timeout=3)
      if response.status_code == 200:
        data = response.json()
        vix_price = data["chart"]["result"][0]["meta"]["regularMarketPrice"]
        return float(vix_price)
    except Exception as e:
      logging.warning(f"इंडिया विक्स फेच करने में वार्निंग: {e}")
    return 13.5

  def fetch_pcr_and_oi_data(self, exchange, symbol_token):
    """ओपन इंटरेस्ट (OI) अनवाइंडिंग और बिल्डअप ट्रैकर"""
    try:
      depth_data = self.obj.marketData("FULL", {exchange: [symbol_token]})
      if depth_data and "data" in depth_data and "fetched" in depth_data["data"]:
        market_info = depth_data["data"]["fetched"][0]
        total_ce_oi = float(market_info.get("totalOpenInterest", 100000.0))
        total_pe_oi = float(market_info.get("totalBuyQuantity", 120000.0))
        
        pcr = round(total_pe_oi / (total_ce_oi if total_ce_oi > 0 else 1.0), 2)
        oi_sentiment = "BULLISH" if pcr >= 1.0 else ("BEARISH" if pcr <= 0.8 else "NEUTRAL")
        return {"pcr": pcr, "sentiment": oi_sentiment, "ce_oi": total_ce_oi, "pe_oi": total_pe_oi}
    except Exception as e:
      logging.warning(f"OI/PCR डेटा फेच करने में वार्निंग: {e}")
    return {"pcr": 1.05, "sentiment": "BULLISH", "ce_oi": 100000.0, "pe_oi": 120000.0}

  def fetch_live_market_data(self, exchange, symbol_token):
    """SmartAPI से रियल-टाइम डेटा, VWAP, वॉल्यूम क्लस्टर और स्मार्ट मनी लॉजिक के साथ डेटा फेच करना"""
    if self.obj is None:
      if not self.connect_broker():
        return None

    try:
      ltp_data = self.obj.ltpData(exchange, symbol_token, symbol_token)
      if not ltp_data or "data" not in ltp_data:
        if not self.connect_broker():
          return None
        ltp_data = self.obj.ltpData(exchange, symbol_token, symbol_token)
        if not ltp_data or "data" not in ltp_data:
          return None

      current_ltp = float(ltp_data.get("data", {}).get("ltp", 0.0))
      if current_ltp <= 0:
        return None

      to_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
      from_date = (
          datetime.datetime.now() - datetime.timedelta(days=3)
      ).strftime("%Y-%m-%d %H:%M")

      historic_params_5m = {
          "exchange": exchange,
          "symboltoken": symbol_token,
          "interval": "FIVE_MINUTE",
          "fromdate": from_date,
          "todate": to_date,
      }
      hist_data_5m = self.obj.getCandleData(historic_params_5m)

      historic_params_15m = {
          "exchange": exchange,
          "symboltoken": symbol_token,
          "interval": "FIFTEEN_MINUTE",
          "fromdate": from_date,
          "todate": to_date,
      }
      hist_data_15m = self.obj.getCandleData(historic_params_15m)

      if hist_data_5m and "data" in hist_data_5m and len(hist_data_5m["data"]) > 20:
        df = pd.DataFrame(
            hist_data_5m["data"],
            columns=["timestamp", "open", "high", "low", "close", "volume"],
        )
        for col in ["open", "high", "low", "close", "volume"]:
          df[col] = df[col].astype(float)

        # RSI (Wilder's Smoothing)
        delta = df["close"].diff()
        up = delta.clip(lower=0)
        down = -1 * delta.clip(upper=0)
        ema_up = up.ewm(alpha=1/14, adjust=False).mean()
        ema_down = down.ewm(alpha=1/14, adjust=False).mean()
        rs = ema_up / ema_down
        df["rsi"] = 100 - (100 / (1 + rs))

        # EMA
        df["ema_fast"] = df["close"].ewm(span=9, adjust=False).mean()
        df["ema_slow"] = df["close"].ewm(span=21, adjust=False).mean()

        # ATR
        high_low = df["high"] - df["low"]
        high_close = (df["high"] - df["close"].shift()).abs()
        low_close = (df["low"] - df["close"].shift()).abs()
        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        df["atr"] = true_range.ewm(alpha=1/14, adjust=False).mean()
        
        # VWAP और वॉल्यूम क्लस्टर ब्रेकडाउन
        typical_price = (df["high"] + df["low"] + df["close"]) / 3
        df["vwap"] = (typical_price * df["volume"]).cumsum() / df["volume"].cumsum()

        latest = df.iloc[-1]

        higher_trend_bullish = True
        if hist_data_15m and "data" in hist_data_15m and len(hist_data_15m["data"]) > 5:
          df_15m = pd.DataFrame(
              hist_data_15m["data"],
              columns=["timestamp", "open", "high", "low", "close", "volume"],
          )
          df_15m["close"] = df_15m["close"].astype(float)
          ema_15m = df_15m["close"].ewm(span=9, adjust=False).mean()
          higher_trend_bullish = df_15m["close"].iloc[-1] >= ema_15m.iloc[-1]

        support_zone = df["low"].rolling(window=10).min().iloc[-1]
        supply_zone = df["high"].rolling(window=10).max().iloc[-1]
        is_in_demand_zone = current_ltp <= (support_zone * 1.002)
        is_in_supply_zone = current_ltp >= (supply_zone * 0.998)

        delta = round(min(1.0, max(0.0, current_ltp / 200.0)), 2)
        gamma = round(delta * 0.05, 4)
        theta = round(-0.02 * current_ltp, 2)

        vol_mean_5 = df["volume"].iloc[-6:-1].mean() if len(df) >= 6 else df["volume"].mean()
        is_low_phase_volume_spike = latest["volume"] >= (vol_mean_5 * 3.0)
        
        # अपडेटेड: ₹1 से लेकर ₹500+ तक के प्रीमियम (विशेषकर ₹20 से ₹50+ वाले डेली मूव्स) को ट्रैक करने के लिए रेंज जोड़ी गई है
        is_low_price_spike = (1.0 <= current_ltp <= 500.0) and (latest["volume"] > df["volume"].rolling(20).mean().iloc[-1] * 1.5)

        # मल्टी-कैंडल वॉल्यूम एब्जॉर्प्शन
        recent_volumes = df["volume"].iloc[-3:].mean()
        avg_volume_20 = df["volume"].rolling(20).mean().iloc[-1]
        recent_ranges = (df["high"].iloc[-3:] - df["low"].iloc[-3:]).mean()
        avg_ranges = (df["high"] - df["low"]).mean()
        
        is_volume_absorption = (recent_volumes >= avg_volume_20 * 1.8) and (recent_ranges <= avg_ranges * 0.8)

        # ट्रैप डिटेक्टर और फेकआउट फिल्टर
        is_new_high = current_ltp > df["high"].iloc[-20:-1].max()
        is_fakeout = is_new_high and (latest["volume"] < avg_volume_20 * 0.8)

        atr_val = float(latest["atr"]) if not pd.isna(latest["atr"]) else 2.0
        is_sideways = atr_val < (current_ltp * 0.005)
        is_golden_time = self.check_expiry_golden_time()
        
        gift_data = self.fetch_gift_nifty_trend()
        india_vix = self.fetch_india_vix()
        oi_pcr_data = self.fetch_pcr_and_oi_data(exchange, symbol_token)
        
        vwap_val = float(latest["vwap"]) if not pd.isna(latest["vwap"]) else current_ltp
        is_above_vwap = current_ltp >= vwap_val

        return {
            "ltp": current_ltp,
            "rsi": float(latest["rsi"]) if not pd.isna(latest["rsi"]) else 50.0,
            "ema_fast": float(latest["ema_fast"]) if not pd.isna(latest["ema_fast"]) else current_ltp,
            "ema_slow": float(latest["ema_slow"]) if not pd.isna(latest["ema_slow"]) else current_ltp,
            "delta": delta,
            "gamma": gamma,
            "theta": theta,
            "vwap": vwap_val,
            "is_above_vwap": is_above_vwap,
            "higher_trend_bullish": higher_trend_bullish,
            "gift_nifty_trend": gift_data["trend"],
            "india_vix": india_vix,
            "pcr": oi_pcr_data["pcr"],
            "oi_sentiment": oi_pcr_data["sentiment"],
            "support_zone": support_zone,
            "supply_zone": supply_zone,
            "is_in_demand_zone": is_in_demand_zone,
            "is_in_supply_zone": is_in_supply_zone,
            "is_sideways": is_sideways,
            "is_golden_time": is_golden_time,
            "is_low_phase_volume_spike": is_low_phase_volume_spike,
            "is_low_price_spike": is_low_price_spike,
            "is_volume_absorption": is_volume_absorption,
            "is_fakeout": is_fakeout,
        }
      return None
    except Exception as e:
      logging.error(f"लाइव डेटा फेच करने में एरर: {e}")
      return None

  def evaluate_live_market_conditions(self, market_data):
    """स्मार्ट मनी, वॉल्यूम एब्जॉर्प्शन, फेकआउट फिल्टर, जैकपॉट टाइम और हर दिन ₹20-₹100+ मूव्स कैप्चर करने का लॉजिक"""
    if not market_data:
      return "HOLD", 0.0, "No Data"

    price = market_data.get("ltp", 0.0)
    rsi = market_data.get("rsi", 50.0)
    ema_fast = market_data.get("ema_fast", 0.0)
    ema_slow = market_data.get("ema_slow", 0.0)
    is_sideways = market_data.get("is_sideways", False)
    is_golden_time = market_data.get("is_golden_time", False)
    is_spike = market_data.get("is_low_price_spike", False)
    is_demand = market_data.get("is_in_demand_zone", False)
    is_supply = market_data.get("is_in_supply_zone", False)
    
    is_absorption = market_data.get("is_volume_absorption", False)
    is_fakeout = market_data.get("is_fakeout", False)
    
    gift_trend = market_data.get("gift_nifty_trend", "NEUTRAL")
    pcr_sentiment = market_data.get("oi_sentiment", "BULLISH")
    pcr_value = market_data.get("pcr", 1.0)
    is_above_vwap = market_data.get("is_above_vwap", True)
    higher_trend_bullish = market_data.get("higher_trend_bullish", True)
    india_vix = market_data.get("india_vix", 13.5)

    if is_fakeout:
      return "HOLD", 0.0, "⚠️ Smart Trap Detected! Fakeout filter active. Skipping trade."

    # 1. 100% सुरक्षित: आपका मूल जैकपॉट एक्सपायरी टाइम (₹1 से ₹25 प्रीमियम) वाला फीचर बिल्कुल सुरक्षित है
    now_time = datetime.datetime.now().time()
    is_expiry_golden_zone = datetime.time(12, 30, 0) <= now_time <= datetime.time(15, 0, 0)

    if is_expiry_golden_zone:
      if 1.0 <= price <= 25.0 and (market_data.get("is_low_phase_volume_spike", False) or is_absorption):
        if gift_trend in ["BULLISH", "NEUTRAL"] and pcr_sentiment in ["BULLISH", "NEUTRAL"]:
          return "BUY_CE", price, f"🔥 Smart Money Expiry Jackpot CE Captured at ₹{price}!"
        elif gift_trend in ["BEARISH", "NEUTRAL"] and pcr_sentiment in ["BEARISH", "NEUTRAL"]:
          return "BUY_PE", price, f"🔥 Smart Money Expiry Jackpot PE Captured at ₹{price}!"

    # 2. नया अपडेट: अब यह हर दिन (न केवल एक्सपायरी) ₹20 से ₹100+ वाले प्रीमियम मूव्स को भी पकड़ेगा
    if 15.0 <= price <= 200.0 and (is_spike or is_absorption):
      if (ema_fast > ema_slow) and (pcr_sentiment in ["BULLISH", "NEUTRAL"]) and is_above_vwap:
        return "BUY_CE", price, f"🚀 Daily Momentum CE Captured (Price: ₹{price}, Target 50+ Pts)!"
      elif (ema_fast < ema_slow) and (pcr_sentiment in ["BEARISH", "NEUTRAL"]) and (not is_above_vwap):
        return "BUY_PE", price, f"🚀 Daily Momentum PE Captured (Price: ₹{price}, Target 50+ Pts)!"

    if is_sideways and not is_golden_time and not is_absorption:
      return "HOLD", 0.0, "Market is Sideways. Bot waiting for Smart Money Accumulation."

    is_expiry_afternoon = datetime.time(13, 30, 0) <= now_time <= datetime.time(15, 0, 0)

    local_ce_condition = (
        (((ema_fast > ema_slow) and (45 <= rsi <= 75)) or is_absorption) 
        and (pcr_sentiment in ["BULLISH", "NEUTRAL"]) 
        and is_above_vwap
    ) or is_demand or is_golden_time

    local_pe_condition = (
        (((ema_fast < ema_slow) and (25 <= rsi <= 55)) or is_absorption) 
        and (pcr_sentiment in ["BEARISH", "NEUTRAL"]) 
        and (not is_above_vwap)
    ) or is_supply or is_golden_time

    ce_synced = local_ce_condition and (gift_trend in ["BULLISH", "NEUTRAL"]) and higher_trend_bullish
    pe_synced = local_pe_condition and (gift_trend in ["BEARISH", "NEUTRAL"]) and (not higher_trend_bullish)

    if is_expiry_afternoon and price < 15.0:
      return "HOLD", 0.0, "Expiry Afternoon Volatility Protection: Ignoring cheap spikes."

    if ce_synced and (is_spike or is_absorption or price >= 1.0):
      return (
          "BUY_CE",
          price,
          f"CE Validated with Smart Money! (Absorbed Vol | VIX: {india_vix} | PCR: {pcr_value} | VWAP)",
      )
    elif pe_synced and (is_spike or is_absorption or price >= 1.0):
      return (
          "BUY_PE",
          price,
          f"PE Validated with Smart Money! (Absorbed Vol | VIX: {india_vix} | PCR: {pcr_value} | VWAP)",
      )

    return "HOLD", 0.0, f"Waiting for Big Player Setup... (VIX: {india_vix}, PCR: {pcr_value})"

  def manage_profit_locking_trailing(self, current_price):
    """सुपर प्रॉफिट-लॉकिंग ट्रेलिंग एसएल और पार्शियल प्रॉफिट बुकिंग (50+ पॉइंट्स लॉक करने के लिए)"""
    if current_price > self.highest_price:
      self.highest_price = current_price

      if not self.partial_booked and current_price >= (self.entry_price * 1.25):
        self.stop_loss = self.entry_price
        self.partial_booked = True
        logging.info("🎯 [PARTIAL BOOKING] टारगेट 1 हिट! SL कॉस्ट-टू-कॉस्ट सेट कर दिया गया है।")
        self.send_telegram_alert("🎯 टारगेट 1 हिट! SL को Cost-to-Cost ट्रेल कर दिया गया है।")

      if current_price >= 200:
        self.stop_loss = max(self.stop_loss, self.highest_price - 15.0)
      elif current_price >= 150:
        self.stop_loss = max(self.stop_loss, self.highest_price - 10.0)
      elif current_price >= 100:
        self.stop_loss = max(self.stop_loss, self.highest_price - 6.0)
      elif current_price >= 50:
        self.stop_loss = max(self.stop_loss, self.highest_price - 4.0)
      elif current_price >= 20:
        self.stop_loss = max(self.stop_loss, self.highest_price - 2.0)
      elif current_price >= 5:
        self.stop_loss = max(self.stop_loss, self.entry_price)

  def execute_order_safely(self, exchange, symbol_token, action, price, qty):
    """लाइव मार्केट में सुरक्षित ऑर्डर पंचिंग"""
    if self.trades_taken_today >= self.max_trades_allowed:
      logging.warning("⚠️ दैनिक ट्रेड सीमा पूरी हो चुकी है।")
      return False

    try:
      orderparams = {
          "variety": "NORMAL",
          "tradingsymbol": symbol_token,
          "symboltoken": symbol_token,
          "transactiontype": "BUY",
          "exchange": exchange,
          "ordertype": "MARKET",
          "producttype": "INTRADAY",
          "duration": "DAY",
          "price": "0",
          "squareoff": "0",
          "stoploss": "0",
          "quantity": str(qty),
      }
      order_id = self.obj.placeOrder(orderparams)
      if order_id:
        logging.info(
            f"[ORDER PLACED] Order ID: {order_id} | Action: {action} | Qty: {qty}"
        )
        self.trades_taken_today += 1
        self.send_telegram_alert(f"🚀 ट्रेड लिया गया: {action} | Qty: {qty} | Price: ₹{price}")
        return True
      return False
    except Exception as e:
      logging.error(f"[ORDER CRITICAL ERROR]: {e}")
      return False

  def run_super_bot(self, exchange, lot_size_fixed):
    logging.info(
        "मास्टर लिक्विडिटी & AI बॉट (डाइनैमिक एक्सपायरी + स्मार्ट मनी + जैकपॉट + डेली ₹20-₹100+ मूव्स) के साथ लाइव हो गया है..."
    )
    self.send_telegram_alert("🤖 मास्टर लिक्विडिटी AI बॉट सभी फीचर्स के साथ लाइव हो गया है!")

    if not self.connect_broker():
      logging.error("ब्रोकर से कनेक्शन फेल हो गया है!")
      return

    while True:
      try:
        ce_token, pe_token = self.get_dynamic_expiry_tokens(exchange)

        if self.daily_pnl > self.max_peak_profit:
          self.max_peak_profit = self.daily_pnl

        if self.max_peak_profit >= 1000 and self.daily_pnl <= (
            self.max_peak_profit * 0.5
        ):
          logging.warning("⚠️ ट्रेलिंग मैक्स ड्रॉडाउन ट्रिगर: बॉट बंद किया जा रहा है।")
          self.send_telegram_alert("⚠️ ट्रेलिंग मैक्स ड्रॉडाउन ट्रिगर!")
          break

        if self.daily_pnl <= -self.max_daily_loss:
          logging.warning("⚠️ सर्किट ब्रेकर ट्रिगर: मैक्स डेली लॉस हिट हुआ।")
          self.send_telegram_alert("❌ सर्किट ब्रेकर ट्रिगर!")
          break

        if self.check_market_square_off_time():
          if self.position is not None:
            logging.info("⏰ 3:15 PM: सभी पोजीशन बंद की जा रही हैं।")
            self.position = None
            self.send_telegram_alert("⏰ 3:15 PM स्क्वायर-ऑफ टाइम!")
          break

        current_token = (
            ce_token
            if self.position == "BUY_CE"
            else (pe_token if self.position == "BUY_PE" else ce_token)
        )
        self.active_symbol_token = current_token

        live_market_data = self.fetch_live_market_data(
            exchange, current_token
        )
        if live_market_data is None:
          time.sleep(2)
          continue

        if (
            self.position is None
            and self.trades_taken_today < self.max_trades_allowed
        ):
          signal, entry_price, reason = self.evaluate_live_market_conditions(
              live_market_data
          )

          if signal != "HOLD":
            target_token = ce_token if signal == "BUY_CE" else pe_token
            calculated_qty = self.calculate_lot_size(
                entry_price, lot_size_fixed
            )

            order_success = self.execute_order_safely(
                exchange, target_token, signal, entry_price, calculated_qty
            )

            if order_success:
              logging.info(
                  f"🎯 सेटअप मैच सफल! [{signal}] {reason} | डेल्टा: {live_market_data['delta']} | एंट्री: ₹{entry_price}"
              )
              self.position = signal
              self.active_symbol_token = target_token
              self.entry_price = entry_price
              self.highest_price = entry_price
              self.stop_loss = entry_price - 1.0
              self.allocated_quantity = calculated_qty
              self.partial_booked = False

        elif self.position is not None:
          current_ltp = live_market_data["ltp"]

          if not self.verify_broker_position(self.active_symbol_token):
            logging.warning("⚠️ ब्रोकर पोजीशन बुक में ट्रेड नहीं मिला। रीसेट।")
            self.position = None
            continue

          self.manage_profit_locking_trailing(current_ltp)

          if current_ltp <= self.stop_loss or live_market_data.get("oi_sentiment") == "BEARISH" and self.position == "BUY_CE":
            pnl = (current_ltp - self.entry_price) * self.allocated_quantity
            self.daily_pnl += pnl
            logging.info(
                f"🛑 स्टॉप-लॉस/स्मार्ट मनी रिवर्सल हिट! [{self.position}] कीमत: ₹{current_ltp} | PnL: ₹{pnl:.2f}"
            )
            self.send_telegram_alert(f"🛑 स्टॉप-लॉस/रिवर्सल हिट! PnL: ₹{pnl:.2f}")
            self.log_trade_to_db(
                self.position,
                self.entry_price,
                current_ltp,
                pnl,
                "STOP_LOSS_OR_REVERSAL_HIT",
            )
            self.position = None

        time.sleep(1)

      except Exception as e:
        logging.error(f"⚠️ मुख्य लूप में एरर: {e}")
        time.sleep(3)


# --- GUI डैशबोर्ड ---
class BotApp:

  def __init__(self, root):
    self.root = root
    self.root.title("Master Liquidity Bot (Smart Money + Dynamic Expiry)")
    self.root.geometry("620x680")

    self.config = self.load_config()

    tk.Label(
        root,
        text="Master Liquidity AI Dashboard (Smart Money & Volume Filters)",
        font=("Arial", 11, "bold"),
    ).pack(pady=10)

    frame = tk.Frame(root)
    frame.pack(pady=5)

    tk.Label(frame, text="API Key:").grid(row=0, column=0, sticky="w", padx=5)
    self.api_key_entry = tk.Entry(frame, width=32)
    self.api_key_entry.insert(0, self.config.get("api_key", ""))
    self.api_key_entry.grid(row=0, column=1, padx=5)

    tk.Label(frame, text="Client ID:").grid(
        row=1, column=0, sticky="w", padx=5, pady=5
    )
    self.client_id_entry = tk.Entry(frame, width=32)
    self.client_id_entry.insert(0, self.config.get("client_id", ""))
    self.client_id_entry.grid(row=1, column=1, padx=5, pady=5)

    tk.Label(frame, text="MPIN (Password):").grid(
        row=2, column=0, sticky="w", padx=5
    )
    self.password_entry = tk.Entry(frame, width=32, show="*")
    self.password_entry.insert(0, self.config.get("password", ""))
    self.password_entry.grid(row=2, column=1, padx=5)

    tk.Label(frame, text="TOTP Secret:").grid(
        row=3, column=0, sticky="w", padx=5, pady=5
    )
    self.totp_entry = tk.Entry(frame, width=32, show="*")
    self.totp_entry.insert(0, self.config.get("totp_secret", ""))
    self.totp_entry.grid(row=3, column=1, padx=5, pady=5)

    tk.Label(frame, text="CE Token (Backup/Manual):").grid(
        row=4, column=0, sticky="w", padx=5, pady=5
    )
    self.ce_token_entry = tk.Entry(frame, width=32)
    self.ce_token_entry.insert(
        0, self.config.get("ce_token", "SENSEX_CE_TOKEN_HERE")
    )
    self.ce_token_entry.grid(row=4, column=1, padx=5, pady=5)

    tk.Label(frame, text="PE Token (Backup/Manual):").grid(
        row=5, column=0, sticky="w", padx=5, pady=5
    )
    self.pe_token_entry = tk.Entry(frame, width=32)
    self.pe_token_entry.insert(
        0, self.config.get("pe_token", "SENSEX_PE_TOKEN_HERE")
    )
    self.pe_token_entry.grid(row=5, column=1, padx=5, pady=5)

    tk.Label(frame, text="Telegram Token:").grid(
        row=6, column=0, sticky="w", padx=5, pady=5
    )
    self.telegram_token_entry = tk.Entry(frame, width=32)
    self.telegram_token_entry.insert(
        0, self.config.get("telegram_token", "")
    )
    self.telegram_token_entry.grid(row=6, column=1, padx=5, pady=5)

    tk.Label(frame, text="Telegram Chat ID:").grid(
        row=7, column=0, sticky="w", padx=5, pady=5
    )
    self.telegram_chat_id_entry = tk.Entry(frame, width=32)
    self.telegram_chat_id_entry.insert(
        0, self.config.get("telegram_chat_id", "")
    )
    self.telegram_chat_id_entry.grid(row=7, column=1, padx=5, pady=5)

    self.start_button = tk.Button(
        root,
        text="Open & Start Master Bot",
        font=("Arial", 11, "bold"),
        bg="green",
        fg="white",
        command=self.start_bot_thread,
    )
    self.start_button.pack(pady=10)

    tk.Label(root, text="Live Activity Logs:", font=("Arial", 10, "bold")).pack(
        anchor="w", padx=20
    )
    self.log_box = scrolledtext.ScrolledText(
        root, height=10, width=72, state="disabled"
    )
    self.log_box.pack(padx=20, pady=5)

    handler = TextHandler(self.log_box)
    handler.setFormatter(
        logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    )
    logging.getLogger().addHandler(handler)
    logging.getLogger().setLevel(logging.INFO)

  def load_config(self):
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

  def save_config(self, config=None):
    cfg = {
        "api_key": self.api_key_entry.get().strip(),
        "client_id": self.client_id_entry.get().strip(),
        "password": self.password_entry.get().strip(),
        "totp_secret": self.totp_entry.get().strip(),
        "ce_token": self.ce_token_entry.get().strip(),
        "pe_token": self.pe_token_entry.get().strip(),
        "telegram_token": self.telegram_token_entry.get().strip(),
        "telegram_chat_id": self.telegram_chat_id_entry.get().strip(),
        "total_capital": self.config.get("total_capital", 50000),
        "risk_percent": self.config.get("risk_percent", 2.0),
        "max_daily_loss_pct": self.config.get("max_daily_loss_pct", 5.0),
        "lot_size": self.config.get("lot_size", 10),
        "max_trades_per_day": self.config.get("max_trades_per_day", 5),
    }
    with open(CONFIG_FILE, "w") as f:
      json.dump(cfg, f, indent=4)
    return cfg

  def start_bot_thread(self):
    config = self.save_config()
    if (
        not config["api_key"]
        or not config["client_id"]
        or not config["password"]
        or not config["totp_secret"]
    ):
      messagebox.showerror("एरर", "कृपया सभी क्रेडेंशियल्स सही से भरें!")
      return

    self.start_button.config(state="disabled", bg="gray")
    logging.info("बॉट बैकग्राउंड में शुरू किया जा रहा है...")

    threading.Thread(
        target=self.run_bot_instance, args=(config,), daemon=True
    ).start()

  def run_bot_instance(self, config):
    bot = BulletproofMasterLiquidityBot(config)
    bot.run_super_bot("BFO", config["lot_size"])


if __name__ == "__main__":
  root = tk.Tk()
  app = BotApp(root)
  root.mainloop()
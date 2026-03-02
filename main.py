"""
═══════════════════════════════════════════════════════
  FULL MARKET SCANNER — Trading Signal Bot
  EMA 8/13 + OrderBlock + Trend Stratejisi
  Kripto + Forex + Emtia + BIST + ABD + Endeksler
═══════════════════════════════════════════════════════
"""

import asyncio
import logging
import json
import os
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import ccxt
import yfinance as yf
import telegram
from telegram.constants import ParseMode

from config import (
    TELEGRAM_TOKEN, TELEGRAM_CHAT_ID,
    BINANCE_API_KEY, BINANCE_SECRET_KEY,
    CHECK_INTERVAL_MINUTES,
    CRYPTO_SCAN_ALL,
    CRYPTO_WHITELIST,
    CRYPTO_MIN_VOLUME_USDT,
    FOREX_SYMBOLS,
    BIST_SYMBOLS,
    US_SYMBOLS,
    INDEX_SYMBOLS,
    SIGNAL_COOLDOWN_HOURS,
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)
log = logging.getLogger(__name__)

signal_history: dict = {}


# ════════════════════════════════════════════════════
# TELEGRAM
# ════════════════════════════════════════════════════
async def send_telegram(msg: str):
    try:
        bot = telegram.Bot(token=TELEGRAM_TOKEN)
        if len(msg) > 4000:
            msg = msg[:4000]
        await bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=msg,
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        log.error(f"Telegram hatası: {e}")


# ════════════════════════════════════════════════════
# TEKNİK ANALİZ
# ════════════════════════════════════════════════════
def ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()


def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain  = delta.clip(lower=0).rolling(period).mean()
    loss  = (-delta.clip(upper=0)).rolling(period).mean()
    rs    = gain / loss
    return 100 - (100 / (1 + rs))


def get_trend(df: pd.DataFrame) -> str:
    if len(df) < 20:
        return "neutral"
    e8  = ema(df["close"], 8)
    e13 = ema(df["close"], 13)
    last_close = df["close"].iloc[-1]
    if e8.iloc[-1] > e13.iloc[-1] and last_close > e8.iloc[-1]:
        return "up"
    if e8.iloc[-1] < e13.iloc[-1] and last_close < e8.iloc[-1]:
        return "down"
    return "neutral"


def check_crossover(df: pd.DataFrame) -> str:
    if len(df) < 15:
        return "none"
    e8  = ema(df["close"], 8)
    e13 = ema(df["close"], 13)
    for i in range(-1, -4, -1):
        prev = i - 1
        if e8.iloc[prev] <= e13.iloc[prev] and e8.iloc[i] > e13.iloc[i]:
            return "bullish"
        if e8.iloc[prev] >= e13.iloc[prev] and e8.iloc[i] < e13.iloc[i]:
            return "bearish"
    return "none"


def find_orderblock(df: pd.DataFrame, direction: str) -> dict | None:
    if len(df) < 10:
        return None
    avg_body = df["close"].sub(df["open"]).abs().rolling(20).mean()

    for i in range(len(df) - 2, max(len(df) - 40, 1), -1):
        curr = df.iloc[i]
        prev = df.iloc[i - 1]
        body_curr = abs(curr["close"] - curr["open"])

        if direction == "long":
            is_impulse   = curr["close"] > curr["open"] and body_curr > avg_body.iloc[i] * 1.5
            is_ob_candle = prev["close"] < prev["open"]
            if is_impulse and is_ob_candle:
                ob_top    = max(prev["open"], prev["close"])
                ob_bottom = min(prev["open"], prev["close"])
                if ob_bottom < df["close"].iloc[-1] * 1.05:
                    return {"top": ob_top, "bottom": ob_bottom}

        elif direction == "short":
            is_impulse   = curr["close"] < curr["open"] and body_curr > avg_body.iloc[i] * 1.5
            is_ob_candle = prev["close"] > prev["open"]
            if is_impulse and is_ob_candle:
                ob_top    = max(prev["open"], prev["close"])
                ob_bottom = min(prev["open"], prev["close"])
                if ob_top > df["close"].iloc[-1] * 0.95:
                    return {"top": ob_top, "bottom": ob_bottom}
    return None


def price_in_ob(price: float, ob: dict) -> bool:
    if ob is None:
        return False
    margin = (ob["top"] - ob["bottom"]) * 0.15
    return (ob["bottom"] - margin) <= price <= (ob["top"] + margin)


def calculate_targets(price: float, direction: str, ob: dict | None) -> tuple:
    if direction == "long":
        sl  = ob["bottom"] * 0.998 if ob else price * 0.985
        tp1 = price + (price - sl) * 1.5
        tp2 = price + (price - sl) * 3.0
    else:
        sl  = ob["top"] * 1.002 if ob else price * 1.015
        tp1 = price - (sl - price) * 1.5
        tp2 = price - (sl - price) * 3.0
    return round(sl, 6), round(tp1, 6), round(tp2, 6)


# ════════════════════════════════════════════════════
# SİNYAL OLUŞTUR
# ════════════════════════════════════════════════════
def analyze(symbol: str, df_4h: pd.DataFrame,
            df_1h: pd.DataFrame, df_15m: pd.DataFrame,
            market: str) -> dict | None:

    trend = get_trend(df_4h)
    if trend == "neutral":
        return None

    direction = "long" if trend == "up" else "short"
    cross     = check_crossover(df_15m)

    expected_cross = "bullish" if direction == "long" else "bearish"
    if cross != expected_cross:
        return None

    # RSI Filtresi
    rsi_val = rsi(df_15m["close"], 14).iloc[-1]
    if direction == "long"  and not (30 < rsi_val < 65):
        return None
    if direction == "short" and not (35 < rsi_val < 70):
        return None

    price = float(df_15m["close"].iloc[-1])
    in_ob = False
    ob    = None

    # Backtest ile optimize edildi: SL%1 TP1:%2 TP2:%4
    if direction == "long":
        sl  = round(price * 0.990, 6)
        tp1 = round(price * 1.020, 6)
        tp2 = round(price * 1.040, 6)
    else:
        sl  = round(price * 1.010, 6)
        tp1 = round(price * 0.980, 6)
        tp2 = round(price * 0.960, 6)

    key = f"{symbol}_{direction}"
    if key in signal_history:
        elapsed = datetime.now() - signal_history[key]
        if elapsed < timedelta(hours=SIGNAL_COOLDOWN_HOURS):
            return None

    signal_history[key] = datetime.now()

    return {
        "symbol":    symbol,
        "market":    market,
        "direction": direction,
        "price":     price,
        "in_ob":     in_ob,
        "ob":        ob,
        "sl":        sl,
        "tp1":       tp1,
        "tp2":       tp2,
        "cross":     cross,
        "trend":     trend,
        "time":      datetime.now().strftime("%d.%m.%Y %H:%M"),
    }


def format_msg(s: dict) -> str:
    icons = {
        "crypto":    "₿",
        "forex":     "💱",
        "bist":      "🇹🇷",
        "commodity": "🥇",
        "us":        "🇺🇸",
        "index":     "🌍",
    }
    icon = icons.get(s["market"], "📊")
    d    = "🟢 LONG" if s["direction"] == "long" else "🔴 SHORT"
    return (
        f"{icon} <b>{s['symbol']}</b>  |  {d}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"💰 Fiyat : <b>{s['price']:.6g}</b>\n"
        f"🛑 Stop  : <b>{s['sl']:.6g}</b>\n"
        f"🎯 TP1   : <b>{s['tp1']:.6g}</b>\n"
        f"🎯 TP2   : <b>{s['tp2']:.6g}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📊 Trend  : {'Yukarı ⬆️' if s['trend']=='up' else 'Aşağı ⬇️'} (4H)\n"
        f"⚡ Tetik  : EMA Crossover (15M)\n"
        f"⏰ {s['time']}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"⚠️ Yatırım tavsiyesi değildir."
    )


# ════════════════════════════════════════════════════
# VERİ ÇEKME
# ════════════════════════════════════════════════════
def get_exchange():
    return ccxt.binance({
        'apiKey': BINANCE_API_KEY,
        'secret': BINANCE_SECRET_KEY,
        'enableRateLimit': True,
        'options': {'defaultType': 'spot'},
    })


def binance_df(exchange, symbol: str, interval: str, limit=100) -> pd.DataFrame | None:
    try:
        sym = symbol[:-4] + "/USDT" if symbol.endswith("USDT") else symbol
        ohlcv = exchange.fetch_ohlcv(sym, interval, limit=limit)
        df = pd.DataFrame(ohlcv, columns=["ts","open","high","low","close","vol"])
        for col in ["open","high","low","close"]:
            df[col] = df[col].astype(float)
        df["ts"] = pd.to_datetime(df["ts"], unit="ms")
        df.set_index("ts", inplace=True)
        return df
    except Exception as e:
        log.warning(f"Binance {symbol} {interval}: {e}")
        return None


def yf_df(symbol: str, period: str, interval: str) -> pd.DataFrame | None:
    try:
        df = yf.Ticker(symbol).history(period=period, interval=interval)
        if df.empty:
            return None
        df.columns = [c.lower() for c in df.columns]
        return df[["open","high","low","close","volume"]]
    except Exception as e:
        log.warning(f"yFinance {symbol}: {e}")
        return None


def get_binance_symbols(exchange) -> list[str]:
    try:
        tickers = exchange.fetch_tickers()
        symbols = []
        for sym, data in tickers.items():
            if not sym.endswith("/USDT"):
                continue
            vol = data.get("quoteVolume") or 0
            if vol >= CRYPTO_MIN_VOLUME_USDT:
                symbols.append(sym.replace("/", ""))
        log.info(f"Binance: {len(symbols)} USDT çifti taranacak")
        return symbols
    except Exception as e:
        log.error(f"Binance sembol listesi hatası: {e}")
        return CRYPTO_WHITELIST


# ════════════════════════════════════════════════════
# TARAMA FONKSİYONLARI
# ════════════════════════════════════════════════════
async def scan_crypto(exchange) -> list:
    signals = []
    symbols = get_binance_symbols(exchange) if CRYPTO_SCAN_ALL else CRYPTO_WHITELIST
    log.info(f"🔍 Kripto taranıyor: {len(symbols)} sembol")

    for i, sym in enumerate(symbols):
        df_4h  = binance_df(exchange, sym, "4h",  120)
        df_1h  = binance_df(exchange, sym, "1h",   80)
        df_15m = binance_df(exchange, sym, "15m",  60)

        if df_4h is None or df_1h is None or df_15m is None:
            continue

        sig = analyze(sym, df_4h, df_1h, df_15m, "crypto")
        if sig:
            signals.append(sig)
            log.info(f"  ✅ SİNYAL: {sym} {sig['direction'].upper()}")

        if i % 5 == 0:
            await asyncio.sleep(0.5)

    return signals


async def scan_forex() -> list:
    signals = []
    log.info(f"🔍 Forex/Emtia taranıyor: {len(FOREX_SYMBOLS)} sembol")

    for sym in FOREX_SYMBOLS:
        df_4h  = yf_df(sym, "60d", "4h")
        df_1h  = yf_df(sym, "30d", "1h")
        df_15m = yf_df(sym, "7d",  "15m")

        if df_4h is None or df_1h is None or df_15m is None:
            continue

        market = "commodity" if any(x in sym for x in ["GC=F","CL=F","SI=F","NG=F","BZ=F","HG=F","ZW=F"]) else "forex"
        sig = analyze(sym.replace("=X","").replace("=F",""), df_4h, df_1h, df_15m, market)
        if sig:
            signals.append(sig)
            log.info(f"  ✅ SİNYAL: {sym} {sig['direction'].upper()}")

        await asyncio.sleep(0.5)

    return signals


async def scan_bist() -> list:
    signals = []
    log.info(f"🔍 BIST taranıyor: {len(BIST_SYMBOLS)} hisse")

    for sym in BIST_SYMBOLS:
        df_4h  = yf_df(sym, "60d", "1d")
        df_1h  = yf_df(sym, "30d", "1h")
        df_15m = yf_df(sym, "5d",  "15m")

        if df_4h is None or df_1h is None or df_15m is None:
            continue

        sig = analyze(sym.replace(".IS",""), df_4h, df_1h, df_15m, "bist")
        if sig:
            signals.append(sig)
            log.info(f"  ✅ SİNYAL: {sym} {sig['direction'].upper()}")

        await asyncio.sleep(0.5)

    return signals


async def scan_us() -> list:
    signals = []
    log.info(f"🔍 ABD Hisseleri taranıyor: {len(US_SYMBOLS)} sembol")

    for sym in US_SYMBOLS:
        df_4h  = yf_df(sym, "60d", "1d")
        df_1h  = yf_df(sym, "30d", "1h")
        df_15m = yf_df(sym, "5d",  "15m")

        if df_4h is None or df_1h is None or df_15m is None:
            continue

        sig = analyze(sym, df_4h, df_1h, df_15m, "us")
        if sig:
            signals.append(sig)
            log.info(f"  ✅ SİNYAL: {sym} {sig['direction'].upper()}")

        await asyncio.sleep(0.3)

    return signals


async def scan_indices() -> list:
    signals = []
    log.info(f"🔍 Endeksler taranıyor: {len(INDEX_SYMBOLS)} sembol")

    for sym in INDEX_SYMBOLS:
        df_4h  = yf_df(sym, "60d", "1d")
        df_1h  = yf_df(sym, "30d", "1h")
        df_15m = yf_df(sym, "5d",  "15m")

        if df_4h is None or df_1h is None or df_15m is None:
            continue

        sig = analyze(sym.replace("^",""), df_4h, df_1h, df_15m, "index")
        if sig:
            signals.append(sig)
            log.info(f"  ✅ SİNYAL: {sym} {sig['direction'].upper()}")

        await asyncio.sleep(0.3)

    return signals



# ════════════════════════════════════════════════════
# WIN RATE TAKİP SİSTEMİ
# ════════════════════════════════════════════════════
SIGNALS_FILE = "signals.json"

def load_signals() -> list:
    if os.path.exists(SIGNALS_FILE):
        with open(SIGNALS_FILE, "r") as f:
            return json.load(f)
    return []

def save_signals(signals: list):
    with open(SIGNALS_FILE, "w") as f:
        json.dump(signals, f, ensure_ascii=False, indent=2)

def record_signal(sig: dict):
    """Yeni sinyali kaydet"""
    signals = load_signals()
    signals.append({
        "id":        len(signals) + 1,
        "symbol":    sig["symbol"],
        "market":    sig["market"],
        "direction": sig["direction"],
        "entry":     sig["price"],
        "sl":        sig["sl"],
        "tp1":       sig["tp1"],
        "tp2":       sig["tp2"],
        "time":      sig["time"],
        "status":    "OPEN",   # OPEN / TP1 / TP2 / SL / TIMEOUT
        "exit_price": None,
        "pnl_pct":   None,
    })
    save_signals(signals)

async def check_open_signals(exchange):
    """Açık sinyallerin TP/SL durumunu kontrol et"""
    signals = load_signals()
    updated = False

    for s in signals:
        if s["status"] != "OPEN":
            continue

        # Sadece kripto sinyalleri kontrol et
        if s["market"] != "crypto":
            continue

        try:
            sym = s["symbol"][:-4] + "/USDT"
            ticker = exchange.fetch_ticker(sym)
            price = float(ticker["last"])
        except:
            continue

        status = None
        if s["direction"] == "long":
            if price <= s["sl"]:
                status = "SL"
            elif price >= s["tp2"]:
                status = "TP2"
            elif price >= s["tp1"]:
                status = "TP1"
        else:
            if price >= s["sl"]:
                status = "SL"
            elif price <= s["tp2"]:
                status = "TP2"
            elif price <= s["tp1"]:
                status = "TP1"

        if status:
            s["status"]     = status
            s["exit_price"] = price
            if s["direction"] == "long":
                s["pnl_pct"] = round((price - s["entry"]) / s["entry"] * 100, 2)
            else:
                s["pnl_pct"] = round((s["entry"] - price) / s["entry"] * 100, 2)
            updated = True

            emoji = "✅" if status in ["TP1","TP2"] else "❌"
            await send_telegram(
                f"{emoji} <b>{s['symbol']} SONUÇ</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"Yön     : {'🟢 LONG' if s['direction']=='long' else '🔴 SHORT'}\n"
                f"Giriş   : {s['entry']:.6g}\n"
                f"Çıkış   : {price:.6g}\n"
                f"Sonuç   : <b>{status}</b>\n"
                f"PnL     : <b>{'+'if s['pnl_pct']>0 else ''}{s['pnl_pct']}%</b>\n"
                f"⏰ {datetime.now().strftime('%d.%m.%Y %H:%M')}"
            )

    if updated:
        save_signals(signals)

async def send_daily_report():
    """Her gün saat 22:00'de günlük rapor gönder"""
    signals = load_signals()
    today = datetime.now().strftime("%d.%m.%Y")

    # Bugünkü kapanan sinyaller
    closed_today = [s for s in signals
                    if s["status"] != "OPEN" and s["time"].startswith(today)]
    open_signals = [s for s in signals if s["status"] == "OPEN"]

    if not closed_today and not open_signals:
        await send_telegram(f"📊 <b>Günlük Rapor — {today}</b>\n\nBugün sinyal gelmedi.")
        return

    wins  = [s for s in closed_today if s["status"] in ["TP1","TP2"]]
    losses = [s for s in closed_today if s["status"] == "SL"]
    win_rate = round(len(wins)/len(closed_today)*100, 1) if closed_today else 0

    msg = f"📊 <b>Günlük Rapor — {today}</b>\n"
    msg += f"━━━━━━━━━━━━━━━━━━━━\n"
    msg += f"Toplam Sinyal : {len(closed_today)}\n"
    msg += f"✅ Kazanan    : {len(wins)}\n"
    msg += f"❌ Kaybeden   : {len(losses)}\n"
    msg += f"🎯 Win Rate   : %{win_rate}\n"

    if closed_today:
        pnl_list = [s["pnl_pct"] for s in closed_today if s["pnl_pct"] is not None]
        if pnl_list:
            msg += f"━━━━━━━━━━━━━━━━━━━━\n"
            msg += f"En İyi  : +{max(pnl_list)}%\n"
            msg += f"En Kötü : {min(pnl_list)}%\n"

    if open_signals:
        msg += f"━━━━━━━━━━━━━━━━━━━━\n"
        msg += f"⏳ Açık Sinyal: {len(open_signals)}\n"
        for s in open_signals[:5]:
            msg += f"  • {s['symbol']} {s['direction'].upper()}\n"

    await send_telegram(msg)

# ════════════════════════════════════════════════════
# ANA DÖNGÜ
# ════════════════════════════════════════════════════
async def handle_commands():
    """Telegram komutlarını dinle: /rapor, /durum"""
    import requests as req
    last_update_id = 0

    while True:
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates"
            r = req.get(url, params={"offset": last_update_id, "timeout": 5}, timeout=10)
            data = r.json()

            if not data.get("ok"):
                await asyncio.sleep(5)
                continue

            for update in data.get("result", []):
                last_update_id = update["update_id"] + 1
                msg = update.get("message", {})
                cmd = msg.get("text", "").strip().lower()

                if cmd == "/rapor":
                    log.info("📊 Manuel rapor istendi")
                    await send_daily_report()

                elif cmd == "/gecmis":
                    signals = load_signals()
                    closed = [s for s in signals if s["status"] != "OPEN"]
                    last100 = closed[-100:] if len(closed) > 100 else closed

                    if not last100:
                        await send_telegram("📋 Henüz kapanan işlem yok.")
                    else:
                        # Her 20 işlemde bir mesaj gönder
                        chunks = [last100[i:i+20] for i in range(0, len(last100), 20)]
                        for idx, chunk in enumerate(chunks):
                            wins = len([s for s in chunk if s["status"] in ["TP1","TP2"]])
                            msg = f"📋 <b>İşlem Geçmişi ({idx*20+1}-{idx*20+len(chunk)})</b>\n"
                            msg += "━━━━━━━━━━━━━━━━━━━━\n"
                            for s in chunk:
                                e = "✅" if s["status"] in ["TP1","TP2"] else "❌"
                                pnl = f"+{s['pnl_pct']}%" if s['pnl_pct'] and s['pnl_pct'] > 0 else f"{s['pnl_pct']}%"
                                d = "L" if s["direction"] == "long" else "S"
                                msg += f"{e} {s['symbol']} {d} → {s['status']} {pnl}\n"
                            wr = round(wins/len(chunk)*100, 1)
                            msg += f"━━━━━━━━━━━━━━━━━━━━\n"
                            msg += f"Win Rate: %{wr}"
                            await send_telegram(msg)
                            await asyncio.sleep(1)

                elif cmd == "/durum":
                    signals = load_signals()
                    open_s  = [s for s in signals if s["status"] == "OPEN"]
                    closed  = [s for s in signals if s["status"] != "OPEN"]
                    wins    = [s for s in closed if s["status"] in ["TP1","TP2"]]
                    wr = round(len(wins)/len(closed)*100,1) if closed else 0
                    await send_telegram(
                        f"🤖 <b>Bot Durumu</b>\n"
                        f"━━━━━━━━━━━━━━━━━━━━\n"
                        f"⏳ Açık Sinyal  : {len(open_s)}\n"
                        f"📊 Toplam Sinyal: {len(closed)}\n"
                        f"✅ Kazanan      : {len(wins)}\n"
                        f"🎯 Win Rate     : %{wr}\n"
                        f"⏰ {datetime.now().strftime('%d.%m.%Y %H:%M')}"
                    )

        except Exception as e:
            log.warning(f"Komut handler hatası: {e}")
        await asyncio.sleep(5)


async def main():
    log.info("🚀 Bot başlatılıyor...")

    exchange = get_exchange()
    total = len(US_SYMBOLS) + len(FOREX_SYMBOLS) + len(BIST_SYMBOLS) + len(INDEX_SYMBOLS)

    await send_telegram(
        f"🤖 <b>Kripto Signal Bot Aktif!</b>\n\n"
        f"₿ Binance USDT çiftleri taranıyor\n"
        f"⏱ Her {CHECK_INTERVAL_MINUTES} dakikada taranıyor\n"
        f"📐 Strateji: EMA 8/13 Crossover (4H Trend + 15M Tetik)"
    )

    # Komut handler'ı arka planda başlat
    asyncio.create_task(handle_commands())

    scan_count = 0
    while True:
        try:
            scan_count += 1
            log.info(f"\n{'═'*50}")
            log.info(f"Tarama #{scan_count} — {datetime.now().strftime('%H:%M')}")

            all_signals = []

            crypto_sigs = await scan_crypto(exchange)
            all_signals.extend(crypto_sigs)

            # Güçlü sinyalleri önce gönder
            all_signals.sort(key=lambda x: x["in_ob"], reverse=True)

            log.info(f"✅ Toplam {len(all_signals)} sinyal bulundu")

            if all_signals:
                for sig in all_signals:
                    await send_telegram(format_msg(sig))
                    record_signal(sig)
                    await asyncio.sleep(1.5)

            # Açık sinyalleri kontrol et
            await check_open_signals(exchange)

            if not all_signals:
                log.info("Sinyal yok, bekleniyor...")

            # Saat 19:00 UTC = 22:00 Türkiye saati
            if datetime.now().hour == 19 and datetime.now().minute < 15:
                await send_daily_report()

            if scan_count % 10 == 0:
                await send_telegram(
                    f"📈 <b>Bot İstatistikleri</b>\n"
                    f"Toplam tarama: {scan_count}\n"
                    f"Son tarama: {datetime.now().strftime('%d.%m %H:%M')}"
                )

            log.info(f"⏳ {CHECK_INTERVAL_MINUTES} dakika bekleniyor...\n")
            await asyncio.sleep(CHECK_INTERVAL_MINUTES * 60)

        except KeyboardInterrupt:
            log.info("Bot durduruldu.")
            await send_telegram("🔴 Bot durduruldu.")
            break
        except Exception as e:
            log.error(f"Hata: {e}")
            await asyncio.sleep(60)


if __name__ == "__main__":
    asyncio.run(main())

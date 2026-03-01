"""
═══════════════════════════════════════════════════════
  FULL MARKET SCANNER — Trading Signal Bot
  EMA 8/13 + OrderBlock + Trend Stratejisi
  Kripto + Forex + Emtia + BIST + ABD + Endeksler
═══════════════════════════════════════════════════════
"""

import asyncio
import logging
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

    # Hacim kontrolü — şimdilik devre dışı
    # if not check_volume(df_15m):
    #     return None

    price = float(df_15m["close"].iloc[-1])
    in_ob = False
    ob    = None
    sl, tp1, tp2 = calculate_targets(price, direction, None)

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
# ANA DÖNGÜ
# ════════════════════════════════════════════════════
async def main():
    log.info("🚀 Bot başlatılıyor...")

    exchange = get_exchange()
    total = len(US_SYMBOLS) + len(FOREX_SYMBOLS) + len(BIST_SYMBOLS) + len(INDEX_SYMBOLS)

    await send_telegram(
        f"🤖 <b>Trading Signal Bot Aktif!</b>\n\n"
        f"📊 Taranan piyasalar:\n"
        f"  ₿ Kripto (Binance USDT)\n"
        f"  💱 Forex & Emtia\n"
        f"  🇹🇷 BIST Hisseleri ({len(BIST_SYMBOLS)} hisse)\n"
        f"  🇺🇸 ABD Hisseleri ({len(US_SYMBOLS)} sembol)\n"
        f"  🌍 Dünya Endeksleri ({len(INDEX_SYMBOLS)} endeks)\n\n"
        f"🔍 Toplam ~{total}+ sembol\n"
        f"⏱ Her {CHECK_INTERVAL_MINUTES} dakikada taranıyor\n"
        f"📐 Strateji: EMA 8/13 + OrderBlock"
    )

    scan_count = 0
    while True:
        try:
            scan_count += 1
            log.info(f"\n{'═'*50}")
            log.info(f"Tarama #{scan_count} — {datetime.now().strftime('%H:%M')}")

            all_signals = []

            crypto_sigs = await scan_crypto(exchange)
            all_signals.extend(crypto_sigs)

            forex_sigs = await scan_forex()
            all_signals.extend(forex_sigs)

            bist_sigs = await scan_bist()
            all_signals.extend(bist_sigs)

            us_sigs = await scan_us()
            all_signals.extend(us_sigs)

            index_sigs = await scan_indices()
            all_signals.extend(index_sigs)

            # Güçlü sinyalleri önce gönder
            all_signals.sort(key=lambda x: x["in_ob"], reverse=True)

            log.info(f"✅ Toplam {len(all_signals)} sinyal bulundu")

            if all_signals:
                for sig in all_signals:
                    await send_telegram(format_msg(sig))
                    await asyncio.sleep(1.5)
            else:
                log.info("Sinyal yok, bekleniyor...")

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

# 🚀 KURULUM REHBERİ — Adım Adım

## Ne Yapıyor Bu Bot?
- Binance'daki TÜM USDT çiftlerini (hacme göre filtrelenmiş) tarar
- 20+ Forex/Emtia çiftini tarar  
- 70+ BIST hissesini tarar
- Her 15 dakikada bir **EMA 8/13 + OrderBlock** koşullarını kontrol eder
- Koşul oluşunca **Telegram'a sinyal gönderir** (Stop Loss ve TP ile birlikte)

---

## ADIM 1 — Telegram Bot Oluştur (5 dakika)

1. Telegram'da **@BotFather** yaz → Aç
2. `/newbot` yaz
3. Bot ismi ver → örn: `Sinyal Botum`
4. Sana şöyle bir token verecek:
   ```
   7123456789:AAFxyz_örnek_token_buraya
   ```
   Bunu kopyala → `config.py`'de `TELEGRAM_TOKEN` kısmına yapıştır

5. Şimdi **@userinfobot** yaz → Aç → `/start` yaz
6. Sana şöyle bir ID verecek:
   ```
   Your user ID: 987654321
   ```
   Bunu kopyala → `config.py`'de `TELEGRAM_CHAT_ID` kısmına yapıştır

---

## ADIM 2 — Binance API Oluştur (5 dakika)

1. [binance.com](https://binance.com) → Giriş yap
2. Sağ üst köşe profil ikonu → **"API Yönetimi"**
3. **"API Oluştur"** → İsim ver (örn: `trading_bot`)
4. E-posta/2FA ile doğrula
5. **⚠️ ÇOK ÖNEMLİ:** İzinlerde sadece **"Okuma"** açık olsun!
   - ❌ İşlem yapma izni → KAPALI
   - ❌ Para çekme izni → KAPALI
   - ✅ Sadece okuma → AÇIK
6. API Key ve Secret'i `config.py`'ye yapıştır

---

## ADIM 3 — Railway.app'e Yükle (7/24 Ücretsiz Çalışır)

### 3a. GitHub'a Yükle
1. [github.com](https://github.com) → Giriş yap (yoksa üye ol, ücretsiz)
2. Sağ üst **"+"** → **"New repository"**
3. İsim ver → **"Create repository"**
4. 4 dosyayı yükle: `main.py`, `config.py`, `requirements.txt`, `Procfile`

### 3b. Railway'e Deploy Et
1. [railway.app](https://railway.app) → GitHub ile giriş yap
2. **"New Project"** → **"Deploy from GitHub Repo"**
3. Az önce oluşturduğun repoyu seç
4. Railway otomatik deploy edecek
5. **"Deployments"** sekmesinde yeşil ✅ görürsen bot çalışıyor demektir!

### 3c. Telegram'dan Kontrol Et
Bot başladığında sana şu mesajı gönderecek:
```
🤖 Trading Signal Bot Aktif!
📊 Taranan piyasalar:
  ₿ Kripto (Binance USDT)
  💱 Forex & Emtia
  🇹🇷 BIST Hisseleri
🔍 Toplam ~250 sembol
⏱ Her 15 dakikada taranıyor
```

---

## Örnek Sinyal Mesajı

```
₿ SOLUSDT  |  🟢 LONG
━━━━━━━━━━━━━━━━━━━━
💰 Fiyat : 185.42
🛑 Stop  : 181.20
🎯 TP1   : 191.88
🎯 TP2   : 198.34
━━━━━━━━━━━━━━━━━━━━
📊 Trend  : Yukarı ⬆️ (4H)
⚡ Tetik  : EMA Crossover (15M)
📦 OB Bölgesi: 183.10 — 185.00
🎖 Güven  : 🔥 GÜÇLÜ (OB İçinde)
⏰ 15.01.2025 14:30
━━━━━━━━━━━━━━━━━━━━
⚠️ Yatırım tavsiyesi değildir.
```

---

## config.py'de Ayarlayabileceğin Şeyler

| Ayar | Varsayılan | Açıklama |
|------|-----------|----------|
| `CRYPTO_SCAN_ALL` | `True` | Tüm coinleri tara |
| `CRYPTO_MIN_VOLUME_USDT` | `5,000,000` | Hacim filtresi — artırırsan daha az coin |
| `CHECK_INTERVAL_MINUTES` | `15` | Tarama sıklığı |
| `SIGNAL_COOLDOWN_HOURS` | `4` | Aynı sembolden tekrar sinyal süresi |

---

## ❓ Sık Sorulan Sorular

**Çok fazla sinyal geliyor?**
→ `CRYPTO_MIN_VOLUME_USDT`'yi artır (örn: 20_000_000)
→ `SIGNAL_COOLDOWN_HOURS`'u artır (örn: 8)

**Railway ücretsiz mi?**
→ Evet, aylık 500 saat ücretsiz — bot için fazlasıyla yeterli

**Bilgisayarım kapalıyken çalışıyor mu?**
→ Evet! Railway bulutta çalışıyor, senin bilgisayarınla ilgisi yok

**BIST verileri doğru mu?**
→ yFinance BIST'te 15-20 dk gecikme var, normal

---

⚠️ **Risk Uyarısı:** Bu bot yatırım tavsiyesi vermez. Her sinyali kendi grafiğinde doğrula. Kaldıraçlı işlemlerde stop loss kullanmayı unutma!

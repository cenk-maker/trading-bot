# ═══════════════════════════════════════════════════
#  TRADING BOT AYARLARI — config.py
#  Buraya kendi bilgilerini yaz, başka hiçbir dosyaya dokunma!
# ═══════════════════════════════════════════════════

# ─────────────────────────────────────────────
# TELEGRAM
# Nasıl alınır → KURULUM.md dosyasını oku
# ─────────────────────────────────────────────
TELEGRAM_TOKEN   = "8276093631:AAHEWLTe3F98B-0LuujG8bEtEuNhvkPaBsk"
TELEGRAM_CHAT_ID = "1084582324"         

# ─────────────────────────────────────────────
# BİNANCE API (Sadece okuma izni yeterli!)
# Nasıl alınır → KURULUM.md dosyasını oku
# ─────────────────────────────────────────────
BINANCE_API_KEY    = "KTVCx0fZLw455hSDMfrAOTYu5mcOZcumAbFocgdCfwUURPAQClKXTwW9JPgPCgfK"
BINANCE_SECRET_KEY = "I23WW9kPFUJiig82GviP3oghoPTZjfHwvf8On0Uio4rjCIX9gVwnY3nbKouhMa1M"

# ─────────────────────────────────────────────
# KRİPTO TARAMA AYARLARI
# ─────────────────────────────────────────────
CRYPTO_SCAN_ALL = True          # True = Tüm USDT çiftleri (önerilir)
                                 # False = Sadece CRYPTO_WHITELIST'teki semboller

CRYPTO_MIN_VOLUME_USDT = 5_000_000   # Minimum günlük hacim (5M USDT)
                                      # Düşürürsen daha fazla coin taranır ama gürültü artar

# CRYPTO_SCAN_ALL = False ise bu liste kullanılır
CRYPTO_WHITELIST = [
    "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT",
    "ADAUSDT", "AVAXUSDT", "DOGEUSDT", "MATICUSDT", "LINKUSDT",
    "DOTUSDT", "LTCUSDT", "UNIUSDT", "ATOMUSDT", "NEARUSDT",
]

# ─────────────────────────────────────────────
# FOREX & EMTİA SEMBOLLERİ
# ─────────────────────────────────────────────
FOREX_SYMBOLS = [
    # Ana Döviz Çiftleri
    "EURUSD=X",     # Euro / Dolar
    "GBPUSD=X",     # Sterlin / Dolar
    "USDJPY=X",     # Dolar / Japon Yeni
    "USDCHF=X",     # Dolar / İsviçre Frangı
    "AUDUSD=X",     # Avustralya Doları / Dolar
    "USDCAD=X",     # Dolar / Kanada Doları
    "NZDUSD=X",     # Yeni Zelanda Doları / Dolar

    # Türk Lirası Çiftleri
    "USDTRY=X",     # Dolar / TL
    "EURTRY=X",     # Euro / TL

    # Çapraz Kurlar
    "EURGBP=X",
    "EURJPY=X",
    "GBPJPY=X",
    "AUDNZD=X",

    # Emtialar
    "GC=F",         # Altın (Gold Futures)
    "SI=F",         # Gümüş (Silver Futures)
    "CL=F",         # Ham Petrol WTI
    "BZ=F",         # Ham Petrol Brent
    "NG=F",         # Doğalgaz
    "HG=F",         # Bakır
    "ZW=F",         # Buğday
]

# ─────────────────────────────────────────────
# BİST HİSSELERİ
# ─────────────────────────────────────────────
BIST_SYMBOLS = [
    # BIST 30 Hisseleri
    "AKBNK.IS",  # Akbank
    "ARCLK.IS",  # Arçelik
    "ASELS.IS",  # Aselsan
    "BIMAS.IS",  # BİM
    "DOHOL.IS",  # Doğan Holding
    "EKGYO.IS",  # Emlak GYO
    "ENKAI.IS",  # Enka İnşaat
    "EREGL.IS",  # Ereğli Demir Çelik
    "FROTO.IS",  # Ford Otosan
    "GARAN.IS",  # Garanti Bankası
    "GUBRF.IS",  # Gübre Fabrikaları
    "HALKB.IS",  # Halk Bankası
    "ISCTR.IS",  # İş Bankası
    "KCHOL.IS",  # Koç Holding
    "KOZAL.IS",  # Koza Altın
    "KRDMD.IS",  # Kardemir
    "MGROS.IS",  # Migros
    "OYAKC.IS",  # Oyak Çimento
    "PETKM.IS",  # Petkim
    "PGSUS.IS",  # Pegasus
    "SAHOL.IS",  # Sabancı Holding
    "SASA.IS",   # SASA Polyester
    "SISE.IS",   # Şişecam
    "TAVHL.IS",  # TAV Havalimanları
    "TCELL.IS",  # Turkcell
    "THYAO.IS",  # Türk Hava Yolları
    "TKFEN.IS",  # Tekfen Holding
    "TOASO.IS",  # Tofaş
    "TTKOM.IS",  # Türk Telekom
    "TUPRS.IS",  # Tüpraş
    "VAKBN.IS",  # Vakıfbank
    "YKBNK.IS",  # Yapı Kredi

    # Popüler BIST 50 Hisseleri
    "AEFES.IS",  # Anadolu Efes
    "AGHOL.IS",  # AG Anadolu Grubu
    "ALARK.IS",  # Alarko Holding
    "ALFAS.IS",  # Alfa Solar
    "ALKIM.IS",  # Alkim Kimya
    "BERA.IS",   # Bera Holding
    "BRSAN.IS",  # Borçelik
    "CIMSA.IS",  # Çimsa
    "CLEBI.IS",  # Çelebi Holding
    "CONSE.IS",  # Consus Energy
    "EGEEN.IS",  # Ege Endüstri
    "EUPWR.IS",  # Europower
    "GESAN.IS",  # Gestamp Sinter
    "GLYHO.IS",  # Global Yatırım Holding
    "GOLTS.IS",  # Göltaş Çimento
    "IHLGM.IS",  # İhlas Gazetecilik
    "INDES.IS",  # İndeks Bilgisayar
    "IPEKE.IS",  # İpek Enerji
    "KARTN.IS",  # Kartonsan
    "KLNMA.IS",  # Kalkınma Yatırım Bankası
    "LOGO.IS",   # Logo Yazılım
    "MAVI.IS",   # Mavi Giyim
    "NETAS.IS",  # Netaş Telekom
    "NTHOL.IS",  # Net Holding
    "ODAS.IS",   # Odaş Elektrik
    "OTKAR.IS",  # Otokar
    "PARSN.IS",  # Parsan
    "QUAGR.IS",  # Quant Agri
    "REEDR.IS",  # Reeder
    "RNSHO.IS",  # Rönesans Holding
    "SELEC.IS",  # Selçuk Ecza
    "SKBNK.IS",  # Şekerbank
    "SMART.IS",  # Smart Güneş
    "SOKM.IS",   # Şok Marketler
    "SUMAS.IS",  # Sümaş
    "SURGY.IS",  # Sur Yapı
    "TRGYO.IS",  # Torunlar GYO
    "TTRAK.IS",  # Türk Traktör
    "ULKER.IS",  # Ülker
    "VESTL.IS",  # Vestel
    "ZOREN.IS",  # Zorlu Enerji
]

# ─────────────────────────────────────────────
# BOT ÇALIŞMA AYARLARI
# ─────────────────────────────────────────────
CHECK_INTERVAL_MINUTES = 15    # Kaç dakikada bir tarasın (15 önerilir)
SIGNAL_COOLDOWN_HOURS  = 4     # Aynı sembol için tekrar sinyal bekle (saat)
                                # 4 = 4 saat içinde aynı sembolden sinyal gelmez

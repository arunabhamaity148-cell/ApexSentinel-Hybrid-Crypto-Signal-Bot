# ApexSentinel Hybrid Crypto Signal Bot

**একটি প্রিমিয়াম কোয়ালিটির Signal-Only Crypto Trading Bot**

### এই বটের কাজ কী?

এই বট **কোনো অটো ট্রেড করে না**।  
শুধুমাত্র **উচ্চমানের ট্রেডিং সিগন্যাল** তৈরি করে **Telegram**-এ পাঠায়।  
আপনি নিজে ম্যানুয়ালি ট্রেড করবেন।

**মূল উদ্দেশ্য:**
- Overfitting এড়িয়ে **বাস্তবসম্মত এবং শক্তিশালী** সিগন্যাল দেওয়া
- False signal কমানো
- Late entry এড়ানো
- Realistic Risk-Reward (RR) বজায় রাখা
- Institutional level risk management প্রয়োগ করা
- সবকিছু measurable ও track করা

### বট কীভাবে কাজ করে? (Step by Step)

1. **Data Layer** → Binance থেকে 4H, 1H, 15M এর ক্যান্ডেল ডেটা নেয় (WebSocket + REST fallback)
2. **Strategy Layer**:
   - Market Regime চেক করে (Trend / Range / Volatility)
   - Higher Timeframe Bias নির্ধারণ করে (BOS / CHoCH swing structure দিয়ে)
   - Liquidity Sweep + Volume Spike খুঁজে বের করে
3. **Filters Layer** → সর্বোচ্চ ৭টি কঠিন ফিল্টার প্রয়োগ করে (quality নিশ্চিত করতে)
4. **Risk Layer** → Daily/Weekly loss limit, cooldown, max concurrent, kill switch ইত্যাদি চেক করে
5. **Notification** → পাস হলে Telegram-এ পরিষ্কার সিগন্যাল পাঠায় (Entry, SL, TP1, TP2, RR, Reason)
6. **Tracking** → প্রতিটি সিগন্যাল SQLite ডাটাবেসে সংরক্ষণ করে, পরে metrics (win rate, expectancy) দেখা যায়

### ফোল্ডার ও ফাইলসমূহের বিস্তারিত বর্ণনা

| ফোল্ডার / ফাইল                  | কাজ কী? |
|-------------------------------|--------|
| `main.py`                     | বটের মূল অর্কেস্ট্রেটর, scheduler, FastAPI health endpoint |
| `config.py`                   | সব সেটিংস (Pydantic দিয়ে type-safe) |
| `data/`                       | Binance ডেটা নেওয়া, ক্যাশিং, retry logic |
| `strategy/`                   | Regime, Pair selection, Signal generation, Target calculation |
| `filters/`                    | Max 7 hard filters + session filter |
| `risk/`                       | Risk management (loss limit, cooldown, kill switch) |
| `tracking/`                   | Journal (SQLite) + Performance metrics |
| `notification/`               | Telegram signal + admin commands (/status, /pause, /outcome ইত্যাদি) |
| `backtest/`                   | Backtest engine (live এর সাথে একই logic) |
| `tests/`                      | Smoke tests |
| `logs/`                       | Structured logging |

### কীভাবে চালাবেন?

1. `pip install -r requirements.txt`
2. `.env.example` কপি করে `.env` বানিয়ে Telegram Token, Chat ID, Admin ID দিন
3. `mkdir -p data logs`
4. `python main.py` চালান
5. Telegram channel-এ সিগন্যাল আসা শুরু হবে

### গুরুত্বপূর্ণ সতর্কতা

- **Safe Mode** ডিফল্টভাবে **ON** থাকে
- প্রথমে **Paper Trading** / Forward Test করুন (কমপক্ষে ৩-৪ সপ্তাহ)
- Journal.db ফাইল থেকে win rate, expectancy, drawdown দেখুন
- কোনো পরামিতি পরিবর্তন করার আগে যথেষ্ট ডেটা সংগ্রহ করুন (overfitting এড়াতে)

### Telegram Commands (শুধু Admin)

- `/status` → বটের বর্তমান অবস্থা
- `/pause` → Kill switch চালু
- `/resume` → Kill switch বন্ধ
- `/outcome BTCUSDT WIN 2.5` → ট্রেডের ফলাফল রেকর্ড
- `/summary` → দৈনিক সারাংশ

---

**বট তৈরির উদ্দেশ্য:**  
Retail hype-এর বাইরে একটি **clean, trustworthy, measurable** signal bot তৈরি করা, যা আপনি নিজে বুঝে ব্যবহার করতে পারবেন এবং ধীরে ধীরে improve করতে পারবেন।

**Less but Better.**

---

**সব `__init__.py` এবং বাংলা README.md** দেওয়া হয়েছে।

এখন আপনি পুরো প্রজেক্ট সেটআপ করে চালাতে পারবেন।

কোনো ফাইল আপডেট বা bug fix লাগলে বলুন।  
শুভ ট্রেডিং!
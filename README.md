# 🎯 JobHunter AI

**JobHunter AI** is an intelligent, automated job aggregator, eligibility checker, and Telegram bot assistant designed to help developers and tech professionals discover, filter, and track high-relevance job opportunities.

---

## 📁 Project Structure

```text
jobhunter-ai/
│
├── app/
│   ├── main.py              # Application bootstrap & bot runner
│   ├── config.py            # Environment & app configuration (Pydantic Settings)
│   │
│   ├── bot/
│   │   ├── handlers.py      # Aiogram message & callback query handlers
│   │   └── keyboards.py     # Interactive inline keyboards & navigation
│   │
│   ├── jobs/
│   │   ├── collector.py     # Multi-source async scrapers & API aggregators
│   │   ├── validator.py     # HTML cleaning, URL check & deduplication
│   │   ├── eligibility.py   # Rule-based candidate eligibility checking
│   │   └── matcher.py       # Profile & skill matching engine (0–100% score)
│   │
│   ├── database/
│   │   ├── models.py        # SQLAlchemy Async Models (User, Job, JobMatch)
│   │   └── database.py      # Async database engine & repository operations
│   │
│   └── scheduler/
│       └── daily_jobs.py    # APScheduler daily digest & periodic scrapers
│
├── .env.example             # Template for environment variables
├── .env                     # Local configuration
├── requirements.txt         # Project dependencies
└── README.md                # Documentation
```

---

## ✨ Features

- **Multi-Source Job Aggregation**: Asynchronously aggregates job listings from **RemoteOK**, **Arbeitnow**, **WeWorkRemotely RSS**, and direct tech feeds.
- **Deduplication & Sanitization**: Strips HTML, validates application URLs, and hashes unique title/company fingerprints to prevent duplicate listings.
- **Smart Profile Matching**: Computes a compatibility score (0–100%) by analyzing skill overlap, role relevance, and remote/location compatibility with transparent match explanations.
- **Interactive Telegram Bot**:
  - `/start` — Onboarding dashboard & interactive menu
  - `/jobs` — Browse card-by-card with compatibility scores & apply links
  - `/profile` — View and edit skills, experience, and search preferences
  - `/setskills <skills>` — Update your active tech stack
  - `/setroles <roles>` — Set your target job roles
  - `/setexp <years>` — Specify years of experience
  - `/digest` — Send an instant personalized job digest
- **Automated Daily Digest**: Scheduled daily delivery of high-compatibility job matches directly to subscribers.

---

## 🚀 Deployment Guide

### Option 1: Render.com (100% Free 24/7 Cloud Worker)

1. Push this repository to **GitHub**.
2. Go to [Render.com](https://render.com/) and click **New +** -> **Blueprint** or **Background Worker**.
3. Select your GitHub repository (`jobhunter`).
4. Set the following environment variables:
   - `BOT_TOKEN`: `8943083272:AAHr8eRczMwlh9AkDGQc7Vbzb6zJbsgSeRU`
   - `DATABASE_URL`: `sqlite+aiosqlite:///jobhunter.db`
   - `TIMEZONE`: `Asia/Kolkata`
   - `DAILY_DIGEST_TIME`: `09:00`
5. Click **Deploy**. Render will install requirements and run `python -m app.main` automatically 24/7.

---

### Option 2: Railway.app (One-Click Deploy)

1. Go to [Railway.app](https://railway.app/) and click **New Project** -> **Deploy from GitHub repo**.
2. Select your repository.
3. In **Variables**, add:
   - `BOT_TOKEN`: `8943083272:AAHr8eRczMwlh9AkDGQc7Vbzb6zJbsgSeRU`
   - `DATABASE_URL`: `sqlite+aiosqlite:///jobhunter.db`
4. Click **Deploy**. Railway will build and run the background bot process.

---

### Option 3: Docker & Docker Compose

Run anywhere Docker is installed:

```bash
# Build and run in the background
docker-compose up -d --build

# View real-time logs
docker-compose logs -f

# Stop the bot
docker-compose down
```

---

### Option 4: Linux VPS / Cloud Server (systemd)

1. SSH into your VPS (Ubuntu/Debian):
```bash
sudo git clone https://github.com/your-username/jobhunter.git /opt/jobhunter
cd /opt/jobhunter
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # configure your BOT_TOKEN
```

2. Create a systemd service:
```bash
sudo nano /etc/systemd/system/jobhunter.service
```

Paste:
```ini
[Unit]
Description=JobHunter AI Telegram Bot
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/jobhunter
ExecStart=/opt/jobhunter/venv/bin/python -m app.main
Restart=always
RestartSec=10
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
```

3. Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable jobhunter
sudo systemctl start jobhunter
sudo systemctl status jobhunter
```

---

### Option 5: 24/7 PM2 Process Manager (Local or Server)

If you have Node.js/PM2 installed:
```bash
npm install -g pm2
pm2 start ecosystem.config.js
pm2 save
pm2 startup
```

To manage:
```bash
pm2 logs jobhunter-bot
pm2 restart jobhunter-bot
pm2 stop jobhunter-bot
```

---

## 🛠️ Local Development

```bash
# Clone and install dependencies
git clone https://github.com/your-username/jobhunter.git
cd jobhunter
pip install -r requirements.txt

# Run the bot
python -m app.main
```

---

## 🤖 Telegram Bot Commands

| Command | Description |
| :--- | :--- |
| `/start` | Launch the bot, create profile, and open dashboard |
| `/jobs` | View top matching jobs ranked by compatibility score |
| `/profile` | Check your current profile, skills, and alert status |
| `/setskills python, fastapi, react` | Set your tech stack skills |
| `/setroles backend developer, data engineer` | Set your preferred job titles |
| `/setexp 3` | Update years of experience |
| `/digest` | Trigger an instant digest message |
| `/subscribe` / `/unsubscribe` | Toggle daily job notifications |
| `/help` | Display help guide |

---

## 🛠️ Architecture & Extensibility

- **Adding New Job Sources**: Add an async collector method in `app/jobs/collector.py` and register it in `JobCollector.collect_and_store_jobs()`.
- **LLM-Enhanced Semantic Matching**: Connect your OpenAI or Gemini API key in `app/jobs/matcher.py` to generate deep CV-to-Job cover letter hints and nuanced qualification scoring.
- **Database Backend**: Switch from default SQLite to PostgreSQL by simply updating `DATABASE_URL` in `.env` (e.g. `postgresql+asyncpg://user:password@localhost:5432/jobhunter`).

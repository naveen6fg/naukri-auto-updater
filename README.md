# Naukri Auto-Updater — GitHub Actions Edition 🚀

Runs **twice daily (10 AM & 9 PM IST)** on GitHub's free cloud runners.
No server. No laptop needed. Completely free.

---

## How It Works

```
GitHub Actions (Ubuntu runner)
  └── Installs Chrome + Python
  └── Runs naukri_updater.py
        └── Logs in to Naukri
        └── Opens Personal Details → edits First Name (toggle space)
        └── Saves → profile timestamp refreshed
  └── Commits toggle_state.txt back to repo (persists state)
```

---

## One-Time Setup (10 minutes)

### Step 1 — Create a GitHub Repository

1. Go to https://github.com/new
2. Name it: `naukri-auto-updater` (keep it **Private** ✅)
3. Don't initialize with README
4. Click **Create repository**

---

### Step 2 — Push this code to GitHub

Open Command Prompt / Git Bash in this folder and run:

```bash
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/naukri-auto-updater.git
git push -u origin main
```

Replace `YOUR_USERNAME` with your GitHub username.

---

### Step 3 — Add your credentials as GitHub Secrets

> ⚠️ Never put your password in code. GitHub Secrets encrypts them safely.

1. Go to your repo on GitHub
2. Click **Settings** tab
3. Left sidebar → **Secrets and variables** → **Actions**
4. Click **"New repository secret"** and add these two:

| Secret Name       | Value                        |
|-------------------|------------------------------|
| `NAUKRI_EMAIL`    | your Naukri login email      |
| `NAUKRI_PASSWORD` | your Naukri password         |

---

### Step 4 — Enable GitHub Actions

1. Click the **Actions** tab in your repo
2. If prompted, click **"I understand my workflows, go ahead and enable them"**

---

### Step 5 — Test it manually

1. Go to **Actions** tab
2. Click **"Naukri Profile Auto-Updater"** in the left list
3. Click **"Run workflow"** → **"Run workflow"** button
4. Watch the logs in real time ✅

---

## Schedule

| Run         | IST       | UTC (cron) |
|-------------|-----------|------------|
| Morning     | 10:00 AM  | `30 4 * * *` |
| Night       |  9:00 PM  | `30 15 * * *` |

> GitHub Actions cron uses UTC. IST = UTC + 5:30, so 10 AM IST = 4:30 AM UTC.

> **Note:** GitHub may delay scheduled runs by up to 10–15 minutes during high load. This is normal.

---

## Monitoring

- Go to **Actions** tab anytime to see run history
- Green ✅ = success, Red ❌ = failed
- If it fails, a `login_failed.png` screenshot is uploaded as an artifact for debugging
- You'll get an email from GitHub automatically if a run fails

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `Login failed` | Re-check secrets — NAUKRI_EMAIL / NAUKRI_PASSWORD |
| Workflow not running on schedule | GitHub delays free-tier cron by up to 15 min; also check Actions is enabled |
| `Name field not found` | Naukri changed their UI — open an issue or re-run manually to check logs |
| Toggle state not saving | Ensure repo has `contents: write` permission (already set in workflow) |

---

## File Structure

```
naukri-auto-updater/
├── .github/
│   └── workflows/
│       └── naukri_update.yml   ← GitHub Actions schedule + steps
├── naukri_updater.py           ← Main script
├── requirements.txt            ← Python dependencies
├── toggle_state.txt            ← Persists add/remove space state across runs
└── .gitignore
```

---

## Security

- Credentials stored as **encrypted GitHub Secrets** — never in code
- Repo is **private** — only you can see it
- `toggle_state.txt` contains only `0` or `1` — no sensitive data

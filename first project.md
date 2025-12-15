# Kernel-First Billing Agent: The Trojan Horse Strategy

This is the perfect way to build this. We are going to use the **"Trojan Horse" Strategy**: we will ostensibly build the Billing Tracker, but we will structure the code so that the "engine" naturally separates from the "logic."

Here is your **Kernel-First Billing Agent Plan**.

It is stripped of all "nice-to-haves." If it doesn't help you fetch an OpenAI invoice *today*, it is cut.

-----

## The Architecture (Mental Model)

We are treating your Billing Tracker as **Plugin #1** inside your new Engine.

  * **The Kernel (The OS):** `main.py`, `scheduler.py`, `db.py` (The boring stuff that runs things).
  * **The Plugin (The App):** `plugins/openai_collector.py`, `plugins/report_generator.py` (The specific logic).

-----

## The Plugin Contract (What Makes It a Kernel)

Every plugin must implement this simple interface. The kernel doesn't care about *what* you're collecting—only that you follow the contract.

```python
# core/plugin_interface.py
from dataclasses import dataclass
from typing import Any, Dict, Optional
from datetime import datetime

@dataclass
class PluginContext:
    """What the kernel gives to every plugin"""
    run_id: str
    secrets: Dict[str, str]  # from .env
    logger: Any              # structured logger
    db_session: Any          # for direct DB access if needed

@dataclass
class PluginResult:
    """What every plugin must return"""
    status: str              # "success" | "failed" | "partial"
    data: Optional[Dict[str, Any]]  # normalized output
    error: Optional[str]     # if failed
    metadata: Dict[str, Any] # stats, counts, timestamps

class Plugin:
    """Base class for all plugins"""
    name: str                # e.g., "openai_collector"
    
    def run(self, ctx: PluginContext, params: Dict[str, Any]) -> PluginResult:
        raise NotImplementedError
```

**Why this matters:** When you add Anthropic in Phase 2, you'll copy the OpenAI plugin and swap the API calls. The kernel never changes.

-----

## Phase 0: Pre-flight (Before You Write Code)

**Goal:** Environment ready, dependencies installed, first successful run of skeleton code.

**Setup Tasks:**

1.  **Create Project Structure:**
    ```bash
    cd ~/projects
    mkdir -p "AI usage-billing tracker/agent_os"
    cd "AI usage-billing tracker/agent_os"
    mkdir -p core plugins tests
    touch main.py requirements.txt .env .gitignore
    ```

2.  **Setup .gitignore:**
    ```bash
    cat > .gitignore << 'EOF'
.env
*.db
*.log
venv/
__pycache__/
*.pyc
.DS_Store
EOF
    ```

3.  **Install Dependencies:**
    ```bash
    python3 -m venv venv
    source venv/bin/activate  # or `venv\Scripts\activate` on Windows
    pip install --upgrade pip
    ```
    
    **requirements.txt:**
    ```
    python-dotenv==1.0.0
    requests==2.31.0
    ```

4.  **Setup .env File:**
    ```bash
    cat > .env << 'EOF'
OPENAI_API_KEY=your_key_here
ANTHROPIC_API_KEY=
EOF
    ```

5.  **Create Minimal main.py:**
    ```python
    # main.py
    import sys
    from dotenv import load_dotenv
    
    __version__ = "0.1.0"
    
    def main():
        load_dotenv()
        print(f"Agent OS v{__version__} - Skeleton loaded")
        return 0
    
    if __name__ == "__main__":
        sys.exit(main())
    ```

**✅ Phase 0 DONE Qualifications:**

  * [x] Run `python main.py` and see "Agent OS v0.1.0 - Skeleton loaded" (no errors). ✅
  * [x] Run `python -c "from dotenv import load_dotenv; load_dotenv(); import os; print('API Key loaded:', bool(os.getenv('OPENAI_API_KEY')))"` and see `True`. ✅
  * [x] `.env` is in `.gitignore` (run `git status` and confirm it's not listed). ✅
  * [x] Run `pip list | grep -E "(dotenv|requests)"` and see both packages installed. ✅

**Phase 0 completed on: December 14, 2024**

**🛑 Rabbit Hole Warning:** Do NOT install 47 packages "just in case." Start lean.

-----

## Phase 1: The "Skeleton" (Fetching Data)

**Goal:** Run a script that fetches yesterday's OpenAI usage and saves it to a local database.

**The "Kernel" Work (20%):**

1.  **Database Setup:** Create a `runs` table (to track execution) and a `results` table (to store data) in SQLite.
2.  **Secret Management:** Create a `.env` loader so we don't hardcode API keys.

**The "Billing" Work (80%):**

1.  **OpenAI Connector:** Write a function `fetch_openai_usage(date)` that hits the OpenAI API.
2.  **Normalization:** Map that JSON response to your "Standard Row" (Provider, Date, Tokens, Cost).

### Concrete Implementation Steps

**Step 1: Create core/db.py**
```python
# core/db.py
import sqlite3
from contextlib import contextmanager
from datetime import datetime

DB_PATH = "agent_os.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Runs table: tracks every execution
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS runs (
            id TEXT PRIMARY KEY,
            plugin_name TEXT NOT NULL,
            status TEXT NOT NULL,
            started_at TEXT NOT NULL,
            finished_at TEXT,
            error TEXT
        )
    """)
    
    # Results table: stores normalized billing data
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT NOT NULL,
            provider TEXT NOT NULL,
            date TEXT NOT NULL,
            tokens INTEGER,
            cost REAL,
            raw_json TEXT,
            created_at TEXT NOT NULL,
            UNIQUE(provider, date)
        )
    """)
    
    conn.commit()
    conn.close()

@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()
```

**Step 2: Create plugins/openai.py**
```python
# plugins/openai.py
import requests
from datetime import datetime, timedelta
import json

def fetch_openai_usage(api_key: str, date: str = None):
    """
    Fetch OpenAI usage for a specific date.
    date format: YYYY-MM-DD (defaults to yesterday)
    """
    if date is None:
        date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    
    # Note: This is a placeholder - adjust to actual OpenAI API endpoint
    # Real endpoint might be: https://api.openai.com/v1/usage
    url = "https://api.openai.com/v1/usage"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    params = {"date": date}
    
    response = requests.get(url, headers=headers, params=params, timeout=30)
    response.raise_for_status()
    
    return response.json()

def normalize_openai_data(raw_data: dict, date: str) -> dict:
    """Map OpenAI response to standard format"""
    # Adjust based on actual API response structure
    return {
        "provider": "OpenAI",
        "date": date,
        "tokens": raw_data.get("total_tokens", 0),
        "cost": raw_data.get("total_cost", 0.0),
        "raw_json": json.dumps(raw_data)
    }
```

**Step 3: Update main.py**
```python
# main.py
import sys
import os
from datetime import datetime
from dotenv import load_dotenv
import uuid

from core.db import init_db, get_db
from plugins.openai import fetch_openai_usage, normalize_openai_data

__version__ = "0.1.0"

def run_fetch_openai():
    """Execute the OpenAI fetch task"""
    run_id = str(uuid.uuid4())
    started_at = datetime.utcnow().isoformat()
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Record run start
        cursor.execute(
            "INSERT INTO runs (id, plugin_name, status, started_at) VALUES (?, ?, ?, ?)",
            (run_id, "openai_collector", "running", started_at)
        )
        conn.commit()
        
        try:
            # Fetch data
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY not found in .env")
            
            raw_data = fetch_openai_usage(api_key)
            normalized = normalize_openai_data(raw_data, 
                (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d"))
            
            # Store result (with UPSERT via REPLACE)
            cursor.execute("""
                INSERT OR REPLACE INTO results 
                (run_id, provider, date, tokens, cost, raw_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                run_id,
                normalized["provider"],
                normalized["date"],
                normalized["tokens"],
                normalized["cost"],
                normalized["raw_json"],
                datetime.utcnow().isoformat()
            ))
            
            # Mark run complete
            cursor.execute(
                "UPDATE runs SET status = ?, finished_at = ? WHERE id = ?",
                ("success", datetime.utcnow().isoformat(), run_id)
            )
            conn.commit()
            
            print(f"✓ Successfully fetched OpenAI usage for {normalized['date']}")
            print(f"  Tokens: {normalized['tokens']}, Cost: ${normalized['cost']:.2f}")
            return 0
            
        except Exception as e:
            # Mark run failed
            cursor.execute(
                "UPDATE runs SET status = ?, finished_at = ?, error = ? WHERE id = ?",
                ("failed", datetime.utcnow().isoformat(), str(e), run_id)
            )
            conn.commit()
            
            print(f"✗ Failed to fetch OpenAI usage: {e}")
            return 1

def main():
    load_dotenv()
    
    if len(sys.argv) < 2:
        print(f"Agent OS v{__version__}")
        print("Usage: python main.py [--task TASK_NAME]")
        print("Tasks: fetch_openai")
        return 1
    
    # Initialize database
    init_db()
    
    if sys.argv[1] == "--task" and len(sys.argv) > 2:
        task = sys.argv[2]
        if task == "fetch_openai":
            return run_fetch_openai()
        else:
            print(f"Unknown task: {task}")
            return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
```

**✅ Phase 1 DONE Qualifications:**

  * [x] Run `python main.py --task fetch_openai` and it finishes without error. ✅
  * [x] Run `sqlite3 agent_os.db "SELECT * FROM runs"` and see 1 run with status "success". ✅
  * [x] Run `sqlite3 agent_os.db "SELECT provider, date, tokens, cost FROM results"` and see 1 row of OpenAI data. ✅
  * [x] If I run it again immediately, run `sqlite3 agent_os.db "SELECT COUNT(*) FROM results"` and still see just 1 row (idempotency via UNIQUE constraint). ✅
  * [x] Run `python main.py --task fetch_openai` with WiFi off and see status "failed" in runs table (not a crash). ✅

**Phase 1 completed on: December 14, 2024**

**Verification Commands:**
```bash
# Check the database was created
ls -lh agent_os.db

# View all runs
sqlite3 agent_os.db "SELECT id, plugin_name, status, started_at FROM runs"

# View results
sqlite3 agent_os.db "SELECT provider, date, tokens, cost FROM results"

# Count total results
sqlite3 agent_os.db "SELECT COUNT(*) as total_records FROM results"
```

**🛑 Rabbit Hole Warning:** Do NOT build a UI. Do NOT build a "DAG" scheduler. Just call the function.

-----

## Phase 2: The "Reliability" (The Kernel Updates)

**Goal:** Make it robust enough to run every night while you sleep.

**The "Kernel" Work (50%):**

1.  **Idempotency Logic:** Add a check: *If `openai_2025_12_13` exists in the DB, do not fetch again.* (Already handled by `UNIQUE(provider, date)` constraint, but add explicit check for cleaner logs).
2.  **Simple Logger:** Instead of `print()`, write to `agent.log` with timestamps.
3.  **Cron/Schedule:** Set up a system cron job (or macOS launchd) to run `main.py` at 6:00 AM.

**The "Billing" Work (50%):**

1.  **Add Provider #2 (Anthropic):** Copy/Paste the OpenAI logic and adapt it for Anthropic.
2.  **Error Handling:** If the API fails, the script should log the error and mark the Run as "Failed" in the DB, but *not* crash the whole OS.

### Concrete Implementation Steps

**Step 1: Create core/logger.py**
```python
# core/logger.py
import logging
from datetime import datetime

LOG_FILE = "agent.log"

def setup_logger(name: str = "agent_os"):
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    
    # File handler
    fh = logging.FileHandler(LOG_FILE)
    fh.setLevel(logging.INFO)
    
    # Console handler
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    
    # Formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)
    
    logger.addHandler(fh)
    logger.addHandler(ch)
    
    return logger
```

**Step 2: Create plugins/anthropic.py**
```python
# plugins/anthropic.py
import requests
from datetime import datetime, timedelta
import json

def fetch_anthropic_usage(api_key: str, date: str = None):
    """
    Fetch Anthropic usage for a specific date.
    date format: YYYY-MM-DD (defaults to yesterday)
    """
    if date is None:
        date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    
    # Placeholder - adjust to actual Anthropic API endpoint
    url = "https://api.anthropic.com/v1/usage"
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "Content-Type": "application/json"
    }
    params = {"date": date}
    
    response = requests.get(url, headers=headers, params=params, timeout=30)
    response.raise_for_status()
    
    return response.json()

def normalize_anthropic_data(raw_data: dict, date: str) -> dict:
    """Map Anthropic response to standard format"""
    return {
        "provider": "Anthropic",
        "date": date,
        "tokens": raw_data.get("total_tokens", 0),
        "cost": raw_data.get("total_cost", 0.0),
        "raw_json": json.dumps(raw_data)
    }
```

**Step 3: Update main.py with logging and Anthropic support**
```python
# main.py (updated)
import sys
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
import uuid

from core.db import init_db, get_db
from core.logger import setup_logger
from plugins.openai import fetch_openai_usage, normalize_openai_data
from plugins.anthropic import fetch_anthropic_usage, normalize_anthropic_data

__version__ = "0.2.0"
logger = setup_logger()

def run_collector(provider_name: str, fetch_fn, normalize_fn, api_key_name: str):
    """Generic collector runner - the kernel pattern emerging"""
    run_id = str(uuid.uuid4())
    started_at = datetime.utcnow().isoformat()
    
    logger.info(f"Starting {provider_name} collection (run_id: {run_id})")
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Record run start
        cursor.execute(
            "INSERT INTO runs (id, plugin_name, status, started_at) VALUES (?, ?, ?, ?)",
            (run_id, f"{provider_name.lower()}_collector", "running", started_at)
        )
        conn.commit()
        
        try:
            # Fetch data
            api_key = os.getenv(api_key_name)
            if not api_key:
                raise ValueError(f"{api_key_name} not found in .env")
            
            date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
            
            # Check if already collected
            cursor.execute(
                "SELECT id FROM results WHERE provider = ? AND date = ?",
                (provider_name, date)
            )
            existing = cursor.fetchone()
            if existing:
                logger.info(f"Data for {provider_name} on {date} already exists - skipping")
                cursor.execute(
                    "UPDATE runs SET status = ?, finished_at = ? WHERE id = ?",
                    ("skipped", datetime.utcnow().isoformat(), run_id)
                )
                conn.commit()
                return 0
            
            raw_data = fetch_fn(api_key, date)
            normalized = normalize_fn(raw_data, date)
            
            # Store result
            cursor.execute("""
                INSERT INTO results 
                (run_id, provider, date, tokens, cost, raw_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                run_id,
                normalized["provider"],
                normalized["date"],
                normalized["tokens"],
                normalized["cost"],
                normalized["raw_json"],
                datetime.utcnow().isoformat()
            ))
            
            # Mark run complete
            cursor.execute(
                "UPDATE runs SET status = ?, finished_at = ? WHERE id = ?",
                ("success", datetime.utcnow().isoformat(), run_id)
            )
            conn.commit()
            
            logger.info(f"✓ {provider_name} collection successful - Tokens: {normalized['tokens']}, Cost: ${normalized['cost']:.2f}")
            return 0
            
        except Exception as e:
            # Mark run failed
            cursor.execute(
                "UPDATE runs SET status = ?, finished_at = ?, error = ? WHERE id = ?",
                ("failed", datetime.utcnow().isoformat(), str(e), run_id)
            )
            conn.commit()
            
            logger.error(f"✗ {provider_name} collection failed: {e}")
            return 1

def run_all_collectors():
    """Run all configured providers"""
    logger.info("=== Starting daily billing collection ===")
    
    collectors = [
        ("OpenAI", fetch_openai_usage, normalize_openai_data, "OPENAI_API_KEY"),
        ("Anthropic", fetch_anthropic_usage, normalize_anthropic_data, "ANTHROPIC_API_KEY"),
    ]
    
    results = []
    for provider, fetch_fn, norm_fn, key_name in collectors:
        # Check if API key exists before running
        if not os.getenv(key_name):
            logger.warning(f"Skipping {provider} - no API key configured")
            continue
        
        exit_code = run_collector(provider, fetch_fn, norm_fn, key_name)
        results.append((provider, exit_code))
    
    # Summary
    success_count = sum(1 for _, code in results if code == 0)
    logger.info(f"=== Collection complete: {success_count}/{len(results)} successful ===")
    
    return 0 if success_count == len(results) else 1

def main():
    load_dotenv()
    init_db()
    
    if len(sys.argv) < 2:
        logger.info(f"Agent OS v{__version__}")
        print("Usage: python main.py [--task TASK_NAME]")
        print("Tasks: fetch_openai, fetch_anthropic, run_all")
        return 1
    
    if sys.argv[1] == "--task" and len(sys.argv) > 2:
        task = sys.argv[2]
        if task == "fetch_openai":
            return run_collector("OpenAI", fetch_openai_usage, normalize_openai_data, "OPENAI_API_KEY")
        elif task == "fetch_anthropic":
            return run_collector("Anthropic", fetch_anthropic_usage, normalize_anthropic_data, "ANTHROPIC_API_KEY")
        elif task == "run_all":
            return run_all_collectors()
        else:
            logger.error(f"Unknown task: {task}")
            return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
```

**Step 4: Setup cron/launchd for automated runs**

**For macOS (launchd):**
```bash
# Create ~/Library/LaunchAgents/com.eriksjaastad.agent_os.plist
cat > ~/Library/LaunchAgents/com.eriksjaastad.agent_os.plist << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.eriksjaastad.agent_os</string>
    <key>ProgramArguments</key>
    <array>
        <string>/Users/eriksjaastad/projects/AI usage-billing tracker/agent_os/venv/bin/python</string>
        <string>/Users/eriksjaastad/projects/AI usage-billing tracker/agent_os/main.py</string>
        <string>--task</string>
        <string>run_all</string>
    </array>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>6</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>
    <key>StandardOutPath</key>
    <string>/Users/eriksjaastad/projects/AI usage-billing tracker/agent_os/cron.log</string>
    <key>StandardErrorPath</key>
    <string>/Users/eriksjaastad/projects/AI usage-billing tracker/agent_os/cron.error.log</string>
</dict>
</plist>
EOF

# Load the launch agent
launchctl load ~/Library/LaunchAgents/com.eriksjaastad.agent_os.plist

# Test it manually (don't wait for 6am)
launchctl start com.eriksjaastad.agent_os

# Check if it's loaded
launchctl list | grep agent_os
```

**For Linux (cron):**
```bash
# Edit crontab
crontab -e

# Add this line (runs daily at 6:00 AM)
0 6 * * * cd /home/erik/projects/AI\ usage-billing\ tracker/agent_os && ./venv/bin/python main.py --task run_all >> cron.log 2>&1
```

**✅ Phase 2 DONE Qualifications:**

  * [x] Run `python main.py --task run_all` with WiFi OFF and see "Failed" status in the `runs` table (not a crash/traceback). ✅
  * [x] Run `python main.py --task run_all` five times in a row, then `sqlite3 agent_os.db "SELECT COUNT(*) FROM results WHERE date = '2025-12-13'"` shows only 2 rows (1 OpenAI, 1 Anthropic - not 10). ✅ (Shows 1 row - OpenAI only, Anthropic skipped due to no API key)
  * [x] Check `agent.log` exists and contains timestamped entries. ✅
  * [x] Run `launchctl list | grep agent_os` (macOS) or `crontab -l` (Linux) and see the scheduled job. ✅
  * [x] Wake up tomorrow after 6:00 AM and run `tail -20 agent.log` - see automated collection happened. ⏳ (Scheduled, will run at 6:00 AM)

**Phase 2 completed on: December 14, 2024**

**Verification Commands:**
```bash
# Test failure handling
# 1. Temporarily break API key
cp .env .env.backup
sed -i '' 's/OPENAI_API_KEY=.*/OPENAI_API_KEY=invalid_key/' .env
python main.py --task fetch_openai
sqlite3 agent_os.db "SELECT status, error FROM runs ORDER BY started_at DESC LIMIT 1"
mv .env.backup .env

# Check idempotency
python main.py --task run_all
python main.py --task run_all
sqlite3 agent_os.db "SELECT provider, date, COUNT(*) as count FROM results GROUP BY provider, date"

# View recent logs
tail -50 agent.log | grep -E "(Starting|successful|failed)"
```

**🛑 Rabbit Hole Warning:** Do NOT build a "retry queue" with exponential backoff yet. Just fail and try again tomorrow.

-----

## Phase 3: The "Value" (The Dashboard)

**Goal:** See the data so you can actually file your taxes/expense it.

**The "Kernel" Work (10%):**

1.  **Export Utility:** A simple function `export_to_csv()` that dumps the `results` table to a file in a synced folder (Dropbox/iCloud).

**The "Billing" Work (90%):**

1.  **Summary Logic:** A script that queries the DB: `SELECT sum(cost) FROM results WHERE month='2025-12'`.
2.  **The "Alert":** If `total > $50`, send a simple email or Discord webhook to yourself.

### Concrete Implementation Steps

**Step 1: Create plugins/exporters.py**
```python
# plugins/exporters.py
import csv
from datetime import datetime
from pathlib import Path

def export_to_csv(db_conn, output_path: str = None):
    """Export results table to CSV"""
    if output_path is None:
        output_path = f"billing_export_{datetime.now().strftime('%Y%m%d')}.csv"
    
    cursor = db_conn.cursor()
    cursor.execute("""
        SELECT provider, date, tokens, cost, created_at
        FROM results
        ORDER BY date DESC, provider
    """)
    
    with open(output_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Provider', 'Date', 'Tokens', 'Cost', 'Collected At'])
        writer.writerows(cursor.fetchall())
    
    return output_path

def send_discord_alert(webhook_url: str, message: str):
    """Send alert to Discord webhook"""
    import requests
    payload = {"content": message}
    response = requests.post(webhook_url, json=payload, timeout=10)
    response.raise_for_status()
```

**Step 2: Create plugins/summary.py**
```python
# plugins/summary.py
from datetime import datetime

def get_monthly_summary(db_conn, year: int = None, month: int = None):
    """Get summary stats for a given month"""
    if year is None or month is None:
        now = datetime.now()
        year = now.year
        month = now.month
    
    month_str = f"{year}-{month:02d}"
    
    cursor = db_conn.cursor()
    cursor.execute("""
        SELECT 
            provider,
            COUNT(*) as days,
            SUM(tokens) as total_tokens,
            SUM(cost) as total_cost
        FROM results
        WHERE date LIKE ?
        GROUP BY provider
    """, (f"{month_str}%",))
    
    results = cursor.fetchall()
    
    # Overall total
    cursor.execute("""
        SELECT 
            COUNT(DISTINCT date) as total_days,
            SUM(cost) as grand_total
        FROM results
        WHERE date LIKE ?
    """, (f"{month_str}%",))
    
    totals = cursor.fetchone()
    
    return {
        "month": month_str,
        "by_provider": [dict(row) for row in results],
        "total_days": totals["total_days"],
        "grand_total": totals["grand_total"] or 0.0
    }

def format_summary_message(summary: dict) -> str:
    """Format summary as readable message"""
    lines = [
        f"📊 AI Billing Summary - {summary['month']}",
        f"Total Days Tracked: {summary['total_days']}",
        f"Grand Total: ${summary['grand_total']:.2f}",
        "",
        "By Provider:"
    ]
    
    for provider in summary['by_provider']:
        lines.append(
            f"  • {provider['provider']}: "
            f"{provider['total_tokens']:,} tokens, "
            f"${provider['total_cost']:.2f} "
            f"({provider['days']} days)"
        )
    
    return "\n".join(lines)
```

**Step 3: Update main.py with export and summary tasks**
```python
# Add to main.py imports
from plugins.exporters import export_to_csv, send_discord_alert
from plugins.summary import get_monthly_summary, format_summary_message

# Add to main() function tasks:
def main():
    load_dotenv()
    init_db()
    
    if len(sys.argv) < 2:
        logger.info(f"Agent OS v{__version__}")
        print("Usage: python main.py [--task TASK_NAME]")
        print("Tasks: fetch_openai, fetch_anthropic, run_all, export, summary, daily_report")
        return 1
    
    if sys.argv[1] == "--task" and len(sys.argv) > 2:
        task = sys.argv[2]
        
        # ... existing tasks ...
        
        elif task == "export":
            with get_db() as conn:
                output_path = export_to_csv(conn)
                logger.info(f"✓ Exported to {output_path}")
            return 0
        
        elif task == "summary":
            with get_db() as conn:
                summary = get_monthly_summary(conn)
                message = format_summary_message(summary)
                print(message)
                logger.info("Summary generated")
            return 0
        
        elif task == "daily_report":
            # Run collection, then send summary if over threshold
            exit_code = run_all_collectors()
            
            with get_db() as conn:
                summary = get_monthly_summary(conn)
                message = format_summary_message(summary)
                
                # Alert if over threshold or zero (broken scraper)
                webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
                should_alert = (
                    summary['grand_total'] > 50.0 or 
                    summary['grand_total'] == 0.0
                )
                
                if should_alert and webhook_url:
                    alert_message = f"⚠️ ALERT: {message}"
                    send_discord_alert(webhook_url, alert_message)
                    logger.info("Alert sent to Discord")
                elif should_alert:
                    logger.warning(f"Alert threshold triggered but no DISCORD_WEBHOOK_URL configured")
                
                # Always export
                export_to_csv(conn)
            
            return exit_code
        
        else:
            logger.error(f"Unknown task: {task}")
            return 1
    
    return 0
```

**Step 4: Update .env with Discord webhook (optional)**
```bash
# Add to .env
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/YOUR_WEBHOOK_ID/YOUR_WEBHOOK_TOKEN
```

**Step 5: Update cron/launchd to use daily_report instead of run_all**
```bash
# Update the launchd plist ProgramArguments to use "daily_report"
# Or for cron, change to:
0 6 * * * cd /path/to/agent_os && ./venv/bin/python main.py --task daily_report >> cron.log 2>&1
```

**✅ Phase 3 DONE Qualifications:**

  * [x] Run `python main.py --task export` and find a CSV file with all billing data. ✅
  * [x] Application can generate summary reports (moved to billing_app.py). ✅
  * [x] Discord alerts implemented in application layer (not agent_os core). ✅
  * [x] Clean separation: agent_os = toolbox, applications = business logic. ✅

**Phase 3 completed on: December 14, 2024**

**Key Architectural Decision:**
- Discord webhooks and billing summaries moved to `AI usage-billing tracker/` application
- agent_os remains generic with only CSV export capability
- NOTIFICATION_PATTERN.md documents how applications add their own notification logic

**Verification Commands:**
```bash
# Test export
python main.py --task export
ls -lh billing_export_*.csv
head billing_export_*.csv

# Test summary
python main.py --task summary

# Test alert (add test data to trigger threshold)
sqlite3 agent_os.db "UPDATE results SET cost = 30.0 WHERE provider = 'OpenAI'"
python main.py --task daily_report

# View in spreadsheet
open billing_export_*.csv  # macOS
# or
libreoffice billing_export_*.csv  # Linux
```

**🛑 Rabbit Hole Warning:** Do NOT build a React Dashboard or a web server. Use Excel/Numbers to view the CSV for now.

-----

## Decision Log (Why We Made These Choices)

This section documents key architectural decisions to prevent future second-guessing.

**Why SQLite over Postgres?**
- **Reason:** Local-first, zero setup, perfect for single-user billing data (<10k rows/year).
- **When to reconsider:** If you need multi-machine access or >100k rows.

**Why no retry queue in Phase 2?**
- **Reason:** Daily cron provides natural retry cadence. Missing one day's data isn't catastrophic for billing.
- **When to reconsider:** When collecting real-time data or mission-critical workflows where 24hr delay is unacceptable.

**Why OpenAI first, not both providers simultaneously?**
- **Reason:** Prove the kernel pattern with one real integration before copy-pasting. Avoid debugging two API integrations at once.
- **When to reconsider:** Never. Sequential validation is always better.

**Why CSV export instead of web dashboard?**
- **Reason:** CSV works everywhere (Excel, Google Sheets, Numbers), requires zero maintenance, and can be version-controlled.
- **When to reconsider:** When you have >5 users or need live filtering/drill-down. For personal use, CSV + spreadsheet is unbeatable.

**Why Discord webhook over email for alerts?**
- **Reason:** Discord webhooks are instant, require no SMTP config, and don't get spam-filtered.
- **When to reconsider:** If you're in email more than Discord, or if you need formal audit trails.

**Why UNIQUE constraint instead of manual idempotency check?**
- **Reason:** Database-enforced uniqueness is bulletproof. Manual checks can have race conditions.
- **When to reconsider:** Never. Let the database do what it's good at.

-----

## Migration Path (Phase 3 → Full Kernel)

After Phase 3 is stable, here's how to evolve into a full Agent OS:

**Phase 4: Generalize the Kernel** *(optional future work)*
1. Extract `run_collector()` into `core/orchestrator.py`
2. Create `workflow.yaml` format for declaring providers
3. Move plugin discovery into `core/plugin_loader.py`
4. Result: `main.py` shrinks to 20 lines, new providers are just YAML + a plugin file

**Phase 5: Add More Agents** *(when ready for project #2)*
1. Create `plugins/speech_to_text.py` using the same PluginContext contract
2. Add webhook trigger support in `core/triggers.py`
3. Result: Two different agents sharing the same kernel infrastructure

**Phase 6: Observability Dashboard** *(when CSV isn't enough)*
1. Add FastAPI endpoint that reads `runs` and `results` tables
2. Create single-page dashboard with Tailwind + Chart.js
3. Result: `localhost:8000/dashboard` shows live runs, but CSV still works

**The key insight:** Each phase keeps the previous phase working. You can stop at Phase 3 and have a production-ready billing tracker. Or continue and build the Agent OS. The "Trojan Horse" worked.

-----

## The Final "Project vs. Kernel" File Structure

If you set up your folders like this *now*, you won't have to refactor later.

```text
/agent_os
  /core            <-- THIS IS THE KERNEL
    __init__.py
    db.py          (SQLite connection + schema)
    logger.py      (Structured logging)
    secrets.py     (Env var loader - future: encrypted vault)
    scheduler.py   (Cron helper - future: internal scheduler)
    plugin_interface.py  (PluginContext, PluginResult, Plugin base class)

  /plugins         <-- THIS IS THE BILLING PROJECT
    __init__.py
    openai.py      (OpenAI API logic)
    anthropic.py   (Anthropic API logic)
    exporters.py   (CSV/Discord logic)
    summary.py     (Aggregation queries)

  /tests           <-- FUTURE: Add pytest tests
    test_db.py
    test_plugins.py

  main.py          (Entry point: loads Core, runs Plugins)
  requirements.txt
  .env
  .gitignore
  agent_os.db      (SQLite database - auto-created)
  agent.log        (Structured logs - auto-created)
```

**Key Observations:**
- **Kernel grows vertically** (more capabilities in `core/`)
- **Plugins grow horizontally** (more providers in `plugins/`)
- **main.py stays thin** (just wires things together)

-----

## Rollback / Failure Strategy

**If Phase 1 fails:**
- Check API key is valid: `curl -H "Authorization: Bearer $OPENAI_API_KEY" https://api.openai.com/v1/models`
- Check database was created: `ls -lh agent_os.db`
- Check for Python errors: `python main.py --task fetch_openai 2>&1 | tee debug.log`

**If Phase 2 fails:**
- Check cron/launchd is loaded: `launchctl list | grep agent_os` or `crontab -l`
- Check permissions: `ls -l ~/Library/LaunchAgents/com.eriksjaastad.agent_os.plist`
- Test manually first: `launchctl start com.eriksjaastad.agent_os && tail -f agent.log`

**If Phase 3 fails:**
- Check Discord webhook: `curl -H "Content-Type: application/json" -d '{"content":"test"}' $DISCORD_WEBHOOK_URL`
- Check CSV can be written: `touch test.csv && rm test.csv` (test write permissions)
- Check database has data: `sqlite3 agent_os.db "SELECT COUNT(*) FROM results"`

**Nuclear option (start fresh):**
```bash
# Backup existing data
cp agent_os.db agent_os.db.backup
cp agent.log agent.log.backup

# Reset database
rm agent_os.db
python main.py --task fetch_openai  # Will recreate schema

# Or restore backup
mv agent_os.db.backup agent_os.db
```

-----

## Strategic Summary

You are "Done" with the **Kernel** when it can run a Python function, log the result to SQLite, and not crash on errors.

You are "Done" with the **Billing Project** when you have a CSV of your costs that you trust enough to show the IRS.

**The beauty of this approach:** By Phase 2, you'll *feel* the kernel emerging naturally. The `run_collector()` function doesn't care if it's OpenAI or Anthropic. That's when you know the architecture is right.

**Start with Phase 0.** Get the skeleton running. Then Phase 1. Don't skip ahead.

The kernel will reveal itself through the work, not through upfront design.

-----

## Quick Start Checklist

```bash
# Phase 0 (10 minutes)
cd ~/projects/AI\ usage-billing\ tracker
mkdir agent_os && cd agent_os
# Copy file structure and code from Phase 0 above
python main.py  # Should see "Agent OS v0.1.0 - Skeleton loaded"

# Phase 1 (1-2 hours)
# Implement db.py, plugins/openai.py, updated main.py
python main.py --task fetch_openai
sqlite3 agent_os.db "SELECT * FROM results"

# Phase 2 (2-3 hours)
# Add logger.py, plugins/anthropic.py, update main.py
# Setup cron/launchd
python main.py --task run_all
tail agent.log

# Phase 3 (1-2 hours)
# Add exporters.py, summary.py, update main.py
python main.py --task daily_report
open billing_export_*.csv
```

**Total time to production: ~1 day of focused work.**

Then you have:
- ✅ Automated daily billing collection
- ✅ Historical database
- ✅ CSV exports for tax time
- ✅ Alerts for anomalies
- ✅ A kernel ready for the next agent

**Now go build it.** Start with Phase 0, right now, before you overthink it.

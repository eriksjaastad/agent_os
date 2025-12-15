# Agent OS

A minimal, local-first workflow engine for building automation agents. Think of it as a "Make-like runtime" that every agent/workflow can plug into.

## What is Agent OS?

Agent OS is a **pure toolbox** - it provides the infrastructure for running scheduled tasks, tracking execution history, and managing state. You build **applications** on top of it that add business logic.

**Agent OS provides:**
- ✅ Task scheduling & execution
- ✅ SQLite-based state management
- ✅ Structured logging
- ✅ Retry & error handling
- ✅ Idempotency by default
- ✅ CSV export utilities

**Agent OS does NOT provide:**
- ❌ Application-specific logic
- ❌ Notification systems (Discord, email, etc.)
- ❌ Business rules or thresholds

## Architecture

```
agent_os/                    (The Kernel - Generic)
├── core/
│   ├── db.py               # SQLite with runs/results tracking
│   ├── logger.py           # Structured logging
│   └── export.py           # Generic CSV export
├── plugins/
│   ├── openai.py           # Example: OpenAI collector
│   └── anthropic.py        # Example: Anthropic collector
└── main.py                 # Task runner

your-app/                   (Your Application - Specific)
├── plugins/
│   ├── your_logic.py       # Your business logic
│   └── your_alerts.py      # Your notifications
└── app.py                  # Uses agent_os + adds your logic
```

## Quick Start

### 1. Setup

```bash
# Clone and setup
git clone https://github.com/yourusername/agent_os.git
cd agent_os

# Create virtual environment and install dependencies
python3 -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your API keys
```

### 2. Initialize Database

```bash
python main.py --task fetch_openai
# This will create agent_os.db and run tables
```

### 3. Run Tasks

```bash
# Collect data from OpenAI
python main.py --task fetch_openai

# Collect from all providers
python main.py --task run_all

# Export to CSV
python main.py --task export
```

### 4. Schedule Daily Runs (macOS)

The included launchd plist runs daily at 6:00 AM:

```bash
# Copy to LaunchAgents (path already set up in Phase 2)
launchctl load ~/Library/LaunchAgents/com.eriksjaastad.agent_os.plist
```

For Linux, use cron:
```bash
0 6 * * * cd /path/to/agent_os && ./venv/bin/python main.py --task run_all
```

## Example Application: AI Usage Billing Tracker

See `AI usage-billing tracker/` for a complete example of building an application on agent_os:

- Uses agent_os for data collection
- Adds billing summaries (monthly cost aggregation)
- Adds Discord alerts (cost threshold notifications)
- Demonstrates clean separation of concerns

## Building Your Own Application

### Pattern

1. **Use agent_os for infrastructure** - data collection, logging, database
2. **Add your logic as plugins** - business rules, calculations, transformations
3. **Add notifications if needed** - Discord, email, Slack (see `NOTIFICATION_PATTERN.md`)

### Example Structure

```python
# your-app/app.py
import sys
sys.path.insert(0, '../agent_os')

from agent_os.main import run_all_collectors
from your_plugins.your_logic import process_data

def main():
    # Use agent_os infrastructure
    run_all_collectors()
    
    # Add your application logic
    process_data()
```

See `NOTIFICATION_PATTERN.md` for detailed examples.

## Key Concepts

### Idempotency

Runs are idempotent by default via database UNIQUE constraints. Running the same collection twice won't create duplicates.

### Run Tracking

Every execution creates a `run` record with:
- Status (running/success/failed/skipped)
- Timestamps (started_at, finished_at)
- Error messages (if failed)

### Results Storage

Data is normalized and stored in `results` table with:
- Provider, date, tokens, cost
- Raw JSON (for debugging)
- Unique constraint on (provider, date)

## Database Schema

```sql
-- Tracks every execution
CREATE TABLE runs (
    id TEXT PRIMARY KEY,
    plugin_name TEXT NOT NULL,
    status TEXT NOT NULL,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    error TEXT
);

-- Stores normalized data
CREATE TABLE results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    provider TEXT NOT NULL,
    date TEXT NOT NULL,
    tokens INTEGER,
    cost REAL,
    raw_json TEXT,
    created_at TEXT NOT NULL,
    UNIQUE(provider, date)
);
```

## Configuration

### Environment Variables

Create a `.env` file:

```bash
# API Keys (required)
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-...

# Application-specific (optional, for your apps)
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
ALERT_THRESHOLD=50.0
```

### Scheduling

- **macOS**: launchd plist (already configured)
- **Linux**: cron job
- **Windows**: Task Scheduler

## Development

### Project Phases

- ✅ **Phase 0**: Skeleton (environment, basic structure)
- ✅ **Phase 1**: Data collection (database, collectors)
- ✅ **Phase 2**: Reliability (logging, scheduling, multiple providers)
- ✅ **Phase 3**: Clean architecture (exports, application pattern)

See `first project.md` for detailed implementation guide.

### Testing

```bash
# Test data collection
python main.py --task fetch_openai

# Check runs table
sqlite3 agent_os.db "SELECT * FROM runs ORDER BY started_at DESC LIMIT 5"

# Check results
sqlite3 agent_os.db "SELECT provider, date, tokens, cost FROM results"

# View logs
tail -50 agent.log
```

## Documentation

- **`MakeLikeKernel_AgentOS_Blueprint.md`** - Full architecture and design
- **`first project.md`** - Step-by-step implementation guide
- **`NOTIFICATION_PATTERN.md`** - How to add notifications to your apps
- **`PHASE_*_COMPLETE.md`** - Development progress logs

## Design Principles

1. **Local-first** - SQLite, no external dependencies for core functionality
2. **Idempotent by default** - Safe to re-run, won't create duplicates
3. **Observable** - All runs tracked, structured logging, exportable data
4. **Kernel pattern** - Generic infrastructure, application-specific plugins
5. **Config over code** - Declarative where possible

## Why SQLite?

- Zero setup, perfect for single-user automation
- Local-first (works offline)
- Easy backups (just copy the .db file)
- Fast enough for <10k records/year
- Can upgrade to Postgres later if needed

## Future Applications

Agent OS is designed to support any automation workflow:

- ✅ **AI Usage Billing Tracker** - Track API costs (working example)
- 🔜 **Speech-to-Text Ops** - Transcription pipeline
- 🔜 **Country AI Tracker** - Policy monitoring
- 🔜 **Your Application** - Whatever you need!

## Contributing

This is a personal project, but the architecture is designed to be extensible. Feel free to fork and adapt for your needs.

## License

MIT

## Credits

Built following the "Trojan Horse" strategy - ostensibly building a billing tracker, but extracting a reusable kernel along the way.

---

**Questions?** See documentation or open an issue.

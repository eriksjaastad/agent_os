# Notification Pattern for Agent OS Applications

## Overview

Agent OS is a pure toolbox - it handles database, logging, and task execution. **It does not contain application-specific logic like notifications.**

If your application needs notifications (Discord, email, SMS, etc.), you implement them in your **application layer**, not in agent_os core.

## Example: Discord Webhook Alerts

Here's how the AI Usage Billing Tracker implements Discord alerts as an **application plugin**.

### Step 1: Create Application Plugin

```python
# AI usage-billing tracker/plugins/billing_alerts.py
import requests

def send_discord_alert(webhook_url: str, message: str):
    """Send alert to Discord webhook"""
    payload = {"content": message}
    response = requests.post(webhook_url, json=payload, timeout=10)
    response.raise_for_status()
    return response

def check_cost_threshold(db_conn, threshold: float = 50.0):
    """
    Check if monthly costs exceed threshold.
    Returns (should_alert, summary_message)
    """
    cursor = db_conn.cursor()
    
    # Get current month total
    from datetime import datetime
    month_str = datetime.now().strftime("%Y-%m")
    
    cursor.execute("""
        SELECT SUM(cost) as total_cost
        FROM results
        WHERE date LIKE ?
    """, (f"{month_str}%",))
    
    total = cursor.fetchone()[0] or 0.0
    
    if total > threshold or total == 0:
        message = f"⚠️ ALERT: Monthly AI costs: ${total:.2f}"
        return (True, message)
    
    return (False, None)
```

### Step 2: Add Task to Application Main

```python
# AI usage-billing tracker/main.py (application-specific)
from core.db import get_db
from plugins.billing_alerts import send_discord_alert, check_cost_threshold
import os

def run_with_alerts():
    """Application-specific task that uses agent_os + adds alerts"""
    # Use agent_os to collect data
    from agent_os.main import run_all_collectors
    run_all_collectors()
    
    # Application logic: check thresholds and alert
    webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
    if webhook_url:
        with get_db() as conn:
            should_alert, message = check_cost_threshold(conn)
            if should_alert:
                send_discord_alert(webhook_url, message)
```

### Step 3: Configure Environment

```bash
# .env in your application directory
OPENAI_API_KEY=sk-...
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/YOUR_ID/YOUR_TOKEN
ALERT_THRESHOLD=50.0
```

## Pattern for Other Notification Types

The same pattern works for:

- **Email**: Use `smtplib` in your app plugin
- **SMS**: Use Twilio SDK in your app plugin  
- **Slack**: Use Slack webhook in your app plugin
- **Custom API**: HTTP POST to your endpoint

## Why This Architecture?

✅ **Agent OS stays generic** - works for any application  
✅ **Applications own their logic** - billing alerts, cost thresholds, etc.  
✅ **Easy to add new apps** - speech-to-text doesn't need billing code  
✅ **Clean separation** - kernel vs application boundaries clear  

## Example Applications Using This Pattern

1. **AI Usage Billing Tracker**: Discord alerts when $ > threshold
2. **Speech-to-Text Ops**: Slack notification on transcription errors
3. **Country AI Tracker**: Email digest of daily policy changes

Each application implements its own notification logic as plugins on top of agent_os.

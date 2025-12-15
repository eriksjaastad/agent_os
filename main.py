# main.py
import sys
import os
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
import uuid

from core.db import init_db, get_db
from core.logger import setup_logger
from core.export import export_results_to_csv
from plugins.openai import fetch_openai_usage, normalize_openai_data
from plugins.anthropic import fetch_anthropic_usage, normalize_anthropic_data

__version__ = "0.2.0"
logger = setup_logger()

def run_collector(provider_name: str, fetch_fn, normalize_fn, api_key_name: str):
    """Generic collector runner - the kernel pattern emerging"""
    run_id = str(uuid.uuid4())
    started_at = datetime.now(timezone.utc).isoformat()
    
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
            
            # Check if already collected (explicit check for cleaner logs)
            cursor.execute(
                "SELECT id FROM results WHERE provider = ? AND date = ?",
                (provider_name, date)
            )
            existing = cursor.fetchone()
            if existing:
                logger.info(f"Data for {provider_name} on {date} already exists - skipping")
                cursor.execute(
                    "UPDATE runs SET status = ?, finished_at = ? WHERE id = ?",
                    ("skipped", datetime.now(timezone.utc).isoformat(), run_id)
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
                datetime.now(timezone.utc).isoformat()
            ))
            
            # Mark run complete
            cursor.execute(
                "UPDATE runs SET status = ?, finished_at = ? WHERE id = ?",
                ("success", datetime.now(timezone.utc).isoformat(), run_id)
            )
            conn.commit()
            
            logger.info(f"✓ {provider_name} collection successful - Tokens: {normalized['tokens']}, Cost: ${normalized['cost']:.2f}")
            return 0
            
        except Exception as e:
            # Mark run failed
            cursor.execute(
                "UPDATE runs SET status = ?, finished_at = ?, error = ? WHERE id = ?",
                ("failed", datetime.now(timezone.utc).isoformat(), str(e), run_id)
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
        print("Tasks: fetch_openai, fetch_anthropic, run_all, export")
        return 1
    
    if sys.argv[1] == "--task" and len(sys.argv) > 2:
        task = sys.argv[2]
        if task == "fetch_openai":
            return run_collector("OpenAI", fetch_openai_usage, normalize_openai_data, "OPENAI_API_KEY")
        elif task == "fetch_anthropic":
            return run_collector("Anthropic", fetch_anthropic_usage, normalize_anthropic_data, "ANTHROPIC_API_KEY")
        elif task == "run_all":
            return run_all_collectors()
        elif task == "export":
            with get_db() as conn:
                output_path = export_results_to_csv(conn)
                logger.info(f"✓ Exported to {output_path}")
            return 0
        else:
            logger.error(f"Unknown task: {task}")
            return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())

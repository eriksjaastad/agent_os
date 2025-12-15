# main.py
"""
Agent OS - A minimal, local-first workflow engine for building automation agents.

This is the main entry point and task runner. It orchestrates data collection
from various providers (OpenAI, Anthropic) and manages run tracking.
"""
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

__version__ = "0.3.0"  # Bumped for code review fixes
logger = setup_logger()

def run_collector(provider_name: str, fetch_fn, normalize_fn, api_key_name: str):
    """
    Generic collector runner - the kernel pattern emerging.

    This function demonstrates the "kernel" design: it handles all the infrastructure
    (run tracking, error handling, logging) while delegating the actual data fetching
    and normalization to provider-specific functions passed as parameters.

    Args:
        provider_name: Human-readable name (e.g., "OpenAI", "Anthropic")
        fetch_fn: Function to fetch raw data from the provider's API
        normalize_fn: Function to normalize raw data to standard format
        api_key_name: Environment variable name containing the API key

    Returns:
        0 on success or skip, 1 on failure
    """
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

            # CONSISTENCY: Use timezone-aware datetime for the target date.
            # Previously this used naive datetime while other timestamps used UTC.
            # Using UTC ensures consistency across all date/time operations.
            date = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")

            # Check if already collected (explicit check for cleaner logs)
            # Note: The UNIQUE(provider, date) constraint provides a safety net,
            # but this explicit check gives us better logging and avoids unnecessary API calls.
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
            # Mark run failed - but don't crash the whole process
            cursor.execute(
                "UPDATE runs SET status = ?, finished_at = ?, error = ? WHERE id = ?",
                ("failed", datetime.now(timezone.utc).isoformat(), str(e), run_id)
            )
            conn.commit()

            logger.error(f"✗ {provider_name} collection failed: {e}")
            return 1

def run_all_collectors():
    """
    Run all configured providers.

    Iterates through all registered collectors and runs each one that has
    an API key configured. Tracks results and provides a summary.

    Returns:
        0 if all attempted collectors succeeded
        1 if any collector failed OR if no collectors were configured
    """
    logger.info("=== Starting daily billing collection ===")

    # Registry of all available collectors
    # To add a new provider: add a tuple with (name, fetch_fn, normalize_fn, env_var_name)
    collectors = [
        ("OpenAI", fetch_openai_usage, normalize_openai_data, "OPENAI_API_KEY"),
        ("Anthropic", fetch_anthropic_usage, normalize_anthropic_data, "ANTHROPIC_API_KEY"),
    ]

    results = []
    skipped_count = 0

    for provider, fetch_fn, norm_fn, key_name in collectors:
        # Check if API key exists before running
        if not os.getenv(key_name):
            logger.warning(f"Skipping {provider} - no API key configured")
            skipped_count += 1
            continue

        exit_code = run_collector(provider, fetch_fn, norm_fn, key_name)
        results.append((provider, exit_code))

    # Summary
    success_count = sum(1 for _, code in results if code == 0)
    total_configured = len(collectors)
    total_attempted = len(results)

    logger.info(
        f"=== Collection complete: {success_count}/{total_attempted} successful "
        f"({skipped_count} skipped due to missing API keys) ==="
    )

    # ROBUSTNESS: Return failure if no collectors were actually run.
    # This prevents silent failures when all API keys are missing (misconfiguration).
    # Previously, if all providers were skipped, this would return 0 (success),
    # which could mask configuration problems.
    if total_attempted == 0:
        logger.error(
            "No collectors were run - check that at least one API key is configured in .env"
        )
        return 1

    return 0 if success_count == total_attempted else 1

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

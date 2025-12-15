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
    
    # Note: Placeholder - adjust to actual Anthropic API endpoint
    # Anthropic doesn't have a public usage API yet, so this is for future compatibility
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

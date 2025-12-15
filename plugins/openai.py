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

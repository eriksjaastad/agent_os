# Agent OS Plugins - The Applications
"""
Provider plugins for Agent OS.

Each plugin implements the collector pattern with two functions:
- fetch_*_usage(api_key, date): Fetches raw data from the provider's API
- normalize_*_data(raw_data, date): Normalizes data to standard format

Available plugins:
- openai: OpenAI API usage collector
- anthropic: Anthropic API usage collector

Usage:
    from plugins import fetch_openai_usage, normalize_openai_data

To add a new provider:
1. Create a new file: plugins/your_provider.py
2. Implement fetch_*_usage() and normalize_*_data() functions
3. Add the import and export below
4. Register in main.py's collectors list
"""

from .openai import fetch_openai_usage, normalize_openai_data
from .anthropic import fetch_anthropic_usage, normalize_anthropic_data

# Public API - what gets exported with "from plugins import *"
__all__ = [
    # OpenAI
    "fetch_openai_usage",
    "normalize_openai_data",
    # Anthropic
    "fetch_anthropic_usage",
    "normalize_anthropic_data",
]

# Agent OS Enhancement Plan: Python API, Testing, and Configuration

## What the Database Currently Holds

### `runs` Table - Execution Tracking
Every time agent_os executes a task, it creates a run record:

```
id                  | UUID (e.g., 69d5cc5a-4aaf-4b68...)
plugin_name         | Which collector ran (e.g., "openai_collector")
status              | Current state: running/success/failed/skipped
started_at          | When execution began (ISO timestamp)
finished_at         | When execution completed (ISO timestamp)
error               | Error message if failed (NULL if success)
```

**Example:**
```
id: 69d5cc5a...
plugin_name: openai_collector
status: skipped
started_at: 2025-12-15T00:20:15
finished_at: 2025-12-15T00:20:15
error: NULL
```

### `results` Table - Collected Data
Normalized data from all providers:

```
id          | Auto-increment integer
run_id      | Links to runs.id
provider    | "OpenAI" | "Anthropic" | etc.
date        | YYYY-MM-DD format
tokens      | Total tokens used (integer)
cost        | Total cost in USD (float)
raw_json    | Original API response (for debugging)
created_at  | When record was created (ISO timestamp)

UNIQUE(provider, date) ← Enforces idempotency
```

**Example:**
```
id: 2
run_id: d21a3c98...
provider: OpenAI
date: 2025-12-13
tokens: 0
cost: 0.0
raw_json: {"object": "list", "data": [], ...}
created_at: 2025-12-15T00:13:41
```

---

## Project Overview

We're enhancing agent_os to be production-ready for multiple applications by:

1. **Python API Module** - Clean programmatic interface (no subprocess hacks)
2. **Test Suite** - Comprehensive testing for reliability
3. **Configuration System** - Externalized settings for flexibility

**Goal:** Transform agent_os from "works for one app" to "production-ready platform."

---

## Phase 0: Pre-flight (Setup Testing Infrastructure)

**Goal:** Environment ready for development, testing tools installed.

### What We're Building

- Testing framework (pytest)
- Test database fixtures
- CI/CD preparation

### Setup Tasks

1. **Install Testing Dependencies**

```bash
cd ~/projects/agent_os
source venv/bin/activate
pip install pytest pytest-cov pytest-mock
```

Update `requirements.txt`:
```
python-dotenv==1.0.0
requests==2.31.0
pytest==7.4.3
pytest-cov==4.1.0
pytest-mock==3.12.0
```

2. **Create Test Directory Structure**

```bash
mkdir -p tests/{unit,integration,fixtures}
touch tests/__init__.py
touch tests/conftest.py
```

3. **Create Test Configuration**

```python
# tests/conftest.py
import pytest
import sqlite3
import tempfile
import os
from contextlib import contextmanager

@pytest.fixture
def temp_db():
    """Create temporary database for tests"""
    fd, path = tempfile.mkstemp(suffix='.db')
    yield path
    os.close(fd)
    os.unlink(path)

@pytest.fixture
def test_db_conn(temp_db):
    """Create test database with schema"""
    conn = sqlite3.connect(temp_db)
    conn.row_factory = sqlite3.Row
    
    # Create schema
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE runs (
            id TEXT PRIMARY KEY,
            plugin_name TEXT NOT NULL,
            status TEXT NOT NULL,
            started_at TEXT NOT NULL,
            finished_at TEXT,
            error TEXT
        )
    """)
    cursor.execute("""
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
        )
    """)
    conn.commit()
    
    yield conn
    conn.close()

@pytest.fixture
def sample_results(test_db_conn):
    """Insert sample data for testing"""
    cursor = test_db_conn.cursor()
    cursor.execute("""
        INSERT INTO results (run_id, provider, date, tokens, cost, raw_json, created_at)
        VALUES 
            ('test-run-1', 'OpenAI', '2025-12-01', 1000, 10.50, '{}', '2025-12-01T12:00:00'),
            ('test-run-2', 'OpenAI', '2025-12-02', 2000, 15.75, '{}', '2025-12-02T12:00:00'),
            ('test-run-3', 'Anthropic', '2025-12-01', 500, 5.25, '{}', '2025-12-01T12:00:00')
    """)
    test_db_conn.commit()
    return test_db_conn
```

4. **Create First Smoke Test**

```python
# tests/test_smoke.py
def test_import_core_modules():
    """Verify core modules can be imported"""
    from core import db, logger, export
    assert db is not None
    assert logger is not None
    assert export is not None

def test_import_plugins():
    """Verify plugins can be imported"""
    from plugins import openai, anthropic
    assert openai is not None
    assert anthropic is not None
```

### ✅ Phase 0 DONE Qualifications

- [ ] Run `pip list | grep pytest` and see pytest 7.4.3 installed
- [ ] Run `pytest tests/test_smoke.py` and see all tests pass
- [ ] Run `pytest --cov=core --cov=plugins` and see coverage report
- [ ] Directory `tests/` exists with conftest.py and fixtures
- [ ] Run `pytest -v` and see structured test output

**🛑 Rabbit Hole Warning:** Do NOT write application tests yet. Just infrastructure.

---

## Phase 1: Python API Module (The Interface)

**Goal:** Create clean programmatic interface for applications to use agent_os.

**The "Kernel" Work (100%):**

This is all kernel work - creating the public API for applications.

### Concrete Implementation Steps

**Step 1: Create API Module**

```python
# core/api.py
"""
Public API for agent_os

Applications should use this module instead of:
- subprocess calls
- direct database access
- importing internal modules

Example:
    from agent_os.core.api import AgentOSClient
    
    client = AgentOSClient()
    result = client.collect_all()
    data = client.query_results(provider='OpenAI')
"""

import os
import sqlite3
from typing import List, Dict, Optional, Any
from datetime import datetime
from contextlib import contextmanager

class AgentOSClient:
    """
    Client for interacting with agent_os programmatically.
    
    This is the ONLY interface applications should use.
    """
    
    def __init__(self, db_path: str = None, config: Dict = None):
        """
        Initialize AgentOS client.
        
        Args:
            db_path: Path to agent_os.db (defaults to ./agent_os.db)
            config: Optional configuration overrides
        """
        self.db_path = db_path or os.environ.get('AGENT_OS_DB', 'agent_os.db')
        self.config = config or {}
        
        # Validate database exists
        if not os.path.exists(self.db_path):
            raise FileNotFoundError(f"Database not found: {self.db_path}")
    
    @contextmanager
    def _get_connection(self):
        """Internal: Get database connection"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
    
    # ===== Collection Methods =====
    
    def collect_all(self, timeout: int = 60) -> Dict[str, Any]:
        """
        Run all configured collectors.
        
        Args:
            timeout: Maximum seconds to wait
            
        Returns:
            {
                'success': bool,
                'duration': float,
                'providers': List[str],
                'errors': List[str]
            }
        """
        import subprocess
        import time
        
        start = time.time()
        
        # Import to get venv path
        agent_os_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        python_path = os.path.join(agent_os_dir, 'venv', 'bin', 'python')
        main_path = os.path.join(agent_os_dir, 'main.py')
        
        result = subprocess.run(
            [python_path, main_path, '--task', 'run_all'],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=agent_os_dir
        )
        
        return {
            'success': result.returncode == 0,
            'duration': time.time() - start,
            'stdout': result.stdout,
            'stderr': result.stderr,
            'exit_code': result.returncode
        }
    
    def collect_provider(self, provider: str, timeout: int = 60) -> Dict[str, Any]:
        """
        Run collection for specific provider.
        
        Args:
            provider: 'openai' or 'anthropic'
            timeout: Maximum seconds to wait
            
        Returns:
            Same as collect_all()
        """
        import subprocess
        import time
        
        start = time.time()
        agent_os_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        python_path = os.path.join(agent_os_dir, 'venv', 'bin', 'python')
        main_path = os.path.join(agent_os_dir, 'main.py')
        
        result = subprocess.run(
            [python_path, main_path, '--task', f'fetch_{provider}'],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=agent_os_dir
        )
        
        return {
            'success': result.returncode == 0,
            'duration': time.time() - start,
            'stdout': result.stdout,
            'stderr': result.stderr,
            'exit_code': result.returncode
        }
    
    # ===== Query Methods =====
    
    def query_results(
        self,
        provider: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Query results with optional filters.
        
        Args:
            provider: Filter by provider name
            start_date: Filter by date >= (YYYY-MM-DD)
            end_date: Filter by date <= (YYYY-MM-DD)
            limit: Maximum results to return
            
        Returns:
            List of result dictionaries
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            query = "SELECT * FROM results WHERE 1=1"
            params = []
            
            if provider:
                query += " AND provider = ?"
                params.append(provider)
            if start_date:
                query += " AND date >= ?"
                params.append(start_date)
            if end_date:
                query += " AND date <= ?"
                params.append(end_date)
            
            query += " ORDER BY date DESC, provider"
            
            if limit:
                query += " LIMIT ?"
                params.append(limit)
            
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
    
    def query_runs(
        self,
        status: Optional[str] = None,
        plugin_name: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Query run history with optional filters.
        
        Args:
            status: Filter by status (success/failed/running/skipped)
            plugin_name: Filter by plugin name
            limit: Maximum results (default 50)
            
        Returns:
            List of run dictionaries
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            query = "SELECT * FROM runs WHERE 1=1"
            params = []
            
            if status:
                query += " AND status = ?"
                params.append(status)
            if plugin_name:
                query += " AND plugin_name = ?"
                params.append(plugin_name)
            
            query += " ORDER BY started_at DESC LIMIT ?"
            params.append(limit)
            
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
    
    def get_monthly_totals(self, year: int, month: int) -> Dict[str, Any]:
        """
        Get aggregated totals for a specific month.
        
        Args:
            year: Year (e.g., 2025)
            month: Month (1-12)
            
        Returns:
            {
                'total_cost': float,
                'total_tokens': int,
                'days_tracked': int,
                'by_provider': [
                    {'provider': 'OpenAI', 'cost': 10.50, 'tokens': 1000},
                    ...
                ]
            }
        """
        month_str = f"{year}-{month:02d}"
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # By provider
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
            by_provider = [dict(row) for row in cursor.fetchall()]
            
            # Overall
            cursor.execute("""
                SELECT 
                    COUNT(DISTINCT date) as days_tracked,
                    SUM(tokens) as total_tokens,
                    SUM(cost) as total_cost
                FROM results
                WHERE date LIKE ?
            """, (f"{month_str}%",))
            totals = dict(cursor.fetchone())
            
            return {
                'total_cost': totals['total_cost'] or 0.0,
                'total_tokens': totals['total_tokens'] or 0,
                'days_tracked': totals['days_tracked'] or 0,
                'by_provider': by_provider
            }
    
    # ===== Export Methods =====
    
    def export_to_csv(self, output_path: Optional[str] = None) -> str:
        """
        Export results to CSV.
        
        Args:
            output_path: Where to save CSV (auto-generated if None)
            
        Returns:
            Path to created CSV file
        """
        from core.export import export_results_to_csv
        
        with self._get_connection() as conn:
            return export_results_to_csv(conn, output_path)
    
    # ===== Health Check Methods =====
    
    def health_check(self) -> Dict[str, Any]:
        """
        Check agent_os health status.
        
        Returns:
            {
                'database': bool,
                'schema_valid': bool,
                'last_run': str (ISO timestamp),
                'total_results': int,
                'total_runs': int
            }
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Check schema
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = {row[0] for row in cursor.fetchall()}
                schema_valid = {'runs', 'results'}.issubset(tables)
                
                # Get stats
                cursor.execute("SELECT COUNT(*) FROM results")
                total_results = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM runs")
                total_runs = cursor.fetchone()[0]
                
                cursor.execute("SELECT started_at FROM runs ORDER BY started_at DESC LIMIT 1")
                last_run_row = cursor.fetchone()
                last_run = last_run_row[0] if last_run_row else None
                
                return {
                    'database': True,
                    'schema_valid': schema_valid,
                    'last_run': last_run,
                    'total_results': total_results,
                    'total_runs': total_runs
                }
        except Exception as e:
            return {
                'database': False,
                'error': str(e)
            }
```

**Step 2: Create API Tests**

```python
# tests/unit/test_api.py
import pytest
from core.api import AgentOSClient
from unittest.mock import patch, MagicMock
import tempfile
import os

def test_client_initialization(test_db_conn, temp_db):
    """Test client can be initialized with database"""
    client = AgentOSClient(db_path=temp_db)
    assert client.db_path == temp_db

def test_query_results_no_filters(sample_results):
    """Test querying results without filters"""
    # Get db path from fixture
    db_path = sample_results.execute("PRAGMA database_list").fetchone()[2]
    
    client = AgentOSClient(db_path=db_path)
    results = client.query_results()
    
    assert len(results) == 3
    assert results[0]['provider'] in ['OpenAI', 'Anthropic']

def test_query_results_with_provider_filter(sample_results):
    """Test querying results filtered by provider"""
    db_path = sample_results.execute("PRAGMA database_list").fetchone()[2]
    
    client = AgentOSClient(db_path=db_path)
    results = client.query_results(provider='OpenAI')
    
    assert len(results) == 2
    assert all(r['provider'] == 'OpenAI' for r in results)

def test_query_results_with_date_range(sample_results):
    """Test querying results with date filters"""
    db_path = sample_results.execute("PRAGMA database_list").fetchone()[2]
    
    client = AgentOSClient(db_path=db_path)
    results = client.query_results(start_date='2025-12-02')
    
    assert len(results) == 1
    assert results[0]['date'] == '2025-12-02'

def test_get_monthly_totals(sample_results):
    """Test monthly aggregation"""
    db_path = sample_results.execute("PRAGMA database_list").fetchone()[2]
    
    client = AgentOSClient(db_path=db_path)
    totals = client.get_monthly_totals(2025, 12)
    
    assert totals['total_cost'] == 31.50  # 10.50 + 15.75 + 5.25
    assert totals['total_tokens'] == 3500  # 1000 + 2000 + 500
    assert totals['days_tracked'] == 2  # Dec 1 and Dec 2
    assert len(totals['by_provider']) == 2  # OpenAI and Anthropic

def test_health_check(sample_results):
    """Test health check returns valid status"""
    db_path = sample_results.execute("PRAGMA database_list").fetchone()[2]
    
    client = AgentOSClient(db_path=db_path)
    health = client.health_check()
    
    assert health['database'] is True
    assert health['schema_valid'] is True
    assert health['total_results'] == 3

@patch('subprocess.run')
def test_collect_all_success(mock_run, test_db_conn, temp_db):
    """Test successful collection via subprocess"""
    # Mock successful subprocess
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = "Collection complete"
    mock_result.stderr = ""
    mock_run.return_value = mock_result
    
    client = AgentOSClient(db_path=temp_db)
    result = client.collect_all()
    
    assert result['success'] is True
    assert result['exit_code'] == 0
    assert mock_run.called

@patch('subprocess.run')
def test_collect_all_failure(mock_run, test_db_conn, temp_db):
    """Test failed collection via subprocess"""
    # Mock failed subprocess
    mock_result = MagicMock()
    mock_result.returncode = 1
    mock_result.stdout = ""
    mock_result.stderr = "API key invalid"
    mock_run.return_value = mock_result
    
    client = AgentOSClient(db_path=temp_db)
    result = client.collect_all()
    
    assert result['success'] is False
    assert result['exit_code'] == 1
    assert 'API key' in result['stderr']
```

**Step 3: Update Billing Tracker to Use API**

```python
# AI usage-billing tracker/billing_app_v2.py
"""
Billing Tracker using Agent OS Python API

This version uses the proper API instead of subprocess hacks.
"""
import sys
import os

# Use agent_os API
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'agent_os'))
from core.api import AgentOSClient

def task_summary():
    """Show monthly billing summary using API"""
    from datetime import datetime
    from plugins.billing_summary import format_summary_message
    
    # Initialize client
    agent_os_path = os.path.join(os.path.dirname(__file__), '..', 'agent_os')
    db_path = os.path.join(agent_os_path, 'agent_os.db')
    client = AgentOSClient(db_path=db_path)
    
    # Check health
    health = client.health_check()
    if not health['database']:
        print(f"❌ Database error: {health.get('error')}")
        return 1
    
    # Get monthly totals (using API instead of raw SQL)
    now = datetime.now()
    totals = client.get_monthly_totals(now.year, now.month)
    
    # Format (reuse existing formatter)
    summary = {
        'month': f"{now.year}-{now.month:02d}",
        'total_days': totals['days_tracked'],
        'grand_total': totals['total_cost'],
        'by_provider': totals['by_provider']
    }
    
    message = format_summary_message(summary)
    print(message)
    return 0

def task_daily_report():
    """Daily collection + alerts + export using API"""
    print("=== Running Daily Billing Report ===")
    
    # Initialize client
    agent_os_path = os.path.join(os.path.dirname(__file__), '..', 'agent_os')
    db_path = os.path.join(agent_os_path, 'agent_os.db')
    client = AgentOSClient(db_path=db_path)
    
    # Step 1: Collect data (using API)
    print("Collecting data...")
    result = client.collect_all(timeout=120)
    
    if not result['success']:
        print(f"⚠️ Collection failed: {result['stderr']}")
        print("Continuing with existing data...")
    else:
        print(f"✓ Collection completed in {result['duration']:.2f}s")
    
    # Step 2: Export (using API)
    print("Exporting data...")
    csv_path = client.export_to_csv()
    print(f"✓ Exported to {csv_path}")
    
    # Step 3: Check health
    health = client.health_check()
    print(f"✓ Health check: {health['total_results']} results, last run: {health['last_run']}")
    
    return 0

def main():
    if len(sys.argv) < 2:
        print("AI Usage Billing Tracker (v2 - API Edition)")
        print("Usage: python billing_app_v2.py [TASK]")
        print("Tasks:")
        print("  summary       - Show monthly billing summary")
        print("  daily_report  - Run daily collection + export")
        return 1
    
    task = sys.argv[1]
    
    if task == "summary":
        return task_summary()
    elif task == "daily_report":
        return task_daily_report()
    else:
        print(f"Unknown task: {task}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
```

### ✅ Phase 1 DONE Qualifications

- [ ] File `core/api.py` exists and contains `AgentOSClient` class
- [ ] Run `pytest tests/unit/test_api.py -v` and see all tests pass
- [ ] Test `AgentOSClient().health_check()` returns valid status
- [ ] Test `AgentOSClient().query_results()` returns list of results
- [ ] Test `AgentOSClient().get_monthly_totals(2025, 12)` returns aggregated data
- [ ] Test `AgentOSClient().collect_all()` runs without errors
- [ ] Billing tracker v2 works using API (no subprocess in application code)
- [ ] Run `pytest --cov=core.api` and see >80% coverage

**Verification Commands:**
```bash
# Test API directly
cd ~/projects/agent_os
source venv/bin/activate
python -c "from core.api import AgentOSClient; client = AgentOSClient(); print(client.health_check())"

# Run API tests
pytest tests/unit/test_api.py -v

# Test billing tracker v2
cd "../AI usage-billing tracker"
python billing_app_v2.py summary
```

**🛑 Rabbit Hole Warning:** Do NOT add caching or fancy features. Just clean API.

---

## Phase 2: Configuration System (Externalized Settings)

**Goal:** Move hardcoded values to configuration files for flexibility.

**The "Kernel" Work (80%):**

Configuration is mostly kernel work, with applications providing their own configs.

### What We're Externalizing

**Currently Hardcoded:**
- Database path (`agent_os.db`)
- Log file path (`agent.log`)
- Cron schedule (6:00 AM)
- Provider API endpoints
- Timeout values

**Should Be Configurable:**
- All paths (database, logs, exports)
- Schedule parameters
- Retry settings
- Log levels
- Provider configurations

### Concrete Implementation Steps

**Step 1: Create Configuration Module**

```python
# core/config.py
"""
Configuration management for agent_os

Loads configuration from:
1. Default values (code)
2. Config file (agent_os.yaml)
3. Environment variables (highest priority)

Example agent_os.yaml:
    database:
      path: ./data/agent_os.db
      timeout: 30
    
    logging:
      level: INFO
      path: ./logs/agent.log
    
    schedule:
      enabled: true
      time: "06:00"
    
    collectors:
      openai:
        enabled: true
        timeout: 60
      anthropic:
        enabled: true
        timeout: 60
"""

import os
import yaml
from typing import Dict, Any, Optional
from dataclasses import dataclass, field

@dataclass
class DatabaseConfig:
    """Database configuration"""
    path: str = "agent_os.db"
    timeout: int = 30
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'DatabaseConfig':
        return cls(**{k: v for k, v in data.items() if k in cls.__annotations__})

@dataclass
class LoggingConfig:
    """Logging configuration"""
    level: str = "INFO"
    path: str = "agent.log"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'LoggingConfig':
        return cls(**{k: v for k, v in data.items() if k in cls.__annotations__})

@dataclass
class ScheduleConfig:
    """Schedule configuration"""
    enabled: bool = True
    time: str = "06:00"
    timezone: str = "UTC"
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'ScheduleConfig':
        return cls(**{k: v for k, v in data.items() if k in cls.__annotations__})

@dataclass
class CollectorConfig:
    """Individual collector configuration"""
    enabled: bool = True
    timeout: int = 60
    retry_count: int = 3
    retry_delay: int = 5
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'CollectorConfig':
        return cls(**{k: v for k, v in data.items() if k in cls.__annotations__})

@dataclass
class AgentOSConfig:
    """Main agent_os configuration"""
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    schedule: ScheduleConfig = field(default_factory=ScheduleConfig)
    collectors: Dict[str, CollectorConfig] = field(default_factory=dict)
    
    @classmethod
    def load(cls, config_path: Optional[str] = None) -> 'AgentOSConfig':
        """
        Load configuration from file and environment.
        
        Priority:
        1. Environment variables (highest)
        2. Config file
        3. Defaults (lowest)
        """
        config = cls()
        
        # Load from file if exists
        if config_path and os.path.exists(config_path):
            with open(config_path, 'r') as f:
                data = yaml.safe_load(f) or {}
                
                if 'database' in data:
                    config.database = DatabaseConfig.from_dict(data['database'])
                if 'logging' in data:
                    config.logging = LoggingConfig.from_dict(data['logging'])
                if 'schedule' in data:
                    config.schedule = ScheduleConfig.from_dict(data['schedule'])
                if 'collectors' in data:
                    config.collectors = {
                        name: CollectorConfig.from_dict(collector_data)
                        for name, collector_data in data['collectors'].items()
                    }
        
        # Override with environment variables
        if 'AGENT_OS_DB_PATH' in os.environ:
            config.database.path = os.environ['AGENT_OS_DB_PATH']
        if 'AGENT_OS_LOG_PATH' in os.environ:
            config.logging.path = os.environ['AGENT_OS_LOG_PATH']
        if 'AGENT_OS_LOG_LEVEL' in os.environ:
            config.logging.level = os.environ['AGENT_OS_LOG_LEVEL']
        
        return config

# Global config instance
_config: Optional[AgentOSConfig] = None

def get_config(config_path: Optional[str] = None) -> AgentOSConfig:
    """Get global configuration instance"""
    global _config
    if _config is None:
        # Try default locations
        default_paths = [
            'agent_os.yaml',
            'config/agent_os.yaml',
            os.path.expanduser('~/.agent_os.yaml')
        ]
        
        for path in default_paths:
            if os.path.exists(path):
                config_path = path
                break
        
        _config = AgentOSConfig.load(config_path)
    return _config

def reload_config(config_path: Optional[str] = None):
    """Force reload configuration"""
    global _config
    _config = AgentOSConfig.load(config_path)
```

**Step 2: Create Example Config Files**

```yaml
# agent_os.yaml.example
# Agent OS Configuration File
# Copy to agent_os.yaml and customize

database:
  path: ./agent_os.db
  timeout: 30

logging:
  level: INFO  # DEBUG, INFO, WARNING, ERROR
  path: ./agent.log
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

schedule:
  enabled: true
  time: "06:00"  # 24-hour format
  timezone: UTC

collectors:
  openai:
    enabled: true
    timeout: 60
    retry_count: 3
    retry_delay: 5
  
  anthropic:
    enabled: true
    timeout: 60
    retry_count: 3
    retry_delay: 5

# Export settings
export:
  default_format: csv
  output_dir: ./exports
  include_raw_json: false
```

**Step 3: Update Core Modules to Use Config**

```python
# core/db.py (UPDATED)
import sqlite3
from contextlib import contextmanager
from core.config import get_config

def get_db_path() -> str:
    """Get database path from config"""
    config = get_config()
    return config.database.path

def init_db():
    config = get_config()
    conn = sqlite3.connect(config.database.path, timeout=config.database.timeout)
    # ... rest of init code ...

@contextmanager
def get_db():
    config = get_config()
    conn = sqlite3.connect(config.database.path, timeout=config.database.timeout)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()
```

```python
# core/logger.py (UPDATED)
import logging
from core.config import get_config

def setup_logger(name: str = "agent_os"):
    config = get_config()
    
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, config.logging.level))
    
    # File handler
    fh = logging.FileHandler(config.logging.path)
    fh.setLevel(getattr(logging, config.logging.level))
    
    # Console handler
    ch = logging.StreamHandler()
    ch.setLevel(getattr(logging, config.logging.level))
    
    # Formatter
    formatter = logging.Formatter(
        config.logging.format,
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)
    
    logger.addHandler(fh)
    logger.addHandler(ch)
    
    return logger
```

**Step 4: Create Configuration Tests**

```python
# tests/unit/test_config.py
import pytest
import os
import tempfile
from core.config import AgentOSConfig, get_config, reload_config

def test_default_config():
    """Test default configuration values"""
    config = AgentOSConfig()
    
    assert config.database.path == "agent_os.db"
    assert config.logging.level == "INFO"
    assert config.schedule.time == "06:00"

def test_load_config_from_yaml():
    """Test loading configuration from YAML file"""
    # Create temp config file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write("""
database:
  path: /custom/path/db.db
  timeout: 60

logging:
  level: DEBUG
  path: /custom/logs/app.log

collectors:
  openai:
    enabled: true
    timeout: 120
""")
        config_path = f.name
    
    try:
        config = AgentOSConfig.load(config_path)
        
        assert config.database.path == "/custom/path/db.db"
        assert config.database.timeout == 60
        assert config.logging.level == "DEBUG"
        assert config.collectors['openai'].timeout == 120
    finally:
        os.unlink(config_path)

def test_environment_override():
    """Test environment variables override config file"""
    # Set environment variable
    os.environ['AGENT_OS_DB_PATH'] = '/env/override/db.db'
    os.environ['AGENT_OS_LOG_LEVEL'] = 'ERROR'
    
    try:
        config = AgentOSConfig.load()
        
        assert config.database.path == '/env/override/db.db'
        assert config.logging.level == 'ERROR'
    finally:
        del os.environ['AGENT_OS_DB_PATH']
        del os.environ['AGENT_OS_LOG_LEVEL']

def test_config_priority():
    """Test configuration priority: ENV > file > defaults"""
    # Create config file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write("""
database:
  path: /file/path/db.db
  timeout: 45
""")
        config_path = f.name
    
    # Set environment (should win)
    os.environ['AGENT_OS_DB_PATH'] = '/env/path/db.db'
    
    try:
        config = AgentOSConfig.load(config_path)
        
        # ENV wins for path
        assert config.database.path == '/env/path/db.db'
        # File wins for timeout (no ENV override)
        assert config.database.timeout == 45
    finally:
        os.unlink(config_path)
        del os.environ['AGENT_OS_DB_PATH']
```

**Step 5: Add YAML Dependency**

Update `requirements.txt`:
```
python-dotenv==1.0.0
requests==2.31.0
pytest==7.4.3
pytest-cov==4.1.0
pytest-mock==3.12.0
pyyaml==6.0.1
```

### ✅ Phase 2 DONE Qualifications

- [ ] File `core/config.py` exists with `AgentOSConfig` class
- [ ] File `agent_os.yaml.example` exists with all settings documented
- [ ] Run `pytest tests/unit/test_config.py -v` and see all tests pass
- [ ] Create custom `agent_os.yaml`, run app, verify it uses custom settings
- [ ] Set `AGENT_OS_DB_PATH=/tmp/test.db`, run app, verify it uses /tmp/test.db
- [ ] Test priority: environment > file > defaults all work correctly
- [ ] Run `git status` and verify `agent_os.yaml` is in `.gitignore`
- [ ] Documentation updated showing configuration options

**Verification Commands:**
```bash
# Test config loading
python -c "from core.config import get_config; print(get_config().database.path)"

# Test environment override
AGENT_OS_DB_PATH=/tmp/test.db python -c "from core.config import get_config; print(get_config().database.path)"

# Test YAML loading
cp agent_os.yaml.example agent_os.yaml
# Edit agent_os.yaml to change database path
python -c "from core.config import get_config; print(get_config().database.path)"

# Run all config tests
pytest tests/unit/test_config.py -v
```

**🛑 Rabbit Hole Warning:** Do NOT build a config UI or validation beyond basics.

---

## Phase 3: Comprehensive Test Suite (Quality Assurance)

**Goal:** Comprehensive tests for reliability and confidence.

**The "Kernel" Work (100%):**

Testing the kernel to ensure it's rock-solid.

### Test Coverage Goals

- **Unit tests**: Core modules (db, logger, export, config, API)
- **Integration tests**: End-to-end workflows
- **Fixtures**: Reusable test data
- **Coverage**: >80% overall, >90% for API module

### Concrete Implementation Steps

**Step 1: Core Module Unit Tests**

```python
# tests/unit/test_db.py
import pytest
import tempfile
import os
from core.db import init_db, get_db

def test_init_db_creates_tables(temp_db):
    """Test database initialization creates required tables"""
    from core.config import AgentOSConfig, reload_config
    
    # Create temp config
    config = AgentOSConfig()
    config.database.path = temp_db
    
    import core.config as config_module
    config_module._config = config
    
    # Initialize
    init_db()
    
    # Verify tables exist
    import sqlite3
    conn = sqlite3.connect(temp_db)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = {row[0] for row in cursor.fetchall()}
    
    assert 'runs' in tables
    assert 'results' in tables
    conn.close()

def test_get_db_context_manager(test_db_conn):
    """Test get_db context manager works correctly"""
    # This test uses the fixture which already tests get_db
    assert test_db_conn is not None
    
    # Test can execute queries
    cursor = test_db_conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    
    assert len(tables) > 0

def test_unique_constraint_enforced(test_db_conn):
    """Test UNIQUE(provider, date) constraint works"""
    cursor = test_db_conn.cursor()
    
    # Insert first record
    cursor.execute("""
        INSERT INTO results (run_id, provider, date, tokens, cost, raw_json, created_at)
        VALUES ('test1', 'OpenAI', '2025-12-01', 100, 1.0, '{}', '2025-12-01T12:00:00')
    """)
    test_db_conn.commit()
    
    # Try to insert duplicate
    with pytest.raises(Exception) as exc_info:
        cursor.execute("""
            INSERT INTO results (run_id, provider, date, tokens, cost, raw_json, created_at)
            VALUES ('test2', 'OpenAI', '2025-12-01', 200, 2.0, '{}', '2025-12-01T13:00:00')
        """)
        test_db_conn.commit()
    
    assert 'UNIQUE constraint failed' in str(exc_info.value)
```

```python
# tests/unit/test_export.py
import pytest
import csv
import os
from core.export import export_results_to_csv

def test_export_creates_csv(sample_results):
    """Test CSV export creates file"""
    output_path = 'test_export.csv'
    
    try:
        result_path = export_results_to_csv(sample_results, output_path)
        
        assert os.path.exists(result_path)
        assert result_path == output_path
    finally:
        if os.path.exists(output_path):
            os.unlink(output_path)

def test_export_contains_correct_data(sample_results):
    """Test CSV export has correct data"""
    output_path = 'test_export.csv'
    
    try:
        export_results_to_csv(sample_results, output_path)
        
        with open(output_path, 'r') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        
        assert len(rows) == 3
        assert rows[0]['provider'] in ['OpenAI', 'Anthropic']
        assert 'tokens' in rows[0]
        assert 'cost' in rows[0]
    finally:
        if os.path.exists(output_path):
            os.unlink(output_path)

def test_export_auto_generates_filename(sample_results):
    """Test CSV export auto-generates filename if not provided"""
    result_path = export_results_to_csv(sample_results)
    
    try:
        assert os.path.exists(result_path)
        assert result_path.startswith('export_results_')
        assert result_path.endswith('.csv')
    finally:
        if os.path.exists(result_path):
            os.unlink(result_path)
```

**Step 2: Integration Tests**

```python
# tests/integration/test_collection_workflow.py
import pytest
import subprocess
import os
import sqlite3

@pytest.mark.integration
def test_full_collection_workflow():
    """Test complete collection workflow end-to-end"""
    # This test requires actual API keys and network
    # Skip if AGENT_OS_INTEGRATION_TESTS not set
    if not os.environ.get('AGENT_OS_INTEGRATION_TESTS'):
        pytest.skip("Integration tests not enabled")
    
    # Run collection
    result = subprocess.run(
        ['./venv/bin/python', 'main.py', '--task', 'run_all'],
        capture_output=True,
        text=True,
        cwd=os.path.dirname(__file__) + '/../../'
    )
    
    assert result.returncode == 0
    
    # Verify data was collected
    conn = sqlite3.connect('agent_os.db')
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM results")
    count = cursor.fetchone()[0]
    
    assert count > 0
    conn.close()

@pytest.mark.integration
def test_api_collection_and_query():
    """Test API collection and querying"""
    if not os.environ.get('AGENT_OS_INTEGRATION_TESTS'):
        pytest.skip("Integration tests not enabled")
    
    from core.api import AgentOSClient
    
    client = AgentOSClient()
    
    # Collect
    result = client.collect_all(timeout=120)
    assert result['success'] is True
    
    # Query
    results = client.query_results(limit=10)
    assert len(results) > 0
    
    # Health check
    health = client.health_check()
    assert health['database'] is True
    assert health['total_results'] > 0
```

**Step 3: Test Documentation**

```markdown
# tests/README.md

## Running Tests

### Quick Tests (Unit Only)
```bash
pytest tests/unit/ -v
```

### Full Test Suite (With Integration)
```bash
# Set integration flag
export AGENT_OS_INTEGRATION_TESTS=1

# Run all tests
pytest tests/ -v

# With coverage
pytest tests/ --cov=core --cov=plugins --cov-report=html
```

### Test Organization

```
tests/
├── unit/              # Fast, isolated tests
│   ├── test_api.py
│   ├── test_config.py
│   ├── test_db.py
│   └── test_export.py
├── integration/       # Slow, requires network/API keys
│   └── test_collection_workflow.py
├── fixtures/          # Reusable test data
│   └── sample_data.py
└── conftest.py        # Shared fixtures
```

### Coverage Goals

- Overall: >80%
- API module: >90%
- Core modules: >85%
- Plugins: >70%

### CI/CD

Tests run automatically on:
- Every commit (unit tests only)
- Pull requests (full suite)
- Nightly (integration tests)
```

### ✅ Phase 3 DONE Qualifications

- [ ] Run `pytest tests/unit/ -v` and see 20+ tests pass
- [ ] Run `pytest --cov=core --cov=plugins` and see >80% coverage
- [ ] File `tests/README.md` documents how to run tests
- [ ] Integration tests exist but skip without `AGENT_OS_INTEGRATION_TESTS` flag
- [ ] Run `pytest tests/unit/test_api.py -v` and see all API tests pass
- [ ] Run `pytest tests/unit/test_config.py -v` and see all config tests pass
- [ ] Run `pytest tests/unit/test_db.py -v` and see all database tests pass
- [ ] Coverage report shows no critical gaps

**Verification Commands:**
```bash
# Run all unit tests
pytest tests/unit/ -v

# Check coverage
pytest tests/ --cov=core --cov=plugins --cov-report=term-missing

# Generate HTML coverage report
pytest tests/ --cov=core --cov=plugins --cov-report=html
open htmlcov/index.html

# Run specific test file
pytest tests/unit/test_api.py -v

# Run with verbose output
pytest tests/ -vv -s
```

**🛑 Rabbit Hole Warning:** Do NOT achieve 100% coverage. >80% is excellent.

---

## Decision Log (Why We Made These Choices)

### Why Python API over subprocess?
**Reason:** Cleaner interface, faster execution, easier testing, type safety.
**When to reconsider:** Never for applications. Subprocess is implementation detail.

### Why YAML for config over JSON/TOML?
**Reason:** Human-friendly, supports comments, widely used, good Python support.
**When to reconsider:** If parsing performance becomes issue (unlikely).

### Why dataclasses for config over dict?
**Reason:** Type hints, IDE autocomplete, validation, clear structure.
**When to reconsider:** If need complex validation (then use Pydantic).

### Why pytest over unittest?
**Reason:** Better fixtures, clearer syntax, powerful plugins, industry standard.
**When to reconsider:** Never. pytest is superior.

### Why >80% coverage target?
**Reason:** Diminishing returns above 80%. Last 20% often trivial code.
**When to reconsider:** For mission-critical modules (aim for 90%+).

### Why keep subprocess in API module?
**Reason:** Clean separation - API doesn't import main.py. Avoids circular dependencies.
**When to reconsider:** When execution overhead matters (profile first).

---

## Strategic Summary

You are "Done" with:
- **Phase 0** when tests run and fixtures work
- **Phase 1** when applications use API (no subprocess in app code)
- **Phase 2** when all paths come from config
- **Phase 3** when >80% coverage achieved

**The beauty of this approach:** Each phase provides immediate value. Phase 1 alone makes billing tracker cleaner. Phase 2 enables flexible deployment. Phase 3 ensures reliability.

**Start with Phase 0.** Get testing infrastructure running. Then Phase 1. Don't skip ahead.

---

## Rollback / Failure Strategy

**If Phase 1 fails:**
- API module breaks existing code
- **Solution:** Keep old subprocess pattern working, add API alongside
- **Rollback:** Just don't use API module yet

**If Phase 2 fails:**
- Config breaks existing deployments
- **Solution:** Config defaults match current hardcoded values
- **Rollback:** Delete config module, revert to hardcoded

**If Phase 3 fails:**
- Tests reveal bugs in core modules
- **Solution:** That's the point! Fix bugs, improve code
- **Rollback:** N/A - tests are documentation

---

## Time Estimate

**Phase 0 (Testing Setup):** 1-2 hours
**Phase 1 (Python API):** 4-6 hours
**Phase 2 (Configuration):** 3-4 hours
**Phase 3 (Test Suite):** 6-8 hours

**Total:** 14-20 hours of focused work

**OR:** 2-3 full work days if you include breaks, reviews, polish.

---

## Success Metrics

### Phase 1 Success
- Billing tracker uses API
- No subprocess calls in application code
- API tests pass
- Applications are cleaner

### Phase 2 Success
- All paths configurable
- Can run multiple instances with different configs
- Config tests pass
- Documentation shows all options

### Phase 3 Success
- >80% test coverage
- All tests pass
- CI/CD ready
- Confident in making changes

---

**Now let's build it.** Start with Phase 0, right now, before you overthink it.

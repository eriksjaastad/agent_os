# Agent OS Refactoring & API Key Migration

> **Purpose:** Migrate from shared credentials to per-project keys, define Agent OS as orchestration engine  
> **Created:** December 21, 2025  
> **Status:** Planning & Migration Phase  
> **Type:** Infrastructure

---

## The Problem We're Solving

1. **Shared API keys** (via agent_os/.env) prevent cost attribution per project
2. **Unclear agent_os purpose** - is it credential storage or orchestration?
3. **No clear pattern** for when to use agent_os vs project-local automation

---

## The Vision: Agent OS as Orchestration Engine

**Think:** n8n/Make.com but self-hosted for YOUR projects

**What it SHOULD do:**
- ✅ Orchestrate workflows across projects
- ✅ Centralized scheduling dashboard (see all cron jobs in one place)
- ✅ Cross-project triggers ("Trading volatility spike → Query Cortana memories")
- ✅ Monitoring & alerting (know when things break)
- ✅ Resource management (prevent rate limit conflicts)
- ✅ Cost aggregation (projects report costs, agent_os shows totals)

**What it SHOULD NOT do:**
- ❌ Store credentials for independent projects
- ❌ Share API keys across experiments
- ❌ Run project code directly (projects run themselves, agent_os orchestrates)

**Architecture Model:**
```
agent_os (orchestration layer)
    │
    ├─ Plugins (projects register themselves)
    │   ├─ Each project owns its credentials
    │   ├─ Projects expose: run_task(), get_status(), report_cost()
    │   └─ agent_os calls plugins, doesn't impersonate them
    │
    ├─ Scheduler (centralized cron view)
    ├─ Monitor (health checks)
    └─ Dashboard (see everything)
```

---

## Phase 1: API Key Migration (Immediate)

### ✅ Completed
- [x] Audit which projects use agent_os/.env
  - **Result:** Only Cortana uses shared keys
  - Trading Projects: Uses own .env ✅
  - image-workflow: Uses own .env ✅

### 🔶 In Progress

#### 1. Create Separate API Key for Cortana
- [ ] Log into OpenAI dashboard
- [ ] Create new API key named: `cortana-openai`
- [ ] Document key location (password manager?)
- [ ] Set usage limits if possible

#### 2. Create Cortana's Own .env File
- [ ] Create `/Users/eriksjaastad/projects/Cortana personal AI/.env`
- [ ] Add to `.gitignore` (verify not committed)
- [ ] Format:
  ```bash
  OPENAI_API_KEY=sk-...cortana-key-here...
  ```

#### 3. Update Cortana Scripts
**Files to update:**
- [ ] `scripts/automation/run_daily_update.sh`
  - Change: `export $(grep -v '^#' /Users/eriksjaastad/projects/agent_os/.env | xargs)`
  - To: `export $(grep -v '^#' "$(dirname "$0")/../../.env" | xargs)`

- [ ] Update `README.md` instructions
  - Remove references to agent_os/.env
  - Document local .env usage

- [ ] Update `CLAUDE.md` examples
  - Remove agent_os/.env references
  - Show local .env pattern

#### 4. Test Cortana with New Key
- [ ] Run manually: `python scripts/core/daily_update.py`
- [ ] Verify it uses new key (check OpenAI dashboard usage)
- [ ] Test launchd automation (wait for 10pm or trigger manually)
- [ ] Verify costs appear under `cortana-openai` key

#### 5. Remove Keys from agent_os/.env
- [ ] **ONLY AFTER** Cortana migration confirmed working
- [ ] Remove OPENAI_API_KEY from agent_os/.env
- [ ] Add comment: "Projects should use their own .env files"
- [ ] Document what agent_os/.env SHOULD contain (if anything)

---

## Phase 2: Define Agent OS Purpose (After Migration)

### Questions to Answer

#### Q1: Hosting
- **Where is agent_os currently hosted?** (Check if it's on Railway or local)
- **Should it be hosted?** (For 24/7 orchestration, yes)
- **What does it currently do?** (Audit agent_os codebase)

**Action:**
- [ ] Check agent_os deployment status
- [ ] Document current capabilities
- [ ] List existing plugins/tasks

---

#### Q2: Webhooks
**Question:** Should agent_os be centralized webhook handler?

**Current usage:**
- Trading Projects: Discord webhook (in Trading's own .env)

**Options:**

**Option A: Centralized Webhook Handler**
- ✅ One place to manage all webhooks
- ✅ Can fan-out (one event → multiple webhooks)
- ✅ Monitoring (see all webhook calls in one place)
- ❌ Projects depend on agent_os being up
- ❌ Another central dependency

**Option B: Per-Project Webhooks**
- ✅ Projects are independent
- ✅ Failure in one doesn't affect others
- ✅ Simpler (each project knows its webhooks)
- ❌ No central monitoring
- ❌ Duplicate webhook logic

**Erik's Decision Needed:**
- [ ] Decide: Centralized webhooks or per-project?
- [ ] **If centralized:** Define webhook routing pattern
- [ ] **If per-project:** Document pattern in scaffolding templates

**My recommendation:** Per-project webhooks, but agent_os can *aggregate notifications* (projects send to agent_os, which fans out to Discord/Slack/etc.). This keeps projects independent but gives you central monitoring.

---

#### Q3: Scheduling Patterns
**Current state:**
- Trading: Railway cron (4x daily + weekly/monthly)
- Cortana: launchd (daily at 10pm)
- image-workflow: Manual + local cron (backups)

**Options:**

**Option A: All Scheduling Through Agent OS**
- ✅ One dashboard to see all schedules
- ✅ Can coordinate (don't run two API-heavy jobs at once)
- ❌ Agent OS becomes critical infrastructure
- ❌ Projects lose independence

**Option B: Projects Handle Own Scheduling**
- ✅ Projects are independent
- ✅ No central point of failure
- ❌ No visibility across projects
- ❌ Can't coordinate resource usage

**Option C: Hybrid (Recommended)**
- Projects handle their own critical schedules
- Agent OS *monitors* and can trigger additional workflows
- Agent OS dashboard shows all schedules (even if not controlling them)
- Agent OS handles cross-project orchestration only

**Erik's Decision Needed:**
- [ ] Decide: Scheduling approach
- [ ] Document pattern in Agent OS roadmap

---

### Tasks to Define Agent OS

- [ ] **Audit agent_os codebase**
  - What does it currently do?
  - What plugins exist?
  - What database schema?
  - What's in agent_os/.env besides API keys?

- [ ] **Create AGENT_OS_ARCHITECTURE.md**
  - Document orchestration model
  - Plugin architecture
  - Webhook strategy (centralized or per-project)
  - Scheduling strategy (centralized, per-project, or hybrid)

- [ ] **Pull out automation tasks from projects**
  - Trading: What could be orchestrated via agent_os?
  - Cortana: What workflows could trigger other projects?
  - image-workflow: Backup coordination with other projects?

- [ ] **Define plugin interface**
  ```python
  class ProjectPlugin:
      def get_status() -> dict
      def report_cost() -> float
      def run_task(task_name: str) -> result
      def get_schedule() -> list[Schedule]
  ```

---

## Phase 3: Project Scaffolding Updates

### Add to Templates

- [ ] **Create .env.example template**
  ```bash
  # .env.example - Copy to .env and fill in values
  
  # API Keys (get from service dashboards)
  OPENAI_API_KEY=sk-...
  ANTHROPIC_API_KEY=sk-ant-...
  
  # Service URLs
  WEBHOOK_URL=https://...
  
  # Project Config
  PROJECT_NAME=my-project
  ```

- [ ] **Update CLAUDE.md.template**
  - Add section: "API Key Management"
  - Naming convention: `{project}-{service}`
  - Never share keys across projects
  - Document .env location

- [ ] **Update .cursorrules.template**
  - Add: "Use project's own .env file, never shared keys"
  - Add: "Update EXTERNAL_RESOURCES.md when adding services"

- [ ] **Create API_KEY_GUIDE.md in patterns/**
  - Why separate keys per project
  - Naming conventions
  - Security best practices
  - When shared keys make sense (rarely)

---

## Phase 4: EXTERNAL_RESOURCES.md Updates

- [ ] **Add API key location tracking**
  ```markdown
  ### OpenAI API
  **Keys:**
  - Trading Projects: .env (key: trading-openai)
  - Cortana: .env (key: cortana-openai)  
  - image-workflow: .env (key: image-workflow-openai)
  
  **Never use:** Shared key across projects
  ```

- [ ] **Document naming convention**
  - Format: `{project-name}-{service}`
  - Examples throughout

- [ ] **Add "API Key Management" section**
  - Link to patterns/API_KEY_GUIDE.md
  - Quick reference

---

## Phase 5: Agent OS Implementation Roadmap

**After architecture is defined:**

### Milestone 1: Monitoring Dashboard
- [ ] Create dashboard showing all project statuses
- [ ] Aggregate costs from all projects
- [ ] Show last run time for all scheduled tasks
- [ ] Alert on failures

### Milestone 2: Plugin System
- [ ] Define plugin interface
- [ ] Convert one project (Trading?) to plugin
- [ ] Test plugin registration/execution

### Milestone 3: Cross-Project Workflows
- [ ] Define workflow DSL (YAML? Python?)
- [ ] Implement workflow engine
- [ ] Create first cross-project workflow

### Milestone 4: Self-Hosted Orchestration
- [ ] Deploy agent_os to Railway (if not already)
- [ ] Migrate schedules (gradually)
- [ ] Monitor and iterate

---

## Open Questions for Erik

1. **Webhooks:** Centralized in agent_os or per-project?
   - My vote: Per-project, agent_os aggregates

2. **Scheduling:** All through agent_os or hybrid?
   - My vote: Hybrid (projects own critical tasks, agent_os orchestrates extras)

3. **Agent_os hosting:** Is it already hosted? Where?
   - Need to check current deployment

4. **Agent_os capabilities:** What does it currently do?
   - Need to audit codebase

5. **Agent_os name:** Keep "Agent OS" or rename?
   - Your decision: Keep it! ✅

---

## Success Criteria

**Phase 1 Complete When:**
- ✅ Cortana uses its own .env file
- ✅ Cortana API key is separate (`cortana-openai`)
- ✅ agent_os/.env has no shared API keys
- ✅ All projects have per-project keys documented in EXTERNAL_RESOURCES.md

**Phase 2 Complete When:**
- ✅ Agent_os purpose clearly defined in AGENT_OS_ARCHITECTURE.md
- ✅ Webhook strategy decided and documented
- ✅ Scheduling strategy decided and documented
- ✅ Plugin interface defined

**Phase 3 Complete When:**
- ✅ Templates updated with API key patterns
- ✅ API_KEY_GUIDE.md created
- ✅ Future projects follow the pattern automatically

**Phase 4 Complete When:**
- ✅ EXTERNAL_RESOURCES.md tracks key locations
- ✅ Naming convention documented
- ✅ Clear guidance on key management

**Phase 5 Complete When:**
- ✅ Agent OS is useful orchestration engine
- ✅ Projects can trigger each other
- ✅ Central dashboard shows everything
- ✅ Actually making your life easier (not just theoretical)

---

## Timeline Estimate

- **Phase 1 (Migration):** 1-2 hours (this weekend)
- **Phase 2 (Definition):** 2-4 hours (next week)
- **Phase 3 (Templates):** 1-2 hours (next week)
- **Phase 4 (Documentation):** 1 hour (next week)
- **Phase 5 (Implementation):** Ongoing (months)

---

## Next Immediate Steps

1. Start Phase 1, Task 1: Create `cortana-openai` API key
2. Answer open questions (webhooks, scheduling, hosting)
3. Audit agent_os codebase to see what it currently does

---

*This document replaces fragile todo lists. Update as you progress.*

**Last updated:** December 21, 2025


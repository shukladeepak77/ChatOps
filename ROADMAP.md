# ChatOps Console — Product Roadmap

**Vision:** A chat-first, self-hosted operations console that helps Enterprise Cloud, Networking, and Telecom/ISP companies reduce L1/L2 support costs by automating routine diagnostics, alerts, and remediation.

**Target Customers:**
- Cloud Infrastructure / Data Centre operators
- Enterprise Networking teams (SD-WAN, campus, DC fabric)
- Telecom / ISP / Mobile Service Providers (NOC teams)

**Competitive Angle:** Simpler to deploy than PagerDuty/OpsRamp, affordable for mid-market, chat-first UX that L1 agents can use without training.

---

## Current State (v0.1 — Prototype, May 2026)

| Area | Status |
|---|---|
| Chat-driven CLI interface | Done |
| System metrics (CPU / Memory / Disk / Uptime) | Done |
| Multi-node SSH monitoring | Done |
| Threshold-based alerts | Done |
| Slack notifications + suppression | Done |
| Service management (status / restart) | Done |
| Network diagnostics (IP / routes / DNS / connections) | Done |
| Log analysis (inline + file upload) | Done |
| Runbooks (built-in: clear_tmp, restart_nginx, rotate_logs, kill_zombie) | Done |
| Daily health report (per-node, HTML + Slack) | Done |
| SQLite metrics history | Done |
| Configuration via chat + UI | Done |
| Help tab + command reference | Done |
| Pytest suite (135 tests) | Done |

---

## Phase 1 — Sellable Prototype (Target: 8 weeks)

**Goal:** Add the minimum enterprise features needed to demo to a pilot customer and collect feedback.

### 1.1 Authentication & Roles
- [ ] Login page (username + password, bcrypt hashed)
- [ ] Three roles: `viewer` (read-only), `operator` (run commands), `admin` (config + users)
- [ ] Session tokens (JWT, 8-hour expiry)
- [ ] User management via chat: `add user`, `list users`, `remove user`, `set role`
- [ ] Lock down all API endpoints behind role checks

### 1.2 Audit Trail
- [ ] Log every chat command with: timestamp, user, command, result summary, node
- [ ] New DB table: `audit_log`
- [ ] Chat command: `show audit log` (last N entries, filterable by user/node/date)
- [ ] API endpoint: `GET /chatops/audit?user=&node=&date=`
- [ ] Export audit log as CSV

### 1.3 Ticketing Integration (Jira)
- [ ] Config: `config set jira_url`, `config set jira_token`, `config set jira_project`
- [ ] Auto-create Jira ticket on CRITICAL alert (with node, metric, timestamp, threshold)
- [ ] Chat: `create ticket <summary>` — manual ticket creation from chat
- [ ] Chat: `show tickets` — list open tickets via Jira API
- [ ] Link alert row to Jira ticket ID in DB

### 1.4 SNMP Polling (Network Devices)
- [ ] Add node type: `snmp` alongside existing `ssh`
- [ ] Chat: `add snmp node <name> <ip> <community>` (SNMPv2c to start)
- [ ] Poll OIDs: interface up/down, ifInErrors, ifOutErrors, ifInOctets, ifOutOctets, sysUpTime
- [ ] Alert on interface down or error rate threshold breach
- [ ] Show SNMP metrics in per-node config and report
- [ ] Dependency: `pysnmp` or `easysnmp`

### 1.5 Escalation Workflow (L1 → L2)
- [ ] Runbook result tracked: `pass` / `fail` / `skipped`
- [ ] On runbook failure: auto-escalate — post to a separate Slack channel (#l2-escalations) with full context
- [ ] Config: `config set escalation_channel <slack_webhook_url>`
- [ ] Chat: `escalate <note>` — manual escalation with typed context
- [ ] Escalation history viewable: `show escalations`

### 1.6 Docker Packaging
- [ ] `Dockerfile` (Python 3.12-slim, uvicorn, non-root user)
- [ ] `docker-compose.yml` (app + optional nginx reverse proxy)
- [ ] `docker-compose.override.yml` for dev (hot reload)
- [ ] Persistent volume for `chatops.db` and `chatops_config.json`
- [ ] Health check endpoint: `GET /healthz`
- [ ] `README.md` with quick-start (3 commands to running)

---

## Phase 2 — Pilot-Ready (Target: 3–4 months after Phase 1)

**Goal:** Deployable at a pilot customer site, multi-operator, integrated with their NOC workflow.

### 2.1 Multi-Tenant Support
- [ ] Tenant model: each tenant has isolated nodes, alerts, metrics, runbooks, users
- [ ] Tenant admin role can manage their own users/nodes
- [ ] Super-admin role for platform operator
- [ ] Tenant-scoped API keys for programmatic access

### 2.2 Runbook Editor (UI)
- [ ] UI tab: Runbooks — list, view, create, edit, delete
- [ ] Runbook definition: name, description, steps (ordered list of shell commands)
- [ ] Step-level output capture and display in chat
- [ ] Runbook version history (keep last 5)
- [ ] Import/export runbooks as JSON

### 2.3 Incident Management
- [ ] Incident lifecycle: Open → Acknowledged → Resolved
- [ ] Auto-open incident on CRITICAL alert
- [ ] Chat: `show incidents`, `ack incident <id>`, `resolve incident <id> <rca>`
- [ ] Incident timeline: events (alert fired, runbook ran, escalated, resolved) ordered by time
- [ ] MTTR / MTTD metrics per node and overall in daily report
- [ ] ServiceNow integration (alongside Jira)

### 2.4 RCA Assistant
- [ ] Correlate alerts fired within a time window across nodes — surface likely root cause
- [ ] Pattern library: known failure signatures (e.g. disk full → log rotation not running)
- [ ] Suggest runbook when pattern matches
- [ ] Chat: `diagnose <node>` — runs all checks and summarises with suggested action

### 2.5 Extended Protocol Support
- [ ] NetConf/YANG (Cisco IOS-XE, Juniper Junos) for config-level monitoring
- [ ] gRPC/gNMI streaming telemetry (modern routers, Nokia SR-OS, Arista EOS)
- [ ] Syslog receiver: ingest syslog from network devices, run log analysis pipeline
- [ ] Trap receiver: SNMP traps → alerts

### 2.6 REST API & Webhooks
- [ ] Full documented REST API (OpenAPI / Swagger UI at `/docs`)
- [ ] Inbound webhook: external systems can post alerts into ChatOps
- [ ] Outbound webhook: send alert/incident events to any HTTP endpoint
- [ ] API key management: `create api key`, `revoke api key`

---

## Phase 3 — Production Grade (Target: 6–9 months after Phase 2)

**Goal:** Enterprise-hardened, scalable, white-labelable, cloud-native deployment.

### 3.1 Infrastructure & Scalability
- [ ] Migrate from SQLite → PostgreSQL
- [ ] Async background workers (Celery or ARQ) for polling and notifications
- [ ] Redis for session store and pub/sub (real-time chat over WebSocket)
- [ ] Kubernetes Helm chart with HPA
- [ ] Multi-region: primary + standby DB replication

### 3.2 Authentication & SSO
- [ ] SAML 2.0 / OIDC (Okta, Azure AD, Google Workspace)
- [ ] MFA (TOTP)
- [ ] LDAP / Active Directory sync for users and groups
- [ ] Session audit and forced logout

### 3.3 LLM-Powered Diagnostics
- [ ] Natural language RCA: feed alert + metrics context to Claude/GPT, get plain-English diagnosis
- [ ] Auto-generate runbook suggestions from incident history
- [ ] Chat understanding: full NL understanding of any ops question, not just keyword patterns
- [ ] Configurable: customer can bring their own LLM API key (Claude, GPT-4, local model)

### 3.4 Telecom / 5G Specific
- [ ] KPIs: call drop rate, handover success rate, RAN node availability, backhaul latency
- [ ] Integration with OSS/BSS systems (IBM Netcool, HP NNMi, Huawei iMaster NCE)
- [ ] Alarm correlation across RAN / Core / Transport layers
- [ ] SLA breach prediction and proactive alert before breach

### 3.5 White-Label & Marketplace
- [ ] Configurable branding (logo, colours, product name) per tenant
- [ ] Plugin SDK: customers/partners can add custom actions, node types, runbooks
- [ ] Marketplace: community runbook library, integration plugins
- [ ] Managed SaaS offering (in addition to self-hosted)

### 3.6 Compliance & Security
- [ ] SOC 2 Type II controls mapped to features
- [ ] Data residency controls (on-prem, specific cloud region)
- [ ] Secrets vault integration (HashiCorp Vault, AWS Secrets Manager) — no plaintext credentials
- [ ] Full TLS termination, mTLS between components
- [ ] Penetration testing and CVE response process

---

## Metrics for Success

| Phase | KPI |
|---|---|
| Phase 1 | 2 pilot customers onboarded, demo-ready in under 30 min |
| Phase 2 | Pilot customers in production, measurable L1 ticket deflection (target 30%) |
| Phase 3 | Paying enterprise contracts, < 5 min MTTD on CRITICAL alerts |

---

## Next Immediate Steps (this sprint)

1. **Auth + Roles** — login page, JWT, role-gated endpoints (Phase 1.1)
2. **Audit Trail** — `audit_log` table, chat command, API endpoint (Phase 1.2)
3. **Docker packaging** — `Dockerfile` + `docker-compose.yml` (Phase 1.6)
4. **SNMP node support** — add snmp node type, poll basic OIDs (Phase 1.4)

---

*Document created: 2026-05-04 | Owner: Deepak Shukla*

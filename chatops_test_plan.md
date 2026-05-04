# ChatOps Test Plan

## Overview

| Category | File | Count |
|----------|------|-------|
| Actions Layer | `test_chatops_actions.py` | 23 |
| Router Layer | `test_chatops_router.py` | 25 |
| Database Layer | `test_chatops_db.py` | 14 |
| Config Layer | `test_chatops_config.py` | 6 |
| Runbooks Layer | `test_chatops_runbooks.py` | 9 |
| API Endpoints | `test_chatops_api.py` | 20 |
| **Total** | | **97** |

---

## 1. Actions Layer — `test_chatops_actions.py`

Unit tests for system metric functions in `chatops/actions.py`.

| ID | Test Name | Input | Expected |
|----|-----------|-------|----------|
| A1 | `test_check_disk_returns_keys` | `check_disk()` | Dict has `total_gb`, `used_gb`, `free_gb`, `percent_used` |
| A2 | `test_check_disk_percent_range` | `check_disk()` | `percent_used` is between 0 and 100 |
| A3 | `test_check_memory_returns_keys` | `check_memory()` | Dict has `total_mb`, `used_mb`, `available_mb`, `percent_used` |
| A4 | `test_check_memory_percent_range` | `check_memory()` | `percent_used` is between 0 and 100 |
| A5 | `test_check_cpu_returns_keys` | `check_cpu()` | Dict has `percent_used`, `cpu_count` |
| A6 | `test_check_cpu_percent_range` | `check_cpu()` | `percent_used` is between 0 and 100 |
| A7 | `test_check_cpu_count_positive` | `check_cpu()` | `cpu_count` >= 1 |
| A8 | `test_check_processes_returns_list` | `check_processes()` | Returns a list |
| A9 | `test_check_processes_has_fields` | `check_processes()` | Each entry has `pid`, `name`, `cpu_pct`, `mem_pct` |
| A10 | `test_check_processes_limit` | `check_processes(n=3)` | Returns at most 3 entries |
| A11 | `test_check_uptime_returns_keys` | `check_uptime()` | Dict has `uptime_days`, `uptime_hours`, `uptime_minutes` |
| A12 | `test_check_uptime_values_non_negative` | `check_uptime()` | All values >= 0 |
| A13 | `test_check_ports_returns_list` | `check_ports()` | Returns a list |
| A14 | `test_alert_status_ok` | `alert_status(50)` | Returns `"OK"` |
| A15 | `test_alert_status_warning` | `alert_status(82)` | Returns `"WARNING"` |
| A16 | `test_alert_status_critical` | `alert_status(92)` | Returns `"CRITICAL"` |
| A17 | `test_alert_status_custom_thresholds` | `alert_status(75, warning=70, critical=90)` | Returns `"WARNING"` |
| A18 | `test_analyze_logs_high_severity` | Log with 4+ ERRORs | `severity == "HIGH"` |
| A19 | `test_analyze_logs_medium_severity` | Log with WARNINGs only | `severity == "MEDIUM"` |
| A20 | `test_analyze_logs_low_severity` | Log with no errors/warnings | `severity == "LOW"` |
| A21 | `test_analyze_logs_db_root_cause` | Log containing "DB" | `root_cause` contains "Database" |
| A22 | `test_analyze_logs_timeout_root_cause` | Log containing "TIMEOUT" | `root_cause` contains "timeout" |
| A23 | `test_analyze_logs_auth_root_cause` | Log containing "AUTH" | `root_cause` contains "Authentication" |

---

## 2. Router Layer — `test_chatops_router.py`

NLP routing and response content validation in `chatops/router.py`.

| ID | Test Name | Input Message | Expected Response Contains |
|----|-----------|---------------|---------------------------|
| R1 | `test_route_disk_exact` | `"check disk"` | `"Disk"` |
| R2 | `test_route_disk_natural` | `"how full is my disk"` | `"Disk"` |
| R3 | `test_route_memory_exact` | `"check memory"` | `"Memory"` |
| R4 | `test_route_memory_natural` | `"how much ram am i using"` | `"Memory"` |
| R5 | `test_route_cpu_exact` | `"check cpu"` | `"CPU"` |
| R6 | `test_route_cpu_natural` | `"whats my cpu load"` | `"CPU"` |
| R7 | `test_route_uptime_exact` | `"check uptime"` | `"Uptime"` |
| R8 | `test_route_uptime_natural` | `"how long has the server been up"` | `"Uptime"` |
| R9 | `test_route_ports` | `"what ports are open"` | `"ports"` |
| R10 | `test_route_processes_exact` | `"top processes"` | `"processes"` |
| R11 | `test_route_processes_natural` | `"what processes are hogging memory"` | `"processes"` |
| R12 | `test_route_health_summary` | `"system health"` | `"overall_status"` key in response dict |
| R13 | `test_route_health_has_all_metrics` | `"system health"` | Response text contains Disk, Memory, CPU, Uptime |
| R14 | `test_route_alerts` | `"show alerts"` | `"alert"` |
| R15 | `test_route_runbooks_list` | `"list runbooks"` | `"run "` (runbook names) |
| R16 | `test_route_config` | `"config"` | `"disk_warning"` or threshold key |
| R17 | `test_route_inline_log_analysis` | `"analyze logs: ERROR db fail"` | `"Severity"` |
| R18 | `test_route_runbook_run_request` | `"run clear_tmp"` | `"confirm"` |
| R19 | `test_route_runbook_confirm_without_run` | `"confirm clear_tmp"` (no prior run) | Error message |
| R20 | `test_route_runbook_cancel` | `"run clear_tmp"` then `"cancel"` | `"Cancelled"` |
| R21 | `test_route_unknown_message` | `"xyzzy nonsense blah"` | Fallback / "didn't understand" |
| R22 | `test_route_empty_message` | `""` | Help text |
| R23 | `test_route_help` | `"help"` | Lists available commands |
| R24 | `test_route_case_insensitive` | `"CHECK DISK"` | Same result as `"check disk"` |
| R25 | `test_route_punctuation_stripped` | `"check disk!"` | Same result as `"check disk"` |

---

## 3. Database Layer — `test_chatops_db.py`

SQLite CRUD operations in `chatops/db.py`. Each test uses a temporary isolated DB.

| ID | Test Name | Operation | Expected |
|----|-----------|-----------|----------|
| D1 | `test_init_db_creates_tables` | `init_db()` | No error; all 3 tables exist |
| D2 | `test_save_and_get_history` | `save_message` → `get_history` | Saved messages appear in result |
| D3 | `test_history_order` | Save 3 messages → `get_history` | Returned in chronological order |
| D4 | `test_history_limit` | Save 10 messages → `get_history(limit=3)` | Returns exactly 3 |
| D5 | `test_clear_history` | `save_message` → `clear_history` → `get_history` | Returns empty list |
| D6 | `test_add_and_get_alerts` | `add_alert` → `get_alerts` | Alert appears in result |
| D7 | `test_alert_fields` | `add_alert` → `get_alerts` | Each row has `id`, `message`, `severity`, `timestamp`, `acked` |
| D8 | `test_ack_alert` | `add_alert` → `ack_alert` → `get_alerts` | `acked == 1` and `acked_at` is set |
| D9 | `test_unacked_count` | Add 2 alerts → ack 1 → `unacked_count` | Returns 1 |
| D10 | `test_get_alerts_unacked_only` | Add acked + unacked → `get_alerts(unacked_only=True)` | Only unacked returned |
| D11 | `test_add_and_get_metrics` | `add_metric` → `get_metric_history` | Saved value appears |
| D12 | `test_metrics_filter_by_name` | Add disk + cpu metrics → `get_metric_history("cpu")` | Only cpu rows returned |
| D13 | `test_metrics_limit` | Add 10 metrics → `get_metric_history(limit=3)` | Returns exactly 3 |
| D14 | `test_metrics_chronological_order` | Add 3 metrics → `get_metric_history` | Oldest record is first |

---

## 4. Config Layer — `test_chatops_config.py`

Threshold configuration in `chatops/config.py`. Each test uses a temporary config file.

| ID | Test Name | Operation | Expected |
|----|-----------|-----------|----------|
| C1 | `test_load_config_defaults` | `load_config()` with no file | Returns all 7 keys with default values |
| C2 | `test_save_and_reload_config` | `save_config({"disk_warning": 75})` → `load_config()` | `disk_warning == 75` |
| C3 | `test_save_config_merges_defaults` | `save_config({"disk_warning": 75})` → `load_config()` | Other keys remain at defaults |
| C4 | `test_alert_status_from_config_ok` | `alert_status_from_config(50, "disk")` | Returns `"OK"` |
| C5 | `test_alert_status_from_config_warning` | `alert_status_from_config(85, "disk")` | Returns `"WARNING"` |
| C6 | `test_alert_status_from_config_critical` | `alert_status_from_config(95, "disk")` | Returns `"CRITICAL"` |

---

## 5. Runbooks Layer — `test_chatops_runbooks.py`

Runbook listing and execution flow in `chatops/runbooks.py`.

| ID | Test Name | Operation | Expected |
|----|-----------|-----------|----------|
| RB1 | `test_list_runbooks_returns_all` | `list_runbooks()` | Returns 4 entries |
| RB2 | `test_list_runbooks_has_fields` | `list_runbooks()` | Each entry has `name`, `description`, `preview` |
| RB3 | `test_request_unknown_runbook` | `request_runbook("nonexistent")` | `status == "error"`, message lists available runbooks |
| RB4 | `test_request_valid_runbook` | `request_runbook("clear_tmp")` | `status == "confirm"`, message contains "confirm clear_tmp" |
| RB5 | `test_confirm_without_request` | `confirm_runbook("clear_tmp")` (no prior request) | `status == "error"` |
| RB6 | `test_confirm_wrong_name` | `request_runbook("clear_tmp")` → `confirm_runbook("large_logs")` | `status == "error"` |
| RB7 | `test_cancel_clears_pending` | `request_runbook` → `cancel_runbook` → `confirm_runbook` | confirm returns `status == "error"` |
| RB8 | `test_request_then_confirm_executes` | `request_runbook("listening_services")` → `confirm_runbook("listening_services")` | `status == "ok"` |
| RB9 | `test_confirm_returns_output` | Full request → confirm flow | `output` is a non-empty string |

---

## 6. API Endpoints — `test_chatops_api.py`

Integration tests via FastAPI `TestClient`.

| ID | Test Name | Method + Endpoint | Expected |
|----|-----------|-------------------|----------|
| E1 | `test_chatops_page_loads` | GET `/chatops` | 200, body contains "ChatOps Console" |
| E2 | `test_message_disk` | POST `/chatops/message` `{"message":"check disk"}` | 200, response contains "Disk" |
| E3 | `test_message_memory` | POST `/chatops/message` `{"message":"check memory"}` | 200, response contains "Memory" |
| E4 | `test_message_cpu` | POST `/chatops/message` `{"message":"check cpu"}` | 200, response contains "CPU" |
| E5 | `test_message_health` | POST `/chatops/message` `{"message":"system health"}` | 200, `overall_status` key present |
| E6 | `test_message_processes` | POST `/chatops/message` `{"message":"top processes"}` | 200, response contains "process" |
| E7 | `test_message_unknown` | POST `/chatops/message` `{"message":"xyzzy blah"}` | 200, graceful fallback message |
| E8 | `test_history_get` | GET `/chatops/history` | 200, `history` key is a list |
| E9 | `test_history_persists_messages` | POST message → GET `/chatops/history` | Message appears in history list |
| E10 | `test_history_clear` | DELETE `/chatops/history` → GET history | History is empty |
| E11 | `test_alerts_get` | GET `/chatops/alerts` | 200, has `alerts` list and `unacked_count` int |
| E12 | `test_alerts_ack` | POST `/chatops/alerts/{id}/ack` | 200, alert is marked acked in subsequent GET |
| E13 | `test_alerts_filter_unacked` | GET `/chatops/alerts?unacked_only=true` | Only alerts with `acked == 0` returned |
| E14 | `test_metrics_history_disk` | GET `/chatops/metrics/history?metric=disk` | 200, `data` is a list |
| E15 | `test_metrics_history_memory` | GET `/chatops/metrics/history?metric=memory` | 200, `data` is a list |
| E16 | `test_metrics_history_cpu` | GET `/chatops/metrics/history?metric=cpu` | 200, `data` is a list |
| E17 | `test_config_get` | GET `/chatops/config` | 200, all 7 threshold keys present |
| E18 | `test_config_update` | PUT `/chatops/config` `{"disk_warning": 75}` | 200, subsequent GET returns `disk_warning == 75` |
| E19 | `test_config_partial_update` | PUT with one field only | Other fields remain at previous values |
| E20 | `test_runbooks_list` | GET `/chatops/runbooks` | 200, `runbooks` list has 4 entries with name/description/preview |

---

## 7. Network Actions — `test_chatops_actions.py` (new)

Unit tests for network monitoring functions added in Phase 2.

| ID | Test Name | Input | Expected |
|----|-----------|-------|----------|
| N1 | `test_check_ip_returns_list` | `check_ip()` | Returns a list |
| N2 | `test_check_ip_has_fields` | `check_ip()` | Each entry has `interface`, `state`, `addresses` |
| N3 | `test_check_routes_returns_list` | `check_routes()` | Returns a list of strings |
| N4 | `test_check_network_stats_returns_list` | `check_network_stats()` | Returns a list |
| N5 | `test_check_network_stats_has_fields` | `check_network_stats()` | Each entry has `interface`, `bytes_sent_mb`, `bytes_recv_mb`, `errors_in`, `errors_out` |
| N6 | `test_check_dns_returns_keys` | `check_dns()` | Dict has `hostname`, `resolved_ip`, `latency_ms`, `status` |
| N7 | `test_check_dns_status_ok` | `check_dns("localhost")` | `status == "OK"` |
| N8 | `test_check_connections_returns_keys` | `check_connections()` | Dict has `total`, `by_state` |

---

## 8. Service Actions — `test_chatops_actions.py` (new)

| ID | Test Name | Input | Expected |
|----|-----------|-------|----------|
| S1 | `test_check_service_returns_keys` | `check_service("ssh")` | Dict has `name`, `active`, `state`, `sub_state` |
| S2 | `test_check_failed_services_returns_list` | `check_failed_services()` | Returns a list |

---

## 9. Node Registry — `test_chatops_nodes.py` (new)

Unit tests for `chatops/nodes.py` using a temporary JSON file.

| ID | Test Name | Operation | Expected |
|----|-----------|-----------|----------|
| ND1 | `test_add_node` | `add_node("web-01", "10.0.0.1", "ubuntu")` | Node appears in `list_nodes()` |
| ND2 | `test_list_nodes_empty` | `list_nodes()` with no file | Returns `{}` |
| ND3 | `test_list_nodes_returns_dict` | After `add_node` | Returns dict with node entry |
| ND4 | `test_get_node_existing` | `get_node("web-01")` after add | Returns dict with `host`, `user`, `key_path` |
| ND5 | `test_get_node_missing` | `get_node("nonexistent")` | Returns `None` |
| ND6 | `test_remove_node_existing` | `add_node` → `remove_node("web-01")` | Returns `True`, node gone from `list_nodes()` |
| ND7 | `test_remove_node_nonexistent` | `remove_node("ghost")` | Returns `False` |

---

## 10. Slack & Report Actions — `test_chatops_actions.py` (new)

| ID | Test Name | Input | Expected |
|----|-----------|-------|----------|
| SL1 | `test_notify_slack_invalid_url_returns_false` | `notify_slack("http://invalid", "cpu", "CRITICAL", 95.0)` | Returns `False` |
| RP1 | `test_generate_report_returns_keys` | `generate_report()` | Dict has `hostname`, `hours`, `generated_at`, `metrics`, `alerts` |
| RP2 | `test_generate_report_metrics_keys` | `generate_report()["metrics"]` | Has `disk`, `memory`, `cpu` keys |
| RP3 | `test_generate_report_alerts_keys` | `generate_report()["alerts"]` | Has `total`, `unacked` keys |
| RP4 | `test_format_report_text_contains_host` | `format_report_text(generate_report())` | String contains hostname |
| RP5 | `test_format_report_slack_contains_host` | `format_report_slack(generate_report())` | String contains hostname |

---

## 11. DB Report Functions — `test_chatops_db.py` (new)

| ID | Test Name | Operation | Expected |
|----|-----------|-----------|----------|
| DB-R1 | `test_get_metric_stats_no_data` | `get_metric_stats("disk", 24)` with empty DB | Returns dict with `samples == 0` and `avg == None` |
| DB-R2 | `test_get_alert_count_empty` | `get_alert_count(24)` with empty DB | Returns `{"total": 0, "unacked": 0}` |
| DB-R3 | `test_get_metric_stats_with_data` | `add_metric` → `get_metric_stats` | Returns correct avg/min/max |
| DB-R4 | `test_get_alert_count_with_data` | `add_alert` → `get_alert_count` | Returns correct total and unacked |

---

## 12. Router — New Routes — `test_chatops_router.py` (new)

| ID | Test Name | Input | Expected |
|----|-----------|-------|----------|
| R-N1 | `test_route_check_ip` | `"check ip"` | Response contains "interface" or "Network interfaces" |
| R-N2 | `test_route_check_routes` | `"check routes"` | Response contains "Routing table" or "route" |
| R-N3 | `test_route_check_network` | `"check network"` | Response contains "interface" or "Network interface stats" |
| R-N4 | `test_route_check_dns` | `"check dns"` | Response contains "DNS" and "status" |
| R-N5 | `test_route_check_connections` | `"check connections"` | Response contains "connections" |
| R-N6 | `test_route_service_status` | `"service status ssh"` | Response contains "Service:" |
| R-N7 | `test_route_restart_prompt` | `"restart ssh"` | Response contains "confirm restart" |
| R-N8 | `test_route_confirm_restart_without_request` | `"confirm restart nginx"` (no prior restart) | Response contains "No pending" |
| R-N9 | `test_route_check_failed_services` | `"check failed services"` | Response contains "failed" or "No failed" |
| R-N10 | `test_route_list_nodes_empty` | `"list nodes"` with no nodes | Response contains "No nodes registered" |
| R-N11 | `test_route_show_report` | `"show report"` | Response contains "Health Report" |
| R-N12 | `test_route_show_report_custom_hours` | `"show report 48h"` | Response contains "48h" |
| R-N13 | `test_route_report_toggle_on` | `"config set report on"` | Response contains "enabled" |
| R-N14 | `test_route_report_toggle_off` | `"config set report off"` | Response contains "disabled" |
| R-N15 | `test_route_report_hour` | `"config set report hour 9"` | Response contains "09:00" |

---

## 13. API Endpoints — New — `test_chatops_api.py` (new)

| ID | Test Name | Method + Endpoint | Expected |
|----|-----------|-------------------|----------|
| E-N1 | `test_report_endpoint` | GET `/chatops/report` | 200, has `hostname`, `metrics`, `alerts` keys |
| E-N2 | `test_report_endpoint_custom_hours` | GET `/chatops/report?hours=48` | 200, `hours == 48` |
| E-N3 | `test_config_includes_new_fields` | GET `/chatops/config` | Response has `slack_webhook`, `alert_suppress_minutes`, `report_enabled`, `report_hour` |

---

## Updated Overview

| Category | File | Original | New | Total |
|----------|------|----------|-----|-------|
| Actions Layer | `test_chatops_actions.py` | 23 | +15 | 38 |
| Router Layer | `test_chatops_router.py` | 25 | +15 | 40 |
| Database Layer | `test_chatops_db.py` | 14 | +4 | 18 |
| Config Layer | `test_chatops_config.py` | 6 | — | 6 |
| Runbooks Layer | `test_chatops_runbooks.py` | 9 | — | 9 |
| API Endpoints | `test_chatops_api.py` | 20 | +3 | 23 |
| Node Registry | `test_chatops_nodes.py` | — | +7 | 7 |
| **Total** | | **97** | **+44** | **141** |

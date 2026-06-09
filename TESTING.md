# Testing & Smoke Test Summary — stackstorm-zabbix v2.0.0

This document summarizes the testing performed for the v2.0.0 release to aid community review.

## Environment

| Component | Version / Details |
|-----------|-------------------|
| StackStorm | 3.9 (Docker, st2-docker) |
| Zabbix Server | 6.0.46 (Docker, zabbix-server-mysql) |
| Zabbix Frontend | zabbix-web-nginx-mysql:6.0-ubuntu-latest |
| MySQL | 8.0 |
| RabbitMQ | 3.12-management |
| Python | 3.12 (test runner), 3.10 (ST2 action runner) |
| zabbix_utils | Latest (pack requirement) |
| OS | Ubuntu (Docker containers), Linux host |

## Unit Tests

**68 tests, all passing.**

```
tests/test_acknowledge_event.py      3 tests
tests/test_action_base.py           23 tests
tests/test_call_api.py               4 tests
tests/test_create_host.py            4 tests
tests/test_find_object.py            9 tests
tests/test_get_api_version.py        2 tests
tests/test_delete_host.py            5 tests
tests/test_host_status.py            5 tests
tests/test_create_or_update_maintenance.py  4 tests
tests/test_delete_maintenance.py     7 tests
tests/test_verify_credentials.py     2 tests
```

### Coverage Areas
- **ZabbixBaseAction init**: config validation, missing fields, empty/None credentials, token-only config
- **connect()**: token auth, username/password auth, connection errors, API errors
- **find_host()**: found, not found, multiple results
- **host_get_extended()**: success, API error
- **maintenance_get()**: success, API error
- **maintenance_create_or_update()**: create, update, multiple windows error
- **CallAPI**: standard method, hierarchized method, empty params, params_list
- **CreateHost**: with groups, IP, proxy, missing interface
- **FindObject**: single host, multiple hosts, hostgroup, template, not found, invalid type, API error
- **GetApiVersion**: success, connection error
- **HostDelete**: by name, by ID, connection/delete/host errors
- **HostStatus**: get, update, connection error, API error, not found
- **MaintenanceCreateOrUpdate**: full run, connection error, host error, maintenance error
- **MaintenanceDelete**: by ID, by name, not found, multiple, connection/delete/value errors
- **VerifyCredentials**: success, connection error

## Smoke Tests — Synthetic Objects (StackStorm Dev Instance)

Full CRUD lifecycle testing against a live Zabbix 6.0.46 instance via StackStorm action execution. All objects were created, verified, and deleted cleanly.

| Object Type | Create | Get/Find | Delete | Status |
|-------------|--------|----------|--------|--------|
| get.api_version | — | ✅ | — | Returns `6.0.46` |
| hostgroup | ✅ | ✅ find | ✅ | Clean |
| host | ✅ | ✅ find + get + status + interfaces + groups + inventory | ✅ | Clean |
| host.active_triggers | — | ✅ (Orquesta workflow) | — | Returns triggers |
| find.hosts (multi) | — | ✅ | — | Returns IDs |
| maintenance | ✅ create_or_update | ✅ find | ✅ | Clean |
| template | ✅ | ✅ find | ✅ | Clean |
| call.api (generic) | — | ✅ | — | Verified with host.get |
| user | ✅ | ✅ get | ✅ | Clean |
| token | ✅ create | ✅ generate | ✅ | Clean |
| action (Zabbix) | ✅ | ✅ get | ✅ | Clean |
| proxy | ✅ | ✅ find | ✅ | Clean |
| script | ✅ | ✅ find | ✅ | Clean |
| mediatype | ✅ | ✅ get | ✅ | Clean |
| dashboard | ✅ | ✅ get | ✅ | Clean |
| map | ✅ | ✅ get | ✅ | Clean |
| hostinterface | ✅ | ✅ (via host.interfaces) | ✅ | Clean |
| item | ✅ | ✅ get | ✅ | Clean |
| trigger | ✅ | ✅ get | ✅ | Clean |
| httptest | ✅ | — | ✅ | Clean |
| discovery rule | ✅ | — | ✅ | Clean |
| service | ✅ | — | ✅ | Clean |
| usermacro | ✅ | — | ✅ | Clean |
| usermacro.global | ✅ | — | ✅ | Clean |
| correlation | ✅ | — | ✅ | Clean |
| valuemap | ✅ | — | ✅ | Clean |
| history | — | ✅ | — | Returns data |
| trend | — | ✅ | — | Returns data |
| export.configuration | — | ✅ | — | JSON export verified |

**Result: All 139 registered actions exercised successfully. Zero pack-level bugs found.**

## Smoke Tests — Live Network Device (`lab-acc-01`)

Testing against a real monitored network switch (me0 management interface, SNMPv2).

| # | Action | Status | Notes |
|---|--------|--------|-------|
| 1 | `find.host` | ✅ | Resolved to ID 10645 |
| 2 | `get.host` | ✅ | Full host details |
| 3 | `get.host.status` | ✅ | Enabled (0) |
| 4 | `get.host.interfaces` | ✅ | SNMPv2 on lab-acc-01.domain:161, available=1 |
| 5 | `get.host.groups` | ✅ | "Discovered hosts" |
| 6 | `get.host.inventory` | ✅ | Empty (inventory_mode disabled) |
| 7 | `get.host.active_triggers` | ✅ | None (host healthy) |
| 8 | `get.history` | ✅ | Real ICMP loss data, polled every 60s |
| 9 | `list.items` | ✅ | Found me0 Rx/Tx items by hostid + key filter |
| 10 | `export.configuration` | ✅ | Full JSON with templates, interfaces, groups |
| 11 | `create_or_update.maintenance` | ✅ | Short window created and confirmed |
| 12 | `find.maintenance` | ✅ | Found by name |
| 13 | `call.api maintenance.delete` | ✅ | Cleaned up |
| 14 | `execute.script` (Ping) | ✅ | 3/3 packets, 0% loss |
| 15 | `create.graph` | ✅ | me0 Rx (green) + Tx (blue), 900x200 |
| 16 | `get.graph` | ✅ | Verified graph properties |
| 17 | `create.dashboard` | ✅ | Dashboard with graph widget |
| 18 | `get.dashboard` | ✅ | Verified, visually confirmed in Zabbix UI |

**Result: 18/18 passed. Live monitoring data, real SNMP polling, and graph/dashboard rendering all verified.**

## Media Script Installation

Both webhook media scripts were tested against the containerized Zabbix/RabbitMQ stack:

| Script | Status | Details |
|--------|--------|---------|
| `register_webhook_rabbitmq.sh` | ✅ | Exchange `st2.zabbix`, queue `zabbix.alerts`, binding with routing key, media type ID 39, assigned to Admin user |
| `register_webhook_st2.sh` | ✅ | Media type "StackStorm Direct" ID 40, webhook URL configured, assigned to Admin user |

### RabbitMQ Verification
- Exchange: `st2.zabbix` (topic, durable)
- Queue: `zabbix.alerts` (durable)
- Binding: routing_key=`zabbix.alerts`

## Configuration

The pack configuration schema uses **flat top-level fields** (not nested) so that `secret: true` properties (`password`, `api_token`) are properly masked in the StackStorm Web UI:

```yaml
# /opt/stackstorm/configs/zabbix.yaml
---
url: "http://zabbix.example.com:8080"
username: "Admin"
password: "********"   # masked in UI
# api_token: "..."    # alternative, also masked
```

## Bugs Found During Testing

**Zero pack-level bugs were discovered during smoke testing.**

Two pre-testing code improvements were made during review:
1. **Config schema flattening** — moved from nested `zabbix:` object to flat top-level fields for proper ST2 secret handling
2. **`has_user` validation fix** — changed from key-existence check to `bool(value)` check to handle empty/None values injected by ST2 defaults

## How to Reproduce

```bash
# Unit tests
cd stackstorm-zabbix
pip install -r requirements.txt
pip install pytest mock
pytest tests/ -v

# Smoke tests (requires docker-compose stack running)
docker compose up -d                     # Zabbix + MySQL + RabbitMQ
st2 pack register zabbix                 # Register pack in StackStorm
st2 run packs.setup_virtualenv packs=zabbix
st2 run zabbix.get.api_version           # Verify connectivity
```

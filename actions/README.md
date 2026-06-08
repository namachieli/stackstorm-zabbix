# Actions Design Guide

This document defines the conventions and architecture for all actions in the Zabbix StackStorm pack. Follow these patterns when adding or modifying actions.

---

## Naming Convention

Actions use a dot-delimited `<verb>.<object>[.<qualifier>]` pattern.

### Verbs

| Verb | Meaning | Object Form |
|------|---------|-------------|
| `get` | Retrieve specific object(s) by ID | Singular |
| `list` | Enumerate/search with optional filters | Plural |
| `find` | Resolve a friendly name to an ID | Singular/Plural |
| `create` | Create a new object | Singular |
| `update` | Modify an existing object | Singular |
| `delete` | Remove an object | Singular |
| `acknowledge` | Acknowledge an event or problem | Singular |
| `execute` | Execute a script on a host | Singular |
| `export` | Export configuration data | Singular |
| `import` | Import configuration data | Singular |
| `generate` | Generate a value (e.g. API token) | Singular |
| `verify` | Test connectivity or credentials | Singular |

### Naming Rules

1. **Verb first**: `create.host`, never `host.create`
2. **Singular for single-object operations**: `get.host`, `create.trigger`
3. **Plural for list/search operations**: `list.hosts`, `list.triggers`
4. **No abbreviations**: `acknowledge` not `ack`, `configuration` not `config`
5. **Zabbix API class names as-is**: `hostgroup` (not `host_group`), `mediatype` (not `media_type`), `httptest` (not `http_test`)
6. **Qualifiers for sub-operations**: `get.host.interfaces`, `update.host.status`, `delete.host.by_id`
7. **Compound verbs allowed sparingly**: `create_or_update.maintenance`

### Objects

Match Zabbix API class names:

```
host, hostgroup, hostinterface, item, trigger, event, problem,
maintenance, template, proxy, usermacro, mediatype, action, alert,
user, usergroup, script, history, trend, service, sla, graph, map,
httptest, drule, dhost, dservice, valuemap, configuration,
correlation, token, dashboard, role
```

### get vs list vs find

| Verb | Purpose | Required Params | Returns |
|------|---------|-----------------|---------|
| `get` | Fetch full object details by ID | ID(s) required | Full object(s) |
| `list` | Search/enumerate with filters | All optional | Array of objects |
| `find` | Resolve friendly name → ID | Name required | ID string or array |

---

## Architecture

### DRY Strategy

The pack uses a minimal set of Python entry points. Most actions are **YAML-only** — they define parameters and point to a shared Python dispatcher.

```
actions/
├── lib/
│   ├── __init__.py
│   └── actions.py                      # ZabbixBaseAction base class
├── call_api.py                         # Generic API dispatcher (~130 actions use this)
├── find_object.py                      # Generic name→ID resolver (7 find actions)
├── acknowledge_event.py                # Event acknowledgement with close logic
├── create_host.py                      # Host creation with interface/proxy logic
├── host_delete.py                      # Host deletion by name or ID
├── host_status.py                      # Get/update host status by hostname
├── maintenance_create_or_update.py     # Timezone math + create-or-update logic
├── maintenance_delete.py               # Delete by name or ID resolution
├── get_api_version.py                  # API version check
├── verify_credentials.py              # Connection test
└── workflows/
    └── get.host.active_triggers.yaml   # Orquesta workflow
```

### When to Use Each Entry Point

| Entry Point | Use When |
|-------------|----------|
| `call_api.py` | Simple CRUD — parameters pass through directly to Zabbix API |
| `find_object.py` | Name-to-ID resolution for any object type |
| Dedicated Python | Pre/post-processing, name resolution before API call, complex parameter construction, multi-step logic |

### When a Dedicated Python File is Warranted

Create a new Python entry point **only** when:
- The action requires name→ID resolution before calling the API
- Complex parameter construction is needed (building nested objects, timezone math)
- Multi-step operations (create-or-update, find-then-delete)
- Custom validation beyond what YAML types provide
- The action combines multiple API calls in one logical operation

If the action just passes parameters through to a single Zabbix API method, use `call_api.py`.

---

## YAML Action Patterns

### Pattern 1: YAML-only via call_api.py (most common)

Used for simple CRUD operations that map directly to a Zabbix API method.

```yaml
---
name: list.hosts
pack: zabbix
runner_type: python-script
description: "List and search Zabbix hosts with optional filtering."
enabled: true
entry_point: call_api.py
parameters:
  api_method:
    default: "host.get"
    immutable: true
  filter:
    type: object
    description: "Filter conditions (e.g. {\"host\": \"myhost\"})."
    required: false
  output:
    type: array
    description: "Fields to return."
    required: false
  limit:
    type: integer
    description: "Maximum number of results."
    required: false
```

Key rules:
- `api_method` is always `immutable: true` with a `default` value
- All other parameters are optional (the Zabbix API defines its own required fields)
- Parameter names match the Zabbix API parameter names exactly
- Use `type: object` for complex filter/search params
- Use `type: array` for list params (IDs, output fields)

### Pattern 2: YAML-only via call_api.py (delete operations)

Delete methods in the Zabbix API take positional arguments (a list of IDs), not keyword arguments. Use `params_list` for these.

```yaml
---
name: delete.hostgroup
pack: zabbix
runner_type: python-script
description: "Delete Zabbix host groups by ID."
enabled: true
entry_point: call_api.py
parameters:
  api_method:
    default: "hostgroup.delete"
    immutable: true
  params_list:
    type: array
    description: "Array of host group IDs to delete."
    required: true
```

### Pattern 3: YAML-only via find_object.py

Used for the 7 find actions. The object-specific details are baked in as immutable defaults.

```yaml
---
name: find.host
pack: zabbix
runner_type: python-script
description: "Resolve a Zabbix hostname to its host ID."
enabled: true
entry_point: find_object.py
parameters:
  object_type:
    default: "host"
    immutable: true
  filter_field:
    default: "host"
    immutable: true
  id_field:
    default: "hostid"
    immutable: true
  allow_multiple:
    default: false
    immutable: true
  name:
    type: string
    description: "Hostname or technical name of the Zabbix host."
    required: true
```

### Pattern 4: Dedicated Python entry point

Used when logic goes beyond simple parameter passthrough.

```yaml
---
name: create.host
pack: zabbix
runner_type: python-script
description: "Create a new Zabbix host with interface configuration."
enabled: true
entry_point: create_host.py
parameters:
  name:
    type: string
    description: "Technical hostname to create."
    required: true
  groups:
    type: array
    description: "List of host group names to assign."
    required: true
```

### Pattern 5: Orquesta workflow

Used when an action chains multiple actions together (e.g. find host → query triggers).

```yaml
---
version: 1.0
description: List all active triggers for a given host

input:
  - hostname
  - priority

tasks:
  get_zabbix_id:
    action: zabbix.find.host
    input:
      name: "{{ ctx().hostname }}"
    next:
      - when: "{{ succeeded() }}"
        publish:
          - host_id: "{{ result().result }}"
        do:
          - get_triggers
```

---

## Python Conventions

### Base Class

All Python actions extend `ZabbixBaseAction` from `lib/actions.py`. The base class provides:

| Method | Purpose |
|--------|---------|
| `connect()` | Authenticate with Zabbix (token or user/pass) |
| `find_host(hostname)` | Resolve hostname → hostid, sets `self.zabbix_host` |
| `host_get_extended(host_ids, select_field, output_fields)` | Get host with extended data |
| `maintenance_get(name)` | Find maintenance by name |
| `maintenance_create_or_update(params)` | Upsert a maintenance window |

### Return Conventions

- **Success**: Return data directly. StackStorm wraps it as a successful result.
- **Failure**: Raise an exception. StackStorm catches it and marks the execution as failed.
- **Never** return `(False, ...)` tuples. Use exceptions for error flow.
- **Never** return `(True, ...)` tuples. Just return the data.

```python
# CORRECT
def run(self, hostname):
    self.connect()
    host_id = self.find_host(hostname)  # Raises ValueError if not found
    return host_id

# WRONG
def run(self, hostname):
    self.connect()
    try:
        host_id = self.find_host(hostname)
        return (True, host_id)
    except Exception as e:
        return (False, str(e))
```

### Error Handling

- Let exceptions propagate — the StackStorm runner handles reporting.
- Only catch and re-raise when adding meaningful context:

```python
try:
    self.client.host.delete(host_id)
except APIRequestError as e:
    raise APIRequestError("Failed to delete host: {0}".format(e))
```

- Never catch generic `Exception` to suppress errors.
- Use `ValueError` for validation failures (bad input, not found, ambiguous matches).
- Use `APIRequestError` pass-through for Zabbix API errors.

### Parameter Naming

| Name | Type | Meaning |
|------|------|---------|
| `hostname` | `string` | A Zabbix host's technical name (used for lookups) |
| `host_id` | `string` | A single Zabbix host ID |
| `host_ids` | `array` | Multiple Zabbix host IDs |
| `name` | `string` | Generic object name (used in find actions, create.host) |

Never use bare `host` — it's ambiguous between name and ID.

### Code Style

- No license headers on action files (pack-level `LICENSE` covers all)
- Single-line class docstring
- Multi-line docstring on `run()` method with Args section
- Import `APIRequestError` from `zabbix_utils.exceptions` only when catching it
- Use `self.connect()` as the first line of every `run()` method
- Use `None` default + conditional initialization for mutable defaults:

```python
def run(self, items=None):
    if items is None:
        items = []
```

---

## call_api.py Internals

The generic dispatcher handles two calling patterns:

1. **Keyword arguments** (get, create, update): Filters out `None` values and passes remaining params as `**kwargs`
2. **Positional arguments** (delete): When `params_list` is provided, passes as `*args`

```python
def run(self, api_method, params_list=None, **params):
    self.connect()
    if params_list is not None:
        method = self._resolve_method(self.client, api_method)
        return method(*params_list)
    filtered = {k: v for k, v in params.items() if v is not None}
    method = self._resolve_method(self.client, api_method)
    return method(**filtered)
```

The `None` filtering is critical — it allows YAML actions to declare many optional parameters without sending empty values to the Zabbix API (which would cause errors).

### Method Resolution

`_resolve_method()` walks a dotted path like `"host.get"` to resolve `self.client.host.get`. This means `api_method` values map exactly to `zabbix_utils` client attributes.

---

## find_object.py Internals

A generic resolver that handles all 7 find actions through immutable YAML parameters:

| find action | object_type | filter_field | id_field | allow_multiple |
|-------------|-------------|--------------|----------|----------------|
| `find.host` | `host` | `host` | `hostid` | `false` |
| `find.hosts` | `host` | `host` | `hostid` | `true` |
| `find.hostgroup` | `hostgroup` | `name` | `groupid` | `false` |
| `find.template` | `template` | `host` | `templateid` | `false` |
| `find.proxy` | `proxy` | `host` | `proxyid` | `false` |
| `find.maintenance` | `maintenance` | `name` | `maintenanceid` | `false` |
| `find.script` | `script` | `name` | `scriptid` | `false` |

When `allow_multiple=false`:
- Returns exactly one ID (string)
- Raises `ValueError` if zero or multiple matches found

When `allow_multiple=true`:
- Returns a list of IDs (may be empty)

---

## YAML File Standards

### Required Fields

Every action YAML must include:

```yaml
---
name: <verb>.<object>[.<qualifier>]
pack: zabbix
runner_type: python-script
description: "<Imperative sentence describing what the action does.>"
enabled: true
entry_point: <python_file.py>
parameters:
  ...
```

### Description Style

- Start with an imperative verb: "List...", "Create...", "Delete...", "Resolve..."
- End with a period
- Be specific: "Delete a Zabbix host by hostname." not "Deletes hosts."
- Include key constraints: "Returns exactly one ID or raises an error."

### Parameter Descriptions

- Start with a noun or qualifier: "Host IDs to retrieve.", "Filter conditions."
- Include examples for complex types: `"Filter conditions (e.g. {\"host\": \"myhost\"})."`
- Note valid values for enums: `"Type: 0 (text), 1 (secret), 2 (vault secret)."`
- Include format for strings: `"Start date/time in format 'Y-m-d H:M'."`

---

## Adding a New Action

### Simple API passthrough (most cases)

1. Identify the Zabbix API method (e.g. `template.get`)
2. Create a YAML file named `<verb>.<object>.yaml`
3. Set `entry_point: call_api.py`
4. Set `api_method` as immutable default matching the Zabbix API method
5. Add parameters matching the Zabbix API docs (use `params_list` for delete methods)
6. All parameters except `api_method` should be `required: false` unless essential for the action's contract

### Name resolution (find)

1. Create a YAML file named `find.<object>.yaml`
2. Set `entry_point: find_object.py`
3. Set `object_type`, `filter_field`, `id_field`, `allow_multiple` as immutable defaults
4. Expose only `name` as the user-facing parameter

### Complex logic

1. Determine if existing Python files can be reused (check if logic fits `call_api.py` with pre-processing)
2. If not, create a new Python file extending `ZabbixBaseAction`
3. Follow the return/error/style conventions above
4. Create the corresponding YAML action file

---

## Dependencies

- **Python library**: `zabbix-utils` 2.0.4+ (official Zabbix Python library)
- **API client pattern**: `self.client.<object>.<method>(**kwargs)`
- **Target Zabbix version**: 6.0 LTS
- **StackStorm runner**: `python-script`
- **Authentication**: Token-based (`api_token`) or credential-based (`username`/`password`), configured in `config.schema.yaml`

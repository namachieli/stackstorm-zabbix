# Zabbix Integration Pack for StackStorm

This pack provides integration with Zabbix 6.0+ for StackStorm 3.9+. It enables:

- **Receiving Zabbix alerts** as StackStorm triggers via native webhook media types
- **Querying Zabbix** for hosts, triggers, events, and inventory
- **Managing Zabbix** hosts, maintenance windows, and monitoring status

## Requirements

- Zabbix 6.0+
- StackStorm 3.9+
- Python 3

## Installation

```shell
st2 pack install zabbix
```

## Configuration

Configure the pack to authenticate with your Zabbix server:

```shell
st2 pack config zabbix
```

### Configuration Parameters

| Parameter | Description | Default | Required |
|:----------|:------------|:--------|:---------|
| `zabbix.url` | Zabbix frontend URL | `http://localhost:8080` | Yes |
| `zabbix.api_token` | Zabbix API token (preferred) | — | No* |
| `zabbix.username` | Zabbix username | `Admin` | No* |
| `zabbix.password` | Zabbix password | `zabbix` | No* |

\* Either `api_token` OR `username`/`password` must be provided.

### Example Configuration (`zabbix.yaml`)

```yaml
---
zabbix:
  url: "http://zabbix.example.com:8080"
  api_token: "your-api-token-here"
```

Or with username/password:

```yaml
---
zabbix:
  url: "http://zabbix.example.com:8080"
  username: "Admin"
  password: "zabbix"
```

## Webhook Setup

This pack uses native Zabbix webhook media types (type=4) to deliver alerts to StackStorm. Two delivery paths are available:

### Option A: Direct StackStorm Webhook (Recommended)

Zabbix posts alerts directly to the StackStorm API. Simplest setup, no additional dependencies.

```
Zabbix Alert → Webhook JS → StackStorm API → zabbix.event_handler trigger
```

**Setup:**

```shell
export ZABBIX_URL="http://localhost:8080"
export ZABBIX_API_TOKEN="your-zabbix-token"  # or use ZABBIX_USER/ZABBIX_PASSWORD
export ST2_API_URL="http://localhost:81"
export ST2_API_KEY="your-st2-api-key"

./scripts/register_webhook_st2.sh
```

### Option B: RabbitMQ Webhook

Zabbix publishes alerts to RabbitMQ via the Management HTTP API. Requires the `stackstorm-rabbitmq` pack to consume messages.

```
Zabbix Alert → Webhook JS → RabbitMQ Mgmt API → Exchange → Queue
                                                                ↓
                              stackstorm-rabbitmq sensor → rule → action
```

**Setup:**

```shell
export ZABBIX_URL="http://localhost:8080"
export ZABBIX_API_TOKEN="your-zabbix-token"
export RABBITMQ_URL="http://localhost:15672"
export RABBITMQ_USER="guest"
export RABBITMQ_PASSWORD="guest"

./scripts/register_webhook_rabbitmq.sh
```

**Additional requirements for RabbitMQ path:**

1. Install the RabbitMQ pack: `st2 pack install rabbitmq`
2. Configure the rabbitmq pack sensor to listen on queue `zabbix.alerts`
3. Write rules matching `rabbitmq.new_message` trigger

**Example rule for RabbitMQ consumption:**

```yaml
---
name: zabbix_high_severity_alert
pack: my_pack
trigger:
  type: rabbitmq.new_message
  parameters:
    queue: zabbix.alerts
criteria:
  trigger.body.payload.trigger_severity:
    type: equals
    pattern: "High"
action:
  ref: some_pack.remediate
  parameters:
    host: "{{ trigger.body.payload.host }}"
    event_id: "{{ trigger.body.payload.event_id }}"
```

### Registration Script Environment Variables

| Variable | Script | Description | Default |
|:---------|:-------|:------------|:--------|
| `ZABBIX_URL` | Both | Zabbix frontend URL | *required* |
| `ZABBIX_API_TOKEN` | Both | Zabbix API token (preferred) | — |
| `ZABBIX_USER` | Both | Zabbix username | `Admin` |
| `ZABBIX_PASSWORD` | Both | Zabbix password | `zabbix` |
| `ZABBIX_ADMIN_USER_ID` | Both | User ID to assign media to | `1` |
| `ST2_API_URL` | ST2 | StackStorm API URL | *required* |
| `ST2_API_KEY` | ST2 | StackStorm API key | *required* |
| `RABBITMQ_URL` | RabbitMQ | RabbitMQ Management API URL | *required* |
| `RABBITMQ_USER` | RabbitMQ | RabbitMQ username | `guest` |
| `RABBITMQ_PASSWORD` | RabbitMQ | RabbitMQ password | `guest` |
| `RABBITMQ_VHOST` | RabbitMQ | Virtual host | `/` |
| `RABBITMQ_EXCHANGE` | RabbitMQ | Exchange name | `st2.zabbix` |
| `RABBITMQ_ROUTING_KEY` | RabbitMQ | Routing key | `zabbix.alerts` |
| `RABBITMQ_QUEUE` | RabbitMQ | Queue name | `zabbix.alerts` |

## Triggers

### zabbix.event_handler

Dispatched when Zabbix sends an alert via the direct StackStorm webhook.

| Parameter | Description |
|:----------|:------------|
| `alert_sendto` | Recipient from Zabbix user media configuration |
| `alert_subject` | Alert subject from Zabbix action |
| `alert_message` | Alert message body (string or JSON object) |
| `host` | Host that triggered the event |
| `event_id` | Zabbix event ID |
| `trigger_id` | Zabbix trigger ID |
| `trigger_name` | Name of the Zabbix trigger |
| `trigger_status` | `PROBLEM` or `OK` |
| `trigger_severity` | Not classified, Information, Warning, Average, High, Disaster |
| `event_time` | Time the event occurred |
| `event_date` | Date the event occurred |

## Actions

| Action | Description |
|:-------|:------------|
| `zabbix.ack_event` | Send acknowledgement message for an event |
| `zabbix.call_api` | Call arbitrary Zabbix API method |
| `zabbix.create_host` | Create a new host in Zabbix |
| `zabbix.get_api_version` | Get Zabbix API version (connectivity test) |
| `zabbix.host_delete` | Delete a Zabbix host by name |
| `zabbix.host_delete_by_id` | Delete a Zabbix host by ID |
| `zabbix.host_get_active_triggers` | Get active triggers for a host (workflow) |
| `zabbix.host_get_alerts` | Get alerts for a host |
| `zabbix.host_get_events` | Get events for a host |
| `zabbix.host_get_hostgroups` | Get/check hostgroups of a host |
| `zabbix.host_get_id` | Get the ID of a host by name |
| `zabbix.host_get_interfaces` | Get interfaces of one or more hosts |
| `zabbix.host_get_inventory` | Get inventory of one or more hosts |
| `zabbix.host_get_multiple_ids` | Get IDs of multiple hosts |
| `zabbix.host_get_status` | Get monitoring status of a host |
| `zabbix.host_get_triggers` | Get triggers for a host |
| `zabbix.host_update_status` | Enable/disable monitoring of a host |
| `zabbix.list_host_groups` | List all host groups |
| `zabbix.list_host_interfaces` | List all host interfaces |
| `zabbix.list_hosts` | List all hosts |
| `zabbix.list_media_types` | List configured media types |
| `zabbix.list_templates` | List all templates |
| `zabbix.maintenance_create_or_update` | Create or update a maintenance window |
| `zabbix.maintenance_delete` | Delete a maintenance window |
| `zabbix.update_host` | Update host properties |
| `zabbix.verify_credentials` | Verify Zabbix credentials are valid |

## Development

### Running Tests

```shell
# Create/activate the virtual environment
source /path/to/st2packs/env/bin/activate

# Run tests
cd stackstorm-zabbix
python -m pytest tests/ -v
```

### Docker Development Environment

Start a local Zabbix instance for testing:

```shell
cd stackstorm-zabbix
docker-compose up -d
```

This starts Zabbix Server, Web UI (port 8080), and MySQL. Access the UI at `http://localhost:8080` with `Admin/zabbix`.

## Migration from 1.x

### Breaking Changes

- **Removed**: `tools/` directory and `register_st2_config_to_zabbix.py` script
- **Removed**: `st2_dispatch.py` AlertScript approach
- **Removed**: Legacy `token` parameter from all actions (use pack config auth instead)
- **Renamed**: `test_credentials` → `verify_credentials`
- **Changed**: Library switched from `py-zabbix` to `zabbix-utils`
- **Changed**: Authentication is now configured exclusively via pack config (`config.schema.yaml`)

### Migration Steps

1. Update pack config to use new schema (add `api_token` or keep `username`/`password`)
2. Run the appropriate registration script to create webhook media types
3. Remove any st2kv references to `zabbix.secret_token` (no longer used)
4. Update any rules referencing `zabbix.test_credentials` to `zabbix.verify_credentials`
5. Remove the legacy AlertScript from Zabbix server (`/usr/lib/zabbix/alertscripts/st2_dispatch.py`)

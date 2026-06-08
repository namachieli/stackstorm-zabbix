#!/usr/bin/env bash
# Register the "StackStorm RabbitMQ" webhook media type in Zabbix and
# configure the RabbitMQ exchange/queue/binding via Management API.
#
# This script:
#   1. Creates RabbitMQ exchange, queue, and binding via Management API
#   2. Authenticates to the Zabbix API
#   3. Creates/updates a webhook media type (type=4) that publishes to RabbitMQ
#   4. Assigns media to the Admin user
#
# Required environment variables:
#   ZABBIX_URL       - Zabbix frontend URL (e.g. http://localhost:8080)
#   RABBITMQ_URL     - RabbitMQ Management API URL (e.g. http://localhost:15672)
#
# Authentication (one of):
#   ZABBIX_API_TOKEN - Zabbix API token (preferred)
#   ZABBIX_USER      - Zabbix username (default: Admin)
#   ZABBIX_PASSWORD  - Zabbix password (default: zabbix)
#
# Optional:
#   RABBITMQ_USER       - RabbitMQ username (default: guest)
#   RABBITMQ_PASSWORD   - RabbitMQ password (default: guest)
#   RABBITMQ_VHOST      - RabbitMQ virtual host (default: /)
#   RABBITMQ_EXCHANGE   - Exchange name (default: st2.zabbix)
#   RABBITMQ_ROUTING_KEY - Routing key (default: zabbix.alerts)
#   RABBITMQ_QUEUE      - Queue name (default: zabbix.alerts)
#   ZABBIX_ADMIN_USER_ID - Zabbix user ID to assign media to (default: 1 = Admin)

set -euo pipefail

: "${ZABBIX_URL:?ZABBIX_URL is required}"
: "${RABBITMQ_URL:?RABBITMQ_URL is required}"

ZABBIX_USER="${ZABBIX_USER:-Admin}"
ZABBIX_PASSWORD="${ZABBIX_PASSWORD:-zabbix}"
ZABBIX_ADMIN_USER_ID="${ZABBIX_ADMIN_USER_ID:-1}"
RABBITMQ_USER="${RABBITMQ_USER:-guest}"
RABBITMQ_PASSWORD="${RABBITMQ_PASSWORD:-guest}"
RABBITMQ_VHOST="${RABBITMQ_VHOST:-/}"
RABBITMQ_EXCHANGE="${RABBITMQ_EXCHANGE:-st2.zabbix}"
RABBITMQ_ROUTING_KEY="${RABBITMQ_ROUTING_KEY:-zabbix.alerts}"
RABBITMQ_QUEUE="${RABBITMQ_QUEUE:-zabbix.alerts}"
MEDIA_TYPE_NAME="StackStorm RabbitMQ"

# URL-encode the vhost for RabbitMQ Management API paths
VHOST_ENCODED=$(python3 -c "import urllib.parse; print(urllib.parse.quote('${RABBITMQ_VHOST}', safe=''))")

# --- RabbitMQ Setup ---

echo "=== RabbitMQ Setup ==="

rabbitmq_api() {
    local method="$1"
    local path="$2"
    local data="${3:-}"

    local args=(-s -o /dev/null -w "%{http_code}" -X "${method}"
        -u "${RABBITMQ_USER}:${RABBITMQ_PASSWORD}"
        -H "Content-Type: application/json")

    if [[ -n "${data}" ]]; then
        args+=(-d "${data}")
    fi

    curl "${args[@]}" "${RABBITMQ_URL}/api${path}"
}

# Create exchange
echo "Creating exchange '${RABBITMQ_EXCHANGE}' on vhost '${RABBITMQ_VHOST}'..."
HTTP_CODE=$(rabbitmq_api PUT "/exchanges/${VHOST_ENCODED}/${RABBITMQ_EXCHANGE}" \
    '{"type": "topic", "durable": true, "auto_delete": false}')
if [[ "${HTTP_CODE}" == "201" || "${HTTP_CODE}" == "204" ]]; then
    echo "Exchange created/confirmed."
elif [[ "${HTTP_CODE}" == "204" ]]; then
    echo "Exchange already exists."
else
    echo "WARNING: Exchange creation returned HTTP ${HTTP_CODE}" >&2
fi

# Create queue
echo "Creating queue '${RABBITMQ_QUEUE}' on vhost '${RABBITMQ_VHOST}'..."
HTTP_CODE=$(rabbitmq_api PUT "/queues/${VHOST_ENCODED}/${RABBITMQ_QUEUE}" \
    '{"durable": true, "auto_delete": false}')
if [[ "${HTTP_CODE}" == "201" || "${HTTP_CODE}" == "204" ]]; then
    echo "Queue created/confirmed."
else
    echo "WARNING: Queue creation returned HTTP ${HTTP_CODE}" >&2
fi

# Create binding
echo "Binding queue '${RABBITMQ_QUEUE}' to exchange '${RABBITMQ_EXCHANGE}' with key '${RABBITMQ_ROUTING_KEY}'..."
HTTP_CODE=$(rabbitmq_api POST "/bindings/${VHOST_ENCODED}/e/${RABBITMQ_EXCHANGE}/q/${RABBITMQ_QUEUE}" \
    "{\"routing_key\": \"${RABBITMQ_ROUTING_KEY}\"}")
if [[ "${HTTP_CODE}" == "201" || "${HTTP_CODE}" == "204" ]]; then
    echo "Binding created."
elif [[ "${HTTP_CODE}" == "409" ]]; then
    echo "Binding already exists."
else
    echo "WARNING: Binding creation returned HTTP ${HTTP_CODE}" >&2
fi

echo ""

# --- Zabbix Setup ---

echo "=== Zabbix Webhook Setup ==="

# JSON-RPC request helper
request_id=1
zabbix_api() {
    local method="$1"
    local params="$2"
    local auth_field=""

    if [[ -n "${AUTH_TOKEN:-}" ]]; then
        auth_field="\"auth\": \"${AUTH_TOKEN}\","
    fi

    local payload
    payload=$(cat <<EOF
{
    "jsonrpc": "2.0",
    "method": "${method}",
    ${auth_field}
    "params": ${params},
    "id": ${request_id}
}
EOF
)
    request_id=$((request_id + 1))

    local response
    response=$(curl -s -X POST \
        -H "Content-Type: application/json-rpc" \
        "${ZABBIX_URL}/api_jsonrpc.php" \
        -d "${payload}")

    local error
    error=$(echo "${response}" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('error',{}).get('data',''))" 2>/dev/null || true)
    if [[ -n "${error}" ]]; then
        echo "ERROR: Zabbix API ${method} failed: ${error}" >&2
        exit 1
    fi

    echo "${response}" | python3 -c "import sys,json; print(json.dumps(json.load(sys.stdin).get('result')))"
}

# Authenticate
echo "Authenticating to Zabbix at ${ZABBIX_URL}..."
AUTH_TOKEN=""
if [[ -n "${ZABBIX_API_TOKEN:-}" ]]; then
    AUTH_TOKEN="${ZABBIX_API_TOKEN}"
    echo "Using API token authentication."
else
    AUTH_TOKEN=$(zabbix_api "user.login" "{\"username\": \"${ZABBIX_USER}\", \"password\": \"${ZABBIX_PASSWORD}\"}" | tr -d '"')
    echo "Authenticated as ${ZABBIX_USER}."
fi

# Webhook JavaScript
WEBHOOK_JS=$(cat <<'JSEOF'
var params = JSON.parse(value);
var req = new HttpRequest();
req.addHeader('Content-Type: application/json');
var auth = Base64.encode(params.RABBITMQ_USER + ':' + params.RABBITMQ_PASSWORD);
req.addHeader('Authorization: Basic ' + auth);
var vhost = encodeURIComponent(params.RABBITMQ_VHOST || '/');
var exchange = encodeURIComponent(params.RABBITMQ_EXCHANGE || 'st2.zabbix');
var url = params.RABBITMQ_URL + '/api/exchanges/' + vhost + '/' + exchange + '/publish';
var message = {
    properties: {content_type: 'application/json', delivery_mode: 2},
    routing_key: params.RABBITMQ_ROUTING_KEY || 'zabbix.alerts',
    payload: JSON.stringify({
        trigger: 'zabbix.event_handler',
        payload: {
            alert_sendto: params.To,
            alert_subject: params.Subject,
            alert_message: params.Message,
            host: params.HostName,
            event_id: params.EventID,
            trigger_id: params.TriggerID,
            trigger_name: params.TriggerName,
            trigger_status: params.TriggerStatus,
            trigger_severity: params.TriggerSeverity,
            event_time: params.EventTime,
            event_date: params.EventDate
        }
    }),
    payload_encoding: 'string'
};
var resp = req.post(url, JSON.stringify(message));
if (req.getStatus() >= 200 && req.getStatus() < 300) {
    return 'OK';
} else {
    throw 'RabbitMQ publish failed with status ' + req.getStatus() + ': ' + resp;
}
JSEOF
)

# Build parameters JSON array
PARAMETERS='[
    {"name": "RABBITMQ_URL", "value": "'"${RABBITMQ_URL}"'"},
    {"name": "RABBITMQ_USER", "value": "'"${RABBITMQ_USER}"'"},
    {"name": "RABBITMQ_PASSWORD", "value": "'"${RABBITMQ_PASSWORD}"'"},
    {"name": "RABBITMQ_VHOST", "value": "'"${RABBITMQ_VHOST}"'"},
    {"name": "RABBITMQ_EXCHANGE", "value": "'"${RABBITMQ_EXCHANGE}"'"},
    {"name": "RABBITMQ_ROUTING_KEY", "value": "'"${RABBITMQ_ROUTING_KEY}"'"},
    {"name": "To", "value": "{ALERT.SENDTO}"},
    {"name": "Subject", "value": "{ALERT.SUBJECT}"},
    {"name": "Message", "value": "{ALERT.MESSAGE}"},
    {"name": "HostName", "value": "{HOST.NAME}"},
    {"name": "EventID", "value": "{EVENT.ID}"},
    {"name": "TriggerID", "value": "{TRIGGER.ID}"},
    {"name": "TriggerName", "value": "{TRIGGER.NAME}"},
    {"name": "TriggerStatus", "value": "{TRIGGER.STATUS}"},
    {"name": "TriggerSeverity", "value": "{TRIGGER.SEVERITY}"},
    {"name": "EventTime", "value": "{EVENT.TIME}"},
    {"name": "EventDate", "value": "{EVENT.DATE}"}
]'

# Escape JS for JSON embedding
WEBHOOK_JS_ESCAPED=$(echo "${WEBHOOK_JS}" | python3 -c "import sys,json; print(json.dumps(sys.stdin.read()))")

# Check if media type already exists
echo "Checking for existing '${MEDIA_TYPE_NAME}' media type..."
EXISTING=$(zabbix_api "mediatype.get" "{\"filter\": {\"name\": \"${MEDIA_TYPE_NAME}\"}}")
EXISTING_ID=$(echo "${EXISTING}" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d[0]['mediatypeid'] if d else '')" 2>/dev/null || true)

if [[ -n "${EXISTING_ID}" ]]; then
    echo "Updating existing media type (ID: ${EXISTING_ID})..."
    zabbix_api "mediatype.update" "{
        \"mediatypeid\": \"${EXISTING_ID}\",
        \"name\": \"${MEDIA_TYPE_NAME}\",
        \"type\": \"4\",
        \"script\": ${WEBHOOK_JS_ESCAPED},
        \"parameters\": ${PARAMETERS},
        \"timeout\": \"30s\",
        \"process_tags\": \"0\",
        \"description\": \"Publishes Zabbix alerts to RabbitMQ for StackStorm consumption.\"
    }" > /dev/null
    MEDIA_TYPE_ID="${EXISTING_ID}"
    echo "Media type updated."
else
    echo "Creating '${MEDIA_TYPE_NAME}' webhook media type..."
    RESULT=$(zabbix_api "mediatype.create" "{
        \"name\": \"${MEDIA_TYPE_NAME}\",
        \"type\": \"4\",
        \"script\": ${WEBHOOK_JS_ESCAPED},
        \"parameters\": ${PARAMETERS},
        \"timeout\": \"30s\",
        \"process_tags\": \"0\",
        \"description\": \"Publishes Zabbix alerts to RabbitMQ for StackStorm consumption.\"
    }")
    MEDIA_TYPE_ID=$(echo "${RESULT}" | python3 -c "import sys,json; print(json.load(sys.stdin)['mediatypeids'][0])")
    echo "Media type created (ID: ${MEDIA_TYPE_ID})."
fi

# Add media to Admin user
echo "Configuring media on user ID ${ZABBIX_ADMIN_USER_ID}..."
EXISTING_MEDIA=$(zabbix_api "user.get" "{\"userids\": \"${ZABBIX_ADMIN_USER_ID}\", \"selectMedias\": \"extend\"}")
HAS_MEDIA=$(echo "${EXISTING_MEDIA}" | python3 -c "
import sys, json
users = json.load(sys.stdin)
if users:
    for m in users[0].get('medias', []):
        if m.get('mediatypeid') == '${MEDIA_TYPE_ID}':
            print('yes')
            break
" 2>/dev/null || true)

if [[ "${HAS_MEDIA}" != "yes" ]]; then
    CURRENT_MEDIAS=$(echo "${EXISTING_MEDIA}" | python3 -c "
import sys, json
users = json.load(sys.stdin)
medias = users[0].get('medias', []) if users else []
for m in medias:
    m.pop('mediaid', None)
    m.pop('userid', None)
medias.append({
    'mediatypeid': '${MEDIA_TYPE_ID}',
    'sendto': 'stackstorm-rabbitmq',
    'active': '0',
    'severity': '63',
    'period': '1-7,00:00-24:00'
})
print(json.dumps(medias))
")
    zabbix_api "user.update" "{
        \"userid\": \"${ZABBIX_ADMIN_USER_ID}\",
        \"medias\": ${CURRENT_MEDIAS}
    }" > /dev/null
    echo "Media assigned to user."
else
    echo "Media already assigned to user."
fi

echo ""
echo "=== Registration Complete ==="
echo "Media Type: ${MEDIA_TYPE_NAME} (ID: ${MEDIA_TYPE_ID})"
echo "RabbitMQ Exchange: ${RABBITMQ_EXCHANGE} (vhost: ${RABBITMQ_VHOST})"
echo "RabbitMQ Queue: ${RABBITMQ_QUEUE}"
echo "Routing Key: ${RABBITMQ_ROUTING_KEY}"
echo ""
echo "Next steps:"
echo "  1. Create a Zabbix Action (Alerts > Actions > Trigger actions) that"
echo "     uses this media type to send notifications on problem events."
echo "  2. Install the stackstorm-rabbitmq pack: st2 pack install rabbitmq"
echo "  3. Configure rabbitmq pack to consume from queue '${RABBITMQ_QUEUE}'"
echo "  4. Create StackStorm rules to process rabbitmq.new_message triggers"
echo "     (see rules/zabbix_rabbitmq_bridge.yaml for an example)"

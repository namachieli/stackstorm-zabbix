#!/usr/bin/env bash
# Register the "StackStorm Direct" webhook media type in Zabbix.
#
# This script authenticates to the Zabbix API and creates/updates a webhook
# media type (type=4) that POSTs alerts directly to the StackStorm API.
#
# Required environment variables:
#   ZABBIX_URL       - Zabbix frontend URL (e.g. http://localhost:8080)
#   ST2_API_URL      - StackStorm API URL (e.g. http://localhost:81)
#   ST2_API_KEY      - StackStorm API key for authentication
#
# Authentication (one of):
#   ZABBIX_API_TOKEN - Zabbix API token (preferred)
#   ZABBIX_USER      - Zabbix username (default: Admin)
#   ZABBIX_PASSWORD  - Zabbix password (default: zabbix)
#
# Optional:
#   ZABBIX_ADMIN_USER_ID - Zabbix user ID to assign media to (default: 1 = Admin)

set -euo pipefail

: "${ZABBIX_URL:?ZABBIX_URL is required}"
: "${ST2_API_URL:?ST2_API_URL is required}"
: "${ST2_API_KEY:?ST2_API_KEY is required}"

ZABBIX_USER="${ZABBIX_USER:-Admin}"
ZABBIX_PASSWORD="${ZABBIX_PASSWORD:-zabbix}"
ZABBIX_ADMIN_USER_ID="${ZABBIX_ADMIN_USER_ID:-1}"
MEDIA_TYPE_NAME="StackStorm Direct"

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
req.addHeader('St2-Api-Key: ' + params.ST2_API_KEY);
var payload = JSON.stringify({
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
});
var url = params.ST2_API_URL + '/api/v1/webhooks/st2';
var resp = req.post(url, payload);
if (req.getStatus() >= 200 && req.getStatus() < 300) {
    return 'OK';
} else {
    throw 'Failed with status ' + req.getStatus() + ': ' + resp;
}
JSEOF
)

# Build parameters JSON array
PARAMETERS='[
    {"name": "ST2_API_URL", "value": "'"${ST2_API_URL}"'"},
    {"name": "ST2_API_KEY", "value": "'"${ST2_API_KEY}"'"},
    {"name": "HTTPProxy", "value": ""},
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
        \"description\": \"Posts Zabbix alerts directly to StackStorm API webhook endpoint.\"
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
        \"description\": \"Posts Zabbix alerts directly to StackStorm API webhook endpoint.\"
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
    # Get current medias and append new one
    CURRENT_MEDIAS=$(echo "${EXISTING_MEDIA}" | python3 -c "
import sys, json
users = json.load(sys.stdin)
medias = users[0].get('medias', []) if users else []
# Strip mediaid so Zabbix treats them as new entries during update
for m in medias:
    m.pop('mediaid', None)
    m.pop('userid', None)
medias.append({
    'mediatypeid': '${MEDIA_TYPE_ID}',
    'sendto': 'stackstorm',
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
echo "Webhook URL: ${ST2_API_URL}/api/v1/webhooks/st2"
echo ""
echo "Next steps:"
echo "  1. Create a Zabbix Action (Alerts > Actions > Trigger actions) that"
echo "     uses this media type to send notifications on problem events."
echo "  2. Ensure the StackStorm zabbix.event_handler trigger is registered"
echo "     and rules are configured to process incoming alerts."

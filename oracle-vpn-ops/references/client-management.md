# Client Management

## Concepts

- **Client** = a user/device config with unique UUID, identified by `email` field
- **Sub ID** = subscription identifier, used in subscription URLs
- **Inbound** = the listening port+protocol config (we have one: VLESS-REALITY on 443)
- Each client is attached to one or more inbounds

## Add a New Client via API

```bash
SSH_KEY="~/Library/Mobile Documents/iCloud~md~obsidian/Documents/Iphone1/KEY/OracleCloud/ssh-key-2026-07-04-private.key"

ssh -i "$SSH_KEY" ubuntu@141.147.189.28 bash -s << 'REMOTE'
# Generate UUID
UUID=$(/usr/local/x-ui/bin/xray-linux-amd64 uuid)
echo "New UUID: $UUID"

# Login to panel API
RESP=$(curl -s -c /tmp/3xui-cookie 'http://localhost:2053/parko-3xui-dashboard/')
CSRF=$(grep -oP 'csrf-token" content="\K[^"]+' <<< "$RESP")
curl -s -b /tmp/3xui-cookie -c /tmp/3xui-cookie -X POST 'http://localhost:2053/parko-3xui-dashboard/login' \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -H "X-CSRF-Token: $CSRF" \
  -d 'username=park0er&password=<PASSWORD>' > /dev/null

# Get fresh CSRF after login
RESP2=$(curl -s -b /tmp/3xui-cookie 'http://localhost:2053/parko-3xui-dashboard/panel/')
CSRF2=$(grep -oP 'csrf-token" content="\K[^"]+' <<< "$RESP2")

# Add client to inbound ID 1
# Replace: EMAIL, SUB_ID, UUID
EMAIL="friend@vpn"
SUB_ID="friend"

curl -s -b /tmp/3xui-cookie -X POST "http://localhost:2053/parko-3xui-dashboard/panel/api/clients/add" \
  -H "X-CSRF-Token: $CSRF2" \
  -H "Content-Type: application/json" \
  -d "{
    \"email\": \"$EMAIL\",
    \"subId\": \"$SUB_ID\",
    \"id\": \"$UUID\",
    \"flow\": \"xtls-rprx-vision\",
    \"limitIp\": 2,
    \"totalGB\": 0,
    \"expiryTime\": 0,
    \"enable\": true,
    \"tgId\": 0,
    \"reset\": 0,
    \"inboundIds\": [1]
  }"
echo ""
echo "Done. Sub URL: http://141.147.189.28:2096/parko-clash/$SUB_ID"
REMOTE
```

**Parameters to customize:**
- `EMAIL`: identifier in panel (e.g. `girlfriend@vpn`, `dad-iphone@vpn`)
- `SUB_ID`: used in subscription URL (keep short, alphanumeric)
- `limitIp`: max concurrent connections (0 = unlimited, 2 = reasonable for one person)
- `totalGB`: traffic limit in bytes (0 = unlimited)
- `expiryTime`: Unix timestamp in ms (0 = never expires)

## Share with Others

### For Clash Verge / ClashX / Mihomo users

Give them the **Clash subscription link**:
```
http://141.147.189.28:2096/parko-clash/<subId>
```

They import it as a Remote Profile in Clash Verge.

### For Shadowrocket / v2rayN / NekoBox users

Give them the **base64 subscription link**:
```
http://141.147.189.28:2096/parko-sub/<subId>
```

Or give them the **vless:// link directly** (copy from panel → Client Info → Copy URL section).

### QR Code

In the 3x-ui panel (via SSH tunnel):
1. Go to Inbounds → expand VLESS-REALITY
2. Click the client's info icon (ℹ️)
3. In "Copy URL" section, click the QR code icon (⏹)
4. Screenshot or show the QR code to the person — they scan it with Shadowrocket

**Key difference:**
- **Subscription link** = auto-updates when you change config
- **vless:// link / QR** = static snapshot, won't auto-update

## Remove a Client

```bash
# Via API (replace EMAIL)
curl -s -b /tmp/3xui-cookie -X POST \
  "http://localhost:2053/parko-3xui-dashboard/panel/api/clients/del/friend@vpn" \
  -H "X-CSRF-Token: $CSRF2"
```

Or simply do it in the panel GUI: Inbounds → expand → click trash icon on the client row.

## List All Clients

```bash
curl -s -b /tmp/3xui-cookie \
  "http://localhost:2053/parko-3xui-dashboard/panel/api/inbounds/list" \
  -H "X-CSRF-Token: $CSRF2" | python3 -m json.tool
```

## Reset Client Traffic

```bash
curl -s -b /tmp/3xui-cookie -X POST \
  "http://localhost:2053/parko-3xui-dashboard/panel/api/clients/resetTraffic/friend@vpn" \
  -H "X-CSRF-Token: $CSRF2"
```

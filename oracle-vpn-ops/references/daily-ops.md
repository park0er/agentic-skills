# Daily Operations

## SSH Access

```bash
SSH_KEY="~/Library/Mobile Documents/iCloud~md~obsidian/Documents/Iphone1/KEY/OracleCloud/ssh-key-2026-07-04-private.key"
SERVER="ubuntu@141.147.189.28"

# Direct SSH
ssh -i "$SSH_KEY" $SERVER

# SSH tunnel for panel (keep terminal open)
ssh -L 2053:localhost:2053 -i "$SSH_KEY" $SERVER
# Then open: http://localhost:2053/parko-3xui-dashboard/
```

## Panel Access

- URL: `http://localhost:2053/parko-3xui-dashboard/`
- User: `park0er`
- Password: ask user (never stored in skill)
- Requires SSH tunnel running first

## Service Management

```bash
# Check status
sudo systemctl status x-ui
# Or:
sudo x-ui status

# Restart
sudo systemctl restart x-ui

# Stop / Start
sudo systemctl stop x-ui
sudo systemctl start x-ui

# Enable/disable autostart
sudo x-ui enable
sudo x-ui disable
```

## View Logs

```bash
# Xray + panel logs (live)
sudo x-ui log

# Systemd journal
sudo journalctl -u x-ui -f --no-pager

# Fail2ban logs
sudo x-ui banlog
```

## Update 3x-ui

```bash
sudo x-ui update
# Or full reinstall (preserves config in /etc/x-ui/x-ui.db):
sudo bash <(curl -Ls https://raw.githubusercontent.com/mhsanaei/3x-ui/master/install.sh)
```

## Check Current Settings

```bash
sudo /usr/local/x-ui/x-ui setting -show true
```

## Change Panel Credentials

```bash
sudo /usr/local/x-ui/x-ui setting -username <new_user> -password <new_pass>
sudo systemctl restart x-ui
```

## Change Web Base Path

```bash
sudo /usr/local/x-ui/x-ui setting -webBasePath /new-path/
sudo systemctl restart x-ui
```

## Firewall (iptables)

```bash
# List current rules
sudo iptables -L INPUT -n --line-numbers

# Add a port
sudo iptables -I INPUT -p tcp --dport <PORT> -j ACCEPT
sudo netfilter-persistent save

# Remove a rule by line number
sudo iptables -D INPUT <line_number>
sudo netfilter-persistent save
```

## System Resource Check

```bash
# Memory (E2.1.Micro only has 1 GB)
free -h

# Disk
df -h

# CPU
top -bn1 | head -5
```

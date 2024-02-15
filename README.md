# TE Internet Usage Monitor

This script monitors internet usage for TE (Telecom Egypt) ISP users, providing updates on usage percentage and remaining data allowance.

## Quick Start

```bash
git clone https://github.com/yourusername/TEinternetmonitor.git
cd TEinternetmonitor
chmod +x zwe.sh
./zwe.sh -u YOUR_USERNAME -p YOUR_PASSWORD
```

## Requirements

- `Bash`
- `notify`
- `curl`
- `jq`

## Options

- `-u`: TE ISP username.
- `-p`: TE ISP password.
- `-sleep`: Interval in seconds between checks (default 60).
- `-n`: Notification ID for custom notifications (optional).

## Usage

Run the script with necessary options:

```bash
./zwe.sh -u <username> -p <password> [-sleep <interval>] [-n <notify_id>]
./zwe.sh -u 0602334567 -p password -sleep 1000 -n wete
```
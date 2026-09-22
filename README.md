# Home Assistant Remote Wake/Sleep

Remotely wake, sleep, and check the status of machines on your LAN (a physical
PC via Wake-on-LAN, a Hyper-V VM via SSH, or anything else you can script)
from Home Assistant — without installing anything on the target machines
themselves.

## How it works

- **`rws_server/`** — a small Flask server, meant to run on an always-on
  device on your LAN (e.g. a Raspberry Pi). It knows nothing about specific
  machines itself; it just discovers "targets" from subfolders and exposes
  them over HTTP.
- **`custom_components/remote_wake_sleep/`** — a Home Assistant custom
  integration that talks to `rws_server`, auto-discovers it via zeroconf, and
  creates a `switch` + `sensor` device per target.

```
Home Assistant  <--HTTP-->  rws_server (Pi)  <--SSH / WOL-->  target machines
```

## 1. Set up `rws_server`

Runs on any always-on machine that can reach your targets (SSH, ping, WOL
broadcast) — typically a Raspberry Pi.

```bash
cd rws_server
pip install -r requirements.txt
```

### Define your targets

Each target is a folder under `rws_server/targets/` with exactly these four
files:

- `config.env` — connection details as `KEY=value` shell variables (host,
  MAC address, SSH user, etc.)
- `wake-up.sh` — turns the machine on
- `go-sleep.sh` — turns the machine off
- `check-status.sh` — prints `server is up` or `server is down`

Each script starts with `source "$(dirname "$0")/config.env"` and uses those
variables instead of hardcoding connection details. This is the only file you
need to touch when a hostname, MAC address, or SSH user changes.

`config.env` files hold real connection details (hostnames, MAC addresses,
SSH usernames) and are gitignored — they never get committed, so this
repository can stay public without leaking anything about your network.

`rws_server/targets_examples/` contains two working examples to copy from,
with a `sample_config.env` (placeholder values, safe to commit) instead of a
real `config.env`:

- `flo-desktop` — a physical Windows PC, woken via a Wake-on-LAN magic
  packet and put to sleep via SSH + `psshutdown`.
- `ubuntu_hyper_v` — a Hyper-V VM, started/stopped via SSH into the Windows
  host running PowerShell `Start-VM`/`Stop-VM` (a VM has no MAC of its own to
  send a magic packet to).

To add a target: copy one of the examples into `rws_server/targets/<name>/`,
rename `sample_config.env` to `config.env`, fill in the real values, and
adjust the scripts if the target needs different commands. No code changes
are needed — the server auto-discovers any folder under `targets/` that has
all four required files (`config.env`, `wake-up.sh`, `go-sleep.sh`,
`check-status.sh`), and auto-registers routes for it.

### Run it

```bash
python3 app.py
```

This starts the server on port 5000 and advertises itself on the LAN via
zeroconf/mDNS (`_remote-wake-sleep._tcp.local.`) so Home Assistant can find
it automatically. For a permanent setup, run it as a systemd service (or
equivalent) on the Pi so it survives reboots.

## 2. Install the Home Assistant integration

The integration is distributed via [HACS](https://hacs.xyz/) as a custom
repository (it's a personal integration, not in the official HACS store):

1. Install HACS on your Home Assistant instance, if you haven't already.
2. In HACS, add this repository as a **custom repository** (category:
   Integration).
3. Install "Remote Wake Sleep" from HACS, then restart Home Assistant.
4. Home Assistant should show a **Discovered** notification for the
   `rws_server` instance on your network (via zeroconf) — click through to
   confirm. If it isn't discovered automatically, add it manually via
   **Settings → Devices & Services → Add Integration → Remote Wake Sleep**
   and enter the server's host/port.

Each target defined on the server becomes its own device in Home Assistant,
with two entities:

- `switch.<target>_power` — turns the machine on/off (backed by
  `wake-up.sh`/`go-sleep.sh`)
- `sensor.<target>_status` — the raw status text (e.g. `server is up`)

Add a **Tile card** per device on your dashboard for a compact status +
toggle widget. New targets added later on the server show up automatically
on the next poll, without reconfiguring the integration.

## Repository layout

```
rws_server/                        Flask server (runs on the Pi)
  app.py
  requirements.txt
  targets/                         Your actual targets (config.env is gitignored)
  targets_examples/                Working reference targets to copy from (sample_config.env, safe to commit)
custom_components/remote_wake_sleep/  Home Assistant custom integration
```

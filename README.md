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

Clone the repo onto that machine and install the dependencies (a virtual
environment is recommended, but any Python 3 interpreter — including an
existing conda/pyenv environment — works fine):

```bash
git clone https://github.com/lerch-florian/homeassistant-remote-wake-sleep.git
cd homeassistant-remote-wake-sleep/rws_server
python3 -m venv .venv
source .venv/bin/activate
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
- `rustdesk` — not a whole machine, but a single Windows service
  (`RustDesk`), started/stopped/queried via SSH + PowerShell
  `Start-Service`/`Stop-Service`/`Get-Service`. Demonstrates that a "target"
  can be anything scriptable over SSH, not just machine power — the SSH
  account needs local admin rights on Windows to control services.

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
zeroconf/mDNS (`_rws._tcp.local.`) so Home Assistant can find it
automatically. Test it from another machine on the LAN before moving on:

```bash
curl http://<server-ip>:5000/targets
curl http://<server-ip>:5000/<target-name>/get-status
```

### Keep it running with PM2

For a permanent setup, run it under a process manager so it survives
crashes and reboots. This project was deployed with
[PM2](https://pm2.keymetrics.io/) (requires Node.js):

```bash
npm install -g pm2

# Start it (point --interpreter at the venv's python if you used one)
pm2 start app.py --name remote_wake_sleep --interpreter /path/to/python

# Persist the process list across reboots
pm2 save
pm2 startup   # prints a command to run once (sets up a systemd unit for PM2 itself)
```

Useful commands afterwards:

```bash
pm2 list                        # check it's online
pm2 logs remote_wake_sleep      # tail its output
pm2 restart remote_wake_sleep   # after pulling code changes
```

Any other process manager (systemd, supervisord, ...) works just as well —
PM2 is just what this project happens to use.

## 2. Install the Home Assistant integration

The integration is distributed via [HACS](https://hacs.xyz/) as a custom
repository (it's a personal integration, not in the official HACS store).

### Prerequisite: HACS itself, and its GitHub authentication

If HACS isn't installed yet, follow the [HACS installation
guide](https://www.hacs.xyz/docs/use/download/download/). During HACS's own
setup it will ask you to authenticate with GitHub via **device flow**:

1. HACS shows you a short code and a link to `github.com/login/device`.
2. Open that link in a browser, sign in if needed, and enter the code.
3. GitHub asks you to authorize **"HACS by HACS"**. It will only request
   **"Public data only"** access — that's expected and sufficient, since
   HACS only reads public repository data (it does not support private
   repositories at all, by design — see [HACS's
   docs](https://www.hacs.xyz/docs/faq/private_repositories/)).
4. Confirm, and HACS finishes setting up.

You only need to do this once per Home Assistant instance. No personal
access token needs to be created or pasted in anywhere — this repo is
public specifically so the standard HACS flow above works without one.

### Add this repository and install

1. In HACS, open the three-dot menu (top right) → **Custom repositories**.
2. Add `https://github.com/lerch-florian/homeassistant-remote-wake-sleep`
   with category **Integration**.
3. Find **"Remote Wake Sleep"** in HACS, click it, and **Download**.
4. Restart Home Assistant.

### Add the integration

Home Assistant should show a **Discovered** notification for the
`rws_server` instance on your network (via zeroconf) — click through to
confirm; host/port are pre-filled. If it isn't discovered automatically
(e.g. HA and the server are on different network segments), add it manually
via **Settings → Devices & Services → Add Integration → Remote Wake Sleep**
and enter the server's host/port yourself.

Each target defined on the server becomes its own device in Home Assistant,
with two entities:

- `switch.<target>_power` — turns the machine on/off (backed by
  `wake-up.sh`/`go-sleep.sh`)
- `sensor.<target>_status` — the raw status text (e.g. `server is up`)

Add a **Tile card** per device on your dashboard for a compact status +
toggle widget. New targets added later on the server show up automatically
on the next poll, without reconfiguring the integration.

### Options

**Settings → Devices & Services → Remote Wake Sleep → Configure** lets you
change the polling interval (default 30s, minimum 5s) without editing any
files — saving it reloads the integration immediately.

## Repository layout

```
rws_server/                        Flask server (runs on the Pi)
  app.py
  requirements.txt
  targets/                         Your actual targets (config.env is gitignored)
  targets_examples/                Working reference targets to copy from (sample_config.env, safe to commit)
custom_components/remote_wake_sleep/  Home Assistant custom integration
```

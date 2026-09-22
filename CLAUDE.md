# CLAUDE.md

Guidance for AI coding agents working in this repository. See
[README.md](README.md) for the user-facing setup guide — this file covers
conventions and constraints that aren't obvious from reading the code.

## Project shape

Two independent components, connected only by HTTP:

- `rws_server/` — a Flask server that runs on a LAN device (e.g. a
  Raspberry Pi) with SSH/network access to the target machines. It has no
  hardcoded knowledge of any machine; it discovers "targets" from
  subfolders at startup.
- `custom_components/remote_wake_sleep/` — a Home Assistant custom
  integration (HACS-distributed) that polls `rws_server` over HTTP and
  exposes a `switch` + `sensor` device per target.

They share no code and are deployed/versioned independently. A change to
one does not require a change to the other unless the HTTP contract
between them changes (`/targets`, `/<target>/wake-up`, `/<target>/go-sleep`,
`/<target>/get-status` — all defined in `rws_server/app.py`).

## Hard constraints (do not violate silently)

- **Never commit real connection details.** `rws_server/targets/*/config.env`
  is gitignored and must stay that way — it holds real hostnames, MAC
  addresses, and SSH usernames. `rws_server/targets_examples/*/sample_config.env`
  is the tracked, placeholder-only counterpart; keep both in sync in
  structure (same keys) whenever the target contract changes.
- **This repo must stay public, or HACS breaks.** HACS does not support
  private repositories at all (not a token/scope issue — it's a hard
  limitation: https://www.hacs.xyz/docs/faq/private_repositories/). Don't
  reintroduce private-repo assumptions (e.g. a token-entry config flow) —
  they don't apply here.
- **HACS only installs `custom_components/remote_wake_sleep/`.** Nothing
  else in the repo (README, `rws_server/`) is touched by a HACS
  install/update. Don't assume `rws_server` gets deployed by installing the
  HACS integration — it's a separate manual deployment step (see README).
- **Bump `custom_components/remote_wake_sleep/manifest.json`'s `version`**
  whenever any file under `custom_components/remote_wake_sleep/` changes.
  HACS uses this to detect and offer updates.
- **`ZeroconfServiceInfo` import must keep its try/except fallback** in
  `config_flow.py`. The deployed Home Assistant instance for this project
  runs 2024.10.1, which predates `homeassistant.helpers.service_info.zeroconf`
  (that module only exists from HA 2024.11+); the fallback imports from
  `homeassistant.components.zeroconf` instead. Removing the fallback breaks
  the config flow entirely ("Invalid handler specified" in the UI) on older
  HA versions.
- **Zeroconf service type must stay ≤ 15 bytes** in the label portion
  (currently `_rws._tcp.local.`, i.e. `rws` = 3 bytes). This is a hard
  DNS-SD limit (RFC 6763) enforced by the `zeroconf` library at
  registration time — exceeding it crashes `rws_server` on startup with
  `BadTypeInNameException`. Keep this in sync between `rws_server/app.py`'s
  `ZEROCONF_SERVICE_TYPE`, `custom_components/remote_wake_sleep/const.py`'s
  `ZEROCONF_SERVICE_TYPE`, and the `manifest.json` `"zeroconf"` key — all
  three must match exactly.
- **Don't use `socket.gethostbyname(hostname)` to find the LAN IP** for
  zeroconf advertising in `rws_server/app.py`. On Debian this can resolve
  to the `/etc/hosts` loopback alias (`127.0.1.1`), making the server
  advertise an unreachable address. Use the outbound-UDP-socket trick in
  `get_local_ip()` instead.

## Conventions

- Each target folder under `rws_server/targets/` (and mirrored in
  `targets_examples/`) must contain exactly: `config.env`, `wake-up.sh`,
  `go-sleep.sh`, `check-status.sh`. `rws_server/app.py`'s
  `discover_targets()` silently skips any folder missing one of these —
  if a target isn't showing up, check for a typo'd filename before
  anything else.
- Target scripts source their config with
  `source "$(dirname "$0")/config.env"` and reference variables like
  `$HOST`, `$SSH_USER`, `$SSH_KEY` — never hardcode connection details in
  the script body.
- `check-status.sh` must print exactly `server is up` or `server is down`
  (used verbatim as the HA sensor state and as the substring match
  `"up" in status.lower()` in `switch.py`'s `is_on`).

## Testing changes locally

There's no test suite. What was actually used during development:

- `python3 -m py_compile <file>.py` for syntax checks on every Python file
  touched (no HA or Flask install needed for this).
- `python3 -c "import json; json.load(open('<file>.json'))"` for
  `manifest.json` / `strings.json` / `translations/en.json`.
- `bash -n <script>.sh` for shell script syntax.
- A scratch venv with `flask` + `zeroconf` installed
  (`rws_server/requirements.txt`) to actually import and exercise
  `rws_server/app.py` (e.g. via `app.test_client()`) before deploying.
- The Home Assistant / HACS side has no local test harness — changes there
  were verified by deploying to the real instance and checking its docker
  logs for import/setup errors (see README for the deployed instance's
  HA version constraint above).

## Deployment reality

The server this project is actually deployed against runs Home Assistant
as a plain Docker container (`ghcr.io/home-assistant/home-assistant:stable`),
**not** Supervised/HAOS — so Supervisor add-ons are not an option for
`rws_server`; it has to run as an independent process (this project uses
PM2, see README) on a machine with LAN/SSH access to the targets.

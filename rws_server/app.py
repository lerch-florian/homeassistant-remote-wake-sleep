import os
import signal
import socket
import subprocess

from flask import Flask
from zeroconf import ServiceInfo, Zeroconf

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TARGETS_DIR = os.path.join(BASE_DIR, 'targets')
REQUIRED_SCRIPTS = ['wake-up.sh', 'go-sleep.sh', 'check-status.sh']

ZEROCONF_SERVICE_TYPE = '_rws._tcp.local.'
SERVICE_PORT = 5000

STATUS_TIMEOUT = 8
ACTION_TIMEOUT = 25

discovered_targets = []


def run_script(target_dir, script_name, timeout):
    """Run a target script; returns its stdout, or None if it timed out."""
    # Own process group so a hung ssh child is killed along with bash.
    proc = subprocess.Popen(
        ['bash', script_name], cwd=target_dir, stdout=subprocess.PIPE, text=True, start_new_session=True
    )
    try:
        out, _ = proc.communicate(timeout=timeout)
        return out.strip()
    except subprocess.TimeoutExpired:
        os.killpg(proc.pid, signal.SIGKILL)
        proc.communicate()
        return None


def register_target(target_name):
    target_dir = os.path.join(TARGETS_DIR, target_name)

    def wake_up():
        run_script(target_dir, 'wake-up.sh', ACTION_TIMEOUT)
        return {}

    def go_sleep():
        run_script(target_dir, 'go-sleep.sh', ACTION_TIMEOUT)
        return {}

    def get_status():
        status = run_script(target_dir, 'check-status.sh', STATUS_TIMEOUT)
        return {'status': status if status is not None else 'server is down'}

    app.add_url_rule(f'/{target_name}/wake-up', f'{target_name}_wake_up', wake_up)
    app.add_url_rule(f'/{target_name}/go-sleep', f'{target_name}_go_sleep', go_sleep)
    app.add_url_rule(f'/{target_name}/get-status', f'{target_name}_get_status', get_status)


def discover_targets():
    if not os.path.isdir(TARGETS_DIR):
        return
    for entry in sorted(os.listdir(TARGETS_DIR)):
        target_dir = os.path.join(TARGETS_DIR, entry)
        if not os.path.isdir(target_dir):
            continue
        if not os.path.isfile(os.path.join(target_dir, 'config.env')):
            continue
        if not all(os.path.isfile(os.path.join(target_dir, script)) for script in REQUIRED_SCRIPTS):
            continue
        discovered_targets.append(entry)
        register_target(entry)


@app.route('/targets')
def list_targets():
    return {'targets': discovered_targets}


def get_local_ip():
    # socket.gethostbyname(hostname) can resolve to a /etc/hosts loopback
    # alias (e.g. 127.0.1.1 on Debian) instead of the actual LAN address, so
    # determine it via a UDP socket connected to an external address instead.
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('8.8.8.8', 80))
        return s.getsockname()[0]
    finally:
        s.close()


def advertise_zeroconf():
    hostname = socket.gethostname()
    local_ip = get_local_ip()
    info = ServiceInfo(
        ZEROCONF_SERVICE_TYPE,
        f'{hostname}.{ZEROCONF_SERVICE_TYPE}',
        addresses=[socket.inet_aton(local_ip)],
        port=SERVICE_PORT,
        properties={},
    )
    zc = Zeroconf()
    zc.register_service(info)
    return zc


discover_targets()


if __name__ == '__main__':
    zeroconf_instance = advertise_zeroconf()
    try:
        app.run(host='0.0.0.0', port=SERVICE_PORT)
    finally:
        zeroconf_instance.unregister_all_services()
        zeroconf_instance.close()

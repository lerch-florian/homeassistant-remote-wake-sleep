#!/bin/bash
source "$(dirname "$0")/config.env"
ssh -o ServerAliveInterval=3 -o ServerAliveCountMax=1 -i "${SSH_KEY}" -n "${SSH_USER}@${HOST}" "psshutdown -accepteula -d -t 0;"

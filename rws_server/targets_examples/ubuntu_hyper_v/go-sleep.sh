#!/bin/bash
source "$(dirname "$0")/config.env"
ssh -o ServerAliveInterval=3 -o ServerAliveCountMax=1 -i "${SSH_KEY}" -n "${SSH_USER}@${SSH_HOST}" "powershell -Command \"Stop-VM -Name ${VM_NAME}\";"

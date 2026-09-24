#!/bin/bash
source "$(dirname "$0")/config.env"
status=$(ssh -o ConnectTimeout=3 -o ServerAliveInterval=3 -o ServerAliveCountMax=1 -i "${SSH_KEY}" -n "${SSH_USER}@${SSH_HOST}" "powershell -Command \"(Get-Service -Name '${SERVICE_NAME}' -ErrorAction SilentlyContinue).Status\"" | tr -d '\r')
if [ "$status" = "Running" ]; then
  echo 'server is up'
else
  echo 'server is down'
fi

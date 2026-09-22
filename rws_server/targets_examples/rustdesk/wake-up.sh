#!/bin/bash
source "$(dirname "$0")/config.env"
ssh -o ServerAliveInterval=3 -o ServerAliveCountMax=1 -i "${SSH_KEY}" -n "${SSH_USER}@${SSH_HOST}" "powershell -Command \"if (Get-Service -Name '${SERVICE_NAME}' -ErrorAction SilentlyContinue) { Start-Service -Name '${SERVICE_NAME}' } else { Start-Process -FilePath '${SERVICE_EXE_PATH}' -ArgumentList '--install-service' }\""

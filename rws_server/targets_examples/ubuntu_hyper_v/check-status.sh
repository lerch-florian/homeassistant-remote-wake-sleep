#!/bin/bash
source "$(dirname "$0")/config.env"
ping -c1 -W1 -q $STATUS_HOST > /dev/null 2>&1 && echo 'server is up' || echo 'server is down'

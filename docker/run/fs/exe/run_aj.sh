#!/bin/bash

. "/ins/setup_venv.sh" "$@"
. "/ins/copy_aj.sh" "$@"

# The project is bind-mounted in local Docker runs, so mark it as safe for git.
git config --global --add safe.directory /aj >/dev/null 2>&1 || true

python /aj/python/helpers/scheduler_bootstrap.py
python /aj/prepare.py --dockerized=true
# python /aj/preload.py --dockerized=true # no need to run preload if it's done during container build

echo "Starting Agent Jumbo..."
exec python /aj/run_ui.py \
    --dockerized=true \
    --port=80 \
    --host="0.0.0.0"
    # --code_exec_ssh_enabled=true \
    # --code_exec_ssh_addr="localhost" \
    # --code_exec_ssh_port=22 \
    # --code_exec_ssh_user="root" \
    # --code_exec_ssh_pass="toor"

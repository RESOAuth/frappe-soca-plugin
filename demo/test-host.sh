#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
runtime="${CONTAINER_RUNTIME:-podman}"
run_id="soca-frappe-$(date +%s)-$$"
network="$run_id"
db="$run_id-db"
redis="$run_id-redis"
host="$run_id-host"
image="localhost/frappe-soca-test:latest"
cleanup() {
  "$runtime" rm -f "$host" "$redis" "$db" >/dev/null 2>&1 || true
  "$runtime" network rm "$network" >/dev/null 2>&1 || true
}
trap cleanup EXIT
"$runtime" network create "$network" >/dev/null
"$runtime" run -d --name "$db" --network "$network" -e MARIADB_ROOT_PASSWORD=soca-disposable-test docker.io/library/mariadb:11.4@sha256:f2f5e00999bd335343e09091e27e39c9386eb1822efcd0e0bac40b0003fa47e3 --character-set-server=utf8mb4 --collation-server=utf8mb4_unicode_ci --skip-character-set-client-handshake >/dev/null
"$runtime" run -d --name "$redis" --network "$network" docker.io/library/redis:7-alpine@sha256:ca0acbb137c1dc3339c8b147a58fd6f42775d4599327b50e7b116c23de501af2 >/dev/null
"$runtime" build -t "$image" -f Containerfile .
"$runtime" run -d --name "$host" --network "$network" --entrypoint bash "$image" -lc 'sleep infinity' >/dev/null
"$runtime" exec "$host" env/bin/python apps/frappe_soca/demo/register-app.py
for attempt in $(seq 1 60); do
  if "$runtime" exec "$db" mariadb-admin ping -uroot -psoca-disposable-test --silent >/dev/null 2>&1; then break; fi
  if [ "$attempt" = 60 ]; then exit 1; fi
  sleep 1
done
"$runtime" exec "$host" bench set-config -g db_host "$db"
"$runtime" exec "$host" bench set-config -g redis_cache "redis://$redis:6379"
"$runtime" exec "$host" bench set-config -g redis_queue "redis://$redis:6379"
"$runtime" exec "$host" bench set-config -g redis_socketio "redis://$redis:6379"
"$runtime" exec "$host" bench new-site soca.test --db-root-password soca-disposable-test --admin-password soca-disposable-admin-9371 --mariadb-user-host-login-scope=%
"$runtime" exec "$host" bench --site soca.test install-app frappe_soca
"$runtime" exec "$host" bench --site soca.test execute frappe_soca.host_checks.run
"$runtime" exec "$host" bench version

#!/bin/sh
# Four disposable clusters, Unix sockets only; never the service's PGDATA.
set -eu
marker=$1
case "$marker" in ''|*[!0-9a-f]*) exit 64;; esac
[ "${#marker}" = 32 ] && [ "$(id -un)" = postgres ] || exit 64
root="/tmp/college_recovery_$marker"
cleanup() {
  [ -d "$root" ] || return 0
  [ -f "$root/owned-marker" ] && [ "$(cat "$root/owned-marker")" = "$marker" ] || return 64
  for cluster in recovered logical standby primary; do
    if [ -d "$root/$cluster" ]; then pg_ctl -D "$root/$cluster" -m immediate -w -t 15 stop >>"$root/cleanup.log" 2>&1 || true; fi
  done
  case "$root" in /tmp/college_recovery_*) rm -rf -- "$root";; *) return 64;; esac
}
if [ "${2:-run}" = cleanup ]; then cleanup; exit; fi
mkdir "$root"
printf '%s' "$marker" >"$root/owned-marker"
trap 'result=$?; if [ "$result" != 0 ]; then for f in "$root"/*.log; do [ ! -f "$f" ] || tail -n 12 "$f"; done; fi; cleanup; exit "$result"' EXIT
mkdir "$root/socket" "$root/archive"
chmod 700 "$root/socket"
initdb -D "$root/primary" -A trust --no-locale -E UTF8 >"$root/init-primary.log"
cat >>"$root/primary/postgresql.conf" <<EOF
listen_addresses=''
unix_socket_directories='$root/socket'
port=55440
shared_buffers='16MB'
wal_level=logical
max_wal_senders=6
max_replication_slots=6
archive_mode=on
archive_command='test -f $root/archive/%f || cp %p $root/archive/%f'
EOF
pg_ctl -D "$root/primary" -l "$root/primary.log" -w -t 30 start >/dev/null
q() { psql -X -v ON_ERROR_STOP=1 -At -h "$root/socket" -p "$1" -U postgres -d postgres -c "$2"; }
q 55440 "CREATE TABLE recovery_events(id int PRIMARY KEY,label text NOT NULL); INSERT INTO recovery_events VALUES(1,'base backup');" >/dev/null
pg_basebackup -h "$root/socket" -p 55440 -U postgres -D "$root/base" -X stream --checkpoint=fast >"$root/basebackup.log" 2>&1
[ -f "$root/base/backup_manifest" ] || exit 1
echo 'PASS: A real physical base backup and manifest are created from the isolated primary.'
q 55440 "INSERT INTO recovery_events VALUES(2,'wanted commit');" >/dev/null
q 55440 "SELECT pg_create_restore_point('college_good');" >/dev/null
q 55440 "INSERT INTO recovery_events VALUES(3,'unwanted later commit');" >/dev/null
echo 'PASS: A named restore point separates wanted data from a later committed change.'
pg_basebackup -h "$root/socket" -p 55440 -U postgres -D "$root/standby" -X stream -R --checkpoint=fast >"$root/standby-backup.log" 2>&1
printf "\nport=55441\n" >>"$root/standby/postgresql.conf"
pg_ctl -D "$root/standby" -l "$root/standby.log" -w -t 30 start >/dev/null
ready=false
for attempt in $(seq 1 30); do
  if [ "$(q 55441 'SELECT pg_is_in_recovery() AND (SELECT count(*) FROM recovery_events)=3' 2>/dev/null || true)" = t ]; then ready=true; break; fi
  sleep 1
done
[ "$ready" = true ] || exit 1
echo 'PASS: A real physical standby is in recovery and receives all three primary rows.'
[ "$(q 55440 'SELECT count(*)>=1 FROM pg_stat_replication')" = t ] || exit 1
echo 'PASS: The primary observes an actual physical WAL-sender connection.'
initdb -D "$root/logical" -A trust --no-locale -E UTF8 >"$root/init-logical.log"
printf "\nlisten_addresses=''\nunix_socket_directories='$root/socket'\nport=55442\nshared_buffers='16MB'\n" >>"$root/logical/postgresql.conf"
pg_ctl -D "$root/logical" -l "$root/logical.log" -w -t 30 start >/dev/null
q 55440 'CREATE PUBLICATION college_publication FOR TABLE recovery_events' >/dev/null
q 55442 'CREATE TABLE recovery_events(id int PRIMARY KEY,label text NOT NULL)' >/dev/null
q 55442 "CREATE SUBSCRIPTION college_subscription CONNECTION 'host=$root/socket port=55440 dbname=postgres user=postgres' PUBLICATION college_publication" >/dev/null
ready=false
for attempt in $(seq 1 30); do
  if [ "$(q 55442 'SELECT count(*)=3 FROM recovery_events' 2>/dev/null || true)" = t ]; then ready=true; break; fi
  sleep 1
done
[ "$ready" = true ] && [ "$(q 55442 'SELECT NOT pg_is_in_recovery()')" = t ] || exit 1
echo 'PASS: An independent logical subscriber receives table data without being a physical recovery standby.'
segment=$(q 55440 'SELECT pg_walfile_name(pg_current_wal_lsn())')
q 55440 'SELECT pg_switch_wal()' >/dev/null
for attempt in $(seq 1 30); do [ ! -f "$root/archive/$segment" ] || break; sleep 1; done
[ -f "$root/archive/$segment" ] || exit 1
echo 'PASS: Completed WAL segments are actually archived before the recovery test.'
cp -a "$root/base" "$root/recovered"
cat >>"$root/recovered/postgresql.conf" <<EOF
port=55443
restore_command='cp $root/archive/%f %p'
recovery_target_name='college_good'
recovery_target_action='promote'
EOF
touch "$root/recovered/recovery.signal"
pg_ctl -D "$root/recovered" -l "$root/recovered.log" -w -t 30 start >/dev/null
ready=false
for attempt in $(seq 1 30); do
  if [ "$(q 55443 'SELECT NOT pg_is_in_recovery() AND (SELECT count(*) FROM recovery_events)=2 AND NOT EXISTS(SELECT 1 FROM recovery_events WHERE id=3)' 2>/dev/null || true)" = t ]; then ready=true; break; fi
  sleep 1
done
[ "$ready" = true ] || exit 1
echo 'PASS: Actual archived-WAL recovery promotes at the named point, retaining wanted rows and excluding the later commit.'
[ "$(q 55440 'SELECT count(*)=3 FROM recovery_events')" = t ] || exit 1
echo 'PASS: Point-in-time restoration leaves the original primary and its later data untouched.'
cleanup
trap - EXIT
[ ! -e "$root" ] || exit 1
echo 'PASS: Exact-marker cleanup stops all four scratch clusters and removes only their generated temporary directory.'

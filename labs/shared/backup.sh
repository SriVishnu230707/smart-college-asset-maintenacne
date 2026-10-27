#!/bin/sh
set -eu
mode=$1
schema=$2
database=$3
marker=$4
case "$schema" in college_step63|college_step64|college_step77|college_step80) ;; *) exit 64;; esac
case "$marker" in ''|*[!0-9a-f]*) exit 64;; esac
[ "${#marker}" = 32 ] || exit 64
case "$database" in college_ops63_*|college_ops64_*|college_ops77_*|college_ops80_*) ;; *) exit 64;; esac
case "$database" in *[!a-z0-9_]*) exit 64;; esac
archive="/tmp/college_backup_${marker}.dump"
export PGHOST=127.0.0.1 PGUSER=college_learner
PGPASSWORD=$(cat /run/secrets/college_learner_password)
export PGPASSWORD
case "$mode" in
 dump) pg_dump --format=custom --no-owner --no-acl --schema="$schema" --file="$archive" college_learning; pg_restore --list "$archive" >/dev/null;;
 restore) pg_restore --exit-on-error --single-transaction --no-owner --no-acl --dbname="$database" "$archive";;
 cleanup) rm -f -- "$archive";;
 *) exit 64;;
esac

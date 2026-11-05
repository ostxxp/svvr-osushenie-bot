#!/bin/sh
set -eu
umask 077
exec 9>/run/lock/svvr-backup.lock
flock -n 9 || exit 0
runuser -u svvr -- /usr/bin/python3 /usr/local/lib/svvr-backup/snapshot.py
if [ ! -f /etc/svvr-backup/cloud.env ]; then
    echo 'Cloud backup is not configured; local snapshot is available.' >&2
    exit 0
fi
set -a
. /etc/svvr-backup/cloud.env
set +a
restic backup /var/lib/svvr-backup/staging/snapshot --tag svvr --host svvr-production
restic forget --tag svvr --host svvr-production --keep-hourly 24 --keep-daily 30 --keep-weekly 8 --keep-monthly 12
touch /var/lib/svvr-backup/last-cloud-success

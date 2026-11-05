#!/bin/sh
set -eu
umask 077
exec 9>/run/lock/svvr-backup.lock
flock -w 1800 9
restic check --read-data
restic prune

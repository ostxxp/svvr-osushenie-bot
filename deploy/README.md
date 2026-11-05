# SVVR deployment and recovery

Replacement VPS prepared on 2026-11-05: `31.57.105.22`, directory
`/opt/svvr-osushenie-bot`, service `svvr-osushenie-bot.service`, user `svvr`.
The migration deliberately starts with an empty SQLite database. Users register
for reminders again through `/start`. Google Sheets remain the source of
objects, assignments, workers, work types, and submitted reports.

Rollout status: production `@SVVR_Osushenie_bot` is running and enabled with
the owner's supplied production token; the developer's local test `.env` is
unchanged. Hourly local and encrypted Google Drive backups are enabled. The
Drive account is `osushenie.rf@gmail.com`, folder `SVVR-backups-2026`, using a
dedicated published Google OAuth desktop application with `drive.file` scope.
An actual cloud snapshot was restored without using the local restic cache;
file checksums, production configuration and SQLite integrity were verified.
A recovery password and OAuth configuration are saved separately on the Mac
in `.backup-recovery/`, excluded from Git. GitHub Actions uses the restricted
`svvr-deploy` account rather than root SSH access.

The service keeps `TZ=UTC`: the current reminder code adds three hours itself.
Do not change the host timezone to fix reminder times.

## Operations

```sh
systemctl status svvr-osushenie-bot
journalctl -u svvr-osushenie-bot --since today
systemctl list-timers 'svvr-*'
systemctl start svvr-backup.service
stat /var/lib/svvr-backup/last-cloud-success
```

Application secrets are in `.env` and `credentials.json` (root:svvr, 0640).
The bot can write only its SQLite directory and two temporary input directories.
Application source is root-owned; the Python environment is owned by the bot user for dependency updates. On new installs,
startup creates the SQLite tables and temporary directories automatically.

## Backup design

- Every hour (with up to five minutes of jitter), `svvr-backup.timer` runs a
  verified SQLite online backup. It includes the schema, application code,
  dependency versions, service definitions, bot and Google credentials, and
  temporary report/feedback files. Live SQLite files are never copied directly.
- Local `.tar.gz` archives accessible only to root and the bot account stay in `/var/backups/svvr` for seven days.
  A stable restore tree is kept in `/var/lib/svvr-backup/staging/snapshot`.
- Restic encrypts and uploads that tree to the father's Google Drive using
  rclone. Its OAuth scope is `drive.file`, limited to files created with rclone.
  The repository password is in `/etc/svvr-backup/restic-password`, OAuth state
  in `/etc/svvr-backup/rclone.conf`, and settings in `cloud.env` in that folder.
  These files must be root-only. Never commit them or put secrets in logs.
- Keep 24 hourly, 30 daily, 8 weekly, and 12 monthly restore points. This is a
  retention policy; history accumulates only after backups start running.
- Each Sunday, `svvr-backup-check.timer` reads and verifies all stored cloud
  data and prunes unreferenced encrypted data. It shares the backup lock.
- `last-cloud-success` is updated only after a successful cloud backup and
  retention run. Failed jobs appear in systemd; no message alerts are configured.
- Files being edited during a snapshot are best-effort: unfinished input may
  need to be entered again. Submitted Google Sheets data is not modified or
  exported by this backup.

Keep the repository password separately from this VPS. A protected recovery
copy on the administrator's Mac is in `.backup-recovery/` (git-ignored).
Copy that password into a password manager for recovery if both machines fail.
Do not save the password unencrypted next to the encrypted cloud repository.

## Restore without the original VPS

1. Install Python 3.12 with venv support, restic, and rclone on a replacement
   machine. Authenticate rclone to the father's Drive, or recover its root-only
   config from the protected recovery copy. Use the existing repository folder,
   not a newly created empty folder.
2. Load the recovered `cloud.env`, set `RCLONE_CONFIG` and
   `RESTIC_PASSWORD_FILE` to the recovered files, and list snapshots:

   ```sh
   set -a
   . /etc/svvr-backup/cloud.env
   set +a
   restic snapshots --tag svvr
   restic restore latest --tag svvr --target /var/tmp/svvr-restore
   ```

3. The restored application tree is
   `/var/tmp/svvr-restore/var/lib/svvr-backup/staging/snapshot`. Verify it before use:

   ```sh
   python3 /var/tmp/svvr-restore/var/lib/svvr-backup/staging/snapshot/deploy/snapshot.py \
     --verify /var/tmp/svvr-restore/var/lib/svvr-backup/staging/snapshot
   ```

4. Stop any existing bot process, move aside its old application/data directory,
   then copy the verified tree to `/opt/svvr-osushenie-bot`. Create the system
   user `svvr`, then set permissions on the restored tree (archive staging
   files are deliberately root-only):

   ```sh
   chown -R root:svvr /opt/svvr-osushenie-bot
   find /opt/svvr-osushenie-bot -type d -exec chmod 750 {} +
   find /opt/svvr-osushenie-bot -type f -exec chmod 640 {} +
   chown -R svvr:svvr /opt/svvr-osushenie-bot/DB \
     /opt/svvr-osushenie-bot/report_info /opt/svvr-osushenie-bot/feedbacks_temp
   python3 -m venv /opt/svvr-osushenie-bot/.venv
   /opt/svvr-osushenie-bot/.venv/bin/pip install \
     -r /opt/svvr-osushenie-bot/requirements.txt
   chmod 750 /opt/svvr-osushenie-bot/deploy/*.sh
   ```
5. Copy `snapshot.py`, `backup.sh`, and `check-backup.sh` from `deploy/` into
   the root-owned `/usr/local/lib/svvr-backup` (scripts executable). Create
   `/var/lib/svvr-backup` root:svvr 0750 and its `staging` subdirectory svvr:svvr
   0700; make `/var/backups/svvr` svvr:svvr 0700. Give svvr ownership of `.venv`
   so dependency updates can run without root. Install the restored systemd
   service/timer files from `deploy/`. Recover the
   root-only backup settings under `/etc/svvr-backup`. Reload systemd, start
   the bot, check its logs, and enable the backup timers. Verify a new cloud
   backup and a restore before considering the replacement complete.

The old Beget instance must remain stopped: if it returns, stop and disable
`svvr-osushenie-bot.service` there before it competes for Telegram polling.

## Deployments

Copy source files without overwriting `.env`, `credentials.json`, `DB/db.db`,
`report_info`, or `feedbacks_temp`; install dependencies as the bot user, back up before
restarting, then check service health. Never deploy a developer's SQLite file.
GitHub Actions uses a dedicated `svvr-deploy` account and SSH key. That account
can upload into `/var/lib/svvr-deploy/incoming` and invoke only the fixed,
root-owned `/usr/local/sbin/svvr-install` through sudo, without arguments.
The installer accepts only main.py, requirements.txt, and flat Python files in
bot/ and DB/, checks Python syntax, creates a backup, installs code atomically,
runs pip as the bot user, and restarts the fixed bot service. It never installs
uploaded service definitions, secrets, databases, or backup executables.
Root backup executables are frozen in `/usr/local/lib/svvr-backup`; snapshot
creation runs as the bot account. Changes to those executables, the installer,
or systemd units require an administrator to install them explicitly.
The deployment account has no root shell or administrative access to other applications.

## Public OAuth information pages

The existing Caddy hostname serves `/svvr-backups/` from
`/var/www/svvr-backups`. The source pages are in `deploy/oauth-site`; the proxy
backup is `/etc/caddy/Caddyfile.before-svvr-backups-20261105`. Existing root,
Ostankino, Paris and food application routes remain separate. On a replacement
server, restore these static files and add a `handle_path /svvr-backups/*`
file-server route to the existing HTTPS host. The public pages contain only
application information and a data-handling notice, never backup data.

For Google access, use the provided OAuth desktop client configuration. Keep
the Google project's publishing status In production. When changing clients or
re-authorizing, confirm that the granted account is the father's account and
that a refresh token is present. A new client using drive.file may not see
files created with a different OAuth client. Do not initialize a new empty
repository over the old one during recovery.

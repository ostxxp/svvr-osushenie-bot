"""Create a consistent SQLite backup plus the files needed to rebuild SVVR."""
import argparse
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import tarfile
import tempfile


def verify(snapshot):
    manifest = json.loads((snapshot / "manifest.json").read_text())
    for name, digest in manifest["sha256"].items():
        if hashlib.sha256((snapshot / name).read_bytes()).hexdigest() != digest:
            raise RuntimeError(f"Checksum mismatch: {name}")
    with sqlite3.connect(f"file:{snapshot / 'DB/db.db'}?mode=ro", uri=True) as db:
        if db.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise RuntimeError("SQLite integrity check failed")
        tables = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if not {"prorabs", "reports"}.issubset(tables):
            raise RuntimeError("Missing SVVR tables")
    return manifest


def create(source, destination, archives):
    os.umask(0o077)
    destination.parent.mkdir(parents=True, exist_ok=True)
    archives.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc)
    with tempfile.TemporaryDirectory(prefix="staging-", dir=destination.parent) as temp:
        stage = Path(temp) / "snapshot"
        stage.mkdir()
        (stage / "DB").mkdir()
        files = [source / name for name in ("main.py", "requirements.txt", ".env", "credentials.json")]
        for directory in ("bot", "DB", "deploy"):
            files.extend((source / directory).rglob("*.py"))
        files.extend((source / "deploy").glob("*.service"))
        files.extend((source / "deploy").glob("*.timer"))
        files.extend((source / "deploy").glob("*.sh"))
        files.extend((source / "deploy").glob("*.md"))
        for directory in ("report_info", "feedbacks_temp"):
            (stage / directory).mkdir()
            files.extend((source / directory).glob("*.txt"))
        for file in files:
            target = stage / file.relative_to(source)
            target.parent.mkdir(parents=True, exist_ok=True)
            try:
                shutil.copyfile(file, target)
            except FileNotFoundError:
                if file.parent.name not in {"report_info", "feedbacks_temp"}:
                    raise
        with sqlite3.connect(f"file:{source / 'DB/db.db'}?mode=ro", uri=True) as live:
            with sqlite3.connect(stage / "DB/db.db") as backup:
                live.backup(backup)
        manifest = {
            "format": 1,
            "created_at": now.isoformat(),
            "sha256": {
                str(file.relative_to(stage)): hashlib.sha256(file.read_bytes()).hexdigest()
                for file in sorted(stage.rglob("*")) if file.is_file()
            },
        }
        (stage / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
        verify(stage)
        archive = archives / f"svvr-{now:%Y%m%dT%H%M%S%fZ}.tar.gz"
        partial = archive.with_suffix(".partial")
        try:
            with tarfile.open(partial, "w:gz") as tar:
                tar.add(stage, arcname="svvr")
            partial.replace(archive)
        finally:
            partial.unlink(missing_ok=True)
        old = destination.with_name(destination.name + ".previous")
        if old.exists():
            shutil.rmtree(old)
        if destination.exists():
            destination.rename(old)
        stage.rename(destination)
        if old.exists():
            shutil.rmtree(old)
    cutoff = (now - timedelta(days=7)).timestamp()
    for file in archives.glob("svvr-*.tar.gz"):
        if file.stat().st_mtime < cutoff:
            file.unlink()
    print(f"Created and verified {archive.name}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=Path("/opt/svvr-osushenie-bot"))
    parser.add_argument("--snapshot", type=Path, default=Path("/var/lib/svvr-backup/staging/snapshot"))
    parser.add_argument("--archives", type=Path, default=Path("/var/backups/svvr"))
    parser.add_argument("--verify", type=Path)
    args = parser.parse_args()
    if args.verify:
        result = verify(args.verify)
        print(f"Backup verified: {result['created_at']}")
    else:
        create(args.source, args.snapshot, args.archives)

#!/usr/bin/python3
"""Root-owned installer: accept only SVVR Python source; run pip as the bot user."""
import os
from pathlib import Path
import pwd
import stat
import subprocess
import sys
import tempfile

APP = Path('/opt/svvr-osushenie-bot')
INCOMING = Path('/var/lib/svvr-deploy/incoming')


def main():
    if len(sys.argv) != 1 or os.geteuid() != 0:
        raise SystemExit('Run only the fixed installer through sudo, with no arguments')
    deployer = pwd.getpwnam('svvr-deploy')
    files = {}
    # Read untrusted uploads with the uploader's permissions, never as root.
    original_groups = os.getgroups()
    os.setgroups([deployer.pw_gid])
    os.setegid(deployer.pw_gid)
    os.seteuid(deployer.pw_uid)
    try:
        for path in INCOMING.rglob('*'):
            relative = path.relative_to(INCOMING)
            allowed = str(relative) in {'main.py', 'requirements.txt'} or (
                len(relative.parts) == 2 and relative.parts[0] in {'bot', 'DB'}
                and path.suffix == '.py'
            )
            if not allowed:
                continue
            if path.is_symlink() or not stat.S_ISREG(path.stat().st_mode):
                raise RuntimeError('Only regular source files are allowed')
            content = path.read_bytes()
            if len(content) > 2_000_000:
                raise RuntimeError('Unexpectedly large source file')
            if path.suffix == '.py':
                compile(content, str(relative), 'exec')
            files[relative] = content
        if not {Path('main.py'), Path('requirements.txt'), Path('bot/__init__.py'), Path('DB/database.py')}.issubset(files):
            raise RuntimeError('Incomplete deployment')
    finally:
        os.seteuid(0)
        os.setegid(0)
        os.setgroups(original_groups)
    subprocess.run(['systemctl', 'start', 'svvr-backup.service'], check=True)
    group = pwd.getpwnam('svvr').pw_gid
    for relative, content in files.items():
        destination = APP / relative
        if not destination.parent.resolve().is_relative_to(APP):
            raise RuntimeError('Unsafe destination directory')
        descriptor, name = tempfile.mkstemp(prefix='.deploy-', dir=destination.parent)
        try:
            with os.fdopen(descriptor, 'wb') as output:
                output.write(content)
                os.fchown(output.fileno(), 0, group)
                os.fchmod(output.fileno(), 0o640)
            os.replace(name, destination)
        finally:
            Path(name).unlink(missing_ok=True)
    subprocess.run([
        'runuser', '-u', 'svvr', '--', str(APP / '.venv/bin/pip'),
        'install', '--disable-pip-version-check', '--no-cache-dir',
        '-r', str(APP / 'requirements.txt'),
    ], cwd=APP, check=True)
    subprocess.run(['systemctl', 'restart', 'svvr-osushenie-bot.service'], check=True)


if __name__ == '__main__':
    main()

"""Move legacy mutable state to the Studio volume before any application imports."""
import os
import shutil
import time
from pathlib import Path


def migrate(app: Path, workspace: Path):
    workspace.mkdir(parents=True, exist_ok=True)
    directories = [
        'webui/data', 'logs', 'screenshots', 'config', 'temp', 'settings',
        '3rdparty/WebBrowser/UserProfile',
    ]
    files = ['config.yaml', 'warp.json', 'smtp_temp.bin']
    for name in ['home', 'cache', 'tmp']:
        (workspace / name).mkdir(parents=True, exist_ok=True)
    for name in directories + files:
        source, target = app / name, workspace / name
        if source.is_symlink():
            if source.resolve() == target.resolve():
                continue
            raise RuntimeError(f'Refusing to replace unexpected symlink: {source}')
        target.parent.mkdir(parents=True, exist_ok=True)
        if source.exists():
            if not target.exists():
                shutil.move(str(source), str(target))
            else:
                # Preserve any legacy conflicts rather than overwrite persisted accounts.
                backup = workspace / 'migration-backups' / str(time.time_ns()) / name
                backup.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(source), str(backup))
        if name in directories:
            target.mkdir(parents=True, exist_ok=True)
        source.parent.mkdir(parents=True, exist_ok=True)
        source.symlink_to(target, target_is_directory=name in directories)
    print(f'[storage] Application data persists in {workspace}', flush=True)


if __name__ == '__main__':
    migrate(Path('/m7a'), Path('/mnt/workspace'))

#!/usr/bin/env python3
from __future__ import annotations

import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FASTVIEW_ENV = 'TASKCAPTAIN_FASTVIEW_BIN'
FASTVIEW_BIN = ROOT / 'rust' / 'taskcaptain-fastview' / 'target' / 'release' / (
    'taskcaptain-fastview.exe' if os.name == 'nt' else 'taskcaptain-fastview'
)
IGNORE_DIRS = {'.git', '.taskcaptain', '.venv', 'venv', 'node_modules', '__pycache__'}
PINNED_ARTIFACTS = {
    'README.md': 0,
    'verification.log': 1,
    'index.html': 2,
    'app.js': 3,
    'styles.css': 4,
}


def format_bytes(size: int) -> str:
    value = float(max(size, 0))
    for unit in ['B', 'KB', 'MB', 'GB']:
        if value < 1024.0 or unit == 'GB':
            if unit == 'B':
                return f'{int(value)} {unit}'
            return f'{value:.1f} {unit}'
        value /= 1024.0
    return f'{int(size)} B'


def resolve_fastview_bin() -> Path | None:
    candidates: list[Path] = []
    env_value = (os.environ.get(FASTVIEW_ENV) or '').strip()
    if env_value:
        candidates.append(Path(env_value).expanduser())
    candidates.append(FASTVIEW_BIN)
    for candidate in candidates:
        try:
            if candidate.exists() and os.access(candidate, os.X_OK):
                return candidate
        except Exception:
            continue
    return None


def fastview_backend_name() -> str:
    return 'rust' if resolve_fastview_bin() else 'python'


def _tail_text_python(path: Path, max_bytes: int) -> bytes:
    with path.open('rb') as fh:
        try:
            fh.seek(0, os.SEEK_END)
            size = fh.tell()
            fh.seek(max(size - max_bytes, 0), os.SEEK_SET)
        except Exception:
            fh.seek(0)
        return fh.read()


def tail_text(path: Path, max_bytes: int = 24 * 1024, max_chars: int = 18_000) -> dict:
    if not path.exists():
        return {
            'text': '',
            'totalSize': 0,
            'shownBytes': 0,
            'truncated': False,
            'backend': fastview_backend_name(),
        }

    total_size = 0
    try:
        total_size = int(path.stat().st_size)
    except Exception:
        total_size = 0

    raw = b''
    backend = 'python'
    helper = resolve_fastview_bin()
    if helper:
        try:
            proc = subprocess.run(
                [str(helper), 'tail', str(path), str(max_bytes)],
                capture_output=True,
                timeout=1.5,
                check=False,
            )
            if proc.returncode == 0:
                raw = proc.stdout
                backend = 'rust'
        except Exception:
            raw = b''

    if not raw:
        raw = _tail_text_python(path, max_bytes)

    text = raw.decode('utf-8', 'ignore')
    if len(text) > max_chars:
        text = text[-max_chars:]
    shown_bytes = min(total_size, max_bytes)
    return {
        'text': text,
        'totalSize': total_size,
        'shownBytes': shown_bytes,
        'truncated': total_size > shown_bytes or len(text.encode('utf-8', 'ignore')) >= shown_bytes,
        'backend': backend,
    }


def _python_workspace_artifacts(workspace: Path, limit: int) -> tuple[list[dict], int]:
    if not workspace.exists():
        return [], 0

    total_files = 0
    items: list[dict] = []
    for root, dirnames, filenames in os.walk(workspace):
        dirnames[:] = [d for d in dirnames if d not in IGNORE_DIRS]
        root_path = Path(root)
        for name in filenames:
            path = root_path / name
            try:
                stat = path.stat()
            except Exception:
                continue
            total_files += 1
            rel = path.relative_to(workspace).as_posix()
            items.append(
                {
                    'path': rel,
                    'fullPath': str(path),
                    'size': int(stat.st_size),
                    'mtime': int(stat.st_mtime),
                    'name': name,
                }
            )

    def sort_key(item: dict):
        return (
            PINNED_ARTIFACTS.get(item.get('name', ''), 999),
            -int(item.get('mtime') or 0),
            item.get('path', ''),
        )

    items.sort(key=sort_key)
    return items[:limit], total_files


def _rust_workspace_artifacts(workspace: Path, limit: int) -> tuple[list[dict], int] | None:
    helper = resolve_fastview_bin()
    if not helper or not workspace.exists():
        return None
    try:
        proc = subprocess.run(
            [str(helper), 'artifacts', str(workspace), str(limit)],
            capture_output=True,
            timeout=1.5,
            check=False,
            text=True,
        )
    except Exception:
        return None
    if proc.returncode != 0:
        return None

    lines = [line for line in proc.stdout.splitlines() if line.strip()]
    total_files = 0
    items: list[dict] = []
    for line in lines:
        if line.startswith('TOTAL\t'):
            try:
                total_files = int(line.split('\t', 1)[1].strip())
            except Exception:
                total_files = 0
            continue
        parts = line.split('\t', 3)
        if len(parts) != 4:
            continue
        try:
            mtime = int(parts[0])
            size = int(parts[1])
        except Exception:
            continue
        rel = parts[2]
        items.append(
            {
                'path': rel,
                'fullPath': str(workspace / rel),
                'size': size,
                'mtime': mtime,
                'name': Path(rel).name,
            }
        )
    return items[:limit], total_files


def list_workspace_artifacts(workspace_path: str | None, limit: int = 10) -> dict:
    workspace = Path(workspace_path or '').expanduser()
    if not workspace.exists():
        return {'items': [], 'totalFiles': 0, 'backend': fastview_backend_name()}

    rust_result = _rust_workspace_artifacts(workspace, limit)
    if rust_result is not None:
        items, total_files = rust_result
        return {'items': items, 'totalFiles': total_files, 'backend': 'rust'}

    items, total_files = _python_workspace_artifacts(workspace, limit)
    return {'items': items, 'totalFiles': total_files, 'backend': 'python'}

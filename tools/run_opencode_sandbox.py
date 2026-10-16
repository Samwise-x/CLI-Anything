"""Run a public-source goal in a disposable, unprivileged Linux container.

Only a sanitized staging copy is exposed. No host credentials or Docker socket
enter the container. Executor source edits are checked before copying back.
"""
from __future__ import annotations
import argparse
import fnmatch
import difflib
import fcntl
from contextlib import contextmanager
import hashlib
import os
from pathlib import Path
import shutil
import signal
import subprocess
import tempfile

IMAGE = 'cli-anything-opencode-sandbox:local'
PROTECTED = ('.opencode', '.github', 'tools', 'AGENTS.md', 'CONTEXT.md',
             'GLOSSARY.md', '.pre-commit-config.yaml', 'docs/adr', '.git', '.goal-loop')
SECRET_PATTERNS = ('.env*', '*.key', '*.pem', 'credentials', 'credential', 'secrets', 'secret', 'token', 'credentials*.yaml', 'credentials*.yml', 'credentials*.toml', 'credentials*.txt', 'secrets*.toml', 'secrets*.txt', 'credentials*.json', 'credential*.json',
                   'secrets*.json', 'secrets*.yaml', 'secrets*.yml', '*token*.json',
                   '*token*.yaml', '*token*.yml', 'id_rsa*', 'id_ed25519*', '.netrc',
                   '.npmrc', '.pypirc', 'auth.json')


def protected(relative):
    text = relative.as_posix()
    return any(text == item or text.startswith(item + '/') for item in PROTECTED)


def secret(relative):
    return any(fnmatch.fnmatch(part.lower(), pattern) for part in relative.parts
               for pattern in SECRET_PATTERNS)


def snapshot(root):
    result = {}
    for directory, dirs, files in os.walk(root, followlinks=False):
        for name in dirs + files:
            path = Path(directory) / name
            if path.is_symlink():
                raise ValueError('symlink forbidden in sandbox tree: ' + str(path.relative_to(root)))
            if not path.is_dir() and not path.is_file():
                raise ValueError('special file forbidden in sandbox tree')
        for name in files:
            path = Path(directory) / name
            relative = path.relative_to(root)
            if relative.parts[0] == '.git' or secret(relative):
                continue
            result[relative] = (hashlib.sha256(path.read_bytes()).hexdigest(), path.stat().st_mode & 0o777)
    return result


def prepare_stage(source, stage):
    baseline = snapshot(source)
    stage.mkdir(parents=True, exist_ok=True)
    for relative in baseline:
        destination = stage / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source / relative, destination)
    return baseline


@contextmanager
def repository_lock(source):
    folder = source / '.goal-loop'
    folder.mkdir(exist_ok=True)
    with (folder / 'sandbox-sync.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)


def sync_stage(source, stage, baseline):
    with repository_lock(source):
        _sync_locked(source, stage, baseline)


def _sync_locked(source, stage, baseline):
    current = snapshot(stage)
    changed = {relative for relative in baseline.keys() | current.keys()
               if baseline.get(relative) != current.get(relative)}
    if any(protected(relative) for relative in changed):
        raise ValueError('protected policy was changed; refusing all sandbox changes')
    host = snapshot(source)
    if any(host.get(relative) != baseline.get(relative) for relative in changed):
        raise ValueError('concurrent host change; refusing all sandbox changes')
    # Validate every parent before the first write; source symlinks are rejected above.
    for relative in changed:
        for parent in relative.parents:
            path = source / parent
            if path.exists() and not path.is_dir():
                raise ValueError('destination parent is not a directory')
    for relative in sorted(changed):
        destination = source / relative
        if relative not in current:
            destination.unlink()
        else:
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(stage / relative, destination)



def source_diff(source, env):
    git = ['git', '--literal-pathspecs', '-c', 'core.fsmonitor=false', '-c', 'core.hooksPath=/dev/null']
    listed = subprocess.run(git + ['ls-files', '-z'], cwd=source, env=env,
                            check=True, capture_output=True, text=True)
    tracked = {Path(item) for item in listed.stdout.split('\0') if item}
    existing = set(snapshot(source))
    allowed = {path for path in tracked | existing if not protected(path) and not secret(path)}
    if not allowed:
        return ''
    result = subprocess.run(git + ['diff', '--no-ext-diff', '--no-textconv', 'HEAD', '--',
                                   *[str(path) for path in sorted(allowed)]],
                            cwd=source, env=env, check=True, capture_output=True, text=True)
    patches = [result.stdout]
    for relative in sorted(existing - tracked):
        if relative not in allowed:
            continue
        try:
            contents = (source / relative).read_text(encoding='utf-8')
        except UnicodeDecodeError:
            patches.append(f'Binary source file added: {relative}\n')
        else:
            patches.extend(difflib.unified_diff([], contents.splitlines(keepends=True),
                                                fromfile='/dev/null', tofile='b/' + str(relative)))
    return ''.join(patches)

def container_command(stage, binary, role, message, command=None):
    readonly = ',readonly' if role != 'executor' else ''
    result = ['docker', 'run', '--rm', '--init', '--read-only', '--cap-drop=ALL',
              '--security-opt=no-new-privileges', '--pids-limit=256', '--memory=2g',
              '--cpus=2', '--user=1000:1000', '--workdir=/workspace',
              '--tmpfs=/tmp:rw,nosuid,nodev,size=536870912,mode=1777',
              '--tmpfs=/home/agent:rw,nosuid,nodev,size=268435456,mode=1777',
              '--env=HOME=/home/agent', '--env=XDG_CONFIG_HOME=/home/agent/.config',
              '--env=XDG_DATA_HOME=/home/agent/.local/share',
              '--env=XDG_CACHE_HOME=/home/agent/.cache',
              '--env=PYTHONDONTWRITEBYTECODE=1', '--env=GIT_CONFIG_NOSYSTEM=1',
              '--env=GIT_CONFIG_GLOBAL=/dev/null', '--env=GIT_TERMINAL_PROMPT=0',
              '--mount', f'type=bind,src={stage},dst=/workspace{readonly}']
    if role == 'executor':
        for name in PROTECTED:
            path = stage / name
            if path.exists():
                result += ['--mount', f'type=bind,src={path},dst=/workspace/{name},readonly']
    if role == 'verify':
        return result + ['--network=none', IMAGE, 'timeout', '-s', 'TERM', '-k', '5s', '780s'] + list(command or [])
    result += ['--mount', f'type=bind,src={binary},dst=/usr/local/bin/opencode,readonly',
               IMAGE, 'timeout', '-s', 'TERM', '-k', '5s', '780s', 'opencode', 'run', '--standalone', '--format', 'json', '--agent',
               'goal-executor' if role == 'executor' else 'goal-reviewer', message]
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('role', choices=('executor', 'reviewer', 'verify'))
    parser.add_argument('arguments', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    if not args.arguments:
        parser.error('a message or verification command is required')
    source = Path(__file__).resolve().parents[1]
    binary = Path('/home/master_j/.opencode/bin/opencode')
    if os.getuid() != 1000:
        parser.error('sandbox currently requires WSL uid 1000')
    def interrupted(signum, frame):
        raise SystemExit(128 + signum)
    signal.signal(signal.SIGTERM, interrupted)
    with tempfile.TemporaryDirectory(prefix='goal-sandbox-') as temporary:
        base = Path(temporary)
        stage = base / 'workspace'
        prepare_stage(source, stage)
        # Reconstruct public-source diff locally without exposing host Git config or objects.
        env = {'PATH': '/usr/bin:/bin', 'HOME': str(base), 'GIT_CONFIG_NOSYSTEM': '1',
               'GIT_CONFIG_GLOBAL': '/dev/null', 'GIT_TERMINAL_PROMPT': '0'}
        (stage / '.goal-loop').mkdir(exist_ok=True)
        (stage / '.goal-loop/source-diff.patch').write_text(source_diff(source, env), encoding='utf-8')
        for command in (['git', 'init', '-q'], ['git', 'add', '-f', '.'],
                        ['git', '-c', 'user.name=Sandbox baseline', '-c',
                         'user.email=sandbox@localhost', 'commit', '-qm', 'Sanitized baseline']):
            subprocess.run(command, cwd=stage, env=env, check=True, stdout=subprocess.DEVNULL)
        for name in PROTECTED:
            path = stage / name
            if not path.exists():
                if name in ('.opencode', '.github', 'tools', 'docs/adr', '.goal-loop'):
                    path.mkdir(parents=True, exist_ok=True)
                else:
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.touch()
        baseline = snapshot(stage)
        message = ' '.join(args.arguments).replace(str(source), '/workspace')
        message += '\nOriginal host source diff is available at /workspace/.goal-loop/source-diff.patch.'
        command = container_command(stage, binary, args.role, message, args.arguments)
        name = 'goal-' + base.name
        command[2:2] = ['--name=' + name]
        try:
            result = subprocess.run(command, env=env, check=False, timeout=840)
        finally:
            subprocess.run(['docker', 'rm', '-f', name], env=env, check=False,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=15)
        if args.role == 'executor' and result.returncode == 0:
            sync_stage(source, stage, baseline)
        raise SystemExit(result.returncode)


if __name__ == '__main__':
    main()

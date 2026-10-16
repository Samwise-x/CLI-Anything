"""Behavioral tests for the Linux isolation boundary."""
import importlib.util
from pathlib import Path
import tempfile
import os
import subprocess
import unittest


class SandboxTests(unittest.TestCase):
    def module(self):
        path = Path(__file__).parents[1] / "run_opencode_sandbox.py"
        self.assertTrue(path.exists(), "sandbox isolation wrapper must exist")
        spec = importlib.util.spec_from_file_location("sandbox", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_container_has_no_privilege_or_host_credential_mount(self):
        sandbox = self.module()
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for name in sandbox.PROTECTED:
                target = root / name
                if '.' not in target.name or target.name in ('.git', '.github', '.opencode', '.goal-loop'):
                    target.mkdir(parents=True, exist_ok=True)
                else:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_text('policy')
            command = sandbox.container_command(root, Path('/opt/opencode'), 'reviewer', 'read')
            self.assertIn('--read-only', command)
            self.assertIn('--cap-drop=ALL', command)
            self.assertIn('--security-opt=no-new-privileges', command)
            self.assertIn('--pids-limit=256', command)
            self.assertIn('--memory=2g', command)
            self.assertIn('--cpus=2', command)
            self.assertIn('--user=1000:1000', command)
            self.assertIn(f'type=bind,src={root},dst=/workspace,readonly', command)
            self.assertNotIn('/var/run/docker.sock', ' '.join(command))
            self.assertNotIn('/home/master_j', ' '.join(command))

    def test_container_passes_selected_model_to_opencode(self):
        sandbox = self.module()
        with tempfile.TemporaryDirectory() as temp:
            command = sandbox.container_command(
                Path(temp), Path("/opt/opencode"), "executor", "do work",
                model="opencode/model-a",
            )
            index = command.index("opencode")
            self.assertEqual(command[index:index + 4], [
                "opencode", "run", "--standalone", "--model",
            ])
            self.assertIn("opencode/model-a", command)

    def test_secret_material_excluded_but_credentials_source_available(self):
        sandbox = self.module()
        with tempfile.TemporaryDirectory() as temp:
            source, stage = Path(temp) / 'source', Path(temp) / 'stage'
            source.mkdir()
            for name in ['.env', 'private.pem', 'credentials.json', 'secrets.yaml', 'credentials', 'secrets', 'credentials.py', 'main.py']:
                (source / name).write_text(name)
            sandbox.prepare_stage(source, stage)
            self.assertEqual(sorted(p.name for p in stage.iterdir()), ['credentials.py', 'main.py'])

    def test_symlink_cannot_copy_host_file(self):
        sandbox = self.module()
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / 'source'
            source.mkdir()
            (source / 'escape').symlink_to('/etc/passwd')
            with self.assertRaisesRegex(ValueError, 'symlink'):
                sandbox.prepare_stage(source, Path(temp) / 'stage')

    def test_sync_rejects_policy_mutation_and_host_concurrent_edit(self):
        sandbox = self.module()
        with tempfile.TemporaryDirectory() as temp:
            source, stage = Path(temp) / 'source', Path(temp) / 'stage'
            source.mkdir()
            (source / 'AGENTS.md').write_text('trusted')
            (source / 'main.py').write_text('old')
            baseline = sandbox.prepare_stage(source, stage)
            (stage / 'AGENTS.md').write_text('hacked')
            with self.assertRaisesRegex(ValueError, 'protected'):
                sandbox.sync_stage(source, stage, baseline)
            (stage / 'AGENTS.md').write_text('trusted')
            (stage / 'main.py').write_text('new')
            (source / 'main.py').write_text('concurrent')
            with self.assertRaisesRegex(ValueError, 'concurrent'):
                sandbox.sync_stage(source, stage, baseline)
            self.assertEqual((source / 'main.py').read_text(), 'concurrent')

    def test_sync_applies_only_unprotected_source_changes(self):
        sandbox = self.module()
        with tempfile.TemporaryDirectory() as temp:
            source, stage = Path(temp) / 'source', Path(temp) / 'stage'
            source.mkdir()
            (source / 'main.py').write_text('old')
            (source / 'delete.py').write_text('old')
            baseline = sandbox.prepare_stage(source, stage)
            (stage / 'main.py').write_text('new')
            (stage / 'delete.py').unlink()
            (stage / 'new.py').write_text('created')
            sandbox.sync_stage(source, stage, baseline)
            self.assertEqual((source / 'main.py').read_text(), 'new')
            self.assertFalse((source / 'delete.py').exists())
            self.assertEqual((source / 'new.py').read_text(), 'created')




    def test_repository_sync_lock_excludes_another_process(self):
        sandbox = self.module()
        self.assertTrue(hasattr(sandbox, 'repository_lock'), 'sync requires repository-wide writer lock')
        with tempfile.TemporaryDirectory() as temp:
            with sandbox.repository_lock(Path(temp)):
                code = "import fcntl,sys; f=open(sys.argv[1], 'a'); fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)"
                result = subprocess.run(['python3', '-c', code,
                                         str(Path(temp) / '.goal-loop/sandbox-sync.lock')],
                                        capture_output=True, text=True)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('BlockingIOError', result.stderr)


    def test_review_diff_empty_allowlist_does_not_emit_secret_only_changes(self):
        sandbox = self.module()
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp)
            env = {'PATH': '/usr/bin:/bin', 'HOME': temp, 'GIT_CONFIG_NOSYSTEM': '1',
                   'GIT_CONFIG_GLOBAL': '/dev/null'}
            subprocess.run(['git', 'init', '-q', temp], check=True, env=env)
            (source / '.env').write_text('old secret\n')
            subprocess.run(['git', 'add', '-f', '.env'], cwd=source, check=True, env=env)
            subprocess.run(['git', '-c', 'user.name=test', '-c', 'user.email=test@test',
                            'commit', '-qm', 'baseline'], cwd=source, check=True, env=env)
            (source / '.env').write_text('SECRET_VALUE\n')
            self.assertEqual(sandbox.source_diff(source, env), '')


    def test_review_diff_literal_glob_filename_cannot_select_secrets(self):
        sandbox = self.module()
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp)
            env = {'PATH': '/usr/bin:/bin', 'HOME': temp, 'GIT_CONFIG_NOSYSTEM': '1',
                   'GIT_CONFIG_GLOBAL': '/dev/null'}
            subprocess.run(['git', 'init', '-q', temp], check=True, env=env)
            (source / '.env').write_text('old secret\n')
            subprocess.run(['git', 'add', '-f', '.env'], cwd=source, check=True, env=env)
            subprocess.run(['git', '-c', 'user.name=test', '-c', 'user.email=test@test',
                            'commit', '-qm', 'baseline'], cwd=source, check=True, env=env)
            (source / '.env').write_text('SECRET_VALUE\n')
            (source / '*').write_text('public source\n')
            patch = sandbox.source_diff(source, env)
            self.assertNotIn('SECRET_VALUE', patch)
            self.assertIn('+public source', patch)

    def test_review_diff_includes_deleted_and_untracked_source_without_secrets(self):
        sandbox = self.module()
        self.assertTrue(hasattr(sandbox, 'source_diff'), 'review diff must cover additions and deletions')
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp)
            env = {'PATH': '/usr/bin:/bin', 'HOME': temp, 'GIT_CONFIG_NOSYSTEM': '1',
                   'GIT_CONFIG_GLOBAL': '/dev/null'}
            subprocess.run(['git', 'init', '-q', temp], check=True, env=env)
            (source / 'removed.py').write_text('old source\n')
            (source / '.env').write_text('SUPER_SECRET\n')
            subprocess.run(['git', 'add', '-f', '.'], cwd=source, check=True, env=env)
            subprocess.run(['git', '-c', 'user.name=test', '-c', 'user.email=test@test',
                            'commit', '-qm', 'baseline'], cwd=source, check=True, env=env)
            (source / 'removed.py').unlink()
            (source / 'new.py').write_text('new source\n')
            (source / '.env').write_text('CHANGED_SECRET\n')
            patch = sandbox.source_diff(source, env)
            self.assertIn('-old source', patch)
            self.assertIn('+new source', patch)
            self.assertNotIn('SUPER_SECRET', patch)
            self.assertNotIn('CHANGED_SECRET', patch)

    @unittest.skipUnless(os.environ.get('RUN_SANDBOX_LIVE') == '1', 'opt-in Linux Docker boundary integration')
    def test_live_executor_and_reviewer_cannot_escape_mount_policy(self):
        sandbox = self.module()
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            root = base / 'workspace'
            root.mkdir()
            # GitHub hosted UID differs from the WSL container UID; this is disposable fixture data.
            root.chmod(0o777)
            (base / 'host-only-marker').write_text('HOST_ONLY_SECRET')
            for name in sandbox.PROTECTED:
                path = root / name
                if name in ('.opencode', '.github', 'tools', 'docs/adr', '.git', '.goal-loop'):
                    path.mkdir(parents=True, exist_ok=True)
                    (path / 'policy').write_text('trusted')
                else:
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_text('trusted')
            for role in ['executor', 'reviewer']:
                script = """import os
from pathlib import Path
assert not Path('/var/run/docker.sock').exists()
assert not Path(HOST_MARKER).exists()
assert 'HOST_ONLY_SECRET' not in os.environ
for name in ['AGENTS.md','.github/policy','.opencode/policy','tools/policy','.git/policy','.goal-loop/policy','docs/adr/policy']:
    try: Path('/workspace',name).write_text('hacked')
    except OSError: pass
    else: raise AssertionError('policy writable: '+name)
try: Path('/etc/host-write').write_text('hacked')
except OSError: pass
else: raise AssertionError('root filesystem writable')
if ROLE == 'executor': Path('/workspace/source.txt').write_text('allowed')
else:
    try: Path('/workspace/source.txt').write_text('hacked')
    except OSError: pass
    else: raise AssertionError('reviewer writable')
""".replace('HOST_MARKER', repr(str(base / 'host-only-marker'))).replace('ROLE', repr(role))
                command = sandbox.container_command(root, Path('/usr/bin/true'), role, '')
                command = command[:command.index(sandbox.IMAGE) + 1] + ['python3', '-c', script]
                result = subprocess.run(command, capture_output=True, text=True, timeout=45,
                                        env={'PATH': '/usr/bin:/bin', 'HOST_ONLY_SECRET': 'do not propagate'})
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual((root / 'source.txt').read_text(), 'allowed')


if __name__ == '__main__':
    unittest.main()

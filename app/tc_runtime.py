#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import shlex
import signal
import subprocess
import shutil
import threading
import time
from datetime import datetime
from pathlib import Path

try:
    from tc_core import (
        ACPX,
        ACTIVE_RUNS,
        ACTIVE_SELF_TESTS,
        CODEX_ACP_BIN,
        DEFAULT_PROFILE_ID,
        RUN_LOCK,
        SELF_TEST_LOCK,
        append_log,
        effective_claw_config,
        effective_network_config,
        ensure_workspace_path,
        load_claw_profile,
        load_product_config,
        load_product_state,
        now_iso,
        probe_openai_like_endpoint,
        product_dir,
        profile_path,
        resolve_workspace_path,
        save_product_config,
        save_product_state,
        slugify,
        TRASH,
        write_json,
    )
    from tc_runtime_shared import (
        extract_codex_dialogue_text,
        extract_json_object,
        infer_project_kind,
        normalize_effort,
        openai_chat_completion,
        openai_responses,
        project_acceptance_profile,
        stringify_for_log,
        summarize_user_claw_messages,
    )
except ModuleNotFoundError:
    from app.tc_core import (
        ACPX,
        ACTIVE_RUNS,
        ACTIVE_SELF_TESTS,
        CODEX_ACP_BIN,
        DEFAULT_PROFILE_ID,
        RUN_LOCK,
        SELF_TEST_LOCK,
        append_log,
        effective_claw_config,
        effective_network_config,
        ensure_workspace_path,
        load_claw_profile,
        load_product_config,
        load_product_state,
        now_iso,
        probe_openai_like_endpoint,
        product_dir,
        profile_path,
        resolve_workspace_path,
        save_product_config,
        save_product_state,
        slugify,
        TRASH,
        write_json,
    )
    from app.tc_runtime_shared import (
        extract_codex_dialogue_text,
        extract_json_object,
        infer_project_kind,
        normalize_effort,
        openai_chat_completion,
        openai_responses,
        project_acceptance_profile,
        stringify_for_log,
        summarize_user_claw_messages,
    )

def build_codex_env(cfg: dict) -> dict:
    codex = cfg.get('codex', {})
    env = os.environ.copy()
    if codex.get('endpoint'):
        env['OPENAI_BASE_URL'] = codex['endpoint']
    if codex.get('apiKey'):
        env['OPENAI_API_KEY'] = codex['apiKey']
    network = effective_network_config(cfg)
    effective_proxy = network.get('proxy', '')
    if effective_proxy:
        env['HTTP_PROXY'] = effective_proxy
        env['HTTPS_PROXY'] = effective_proxy
        env['http_proxy'] = effective_proxy
        env['https_proxy'] = effective_proxy
    else:
        for key in ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy']:
            env.pop(key, None)
    effective_no_proxy = network.get('noProxy', '')
    env['NO_PROXY'] = effective_no_proxy
    env['no_proxy'] = effective_no_proxy

    # Make execution more reliable for “install deps + run benchmarks” flows.
    # - Prefer system python3 (Ubuntu /usr/bin/python3 -> 3.12) over Linuxbrew python3 (often newer, fewer wheels).
    # - Ensure WSL GPU shim tools (nvidia-smi) are discoverable when present.
    # - Provide a stable PYTHON entry point for scripts.
    try:
        path_parts = [p for p in (env.get('PATH') or '').split(':') if p]
        preferred = ['/usr/bin', '/usr/lib/wsl/lib']
        node_paths: list[str] = []
        nvm_root = Path('/home/a/.nvm/versions/node')
        if nvm_root.exists():
            for candidate in sorted(nvm_root.glob('*/bin'), reverse=True):
                if (candidate / 'node').exists():
                    node_paths.append(str(candidate))
        windows_node = Path('/mnt/c/Program Files/nodejs')
        if windows_node.exists():
            node_paths.append(str(windows_node))
        new_parts: list[str] = []
        for p in preferred + node_paths + path_parts:
            if p and p not in new_parts:
                new_parts.append(p)
        if new_parts:
            env['PATH'] = ':'.join(new_parts)
    except Exception:
        pass

    env.setdefault('PYTHON', '/usr/bin/python3')
    env.setdefault('PIP_DISABLE_PIP_VERSION_CHECK', '1')
    env.setdefault('PIP_NO_INPUT', '1')
    return env


def build_codex_agent_command(
    cfg: dict,
    *,
    extra_configs: list[str] | None = None,
) -> str:
    tokens = [CODEX_ACP_BIN] if CODEX_ACP_BIN else []
    codex = cfg.get('codex', {})
    for item in extra_configs or []:
        if item:
            tokens += ['-c', item]
    if codex.get('model'):
        tokens += ['-c', f'model="{codex.get("model")}"']
    effort = normalize_effort(codex.get('thinking'))
    if effort:
        tokens += ['-c', f'model_reasoning_effort="{effort}"']
    return ' '.join(shlex.quote(x) for x in tokens) if tokens else ''


def prepare_workspace(product_id: str, cfg: dict) -> tuple[dict, bool, str]:
    raw_folder = cfg.get('productFolder') or '/tmp'
    resolved_path = resolve_workspace_path(raw_folder)
    existed = resolved_path.exists()
    ok, detail = ensure_workspace_path(raw_folder)
    if ok:
        cfg['productFolder'] = detail
        save_product_config(product_id, cfg)
        status = 'ready' if existed else 'created'
        return cfg, True, f'{status}: {detail}'
    return cfg, False, f'create-failed: {raw_folder} ({detail})'


def update_state(product_id: str, **kwargs):
    st = load_product_state(product_id)
    st.update(kwargs)
    st['updatedAt'] = now_iso()
    save_product_state(product_id, st)


def append_user_claw_message(product_id: str, role: str, text: str):
    st = load_product_state(product_id)
    st.setdefault('conversations', {}).setdefault('userClaw', []).append({'ts': now_iso(), 'role': role, 'text': text})
    st['updatedAt'] = now_iso()
    save_product_state(product_id, st)


def append_claw_codex_message(product_id: str, role: str, text: str):
    st = load_product_state(product_id)
    st.setdefault('conversations', {}).setdefault('clawCodex', []).append({'ts': now_iso(), 'role': role, 'text': text})
    st['updatedAt'] = now_iso()
    save_product_state(product_id, st)


def append_legacy_codex_conversation(product_id: str, text: str):
    st = load_product_state(product_id)
    st.setdefault('conversation', []).append({'ts': now_iso(), 'role': 'codex', 'text': text})
    st['updatedAt'] = now_iso()
    save_product_state(product_id, st)


def active_run_info(product_id: str):
    with RUN_LOCK:
        return ACTIVE_RUNS.get(product_id)


def set_active_run(product_id: str, info: dict):
    with RUN_LOCK:
        ACTIVE_RUNS[product_id] = info


def set_active_proc(product_id: str, proc):
    with RUN_LOCK:
        info = ACTIVE_RUNS.get(product_id)
        if info is not None:
            info['proc'] = proc


def clear_active_run(product_id: str):
    with RUN_LOCK:
        ACTIVE_RUNS.pop(product_id, None)


def active_self_test_info(product_id: str):
    with SELF_TEST_LOCK:
        return ACTIVE_SELF_TESTS.get(product_id)


def set_active_self_test(product_id: str, info: dict):
    with SELF_TEST_LOCK:
        ACTIVE_SELF_TESTS[product_id] = info


def clear_active_self_test(product_id: str):
    with SELF_TEST_LOCK:
        ACTIVE_SELF_TESTS.pop(product_id, None)


def terminate_process_tree(proc, grace_seconds: float = 5.0):
    if not proc:
        return
    try:
        if proc.poll() is not None:
            return
    except Exception:
        return
    try:
        os.killpg(proc.pid, signal.SIGTERM)
    except Exception:
        try:
            proc.terminate()
        except Exception:
            pass
    deadline = time.time() + grace_seconds
    while time.time() < deadline:
        try:
            if proc.poll() is not None:
                return
        except Exception:
            return
        time.sleep(0.1)
    try:
        os.killpg(proc.pid, signal.SIGKILL)
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass


def start_run(product_id: str) -> str:
    info = active_run_info(product_id)
    if info and info.get('thread') and info['thread'].is_alive():
        return info.get('run_id') or 'running'

    st = load_product_state(product_id)
    run_id = datetime.now().strftime('%Y%m%d-%H%M%S')
    stop_event = threading.Event()
    st.update({'status': 'running', 'updatedAt': now_iso(), 'lastRunId': run_id, 'lastError': None, 'stopRequested': False, 'currentTurn': 0})
    save_product_state(product_id, st)
    cfg = load_product_config(product_id)
    claw_eff = effective_claw_config(cfg)
    append_user_claw_message(product_id, 'claw', f"{claw_eff.get('profileName')} accepted the run request. Preparing supervisor context for Codex.")
    t_runner = threading.Thread(target=run_supervision_loop, args=(product_id, run_id, stop_event), daemon=True)
    set_active_run(product_id, {'thread': t_runner, 'proc': None, 'run_id': run_id, 'stop_event': stop_event})
    t_runner.start()
    return run_id


def stop_run(product_id: str) -> bool:
    info = active_run_info(product_id)
    if not info:
        update_state(product_id, status='stopped', stopRequested=True)
        append_user_claw_message(product_id, 'claw', 'Stop requested while no active Codex subprocess was found. Product marked stopped.')
        return False
    info['stop_event'].set()
    update_state(product_id, stopRequested=True)
    append_user_claw_message(product_id, 'claw', 'Stop requested by user. Agent is terminating the active Codex run.')
    proc = info.get('proc')
    if proc and proc.poll() is None:
        try:
            os.killpg(proc.pid, signal.SIGTERM)
        except Exception:
            try:
                proc.terminate()
            except Exception:
                pass
    return True


def delete_product(product_id: str) -> tuple[bool, str]:
    info = active_run_info(product_id)
    if info and info.get('thread') and info['thread'].is_alive():
        return False, 'running'
    src = product_dir(product_id)
    if not src.exists():
        return False, 'missing'
    dst = TRASH / f"{datetime.now().strftime('%Y%m%d-%H%M%S')}-{product_id}"
    shutil.move(str(src), str(dst))
    return True, str(dst)


def start_self_test(product_id: str) -> str:
    info = active_self_test_info(product_id)
    if info and info.get('thread') and info['thread'].is_alive():
        return 'already-running'

    st = load_product_state(product_id)
    st.setdefault('selfTest', {})
    st['selfTest'] = {'status': 'running', 'updatedAt': now_iso(), 'checks': {}}
    st['updatedAt'] = now_iso()
    save_product_state(product_id, st)

    t_runner = threading.Thread(target=run_self_test, args=(product_id,), daemon=True)
    set_active_self_test(product_id, {'thread': t_runner, 'procs': [], 'startedAt': now_iso()})
    t_runner.start()
    return 'started'


def save_current_product_claw_as_profile(product_id: str, form: dict[str, str]) -> str:
    cfg = load_product_config(product_id)
    claw_eff = effective_claw_config(cfg)
    name = form.get('profileName', '').strip() or f"{cfg.get('name', 'product')} agent"
    pid = slugify(name)
    path = profile_path(pid)
    i = 2
    while path.exists():
        pid = f'{slugify(name)}-{i}'
        path = profile_path(pid)
        i += 1
    ts = now_iso()
    profile = {
        'id': pid,
        'name': name,
        'description': form.get('profileDescription', '').strip() or f"Saved from product {cfg.get('name', product_id)}",
        'model': claw_eff.get('model', ''),
        'thinking': claw_eff.get('thinking', ''),
        'soul': claw_eff.get('soul', ''),
        'skills': claw_eff.get('skills', ''),
        'createdAt': ts,
        'updatedAt': ts,
    }
    write_json(path, profile)
    cfg.setdefault('claw', {})['profileId'] = pid
    cfg['claw']['model'] = ''
    cfg['claw']['thinking'] = ''
    cfg['claw']['soul'] = ''
    cfg['claw']['skills'] = ''
    save_product_config(product_id, cfg)
    append_user_claw_message(product_id, 'claw', f"Current Agent identity was saved as reusable profile '{profile['name']}'. Future products can reuse it directly.")
    return pid


def run_self_test(product_id: str) -> None:
    d = product_dir(product_id)
    cfg = load_product_config(product_id)
    claw_log = d / 'logs' / 'claw.log'
    codex_log = d / 'logs' / 'codex.log'
    codex = cfg.get('codex', {})
    claw_eff = effective_claw_config(cfg)
    network = effective_network_config(cfg)
    checks = {}

    def log_claw(text: str):
        append_log(claw_log, f'[{now_iso()}] {text}')

    def log_codex(text: str):
        append_log(codex_log, f'[{now_iso()}] {text}')

    def record_self_test(final_status: str):
        st = load_product_state(product_id)
        st['selfTest'] = {'status': final_status, 'updatedAt': now_iso(), 'checks': checks}
        st['updatedAt'] = now_iso()
        save_product_state(product_id, st)

    def run_selftest_command(cmd: list[str], timeout_seconds: int) -> tuple[int | None, str, bool]:
        # Stream stdout/stderr into codex.log while the command is running (better UX vs waiting for communicate()).
        proc = None
        try:
            proc = subprocess.Popen(
                cmd,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                start_new_session=True,
                bufsize=1,
            )
            info = active_self_test_info(product_id)
            if info is not None:
                info.setdefault('procs', []).append(proc)

            io_lock = threading.Lock()
            stdout_chunks: list[str] = []
            stderr_chunks: list[str] = []

            def reader(stream, chunks: list[str], key: str):
                try:
                    while True:
                        line = stream.readline()
                        if line == '':
                            break
                        with io_lock:
                            chunks.append(line)
                        try:
                            if key == 'stdout':
                                log_codex(line.rstrip())
                            else:
                                log_codex('[stderr] ' + line.rstrip())
                        except Exception:
                            pass
                except Exception as e:
                    with io_lock:
                        chunks.append(f"\n[taskcaptain {key} reader error] {e}\n")

            t_out = threading.Thread(target=reader, args=(proc.stdout, stdout_chunks, 'stdout'), daemon=True)
            t_err = threading.Thread(target=reader, args=(proc.stderr, stderr_chunks, 'stderr'), daemon=True)
            t_out.start()
            t_err.start()

            def combined_output() -> str:
                with io_lock:
                    stdout = ''.join(stdout_chunks)
                    stderr = ''.join(stderr_chunks)
                return stdout + (("\n" + stderr) if stderr else '')

            start_ts = time.time()
            while True:
                if proc.poll() is not None:
                    t_out.join(timeout=2)
                    t_err.join(timeout=2)
                    return proc.returncode, combined_output(), False

                if timeout_seconds is not None and time.time() - start_ts > timeout_seconds:
                    terminate_process_tree(proc)
                    t_out.join(timeout=2)
                    t_err.join(timeout=2)
                    return None, combined_output(), True

                time.sleep(0.2)
        finally:
            if proc is not None:
                info = active_self_test_info(product_id)
                if info is not None:
                    info['procs'] = [p for p in info.get('procs', []) if p is not proc]

    try:
        log_claw('Starting self-test.')
        cfg, workspace_ok, workspace_detail = prepare_workspace(product_id, cfg)
        product_folder = cfg.get('productFolder') or '/tmp'
        env = build_codex_env(cfg)

        checks['agent_config'] = {
            'ok': bool(claw_eff.get('endpoint') and claw_eff.get('model')),
            'detail': f"profile={claw_eff.get('profileName','-')} endpoint={claw_eff.get('endpoint','-')} model={claw_eff.get('model','-')} thinking={claw_eff.get('thinking','-')} apiKey={'yes' if claw_eff.get('apiKey') else 'no'}",
        }
        log_claw(f"Self-test agent_config: {checks['agent_config']}")

        checks['agent_connection'] = probe_openai_like_endpoint(
            claw_eff.get('endpoint', ''),
            claw_eff.get('apiKey'),
            proxy=network.get('proxy'),
            no_proxy=network.get('noProxy'),
        )
        log_claw(f"Self-test agent_connection: {checks['agent_connection']['ok']}")

        checks['product_folder'] = {'ok': workspace_ok, 'detail': workspace_detail}
        log_claw(f"Self-test product_folder: {checks['product_folder']}")

        acpx_cmd = [str(ACPX), '--version']
        rc, out, timed_out = run_selftest_command(acpx_cmd, 15)
        log_codex(f'[taskcaptain] self-test command finished: acpx_cli rc={rc} timedOut={timed_out}')
        if timed_out:
            checks['acpx_cli'] = {'ok': False, 'detail': f'timed out after 15 seconds: {" ".join(acpx_cmd)}'}
        else:
            checks['acpx_cli'] = {'ok': rc == 0 and bool((out or '').strip()), 'detail': (out or '').strip()[-500:]}
        log_claw(f"Self-test acpx_cli: {checks['acpx_cli']['ok']}")

        agent_bin_cmd = [str(CODEX_ACP_BIN), '--help'] if CODEX_ACP_BIN else []
        if not agent_bin_cmd:
            checks['codex_agent_bin'] = {'ok': False, 'detail': 'missing CODEX_ACP_BIN'}
        else:
            rc, out, timed_out = run_selftest_command(agent_bin_cmd, 15)
            log_codex(f'[taskcaptain] self-test command finished: codex_agent_bin rc={rc} timedOut={timed_out}')
            if timed_out:
                checks['codex_agent_bin'] = {'ok': False, 'detail': f'timed out after 15 seconds: {" ".join(agent_bin_cmd)}'}
            else:
                detail = (out or '').strip()[-500:]
                checks['codex_agent_bin'] = {'ok': rc == 0 and ('Usage:' in out or 'Override a configuration value' in out), 'detail': detail}
        log_claw(f"Self-test codex_agent_bin: {checks['codex_agent_bin']['ok']}")

        agent_cmd = build_codex_agent_command(cfg, extra_configs=['sandbox_permissions=["disk-full-read-access"]'])
        if agent_cmd:
            prompt_cmd = [str(ACPX), '--cwd', product_folder, '--approve-all', '--non-interactive-permissions', 'deny', '--agent', agent_cmd, 'exec', 'Reply with exactly SELFTEST_CODEX_OK']
        else:
            prompt_cmd = [str(ACPX), '--cwd', product_folder, '--approve-all', '--non-interactive-permissions', 'deny', 'codex', 'exec', 'Reply with exactly SELFTEST_CODEX_OK']

        rc, out, timed_out = run_selftest_command(prompt_cmd, 60)
        log_codex(f'[taskcaptain] self-test command finished: codex_prompt rc={rc} timedOut={timed_out}')
        if timed_out:
            checks['codex_prompt'] = {'ok': False, 'detail': f'timed out after 60 seconds: {" ".join(prompt_cmd)}'}
        else:
            checks['codex_prompt'] = {'ok': rc == 0 and 'SELFTEST_CODEX_OK' in out, 'detail': out[-500:]}
        log_claw(f"Self-test codex_prompt: {checks['codex_prompt']['ok']}")

        overall = (
            checks['agent_config']['ok']
            and checks['agent_connection']['ok']
            and checks['product_folder']['ok']
            and checks['acpx_cli']['ok']
            and checks['codex_agent_bin']['ok']
            and checks['codex_prompt']['ok']
        )
        record_self_test('passed' if overall else 'failed')
        append_user_claw_message(product_id, 'claw', f"Self-test finished: {'passed' if overall else 'failed'}.")
        log_claw(f"Self-test finished: {'passed' if overall else 'failed'}.")
    except Exception as e:
        checks['internal_error'] = {'ok': False, 'detail': str(e)}
        record_self_test('failed')
        append_user_claw_message(product_id, 'claw', 'Self-test finished: failed.')
        log_claw(f'Self-test failed with exception: {e}')
    finally:
        info = active_self_test_info(product_id)
        if info is not None:
            for proc in info.get('procs', []):
                terminate_process_tree(proc)
        clear_active_self_test(product_id)


def run_codex_command(
    cmd: list[str],
    env: dict,
    timeout_seconds: int | None,
    stop_event: threading.Event,
    product_id: str,
    progress_probe=None,
    on_stdout_line=None,
    on_stderr_line=None,
    idle_grace_seconds: int = 1800,
    hard_deadlock_seconds: int | None = 43200,
    poll_seconds: float = 2.0,
):
    proc = subprocess.Popen(cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, start_new_session=True, bufsize=1)
    set_active_proc(product_id, proc)
    start = time.time()
    activity = {'stdout': start, 'stderr': start}
    io_lock = threading.Lock()
    stdout_chunks: list[str] = []
    stderr_chunks: list[str] = []

    def reader(stream, chunks: list[str], key: str):
        try:
            while True:
                line = stream.readline()
                if line == '':
                    break
                with io_lock:
                    chunks.append(line)
                    activity[key] = time.time()
                try:
                    if key == 'stdout' and on_stdout_line is not None:
                        on_stdout_line(line)
                    if key == 'stderr' and on_stderr_line is not None:
                        on_stderr_line(line)
                except Exception:
                    pass
        except Exception as e:
            with io_lock:
                chunks.append(f'\n[taskcaptain {key} reader error] {e}\n')
                activity[key] = time.time()

    t_out = threading.Thread(target=reader, args=(proc.stdout, stdout_chunks, 'stdout'), daemon=True)
    t_err = threading.Thread(target=reader, args=(proc.stderr, stderr_chunks, 'stderr'), daemon=True)
    t_out.start()
    t_err.start()

    def combined_output() -> str:
        with io_lock:
            stdout = ''.join(stdout_chunks)
            stderr = ''.join(stderr_chunks)
        return stdout + (("\n" + stderr) if stderr else '')

    last_probe_value = None
    last_probe_at = start
    if progress_probe is not None:
        try:
            last_probe_value = progress_probe()
        except Exception as e:
            last_probe_value = {'probeError': str(e)}

    while True:
        if stop_event.is_set():
            terminate_process_tree(proc)
            t_out.join(timeout=2)
            t_err.join(timeout=2)
            return -15, combined_output(), True

        now = time.time()
        if progress_probe is not None:
            try:
                probe_value = progress_probe()
            except Exception as e:
                probe_value = {'probeError': str(e)}
            if probe_value != last_probe_value:
                last_probe_value = probe_value
                last_probe_at = now

        if proc.poll() is not None:
            t_out.join(timeout=2)
            t_err.join(timeout=2)
            return proc.returncode, combined_output(), False

        if timeout_seconds is not None and now - start > timeout_seconds:
            terminate_process_tree(proc)
            t_out.join(timeout=2)
            t_err.join(timeout=2)
            return 124, combined_output(), False

        last_activity_at = max(last_probe_at, activity['stdout'], activity['stderr'])
        if idle_grace_seconds and now - last_activity_at > idle_grace_seconds:
            terminate_process_tree(proc)
            t_out.join(timeout=2)
            t_err.join(timeout=2)
            out = combined_output()
            out += f"\n[taskcaptain] terminated after {int(now - last_activity_at)}s with no progress evidence."
            return 124, out, False

        if hard_deadlock_seconds is not None and now - start > hard_deadlock_seconds:
            terminate_process_tree(proc)
            t_out.join(timeout=2)
            t_err.join(timeout=2)
            out = combined_output()
            out += f"\n[taskcaptain] terminated after absolute deadlock guard of {int(hard_deadlock_seconds)}s."
            return 124, out, False

        time.sleep(poll_seconds)


def run_supervision_loop(product_id: str, run_id: str, stop_event: threading.Event) -> None:
    d = product_dir(product_id)
    cfg = load_product_config(product_id)
    claw_log = d / 'logs' / 'claw.log'
    codex_log = d / 'logs' / 'codex.log'

    def set_state(**kwargs):
        st = load_product_state(product_id)
        st.update(kwargs)
        st['updatedAt'] = now_iso()
        save_product_state(product_id, st)

    def log_claw(text: str):
        append_log(claw_log, f'[{now_iso()}] {text}')

    def log_codex(text: str):
        append_log(codex_log, f'[{now_iso()}] {text}')

    cfg, workspace_ok, workspace_detail = prepare_workspace(product_id, cfg)
    product_folder = cfg.get('productFolder') or '/tmp'
    codex = cfg.get('codex', {})
    claw_eff = effective_claw_config(cfg)
    network = effective_network_config(cfg)
    env = build_codex_env(cfg)

    def workspace_snapshot(max_files: int = 120, max_depth: int = 4) -> str:
        root = Path(product_folder)
        if not root.exists():
            return f'(workspace missing) {product_folder}'
        ignore = {'.git', 'node_modules', '__pycache__', '.venv', 'venv', '.idea', '.pytest_cache', 'dist', 'build'}
        lines = []
        truncated = False
        try:
            for path in sorted(root.rglob('*')):
                try:
                    rel = path.relative_to(root)
                except Exception:
                    continue
                if any(part in ignore for part in rel.parts):
                    continue
                if path.is_dir():
                    continue
                if len(rel.parts) > max_depth:
                    truncated = True
                    continue
                try:
                    size = path.stat().st_size
                except Exception:
                    size = 0
                lines.append(f'- {rel.as_posix()} ({size} bytes)')
                if len(lines) >= max_files:
                    truncated = True
                    break
        except Exception as e:
            return f'(workspace snapshot error: {e})'
        if not lines:
            return '(workspace is empty)'
        if truncated:
            lines.append(f'- … truncated after {len(lines)} entries')
        return '\n'.join(lines)

    def workspace_material_files(max_depth: int = 4) -> list[str]:
        root = Path(product_folder)
        if not root.exists():
            return []
        ignore_dirs = {'.git', 'node_modules', '__pycache__', '.venv', 'venv', '.idea', '.pytest_cache', 'dist', 'build'}
        ignore_names = {'.DS_Store'}
        ignore_prefixes = {'.w', '.probe_', '.tc_'}
        files: list[str] = []
        try:
            for path in sorted(root.rglob('*')):
                try:
                    rel = path.relative_to(root)
                except Exception:
                    continue
                if any(part in ignore_dirs for part in rel.parts):
                    continue
                if path.is_dir():
                    continue
                if len(rel.parts) > max_depth:
                    continue
                name = path.name
                if name in ignore_names:
                    continue
                if any(name.startswith(prefix) for prefix in ignore_prefixes):
                    continue
                files.append(rel.as_posix())
        except Exception:
            return []
        return files

    def build_file_delta(before: list[str], after: list[str]) -> str:
        before_set = set(before)
        after_set = set(after)
        added = sorted(after_set - before_set)
        removed = sorted(before_set - after_set)
        kept = sorted(after_set & before_set)
        lines = []
        if added:
            lines.append('Added files:')
            lines.extend(f'- {x}' for x in added[:40])
        if removed:
            lines.append('Removed files:')
            lines.extend(f'- {x}' for x in removed[:20])
        if kept and not added and not removed:
            lines.append('No material file delta detected.')
        return '\n'.join(lines) if lines else 'No material file delta detected.'

    def workspace_progress_signature() -> dict:
        root = Path(product_folder)
        files = workspace_material_files()
        sample = []
        total_size = 0
        newest_mtime = 0.0
        for rel in files[:80]:
            path = root / rel
            try:
                stat = path.stat()
                total_size += stat.st_size
                newest_mtime = max(newest_mtime, stat.st_mtime)
                sample.append((rel, stat.st_size, int(stat.st_mtime)))
            except Exception:
                sample.append((rel, None, None))
        progress_path = root / '.taskcaptain' / 'progress.json'
        progress_blob = None
        if progress_path.exists():
            try:
                progress_blob = progress_path.read_text(encoding='utf-8', errors='ignore')[:4000]
            except Exception as e:
                progress_blob = f'progress-read-error:{e}'
        return {
            'filesCount': len(files),
            'filesSample': sample,
            'totalSize': total_size,
            'newestMtime': int(newest_mtime) if newest_mtime else 0,
            'progressBlob': progress_blob,
        }

    def default_codex_task(turn: int, files: list[str]) -> str:
        if project_kind == 'algorithm_research':
            if not files:
                return (
                    f"Work on the algorithm/research task '{cfg.get('name')}' inside the current working directory.\n"
                    f"Goal: {cfg.get('goal')}\n"
                    "The workspace is empty. First create concrete research artifacts immediately instead of only discussing ideas.\n"
                    "Create at minimum: README.md plus one or more of: notes.md, experiment_plan.md, benchmark.py, prototype.py, analysis.md.\n"
                    "Your task is to make the idea testable: formalize the hypothesis, define success/failure criteria, add a benchmark or experiment scaffold, and produce an initial implementation/analysis artifact.\n"
                    "A meaningful negative result, inconclusive result, or falsification can still be valuable if clearly supported by evidence.\n"
                    "Reply with a concise summary of CHANGES, VERIFICATION, and REMAINING."
                )
            return (
                f"Continue the algorithm/research task '{cfg.get('name')}' in the current working directory.\n"
                f"Goal: {cfg.get('goal')}\n"
                "Prefer producing stronger evidence over polishing prose: improve the prototype, run benchmarks, tighten reasoning, compare alternatives, or document why the idea does or does not work.\n"
                "Reply with a concise summary of CHANGES, VERIFICATION, and REMAINING blockers."
            )
        if not files:
            return (
                f"Build the smallest runnable demo for '{cfg.get('name')}' inside the current working directory.\n"
                f"Goal: {cfg.get('goal')}\n"
                "The workspace is empty. Your priority is to create real files immediately instead of planning only.\n"
                "Create at minimum: README.md, index.html, app.js, styles.css.\n"
                "Prefer a static implementation with seeded demo data unless a backend is clearly required by the goal.\n"
                "Do one bounded verification command after creating files, then reply with a concise summary of CHANGES, VERIFICATION, and REMAINING."
            )
        return (
            f"Continue implementing '{cfg.get('name')}' in the current working directory.\n"
            f"Goal: {cfg.get('goal')}\n"
            "Read the existing workspace first, then make the highest-value next changes.\n"
            "Run only bounded verification commands.\n"
            "Reply with a concise summary of CHANGES, VERIFICATION, and REMAINING blockers."
        )

    def call_claw_json(stage: str, user_prompt: str, timeout_seconds: int = 120) -> tuple[dict, str]:
        system_prompt = (
            f"You are {claw_eff.get('profileName')}, the product manager, researcher, supervisor, and acceptance lead for TaskCaptain.\n"
            f"Soul: {claw_eff.get('soul')}\n"
            f"Skills: {claw_eff.get('skills')}\n"
            "Your job is to drive an autonomous delivery loop: understand the requirement, inspect evidence, decide what Codex should do next, and decide whether the product is delivered or failed.\n"
            "Codex is the implementation agent. You are not Codex. Do not pretend to have edited files yourself.\n"
            "Assume Codex can execute shell commands inside the product folder. If the user enabled MaxPermission for Codex, Codex is allowed to install dependencies (prefer local venv) and run real tests/benchmarks to produce evidence.\n"
            "For goals that explicitly require empirical comparison (benchmarks / performance / 跑分 / 对比), do NOT treat placeholder templates as sufficient: require executed result artifacts (CSV/MD/logs) or a rigorously supported negative/inconclusive finding backed by actual runs.\n"
            "If execution is blocked by missing dependencies or environment setup, instruct Codex to fix the environment and rerun.\n"
            "Be strict and evidence-based. Do not declare delivery unless the workspace and verification evidence justify it.\n"
            "Respond with JSON only, no markdown fences."
        )
        effort = normalize_effort(claw_eff.get('thinking'))
        # Prefer /responses so reasoning.effort can take effect; fall back to /chat/completions if needed.
        try:
            combined_input = system_prompt + '\n\n' + user_prompt
            text, raw = openai_responses(
                claw_eff.get('endpoint', ''),
                claw_eff.get('apiKey', ''),
                claw_eff.get('model', '') or DEFAULT_PROFILE_ID,
                combined_input,
                reasoning_effort=effort,
                timeout=timeout_seconds,
                proxy=network.get('proxy'),
                no_proxy=network.get('noProxy'),
            )
        except Exception:
            text, raw = openai_chat_completion(
                claw_eff.get('endpoint', ''),
                claw_eff.get('apiKey', ''),
                claw_eff.get('model', '') or DEFAULT_PROFILE_ID,
                [
                    {'role': 'system', 'content': system_prompt},
                    {'role': 'user', 'content': user_prompt},
                ],
                timeout=timeout_seconds,
                proxy=network.get('proxy'),
                no_proxy=network.get('noProxy'),
            )
        usage = raw.get('usage') if isinstance(raw, dict) else None
        if usage:
            log_claw(f"Claw {stage} usage: {json.dumps(usage, ensure_ascii=False)}")
        parsed = extract_json_object(text) or {}
        if not isinstance(parsed, dict):
            parsed = {}
        log_claw(f'Claw {stage} raw output:\n{text}')
        return parsed, text

    try:
        if not workspace_ok:
            log_claw(f'Workspace prepare failed before run: {workspace_detail}')
            append_user_claw_message(product_id, 'claw', f'Workspace prepare failed before run: {workspace_detail}')
            set_state(status='failed', lastError=workspace_detail, stopRequested=False)
            return
        log_claw(f'Starting run {run_id}. Goal: {cfg.get("goal", "")}'.strip())
        log_claw(f'Workspace {workspace_detail}.')
        log_claw(f"Execution policy: Claw is the product manager / planner / reviewer / acceptance lead; Codex is the implementation executor inside the product folder.")
        append_user_claw_message(product_id, 'claw', f"{claw_eff.get('profileName')} started run {run_id}. I will plan, review, and decide delivery based on evidence while Codex implements.")
        append_claw_codex_message(product_id, 'claw', f"Run {run_id} opened. Claw supervisor identity: {claw_eff.get('profileName')}.")
        log_claw('Using one-shot Codex exec path with Claw-led plan/review loop.')
        if codex.get('maxPermission'):
            log_claw('Using approve-all permission mode for Codex runs.')

        st = load_product_state(product_id)
        user_context = summarize_user_claw_messages(st)
        project_kind = infer_project_kind(cfg, user_context)
        acceptance_profile = project_acceptance_profile(project_kind)
        progress_idle_grace = int(os.environ.get('TASKCAPTAIN_PROGRESS_IDLE_GRACE_SECONDS', '1800'))
        progress_deadlock_guard = int(os.environ.get('TASKCAPTAIN_PROGRESS_DEADLOCK_SECONDS', '43200'))
        progress_poll_seconds = float(os.environ.get('TASKCAPTAIN_PROGRESS_POLL_SECONDS', '2'))
        cmd_prefix = [str(ACPX), '--cwd', product_folder, '--ttl', '30']
        if codex.get('maxPermission'):
            cmd_prefix += ['--approve-all', '--non-interactive-permissions', 'deny']

        initial_snapshot = workspace_snapshot()
        initial_files = workspace_material_files()
        plan_prompt = (
            f"Stage: initial_planning\n"
            f"Project kind: {project_kind}\n"
            f"Product name: {cfg.get('name')}\n"
            f"Goal: {cfg.get('goal')}\n"
            f"Codex MaxPermission: {bool(codex.get('maxPermission'))}\n"
            f"User requests so far:\n{user_context}\n\n"
            f"Current workspace snapshot:\n{initial_snapshot}\n\n"
            f"Delivery bar for this project type:\n{json.dumps(acceptance_profile.get('delivery_bar', []), ensure_ascii=False)}\n\n"
            f"Stretch bar for this project type:\n{json.dumps(acceptance_profile.get('stretch_bar', []), ensure_ascii=False)}\n\n"
            f"Verification focus:\n{acceptance_profile.get('verification_focus', '')}\n\n"
            "Return JSON with exactly these fields: decision, summary, phased_plan, acceptance_checks, codex_task, failure_reason.\n"
            "- decision must be one of: delegate, deliver, fail\n"
            "- phased_plan: list of short stage bullets\n"
            "- acceptance_checks: list of concrete checks focused on the delivery bar first\n"
            "- codex_task: the exact next implementation brief for Codex if decision=delegate\n"
            "- do not treat stretch-bar items as mandatory blockers when delivery-bar evidence can already justify delivery\n"
            "If the workspace is effectively empty, codex_task must force immediate file creation and a minimal runnable scaffold before polish."
        )
        plan, plan_raw = call_claw_json('plan', plan_prompt, timeout_seconds=120)
        plan_decision = (plan.get('decision') or '').strip().lower()
        acceptance_checks = plan.get('acceptance_checks') if isinstance(plan.get('acceptance_checks'), list) else []
        phased_plan = plan.get('phased_plan') if isinstance(plan.get('phased_plan'), list) else []
        if phased_plan:
            append_user_claw_message(product_id, 'claw', 'Claw initial plan:\\n' + '\\n'.join(f'- {x}' for x in phased_plan[:8]))
        if acceptance_checks:
            append_user_claw_message(product_id, 'claw', 'Claw acceptance checks:\\n' + '\\n'.join(f'- {x}' for x in acceptance_checks[:8]))
        if plan_decision == 'deliver':
            set_state(status='delivered', stopRequested=False)
            append_user_claw_message(product_id, 'claw', plan.get('summary') or 'Claw judged the product already delivered at planning stage.')
            return
        if plan_decision == 'fail':
            set_state(status='failed', lastError=plan.get('failure_reason') or 'claw planning failed the task', stopRequested=False)
            append_user_claw_message(product_id, 'claw', plan.get('summary') or 'Claw judged the task should fail at planning stage.')
            return

        current_codex_task = (plan.get('codex_task') or '').strip() or default_codex_task(1, initial_files)
        last_codex_excerpt = ''

        max_turns = 8
        try:
            max_turns = int(cfg.get('maxTurns') or 8)
        except Exception:
            max_turns = 8
        if max_turns < 1:
            max_turns = 1
        if max_turns > 99:
            max_turns = 99

        for turn in range(1, max_turns + 1):
            if stop_event.is_set():
                log_claw('Stop requested before next Codex turn. Marking stopped.')
                append_user_claw_message(product_id, 'claw', f"{claw_eff.get('profileName')} stopped before dispatching the next Codex turn.")
                set_state(status='stopped', stopRequested=True)
                return

            set_state(status='running', stopRequested=False, currentTurn=turn)
            before_files = workspace_material_files()
            before_snapshot = workspace_snapshot()
            codex_dispatch = (
                f"You are Codex, the implementation executor for task '{cfg.get('name')}'.\n"
                f"Goal: {cfg.get('goal')}\n"
                f"Work only inside: {product_folder}\n"
                "Claw is your product manager and acceptance lead. Follow Claw's brief exactly.\n"
                "Do real implementation work in files, not planning-only output.\n"
                "Use bounded verification only; do not start long-lived servers or watchers.\n"
                "If Codex MaxPermission is enabled, you are allowed to set up the environment inside the product folder: create a local venv (e.g. .venv), install dependencies (pip/uv), and run real tests/benchmarks to produce evidence artifacts (CSV/MD/logs). Do not defer execution to the user when you have permission.\n"
                "If you need Python, prefer /usr/bin/python3 (system python) for best wheel compatibility.\n"
                "Create and maintain a lightweight progress checkpoint at .taskcaptain/progress.json while you work.\n"
                "That checkpoint should contain useful JSON such as current_stage, current_task, changed_files, blockers, and updated_at. Update it whenever you meaningfully progress.\n"
                "If you are thinking for a long time, refresh the progress checkpoint before and after major substeps so the supervisor can distinguish healthy deep work from a stall.\n"
                "At the end, reply with three short sections titled CHANGES, VERIFICATION, and REMAINING.\n\n"
                f"Claw brief for this turn:\n{current_codex_task}\n"
            )
            log_claw(f'Dispatching Codex implementation turn {turn}.')
            append_claw_codex_message(product_id, 'claw', f"Implementation turn {turn}. Claw brief:\n{current_codex_task[:3000]}")
            extra_configs: list[str] = []
            if codex.get('maxPermission'):
                # Full-access mode: allow Codex to run commands, write artifacts, and install deps without sandbox restrictions.
                extra_configs += ['sandbox_mode="danger-full-access"', 'network_access="enabled"']
            agent_cmd = build_codex_agent_command(cfg, extra_configs=extra_configs)
            if agent_cmd:
                run_cmd = cmd_prefix + ['--agent', agent_cmd, 'exec', codex_dispatch]
            else:
                run_cmd = cmd_prefix + ['codex', 'exec', codex_dispatch]

            rc, out, was_stopped = run_codex_command(
                run_cmd,
                env,
                None,
                stop_event,
                product_id,
                progress_probe=None,
                on_stdout_line=lambda line: append_log(codex_log, f'[{now_iso()}] ' + line.rstrip()),
                on_stderr_line=lambda line: append_log(codex_log, f'[{now_iso()}] [stderr] ' + line.rstrip()),
                idle_grace_seconds=progress_idle_grace,
                hard_deadlock_seconds=progress_deadlock_guard,
                poll_seconds=progress_poll_seconds,
            )
            log_codex(f'[taskcaptain] codex exec finished rc={rc} stopped={was_stopped}')
            codex_dialogue_text = extract_codex_dialogue_text(out, max_chars=5000)
            append_claw_codex_message(product_id, 'codex', codex_dialogue_text)
            append_legacy_codex_conversation(product_id, codex_dialogue_text)
            set_active_proc(product_id, None)
            if out.strip():
                last_codex_excerpt = out[-4000:]

            if was_stopped:
                log_claw('Codex run stopped by user request. Marking stopped.')
                append_user_claw_message(product_id, 'claw', f"{claw_eff.get('profileName')} confirmed the Codex run was stopped by user request.")
                set_state(status='stopped', stopRequested=True)
                return

            after_files = workspace_material_files()
            after_snapshot = workspace_snapshot()
            file_delta = build_file_delta(before_files, after_files)
            review_prompt = (
                f"Stage: review_after_codex_turn\n"
                f"Project kind: {project_kind}\n"
                f"Product name: {cfg.get('name')}\n"
                f"Goal: {cfg.get('goal')}\n"
                f"Codex MaxPermission: {bool(codex.get('maxPermission'))}\n"
                f"Turn: {turn}\n"
                f"Known acceptance checks: {json.dumps(acceptance_checks, ensure_ascii=False)}\n"
                f"Delivery bar: {json.dumps(acceptance_profile.get('delivery_bar', []), ensure_ascii=False)}\n"
                f"Stretch bar: {json.dumps(acceptance_profile.get('stretch_bar', []), ensure_ascii=False)}\n"
                f"Verification focus: {acceptance_profile.get('verification_focus', '')}\n\n"
                f"Workspace snapshot before turn:\n{before_snapshot}\n\n"
                f"Workspace snapshot after turn:\n{after_snapshot}\n\n"
                f"Material file delta:\n{file_delta}\n\n"
                f"Codex exit code: {rc}\n"
                f"Progress idle grace seconds: {progress_idle_grace}\n"
                f"Progress deadlock guard seconds: {progress_deadlock_guard}\n"
                f"Workspace progress signature after turn: {json.dumps(workspace_progress_signature(), ensure_ascii=False)}\n"
                f"Codex output excerpt:\n{last_codex_excerpt[-3000:]}\n\n"
                "Return JSON with exactly these fields: decision, summary, evidence, next_codex_task, delivery_summary, failure_reason.\n"
                "- decision must be one of: delegate, deliver, fail\n"
                "- evidence must be a short list of concrete observations from files/logs/output\n"
                "- next_codex_task must be the next specific implementation brief if decision=delegate\n"
                "- first judge whether the current evidence already satisfies the delivery bar for this project type\n"
                "- do not block delivery only because stretch-bar items are missing if the delivery bar is already met\n"
                "- for algorithm/research/theoretical work, a meaningful negative result, inconclusive result, benchmark finding, or falsified idea can still be a valid delivery if it is rigorous and useful\n"
                "- fail only if progress is blocked or evidence shows the current goal cannot be met reasonably"
            )
            review, review_raw = call_claw_json('review', review_prompt, timeout_seconds=120)
            decision = (review.get('decision') or '').strip().lower()
            summary = (review.get('summary') or '').strip()
            evidence = review.get('evidence') if isinstance(review.get('evidence'), list) else []
            if summary:
                append_user_claw_message(product_id, 'claw', f"Turn {turn} review: {summary}")
            if evidence:
                append_user_claw_message(product_id, 'claw', 'Evidence:\\n' + '\\n'.join(f'- {x}' for x in evidence[:8]))

            if decision == 'deliver':
                delivery_summary = (stringify_for_log(review.get('delivery_summary')) or summary or 'Claw judged the product delivered based on workspace evidence.').strip()
                log_claw(f'Claw marked product delivered on turn {turn}.')
                append_user_claw_message(product_id, 'claw', delivery_summary)
                set_state(status='delivered', lastError=None, stopRequested=False)
                return
            if decision == 'fail':
                failure_reason = (review.get('failure_reason') or summary or 'Claw marked the task failed after review.').strip()
                log_claw(f'Claw marked product failed on turn {turn}: {failure_reason}')
                append_user_claw_message(product_id, 'claw', failure_reason)
                set_state(status='failed', lastError=failure_reason, stopRequested=False)
                return

            next_task = (review.get('next_codex_task') or '').strip()
            if not next_task:
                next_task = default_codex_task(turn + 1, after_files)
                log_claw(f'Claw review did not provide next_codex_task on turn {turn}; using fallback task.')
            current_codex_task = next_task
            set_state(status='running', stopRequested=False, lastError=f'awaiting next iteration after turn {turn}')
            time.sleep(2)

        log_claw('Reached Claw supervision turn limit without delivery/final failure. Marking failed for now.')
        append_user_claw_message(product_id, 'claw', 'Claw supervision turn limit reached without delivery or final failure. Product marked failed for now.')
        set_state(status='failed', lastError=f'claw supervision turn limit reached (maxTurns={max_turns})', stopRequested=False)
    except Exception as e:
        log_claw(f'Run failed with exception: {e}')
        append_user_claw_message(product_id, 'claw', f'Run failed with exception: {e}')
        set_state(status='failed', lastError=str(e), stopRequested=False)
    finally:
        try:
            st_final = load_product_state(product_id)
            if st_final.get('status') == 'running':
                log_claw('Run is exiting while state is still running; applying reconcile fallback.')
                append_user_claw_message(product_id, 'claw', 'Run exited without a terminal state. Applying reconcile fallback based on the latest evidence.')
                if workspace_material_files():
                    set_state(status='failed', lastError='run exited without terminal decision; manual review recommended', stopRequested=False)
                else:
                    set_state(status='failed', lastError='run exited without producing deliverable evidence', stopRequested=False)
        except Exception as reconcile_error:
            log_claw(f'Reconcile fallback failed: {reconcile_error}')
        clear_active_run(product_id)


#!/usr/bin/env python3
from __future__ import annotations

import html
from datetime import datetime

try:
    from tc_core import I18N, load_product_config, load_product_state, product_dir, t
    from tc_fastview import fastview_backend_name, format_bytes, list_workspace_artifacts, tail_text
    from tc_runtime import active_run_info, extract_codex_dialogue_text
    from tc_ui import badge_class_for
except ModuleNotFoundError:
    from app.tc_core import I18N, load_product_config, load_product_state, product_dir, t
    from app.tc_fastview import fastview_backend_name, format_bytes, list_workspace_artifacts, tail_text
    from app.tc_runtime import active_run_info, extract_codex_dialogue_text
    from app.tc_ui import badge_class_for


def render_dialogue(items: list[dict], empty_text: str) -> str:
    if not items:
        return f"<div class='flex-1 flex items-center justify-center p-8'><div class=\"text-center p-6 border border-dashed border-slate-300 dark:border-zinc-700 rounded-xl text-slate-500 dark:text-zinc-400 text-sm\">{html.escape(empty_text)}</div></div>"
    rows = []
    for x in items:
        role = x.get('role', '')
        is_user = role == 'user'
        if is_user:
            bubble_class = 'chat-bubble-user w-[85%] ml-auto bg-brand-50 border border-brand-100 dark:bg-brand-900/20 dark:border-brand-800/50 p-3.5 rounded-2xl shadow-sm'
            role_class = 'text-brand-600 dark:text-brand-400'
            role_display = 'USER'
        else:
            bubble_class = 'chat-bubble-bot w-[85%] bg-white dark:bg-zinc-800 border border-slate-200 dark:border-zinc-700 p-3.5 rounded-2xl shadow-sm'
            role_class = 'text-emerald-600 dark:text-emerald-400' if role == 'claw' else 'text-slate-500 dark:text-zinc-400'
            role_display = 'AGENT' if role == 'claw' else role.upper()
            if role == 'codex':
                bubble_class = 'chat-bubble-user w-[90%] ml-auto bg-slate-100 border border-slate-200 dark:bg-zinc-800 dark:border-zinc-700 p-3.5 rounded-2xl shadow-sm text-slate-700 dark:text-slate-300'

        if role == 'claw':
            header_content = f"<span class='text-xs font-bold {role_class} tracking-wider'>{html.escape(role_display)}</span><span class='text-[10px] font-mono text-slate-400'>{html.escape(x.get('ts', ''))}</span>"
        else:
            header_content = f"<span class='text-[10px] font-mono text-slate-400'>{html.escape(x.get('ts', ''))}</span><span class='text-xs font-bold {role_class} tracking-wider'>{html.escape(role_display)}</span>"

        rows.append(
            f"""
        <div class='{bubble_class} mb-4'>
          <div class='flex justify-between items-end mb-2'>
            {header_content}
          </div>
          <div class='text-sm font-mono leading-relaxed break-words whitespace-pre-wrap'>{html.escape(x.get('text', ''))}</div>
        </div>
        """
        )
    return ''.join(rows)


def render_checks_html(checks: dict, lang: str) -> str:
    return ''.join(
        f"<tr class='border-b border-slate-100 dark:border-zinc-800 last:border-0'><td class='py-3 pr-4 font-semibold text-sm'>{html.escape(k)}</td><td class='py-3 px-4'><span class='inline-flex items-center px-2 py-0.5 rounded text-xs font-bold {'bg-emerald-100 text-emerald-700 dark:bg-emerald-500/20 dark:text-emerald-400' if v.get('ok') else 'bg-red-100 text-red-700 dark:bg-red-500/20 dark:text-red-400'}'>{'Pass' if v.get('ok') else 'Fail'}</span></td><td class='py-3 pl-4 font-mono text-xs text-slate-500 break-all'>{html.escape(str(v.get('detail', '')))}</td></tr>"
        for k, v in checks.items()
    ) or f"<tr><td colspan='3' class='py-4 text-slate-500 text-center text-sm'>{html.escape(t(lang, 'not_run'))}</td></tr>"


def _format_mtime(epoch: int) -> str:
    try:
        return datetime.fromtimestamp(epoch).strftime('%Y-%m-%d %H:%M')
    except Exception:
        return '-'


def render_artifacts_html(items: list[dict], lang: str) -> str:
    if not items:
        return f"<div class='rounded-xl border border-dashed border-slate-300 dark:border-zinc-700 p-4 text-sm text-slate-500 dark:text-zinc-400'>{html.escape(t(lang, 'no_artifacts'))}</div>"

    rows = []
    for item in items:
        rows.append(
            f"""
            <div class='flex items-start justify-between gap-3 rounded-xl border border-slate-200 dark:border-zinc-800 bg-slate-50/60 dark:bg-zinc-900/30 px-3 py-3'>
              <div class='min-w-0'>
                <div class='font-mono text-xs text-slate-700 dark:text-slate-300 break-all'>{html.escape(item.get('path', ''))}</div>
                <div class='mt-1 text-[11px] text-slate-500 dark:text-zinc-400'>{html.escape(format_bytes(int(item.get('size') or 0)))} · {html.escape(_format_mtime(int(item.get('mtime') or 0)))}</div>
              </div>
              <button type='button' class='shrink-0 text-[11px] font-semibold px-2.5 py-1 rounded-lg border border-slate-200 dark:border-zinc-700 bg-white dark:bg-zinc-800 hover:bg-slate-100 dark:hover:bg-zinc-700 transition copy-btn' data-copy-text='{html.escape(item.get("fullPath", ""))}'>{html.escape(t(lang, 'copy_path'))}</button>
            </div>
            """
        )
    return ''.join(rows)


def _log_note(lang: str, view: dict) -> str:
    return t(
        lang,
        'log_tail_status',
        shown=format_bytes(int(view.get('shownBytes') or 0)),
        total=format_bytes(int(view.get('totalSize') or 0)),
    )


def build_product_live_payload(pid: str, lang: str) -> dict:
    d = product_dir(pid)
    cfg = load_product_config(pid)
    st = load_product_state(pid)
    self_test = st.get('selfTest', {})
    checks = self_test.get('checks', {})
    user_claw = st.get('conversations', {}).get('userClaw', [])[-30:]
    claw_codex = st.get('conversations', {}).get('clawCodex', [])[-30:]
    claw_codex = [
        {
            **item,
            'text': extract_codex_dialogue_text(item.get('text', '')) if item.get('role') == 'codex' else item.get('text', ''),
        }
        for item in claw_codex
    ]
    status = st.get('status', 'idle')
    st_status = self_test.get('status', 'not-run')
    is_running = status == 'running' and bool(active_run_info(pid))
    claw_log_view = tail_text(d / 'logs' / 'claw.log')
    codex_log_view = tail_text(d / 'logs' / 'codex.log')
    artifacts = list_workspace_artifacts(cfg.get('productFolder'), limit=10)
    fastview_backend = 'rust' if 'rust' in {fastview_backend_name(), artifacts.get('backend'), claw_log_view.get('backend'), codex_log_view.get('backend')} else 'python'

    return {
        'status': status,
        'statusLabel': t(lang, status) if status in I18N[lang] else status,
        'statusClass': badge_class_for(status),
        'currentTurn': int(st.get('currentTurn') or 0),
        'maxTurns': int(cfg.get('maxTurns') or 8),
        'updatedAt': st.get('updatedAt') or '',
        'selfTestStatus': st_status,
        'selfTestStatusLabel': t(lang, st_status) if st_status in I18N[lang] else st_status,
        'selfTestStatusClass': badge_class_for(st_status),
        'selfTestRunning': st_status == 'running',
        'isRunning': is_running,
        'userClawHtml': render_dialogue(user_claw, t(lang, 'no_user_claw')),
        'clawCodexHtml': render_dialogue(claw_codex, t(lang, 'no_claw_codex')),
        'checksHtml': render_checks_html(checks, lang),
        'artifactCount': int(artifacts.get('totalFiles') or 0),
        'artifactHtml': render_artifacts_html(artifacts.get('items') or [], lang),
        'fastviewLabel': t(lang, 'rust_fast_path') if fastview_backend == 'rust' else t(lang, 'python_fallback'),
        'tailWindowLabel': t(lang, 'tailing_recent_logs', size=format_bytes(int(claw_log_view.get('shownBytes') or 0))),
        'clawLog': claw_log_view.get('text') or t(lang, 'no_logs'),
        'codexLog': codex_log_view.get('text') or t(lang, 'no_logs'),
        'clawLogNote': _log_note(lang, claw_log_view),
        'codexLogNote': _log_note(lang, codex_log_view),
    }

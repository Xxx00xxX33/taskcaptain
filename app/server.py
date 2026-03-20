#!/usr/bin/env python3
from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, quote, urlparse

# When launched as `python3 app/server.py`, imports resolve as top-level sibling modules.
# When imported from elsewhere, fall back to `app.*` package imports.
try:
    from tc_core import (
        DEFAULT_LANG,
        HOST,
        PORT,
        DEFAULT_NO_PROXY,
        append_log,
        create_product,
        effective_claw_config,
        ensure_default_profile,
        load_product_config,
        normalize_lang,
        now_iso,
        product_dir,
        save_claw_profile_from_form,
        save_product_config,
    )
    from tc_live import build_product_live_payload
    from tc_pages import render_index_page, render_product_page
    from tc_runtime import (
        append_user_claw_message,
        delete_product,
        save_current_product_claw_as_profile,
        start_run,
        start_self_test,
        stop_run,
    )
except ModuleNotFoundError:  # pragma: no cover
    from app.tc_core import (
        DEFAULT_LANG,
        HOST,
        PORT,
        DEFAULT_NO_PROXY,
        append_log,
        create_product,
        effective_claw_config,
        ensure_default_profile,
        load_product_config,
        normalize_lang,
        now_iso,
        product_dir,
        save_claw_profile_from_form,
        save_product_config,
    )
    from app.tc_live import build_product_live_payload
    from app.tc_pages import render_index_page, render_product_page
    from app.tc_runtime import (
        append_user_claw_message,
        delete_product,
        save_current_product_claw_as_profile,
        start_run,
        start_self_test,
        stop_run,
    )


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        lang = normalize_lang(parse_qs(parsed.query).get('lang', [DEFAULT_LANG])[0])
        if parsed.path == '/':
            return self.send_html(render_index_page(lang))
        if parsed.path.startswith('/product/'):
            pid = parsed.path.split('/')[-1]
            return self.send_html(render_product_page(pid, lang))
        if parsed.path == '/api/product-live':
            # Back-compat alias (older frontend polling).
            pid = parse_qs(parsed.query).get('id', [''])[0]
            if pid:
                return self.send_json(build_product_live_payload(pid, lang))
            return self.send_json({'error': 'missing id'})
        if parsed.path.startswith('/api/product-live/'):
            pid = parsed.path.split('/')[-1]
            return self.send_json(build_product_live_payload(pid, lang))
        self.send_error(404)

    def do_POST(self):
        parsed = urlparse(self.path)
        length = int(self.headers.get('Content-Length', '0'))
        raw = self.rfile.read(length).decode('utf-8')
        parsed_form = parse_qs(raw)
        form = {k: v[0] for k, v in parsed_form.items()}
        lang = normalize_lang(form.get('lang'))

        if parsed.path == '/create':
            pid = create_product(form)
            self.redirect(f'/product/{pid}?lang={lang}')
            return
        if parsed.path == '/profiles/create':
            save_claw_profile_from_form(form)
            self.redirect(f'/?lang={lang}')
            return

        if parsed.path == '/bulk-delete':
            for pid in parsed_form.get('productIds', []):
                try:
                    delete_product(pid)
                except Exception:
                    pass
            self.redirect(f'/?lang={lang}')
            return

        if parsed.path.startswith('/set-claw-thinking/'):
            pid = parsed.path.split('/')[-1]
            cfg = load_product_config(pid)
            v = (form.get('thinking') or '').strip().lower()
            if v and v not in {'low', 'medium', 'high', 'xhigh'}:
                v = ''
            cfg.setdefault('claw', {})['thinking'] = v
            save_product_config(pid, cfg)
            append_log(product_dir(pid) / 'logs' / 'claw.log', f"[{now_iso()}] Updated claw thinking/effort to {v or '(inherit)'} via UI.")
            self.redirect(f'/product/{pid}?lang={lang}')
            return

        if parsed.path.startswith('/set-codex-thinking/'):
            pid = parsed.path.split('/')[-1]
            cfg = load_product_config(pid)
            v = (form.get('thinking') or '').strip().lower()
            if v and v not in {'low', 'medium', 'high', 'xhigh'}:
                v = 'medium'
            cfg.setdefault('codex', {})['thinking'] = v
            save_product_config(pid, cfg)
            append_log(product_dir(pid) / 'logs' / 'claw.log', f'[{now_iso()}] Updated codex thinking/effort to {v} via UI.')
            self.redirect(f'/product/{pid}?lang={lang}')
            return

        if parsed.path.startswith('/set-max-turns/'):
            pid = parsed.path.split('/')[-1]
            cfg = load_product_config(pid)
            try:
                v = int((form.get('maxTurns') or '').strip() or str(cfg.get('maxTurns') or 8))
            except Exception:
                v = int(cfg.get('maxTurns') or 8)
            if v < 1:
                v = 1
            if v > 99:
                v = 99
            cfg['maxTurns'] = v
            save_product_config(pid, cfg)
            append_log(product_dir(pid) / 'logs' / 'claw.log', f'[{now_iso()}] Updated maxTurns to {v} via UI.')
            self.redirect(f'/product/{pid}?lang={lang}')
            return

        if parsed.path.startswith('/save-runtime-settings/'):
            pid = parsed.path.split('/')[-1]
            cfg = load_product_config(pid)
            try:
                max_turns = int((form.get('maxTurns') or '').strip() or str(cfg.get('maxTurns') or 8))
            except Exception:
                max_turns = int(cfg.get('maxTurns') or 8)
            if max_turns < 1:
                max_turns = 1
            if max_turns > 99:
                max_turns = 99
            claw_thinking = (form.get('clawThinking') or '').strip().lower()
            codex_thinking = (form.get('codexThinking') or '').strip().lower()
            if claw_thinking and claw_thinking not in {'low', 'medium', 'high', 'xhigh'}:
                claw_thinking = ''
            if codex_thinking not in {'low', 'medium', 'high', 'xhigh'}:
                codex_thinking = cfg.get('codex', {}).get('thinking', 'medium')
            cfg['maxTurns'] = max_turns
            cfg.setdefault('claw', {})['thinking'] = claw_thinking
            cfg.setdefault('codex', {})['thinking'] = codex_thinking
            save_product_config(pid, cfg)
            append_log(
                product_dir(pid) / 'logs' / 'claw.log',
                f'[{now_iso()}] Updated runtime settings via UI: maxTurns={max_turns}, clawThinking={claw_thinking or "(inherit)"}, codexThinking={codex_thinking}.',
            )
            self.redirect(f'/product/{pid}?lang={lang}')
            return

        if parsed.path.startswith('/save-connection-settings/'):
            pid = parsed.path.split('/')[-1]
            cfg = load_product_config(pid)
            claw = cfg.setdefault('claw', {})
            codex = cfg.setdefault('codex', {})
            network = cfg.setdefault('network', {})
            claw['endpoint'] = (form.get('clawEndpoint') or '').strip() or claw.get('endpoint', '')
            claw['apiKey'] = (form.get('clawApiKey') or '').strip()
            codex['endpoint'] = (form.get('codexEndpoint') or '').strip() or codex.get('endpoint', '')
            codex['apiKey'] = (form.get('codexApiKey') or '').strip()
            network['proxy'] = (form.get('proxy') or '').strip()
            network['noProxy'] = (form.get('noProxy') or '').strip() or network.get('noProxy') or DEFAULT_NO_PROXY
            save_product_config(pid, cfg)
            append_log(
                product_dir(pid) / 'logs' / 'claw.log',
                f'[{now_iso()}] Updated connection settings via UI: agentEndpoint={claw.get("endpoint","")}, codexEndpoint={codex.get("endpoint","")}, proxy={network.get("proxy","") or "(direct)"}, noProxy={network.get("noProxy","")}.',
            )
            self.redirect(f'/product/{pid}?lang={lang}')
            return

        if parsed.path.startswith('/start/'):
            pid = parsed.path.split('/')[-1]
            start_run(pid)
            self.redirect(f'/product/{pid}?lang={lang}')
            return
        if parsed.path.startswith('/stop/'):
            pid = parsed.path.split('/')[-1]
            stop_run(pid)
            self.redirect(f'/product/{pid}?lang={lang}')
            return

        if parsed.path.startswith('/delete/'):
            pid = parsed.path.split('/')[-1]
            ok, _ = delete_product(pid)
            self.redirect(f"/?lang={lang}" if ok else f'/product/{pid}?lang={lang}')
            return

        if parsed.path.startswith('/selftest/'):
            pid = parsed.path.split('/')[-1]
            result = start_self_test(pid)
            if result == 'already-running':
                append_user_claw_message(pid, 'claw', 'Self-test request ignored because a self-test is already running for this task.')
                append_log(product_dir(pid) / 'logs' / 'claw.log', f'[{now_iso()}] Ignored duplicate self-test request while a self-test was already running.')
            self.redirect(f'/product/{pid}?lang={lang}')
            return

        if parsed.path.startswith('/append-user/'):
            pid = parsed.path.split('/')[-1]
            text = (form.get('message') or '').strip()
            if text:
                cfg = load_product_config(pid)
                claw_eff = effective_claw_config(cfg)
                append_user_claw_message(pid, 'user', text)
                append_user_claw_message(
                    pid,
                    'claw',
                    f"{claw_eff.get('profileName')} received this instruction and will incorporate it into the next supervision / Codex dispatch cycle.",
                )
                append_log(product_dir(pid) / 'logs' / 'claw.log', f'[{now_iso()}] User -> Agent: {text}')
            self.redirect(f'/product/{pid}?lang={lang}')
            return

        if parsed.path.startswith('/save-profile/'):
            pid = parsed.path.split('/')[-1]
            save_current_product_claw_as_profile(pid, form)
            self.redirect(f'/product/{pid}?lang={lang}')
            return

        self.send_error(404)

    def send_html(self, body: bytes):
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_json(self, obj):
        body = (json.dumps(obj, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def redirect(self, location: str):
        safe_location = quote(location, safe='/:?=&-_.~')
        self.send_response(303)
        self.send_header('Location', safe_location)
        self.end_headers()

    def log_message(self, fmt, *args):
        return


def main():
    ensure_default_profile()
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f'Listening on http://{HOST}:{PORT}')
    httpd.serve_forever()


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from urllib.request import Request

try:
    from tc_core import effective_claw_config, open_url
except ModuleNotFoundError:
    from app.tc_core import effective_claw_config, open_url


def summarize_user_claw_messages(st: dict, limit: int = 8) -> str:
    user_msgs = [x.get('text', '') for x in st.get('conversations', {}).get('userClaw', []) if x.get('role') == 'user']
    return '\n'.join(f'- {x}' for x in user_msgs[-limit:]) or '- none'


def extract_terminal_token(text: str) -> str | None:
    matches = re.findall(r'(?m)^(DELIVERED_OK|FAILED_FINAL|NEEDS_MORE_WORK)\s*$', text or '')
    return matches[-1] if matches else None


def extract_json_object(text: str) -> dict | None:
    raw = (text or '').strip()
    if not raw:
        return None
    fenced = re.match(r'^```(?:json)?\s*(.*?)\s*```$', raw, re.S)
    if fenced:
        raw = fenced.group(1).strip()
    try:
        obj = json.loads(raw)
        if isinstance(obj, dict):
            return obj
    except Exception:
        pass
    decoder = json.JSONDecoder()
    for i, ch in enumerate(raw):
        if ch != '{':
            continue
        try:
            obj, _ = decoder.raw_decode(raw[i:])
        except Exception:
            continue
        if isinstance(obj, dict):
            return obj
    return None


def extract_codex_dialogue_text(text: str, max_chars: int = 5000) -> str:
    raw = (text or '').replace('\r\n', '\n').strip()
    if not raw:
        return ''

    raw = re.sub(r'(?ms)\n?\[done\] end_turn\s*$', '', raw).strip()

    changes_matches = list(re.finditer(r'(?m)^CHANGES\s*$', raw))
    if changes_matches:
        return raw[changes_matches[-1].start():].strip()[-max_chars:]

    for marker in ['Traceback (most recent call last):', 'TypeError:', 'RuntimeError:', 'Error:', 'Failed to spawn agent command:', '/usr/bin/env:']:
        idx = raw.rfind(marker)
        if idx >= 0:
            return raw[idx:].strip()[-max_chars:]

    lines = raw.splitlines()
    filtered: list[str] = []
    skip_block = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith('[tool]') or stripped == '[plan]':
            skip_block = True
            continue
        if skip_block:
            if not stripped:
                skip_block = False
            continue
        if stripped.startswith('[client]') or stripped.startswith('[thinking]') or stripped.startswith('[done]'):
            continue
        filtered.append(line)

    cleaned = '\n'.join(filtered).strip()
    if cleaned:
        return cleaned[-max_chars:]
    return raw[-max_chars:]


def stringify_for_log(value) -> str:
    if value is None:
        return ''
    if isinstance(value, str):
        return value
    try:
        return json.dumps(value, ensure_ascii=False)
    except Exception:
        try:
            return str(value)
        except Exception:
            return ''


def normalize_effort(value: str | None) -> str | None:
    v = (value or '').strip().lower()
    if v in {'low', 'medium', 'high', 'xhigh'}:
        return v
    return None


def build_responses_url(base: str) -> str:
    base = (base or '').rstrip('/')
    if not base:
        return ''
    if base.endswith('/responses'):
        return base
    return f'{base}/responses'


def parse_responses_output_text(parsed: dict) -> str:
    if isinstance(parsed.get('output_text'), str):
        return parsed.get('output_text') or ''
    out = parsed.get('output')
    if isinstance(out, list):
        parts: list[str] = []
        for item in out:
            if not isinstance(item, dict):
                continue
            content = item.get('content')
            if not isinstance(content, list):
                continue
            for c in content:
                if not isinstance(c, dict):
                    continue
                if c.get('type') in {'output_text', 'text'}:
                    t = c.get('text')
                    if isinstance(t, str):
                        parts.append(t)
        return ''.join(parts)
    return ''


def openai_responses(
    base_url: str,
    api_key: str | None,
    model: str,
    input_text: str,
    reasoning_effort: str | None = None,
    timeout: int = 120,
    proxy: str | None = None,
    no_proxy: str | None = None,
) -> tuple[str, dict]:
    url = build_responses_url(base_url)
    if not url:
        raise RuntimeError('missing responses base url')
    headers = {'Content-Type': 'application/json'}
    if api_key:
        headers['Authorization'] = f'Bearer {api_key}'
    payload: dict = {
        'model': model,
        'input': input_text,
        'stream': False,
    }
    if reasoning_effort:
        payload['reasoning'] = {'effort': reasoning_effort}
    req = Request(url, data=json.dumps(payload).encode('utf-8'), headers=headers, method='POST')
    with open_url(req, timeout=timeout, proxy=proxy, no_proxy=no_proxy) as resp:
        body = resp.read().decode('utf-8', 'ignore')
    parsed = json.loads(body)
    return parse_responses_output_text(parsed), parsed


def build_chat_completions_url(base: str) -> str:
    base = (base or '').rstrip('/')
    if not base:
        return ''
    if base.endswith('/chat/completions'):
        return base
    return f'{base}/chat/completions'


def infer_project_kind(cfg: dict, user_context: str = '') -> str:
    text = ' '.join([
        str(cfg.get('name', '')),
        str(cfg.get('goal', '')),
        str(user_context or ''),
    ]).lower()
    if any(k in text for k in ['算法', 'algorithm', '优化', 'optimization', 'theory', 'theoretical', 'idea', 'proof', 'benchmark', '性能', '复杂度', '收敛', 'search strategy']):
        return 'algorithm_research'
    if any(k in text for k in ['frontend', '前端', '页面', 'dashboard', 'demo', '界面', '交互', '库存', '订单', '采购', '台']):
        return 'frontend_demo'
    if any(k in text for k in ['api', 'backend', '后端', 'server', '服务', '数据库', '接口']):
        return 'backend_service'
    if any(k in text for k in ['script', 'cli', '命令行', '批处理', 'automation', '工具']):
        return 'script_tool'
    if any(k in text for k in ['文档', 'docs', 'readme', '手册', '教程', 'spec']):
        return 'docs_or_spec'
    return 'general_software'


def project_acceptance_profile(kind: str) -> dict:
    profiles = {
        'frontend_demo': {
            'delivery_bar': [
                'Project structure exists and is non-empty.',
                'There is a documented local startup path.',
                'The main UI renders in Chinese (or the requested language) and is not blank.',
                'Core pages/modules requested by the user are present.',
                'At least one real interaction or workflow is verified.',
                'README includes install/start/demo steps and verification notes.',
            ],
            'stretch_bar': [
                'Browser-level automated acceptance coverage exists.',
                'UI polish and advanced regression checks are present.',
                'Extended data persistence or more advanced UX checks are covered.',
            ],
            'verification_focus': 'Prefer build/start/browser/http verification and key-file inspection. Do not block delivery only because stretch-bar browser automation is missing if delivery-bar evidence is already strong.',
        },
        'backend_service': {
            'delivery_bar': [
                'Service starts locally with documented instructions.',
                'At least one key endpoint or workflow is exercised successfully.',
                'Configuration/README is sufficient for local use.',
                'Core data flow and expected outputs are demonstrated.',
            ],
            'stretch_bar': [
                'Automated test suite coverage is added.',
                'Load/error-handling cases are documented or tested.',
            ],
            'verification_focus': 'Prefer startup logs, HTTP status checks, smoke tests, and configuration correctness.',
        },
        'script_tool': {
            'delivery_bar': [
                'The tool runs locally with a documented command.',
                'Representative input/output behavior is demonstrated.',
                'README explains usage and limitations.',
            ],
            'stretch_bar': [
                'Extra automation, packaging, or edge-case coverage is added.',
            ],
            'verification_focus': 'Prefer CLI execution evidence, deterministic examples, and output inspection.',
        },
        'docs_or_spec': {
            'delivery_bar': [
                'Core requested documents/specs exist and are coherent.',
                'Structure, scope, and examples are sufficient for use.',
            ],
            'stretch_bar': [
                'Extended polish, diagrams, or exhaustive examples are added.',
            ],
            'verification_focus': 'Prefer direct file-content inspection over build/runtime checks.',
        },
        'algorithm_research': {
            'delivery_bar': [
                'The hypothesis/idea is clearly stated.',
                'A concrete method or algorithm design is produced.',
                'There is an evaluation plan or experiment design.',
                'There is at least one implementation artifact, derivation artifact, benchmark artifact, or falsification result.',
                'The result clearly states whether the idea appears promising, inconclusive, or ineffective.',
            ],
            'stretch_bar': [
                'There are broader benchmarks, stronger proofs, more baselines, or more complete ablations.',
                'There is a stronger implementation/performance package beyond the minimum validation needed for the current idea.',
            ],
            'verification_focus': 'Do not treat “not fully proven” as automatic failure. For research/theory work, delivery can be a well-supported negative result, an inconclusive result, a benchmark report, a derivation, or a prototype with evidence. Judge validity of the idea, rigor of reasoning, and whether the current iteration produced meaningful evidence.',
        },
        'general_software': {
            'delivery_bar': [
                'Non-empty project artifacts exist.',
                'There is a documented way to run or inspect the result.',
                'Core requested capability is demonstrated with evidence.',
            ],
            'stretch_bar': [
                'Additional polish, automation, or stronger testing is added.',
            ],
            'verification_focus': 'Prefer pragmatic evidence of use over perfection.',
        },
    }
    return profiles.get(kind, profiles['general_software'])


def openai_chat_completion(
    base_url: str,
    api_key: str | None,
    model: str,
    messages: list[dict],
    timeout: int = 120,
    proxy: str | None = None,
    no_proxy: str | None = None,
) -> tuple[str, dict]:
    url = build_chat_completions_url(base_url)
    if not url:
        raise RuntimeError('missing chat completions base url')
    headers = {'Content-Type': 'application/json'}
    if api_key:
        headers['Authorization'] = f'Bearer {api_key}'
    payload = {
        'model': model,
        'messages': messages,
        'stream': False,
    }
    req = Request(url, data=json.dumps(payload).encode('utf-8'), headers=headers, method='POST')
    with open_url(req, timeout=timeout, proxy=proxy, no_proxy=no_proxy) as resp:
        body = resp.read().decode('utf-8', 'ignore')
    parsed = json.loads(body)
    choices = parsed.get('choices') or []
    if not choices:
        raise RuntimeError(f'no choices in chat completion response: {body[:500]}')
    message = choices[0].get('message') or {}
    content = message.get('content', '')
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict):
                if item.get('type') == 'text':
                    parts.append(item.get('text', ''))
                elif 'text' in item:
                    parts.append(str(item.get('text', '')))
        content = ''.join(parts)
    return str(content or ''), parsed


def claw_identity_block(cfg: dict) -> str:
    claw_eff = effective_claw_config(cfg)
    return (
        f"Supervisor identity name: {claw_eff.get('profileName')}\n"
        f"Supervisor soul: {claw_eff.get('soul')}\n"
        f"Supervisor skills/priorities: {claw_eff.get('skills')}\n"
        f"Supervisor model preference: {claw_eff.get('model')}\n"
        f"Supervisor thinking preference: {claw_eff.get('thinking')}\n"
        "You are an independent supervisor identity that may be reused across multiple products. Codex is the implementation executor, not the same thing as you."
    )

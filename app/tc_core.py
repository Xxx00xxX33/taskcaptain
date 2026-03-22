#!/usr/bin/env python3
from __future__ import annotations

import html
import json
import os
import re
import shutil
import shlex
import signal
import subprocess
import threading
import time
import unicodedata
import uuid
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, quote, urlparse
from urllib.request import ProxyHandler, Request, build_opener, urlopen

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / 'data'
PRODUCTS = DATA / 'products'
TRASH = DATA / 'trash'
CLAW_PROFILES = DATA / 'claw-profiles'
RUNS = ROOT / 'runs'


def load_dotenv_defaults() -> None:
    env_path = ROOT / '.env'
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding='utf-8').splitlines():
        line = raw_line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, value = line.split('=', 1)
        key = key.strip()
        value = value.strip()
        if not key:
            continue
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]
        os.environ.setdefault(key, value)


load_dotenv_defaults()

DEFAULT_ACPX = '/home/a/.openclaw/extensions/acpx/node_modules/.bin/acpx'
ACPX = Path(os.environ.get('ACPX_BIN', DEFAULT_ACPX))

DEFAULT_CODEX_ACP_JS = '/home/a/.npm/_npx/e3854e347c184741/node_modules/.bin/codex-acp'
DEFAULT_CODEX_ACP_NATIVE = '/home/a/.npm/_npx/e3854e347c184741/node_modules/@zed-industries/codex-acp-linux-x64/bin/codex-acp'
CODEX_ACP_BIN = os.environ.get(
    'CODEX_ACP_BIN',
    DEFAULT_CODEX_ACP_NATIVE if Path(DEFAULT_CODEX_ACP_NATIVE).exists() else DEFAULT_CODEX_ACP_JS,
).strip()

HOST = os.environ.get('PRODUCTS_UI_HOST', '127.0.0.1')
PORT = int(os.environ.get('PRODUCTS_UI_PORT', '8765'))
DEFAULT_LANG = os.environ.get('PRODUCTS_UI_DEFAULT_LANG', 'en')
DEFAULT_AGENT_ENDPOINT = os.environ.get('PRODUCTS_UI_DEFAULT_OPENAI_BASE_URL', 'https://api.loveatri.su/v1')
DEFAULT_AGENT_API_KEY = os.environ.get(
    'PRODUCTS_UI_DEFAULT_OPENAI_API_KEY',
    'sk-pvVnxLEwR1SKD5Q9U5pwf7z2reGTieDj98aP5izGv3NTYywY',
)
DEFAULT_CODEX_ENDPOINT = os.environ.get('PRODUCTS_UI_DEFAULT_CODEX_BASE_URL', DEFAULT_AGENT_ENDPOINT)
DEFAULT_CODEX_API_KEY = os.environ.get('PRODUCTS_UI_DEFAULT_CODEX_API_KEY', DEFAULT_AGENT_API_KEY)
DEFAULT_PRODUCT_FOLDER = os.environ.get('PRODUCTS_UI_DEFAULT_PRODUCT_FOLDER', str(ROOT / 'workspace'))
DEFAULT_PROXY = os.environ.get('PRODUCTS_UI_PROXY', '').strip()
DEFAULT_NO_PROXY = os.environ.get('PRODUCTS_UI_NO_PROXY', '127.0.0.1,localhost,::1').strip()
DEFAULT_PROFILE_ID = 'sandrone-default'
MAX_INITIAL_REQUIREMENT_BYTES = int(os.environ.get('TASKCAPTAIN_MAX_INITIAL_REQUIREMENT_BYTES', '262144'))
MAX_INITIAL_REQUIREMENT_PROMPT_CHARS = int(os.environ.get('TASKCAPTAIN_MAX_INITIAL_REQUIREMENT_PROMPT_CHARS', '12000'))

for p in [PRODUCTS, TRASH, CLAW_PROFILES, RUNS]:
    p.mkdir(parents=True, exist_ok=True)

ACTIVE_RUNS: dict[str, dict] = {}
ACTIVE_SELF_TESTS: dict[str, dict] = {}
RUN_LOCK = threading.Lock()
SELF_TEST_LOCK = threading.Lock()

I18N = {
    'zh': {
        'app_title': 'TaskCaptain 产品控制台',
        'app_subtitle': '本地产品工作台：把 User↔Agent、Agent↔Codex、日志拆开，同时保持可复用的独立身份。',
        'language': '语言',
        'lang_zh': '中文',
        'lang_en': 'English',
        'create_product': '创建新任务',
        'product_name': '任务名称',
        'goal': '目标',
        'goal_placeholder': '这个任务要实现什么？',
        'initial_requirement_json': '初始要求 JSON',
        'initial_requirement_json_help': '可上传一个 .json 文件作为初始要求输入；提交后会自动保存原文件并纳入 Agent 的初始上下文。',
        'initial_requirement_json_hint': '支持 UTF-8 JSON，建议放任务说明、结构化约束、验收标准等。',
        'initial_requirement_json_preview': 'JSON 预览',
        'initial_requirement_json_empty': '未选择 JSON 文件。',
        'initial_requirement_json_ready': '已识别 JSON 文件：{filename}（{size}），提交后会自动导入初始要求。',
        'initial_requirement_json_invalid': '文件不是有效 JSON，请检查后重新选择。',
        'initial_requirement_imported': '已导入初始 JSON',
        'initial_requirement_source': '源文件',
        'initial_requirement_storage': '已保存',
        'create_error_prefix': '创建失败：',
        'max_turns': '最大回合数',
        'max_turns_help': '每次运行最多执行多少个回合；达到上限会标记失败（默认 8）。',
        'turn_progress': '回合进度',
        'product_folder': '工作目录（可写范围）',
        'claw_endpoint': 'Agent 端点',
        'claw_api_key': 'Agent API Key',
        'claw_model': 'Agent 模型（留空则继承 profile）',
        'claw_thinking': 'Agent 思考强度（留空则继承 profile）',
        'claw_profile': 'Agent Profile',
        'claw_profile_select': '选择可复用的 Agent Profile',
        'claw_soul': 'Agent Soul（留空则继承 profile）',
        'claw_skills': 'Agent Skills（留空则继承 profile）',
        'network_setting': '网络与代理',
        'connection_setting': '连接设置',
        'runtime_setting': '运行设置',
        'proxy_url': '代理地址',
        'proxy_help': '例如 http://127.0.0.1:7897；留空表示直连。',
        'no_proxy': '直连白名单',
        'save_connection_button': '保存连接设置',
        'save_runtime_button': '保存运行设置',
        'tasks_tab': '任务',
        'profiles_tab': 'Profiles',
        'task_form_tab': '新任务',
        'profile_form_tab': '新 Profile',
        'dialogue_tab': '对话',
        'logs_tab': '日志',
        'overview_tab': '概览',
        'codex_endpoint': 'Codex 端点',
        'codex_api_key': 'Codex API Key',
        'codex_model': 'Codex 模型',
        'codex_thinking': 'Codex 思考强度',
        'enable_plan': '启用 Codex Plan 模式（尽力设置）',
        'enable_max_permission': 'Codex 最高权限（工作目录内 approve-all）',
        'create_button': '创建任务',
        'active_products': '现有任务',
        'no_products': '还没有任务，先在右侧创建一个。',
        'created_at': '创建时间',
        'back': '返回控制台',
        'status': '状态',
        'self_test': '自检',
        'configuration_details': '配置详情',
        'workspace_folder': '工作目录',
        'claw_setting': 'Agent 设置',
        'codex_setting': 'Codex 设置',
        'model': '模型',
        'thinking': '思考',
        'modes': '模式',
        'api_key_present': 'API Key 已设置',
        'yes': '是',
        'no': '否',
        'run_self_test': '运行自检',
        'start_continue_run': '开始 / 继续运行',
        'stop_run': '停止运行',
        'delete_product': '删除任务',
        'delete_confirm': '确定删除这个任务吗？会移动到回收区。',
        'bulk_delete': '批量删除',
        'bulk_delete_confirm': '确定批量删除选中的项目吗？运行中的项目会跳过，其他会移动到回收区。',
        'select_for_bulk_delete': '全选用于批量删除',
        'running_skip_note': '运行中的项目不会被批量删除',
        'append_requirement': '发送给 Agent',
        'append_placeholder': '给 Agent 的新需求、修正意见、交付约束……',
        'append_button': '发送',
        'user_claw_dialogue': 'User ↔ Agent 对话区',
        'claw_codex_dialogue': 'Agent ↔ Codex 对话区',
        'no_user_claw': '还没有 User ↔ Agent 对话。',
        'no_claw_codex': '还没有 Agent ↔ Codex 对话。',
        'claw_log': 'Agent Log',
        'codex_log': 'Codex Log',
        'no_logs': '还没有日志。',
        'quick_signals': '运行信号',
        'recent_artifacts': '最近产物',
        'no_artifacts': '暂无产物。',
        'artifact_count': '产物数',
        'updated_at': '更新于',
        'live_sync': '最近同步',
        'log_mode': '日志读取',
        'recent_tail': '最近尾部',
        'rust_fast_path': 'Rust 快速路径',
        'python_fallback': 'Python 回退',
        'tailing_recent_logs': '仅展示最近 {size} 的日志尾部',
        'log_tail_status': '显示最近 {shown} / 总 {total}',
        'copy_path': '复制路径',
        'untitled': '未命名任务',
        'self_test_details': '自检详情',
        'not_run': '未运行',
        'idle': '空闲',
        'running': '运行中',
        'stopped': '已停止',
        'delivered': '已交付',
        'failed': '失败',
        'passed': '通过',
        'check': '检查项',
        'result': '结果',
        'detail': '详情',
        'role_policy_title': '执行分工策略',
        'role_policy_body': '当前产品策略：主要代码和产品文件由 Codex 在产品目录内完成；Agent 负责规划、监督、联网、下载数据集、归纳需求与状态推进，不直接在产品目录内写主产品代码。',
        'claw_identity_title': '当前生效的 Agent 身份',
        'claw_identity_body': 'Agent 现在被建模成可复用 profile：profile 负责默认 soul / skills / model / thinking；每个产品只是在此基础上做局部覆盖，因此不会和 Codex 绑成同一个东西。',
        'effective_claw_identity': '当前生效的 Agent 身份',
        'profile_name': 'Profile 名称',
        'profile_description': 'Profile 描述',
        'profile_soul_placeholder': '例如：Rigorous, efficient, pragmatic supervisor. Think like an engineer-scientist.',
        'profile_skills_placeholder': '例如：complex planning\nnetwork / computer / AI debugging\nautonomous exploration',
        'profile_desc_placeholder': '这个 Agent profile 适合什么项目、有什么风格？',
        'reusable_claw_profiles': '可复用 Agent Profiles',
        'no_profiles': '还没有 profile，将自动使用默认的 Sandrone profile。',
        'create_profile': '创建新 Profile',
        'create_profile_button': '创建 Profile',
        'save_current_claw_profile': '把当前 Agent 保存成可复用 Profile',
        'save_profile_button': '保存为 Profile',
        'profile_saved_hint': '保存后，新项目可直接复用这个 Agent。',
        'profile_label': 'Profile',
        'soul_label': 'Soul',
        'skills_label': 'Skills',
        'inherited_from_profile': '继承自 profile',
        'profile_model_hint': 'Profile 默认模型',
        'profile_thinking_hint': 'Profile 默认思考强度',
    },
    'en': {
        'app_title': 'TaskCaptain Console',
        'app_subtitle': 'Local task workspace: Separate User↔Agent and Agent↔Codex dialogues and logs, with reusable independent profiles.',
        'language': 'Language',
        'lang_zh': '中文',
        'lang_en': 'English',
        'create_product': 'Create New Task',
        'product_name': 'Task Name',
        'goal': 'Goal',
        'goal_placeholder': 'What should this task achieve?',
        'initial_requirement_json': 'Initial Requirement JSON',
        'initial_requirement_json_help': 'Upload a `.json` file as structured initial input. The original file will be saved and included in Agent context when the task is created.',
        'initial_requirement_json_hint': 'UTF-8 JSON recommended. Good for task briefs, constraints, and acceptance criteria.',
        'initial_requirement_json_preview': 'JSON Preview',
        'initial_requirement_json_empty': 'No JSON file selected.',
        'initial_requirement_json_ready': 'JSON file detected: {filename} ({size}). It will be imported into the initial requirement on submit.',
        'initial_requirement_json_invalid': 'The selected file is not valid JSON.',
        'initial_requirement_imported': 'Initial JSON imported',
        'initial_requirement_source': 'Source file',
        'initial_requirement_storage': 'Stored copy',
        'create_error_prefix': 'Create failed: ',
        'max_turns': 'Max Turns',
        'max_turns_help': 'Max Claw↔Codex turns per run; reaching the limit will mark failed (default 8).',
        'turn_progress': 'Turn progress',
        'product_folder': 'Workspace Folder (Codex writable)',
        'claw_endpoint': 'Agent Endpoint',
        'claw_api_key': 'Agent API Key',
        'claw_model': 'Agent Model (blank = inherit)',
        'claw_thinking': 'Agent Thinking (blank = inherit)',
        'claw_profile': 'Agent Profile',
        'claw_profile_select': 'Choose reusable Agent profile',
        'claw_soul': 'Agent Soul (blank = inherit)',
        'claw_skills': 'Agent Skills (blank = inherit)',
        'network_setting': 'Network & Proxy',
        'connection_setting': 'Connection Settings',
        'runtime_setting': 'Runtime Settings',
        'proxy_url': 'Proxy URL',
        'proxy_help': 'For example http://127.0.0.1:7897. Leave blank for direct connection.',
        'no_proxy': 'No Proxy',
        'save_connection_button': 'Save Connection Settings',
        'save_runtime_button': 'Save Runtime Settings',
        'tasks_tab': 'Tasks',
        'profiles_tab': 'Profiles',
        'task_form_tab': 'New Task',
        'profile_form_tab': 'New Profile',
        'dialogue_tab': 'Dialogue',
        'logs_tab': 'Logs',
        'overview_tab': 'Overview',
        'codex_endpoint': 'Codex Endpoint',
        'codex_api_key': 'Codex API Key',
        'codex_model': 'Codex Model',
        'codex_thinking': 'Codex Thinking',
        'enable_plan': 'Enable Codex Plan Mode (best effort)',
        'enable_max_permission': 'Codex Max Permission (approve-all in folder)',
        'create_button': 'Create Task',
        'active_products': 'Active Tasks',
        'no_products': 'No tasks yet. Create one on the right to get started.',
        'created_at': 'Created',
        'back': 'Back to Dashboard',
        'status': 'Status',
        'self_test': 'Self-test',
        'configuration_details': 'Configuration Details',
        'workspace_folder': 'Workspace Folder',
        'claw_setting': 'Agent Setting',
        'codex_setting': 'Codex Setting',
        'model': 'Model',
        'thinking': 'Thinking',
        'modes': 'Modes',
        'api_key_present': 'API Key Set',
        'yes': 'Yes',
        'no': 'No',
        'run_self_test': 'Run Self-Test',
        'start_continue_run': 'Start / Continue Run',
        'stop_run': 'Stop Run',
        'delete_product': 'Delete Task',
        'delete_confirm': 'Delete this task? It will be moved to trash.',
        'bulk_delete': 'Bulk Delete',
        'bulk_delete_confirm': 'Delete selected tasks? Running ones will be skipped; others will be moved to trash.',
        'select_for_bulk_delete': 'Select all for bulk delete',
        'running_skip_note': 'Running tasks will be skipped',
        'append_requirement': 'Send to Agent',
        'append_placeholder': 'Send a new requirement, correction, or constraint to Agent...',
        'append_button': 'Send',
        'user_claw_dialogue': 'User ↔ Agent Dialogue',
        'claw_codex_dialogue': 'Agent ↔ Codex Dialogue',
        'no_user_claw': 'No User ↔ Agent dialogue yet.',
        'no_claw_codex': 'No Agent ↔ Codex dialogue yet.',
        'claw_log': 'Agent Log',
        'codex_log': 'Codex Log',
        'no_logs': 'No logs yet.',
        'quick_signals': 'Quick Signals',
        'recent_artifacts': 'Recent Artifacts',
        'no_artifacts': 'No artifacts yet.',
        'artifact_count': 'Artifacts',
        'updated_at': 'Updated',
        'live_sync': 'Last Sync',
        'log_mode': 'Log Reading',
        'recent_tail': 'Recent Tail',
        'rust_fast_path': 'Rust fast path',
        'python_fallback': 'Python fallback',
        'tailing_recent_logs': 'Showing the most recent {size} of each log',
        'log_tail_status': 'Showing recent {shown} / total {total}',
        'copy_path': 'Copy Path',
        'untitled': 'Untitled Task',
        'self_test_details': 'Self-test Details',
        'not_run': 'not-run',
        'idle': 'idle',
        'running': 'running',
        'stopped': 'stopped',
        'delivered': 'delivered',
        'failed': 'failed',
        'passed': 'passed',
        'check': 'Check',
        'result': 'Result',
        'detail': 'Detail',
        'role_policy_title': 'Execution Policy',
        'role_policy_body': 'Main code and product files are written by Codex inside the product folder; Agent handles planning, supervision, networking, dataset download, requirement synthesis, and progress management, and does not directly write main product code into the product folder.',
        'claw_identity_title': 'Independent Agent Identity',
        'claw_identity_body': 'Agent is modeled as a reusable profile: the profile owns default soul / skills / model / thinking, while each product only adds local overrides.',
        'effective_claw_identity': 'Effective Agent Identity',
        'profile_name': 'Profile Name',
        'profile_description': 'Profile Description',
        'profile_soul_placeholder': 'e.g. Rigorous, efficient, pragmatic supervisor. Think like an engineer-scientist.',
        'profile_skills_placeholder': 'e.g. complex planning\nnetwork / computer / AI debugging\nautonomous exploration',
        'profile_desc_placeholder': 'What kind of work is this Agent profile good at?',
        'reusable_claw_profiles': 'Reusable Agent Profiles',
        'no_profiles': 'No profiles yet; the default Sandrone profile will be used automatically.',
        'create_profile': 'Create New Profile',
        'create_profile_button': 'Create Profile',
        'save_current_claw_profile': 'Save current Agent as reusable profile',
        'save_profile_button': 'Save as Profile',
        'profile_saved_hint': 'After saving, new projects can reuse this Agent directly.',
        'profile_label': 'Profile',
        'soul_label': 'Soul',
        'skills_label': 'Skills',
        'inherited_from_profile': 'Inherited from profile',
        'profile_model_hint': 'Profile default model',
        'profile_thinking_hint': 'Profile default thinking',
    },
}


def t(lang: str, key: str, **kwargs) -> str:
    lang = lang if lang in I18N else DEFAULT_LANG
    text = I18N[lang].get(key, I18N[DEFAULT_LANG].get(key, key))
    return text.format(**kwargs) if kwargs else text


def normalize_lang(value: str | None) -> str:
    return value if value in I18N else DEFAULT_LANG


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec='seconds')


def slugify(text: str) -> str:
    normalized = unicodedata.normalize('NFKD', text)
    ascii_text = normalized.encode('ascii', 'ignore').decode('ascii').lower()
    base = re.sub(r'[^a-z0-9]+', '-', ascii_text).strip('-')
    while '--' in base:
        base = base.replace('--', '-')
    return base or f'product-{uuid.uuid4().hex[:8]}'


def normalize_product_identity(raw_name: str, raw_folder: str) -> tuple[str, str, bool]:
    name = (raw_name or '').strip()
    folder = (raw_folder or '').strip()
    inferred_from_name_path = False

    default_folder = str(Path(DEFAULT_PRODUCT_FOLDER).expanduser())
    folder = str(Path(folder).expanduser()) if folder else ''

    looks_like_path = bool(name) and (
        name.startswith('/')
        or name.startswith('~')
        or name.startswith('./')
        or name.startswith('../')
        or bool(re.match(r'^[A-Za-z]:[\\/]', name))
    )

    if looks_like_path and (not folder or folder == default_folder):
        p = Path(name).expanduser()
        folder = str(p)
        if p.name.strip():
            name = p.name.strip()
        inferred_from_name_path = True

    if not name:
        name = 'Untitled Product'
    if not folder:
        folder = default_folder
    folder = str(resolve_workspace_path(folder))

    return name, folder, inferred_from_name_path


def product_dir(product_id: str) -> Path:
    return PRODUCTS / product_id


def resolve_workspace_path(raw_path: str | None) -> Path:
    text = (raw_path or '').strip()
    if not text:
        return Path(DEFAULT_PRODUCT_FOLDER).expanduser()
    p = Path(text).expanduser()
    if p.is_absolute():
        return p
    return (ROOT / p).resolve()


def ensure_workspace_path(raw_path: str | None) -> tuple[bool, str]:
    try:
        path = resolve_workspace_path(raw_path)
        path.mkdir(parents=True, exist_ok=True)
        return True, str(path)
    except Exception as e:
        return False, str(e)


def profile_path(profile_id: str) -> Path:
    return CLAW_PROFILES / f'{profile_id}.json'


def read_json(path: Path, default=None):
    if not path.exists():
        return {} if default is None else default
    return json.loads(path.read_text(encoding='utf-8'))


def write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def append_log(path: Path, line: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('a', encoding='utf-8') as fh:
        fh.write(line.rstrip() + '\n')


def default_claw_profile() -> dict:
    ts = now_iso()
    return {
        'id': DEFAULT_PROFILE_ID,
        'name': 'Sandrone Default',
        'description': 'Rigorous, efficient, pragmatic supervisor for hard engineering / network / AI work.',
        'model': 'local8317_chat/gpt-5.4',
        'thinking': 'high',
        'soul': 'Rigorous, efficient, pragmatic. Think like a scientist / engineer / programmer. Do autonomous exploration and converge to verifiable outcomes.',
        'skills': 'complex task planning\nnetwork / computer / AI debugging\nautonomous exploration\nproject supervision\nclear progress reporting',
        'createdAt': ts,
        'updatedAt': ts,
    }


def ensure_default_profile() -> None:
    path = profile_path(DEFAULT_PROFILE_ID)
    if not path.exists():
        write_json(path, default_claw_profile())


def normalize_profile(profile: dict) -> tuple[dict, bool]:
    changed = False
    base = default_claw_profile()
    for key in ['id', 'name', 'description', 'model', 'thinking', 'soul', 'skills', 'createdAt', 'updatedAt']:
        if key not in profile:
            profile[key] = base[key]
            changed = True
    return profile, changed


def list_claw_profiles() -> list[dict]:
    ensure_default_profile()
    items: list[dict] = []
    for path in sorted(CLAW_PROFILES.glob('*.json')):
        profile = read_json(path, {})
        profile, changed = normalize_profile(profile)
        if changed:
            write_json(path, profile)
        items.append(profile)
    items.sort(key=lambda x: (x.get('id') != DEFAULT_PROFILE_ID, x.get('name', '').lower()))
    return items


def load_claw_profile(profile_id: str | None) -> dict:
    ensure_default_profile()
    pid = profile_id or DEFAULT_PROFILE_ID
    path = profile_path(pid)
    if not path.exists():
        pid = DEFAULT_PROFILE_ID
        path = profile_path(pid)
    profile = read_json(path, {})
    profile, changed = normalize_profile(profile)
    if changed:
        write_json(path, profile)
    return profile


def save_claw_profile_from_form(form: dict[str, str]) -> str:
    name = form.get('profileName', '').strip() or 'Unnamed Claw Profile'
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
        'description': form.get('profileDescription', '').strip(),
        'model': form.get('profileModel', '').strip() or default_claw_profile()['model'],
        'thinking': form.get('profileThinking', '').strip() or default_claw_profile()['thinking'],
        'soul': form.get('profileSoul', '').strip() or default_claw_profile()['soul'],
        'skills': form.get('profileSkills', '').strip() or default_claw_profile()['skills'],
        'createdAt': ts,
        'updatedAt': ts,
    }
    write_json(path, profile)
    return pid


def normalize_config(cfg: dict) -> tuple[dict, bool]:
    changed = False
    if 'id' not in cfg:
        cfg['id'] = f'product-{uuid.uuid4().hex[:8]}'
        changed = True
    if 'maxTurns' not in cfg:
        cfg['maxTurns'] = 8
        changed = True
    else:
        try:
            cfg['maxTurns'] = int(cfg.get('maxTurns') or 8)
        except Exception:
            cfg['maxTurns'] = 8
        if cfg['maxTurns'] < 1:
            cfg['maxTurns'] = 1
        if cfg['maxTurns'] > 99:
            cfg['maxTurns'] = 99
    normalized_folder = str(resolve_workspace_path(cfg.get('productFolder')))
    if cfg.get('productFolder') != normalized_folder:
        cfg['productFolder'] = normalized_folder
        changed = True
    claw = cfg.setdefault('claw', {})
    codex = cfg.setdefault('codex', {})
    network = cfg.setdefault('network', {})
    if 'initialRequirement' in cfg and not isinstance(cfg.get('initialRequirement'), dict):
        cfg.pop('initialRequirement', None)
        changed = True
    defaults = {
        'endpoint': DEFAULT_AGENT_ENDPOINT,
        'apiKey': DEFAULT_AGENT_API_KEY,
        'profileId': DEFAULT_PROFILE_ID,
        'model': '',
        'thinking': '',
        'soul': '',
        'skills': '',
    }
    for k, v in defaults.items():
        if k not in claw:
            claw[k] = v
            changed = True
    codex_defaults = {
        'endpoint': DEFAULT_CODEX_ENDPOINT,
        'apiKey': DEFAULT_CODEX_API_KEY,
        'model': 'gpt-5.4-medium',
        'thinking': 'medium',
        'planMode': True,
        'maxPermission': True,
        'sessionName': f"oc-product-{cfg['id']}",
    }
    for k, v in codex_defaults.items():
        if k not in codex:
            codex[k] = v
            changed = True
    network_defaults = {
        'proxy': DEFAULT_PROXY,
        'noProxy': DEFAULT_NO_PROXY,
    }
    for k, v in network_defaults.items():
        if k not in network:
            network[k] = v
            changed = True
    if 'createdAt' not in cfg:
        cfg['createdAt'] = now_iso()
        changed = True
    return cfg, changed


def normalize_state(st: dict) -> tuple[dict, bool]:
    changed = False
    defaults = {
        'status': 'idle',
        'createdAt': now_iso(),
        'updatedAt': now_iso(),
        'lastRunId': None,
        'lastError': None,
        'currentTurn': 0,
        'selfTest': {'status': 'not-run', 'updatedAt': None, 'checks': {}},
        'stopRequested': False,
    }
    for k, v in defaults.items():
        if k not in st:
            st[k] = v
            changed = True
    if 'conversation' not in st:
        st['conversation'] = []
        changed = True
    conversations = st.get('conversations')
    if not isinstance(conversations, dict):
        conversations = {}
        st['conversations'] = conversations
        changed = True
    if 'userClaw' not in conversations:
        conversations['userClaw'] = []
        changed = True
    if 'clawCodex' not in conversations:
        conversations['clawCodex'] = []
        changed = True
    legacy = st.get('conversation') or []
    if legacy and not conversations['userClaw'] and not conversations['clawCodex']:
        for item in legacy:
            role = item.get('role')
            if role in {'user', 'claw'}:
                conversations['userClaw'].append(item)
            else:
                conversations['clawCodex'].append(item)
        changed = True
    return st, changed


def load_product_config(product_id: str) -> dict:
    path = product_dir(product_id) / 'config.json'
    cfg = read_json(path, {})
    cfg, changed = normalize_config(cfg)
    if changed:
        write_json(path, cfg)
    return cfg


def save_product_config(product_id: str, cfg: dict) -> None:
    cfg, _ = normalize_config(cfg)
    write_json(product_dir(product_id) / 'config.json', cfg)


def load_product_state(product_id: str) -> dict:
    path = product_dir(product_id) / 'state.json'
    st = read_json(path, {})
    st, changed = normalize_state(st)
    if changed:
        write_json(path, st)
    return st


def save_product_state(product_id: str, st: dict) -> None:
    st, _ = normalize_state(st)
    write_json(product_dir(product_id) / 'state.json', st)


def effective_claw_config(cfg: dict) -> dict:
    claw = cfg.get('claw', {})
    profile = load_claw_profile(claw.get('profileId'))
    return {
        'profileId': profile.get('id'),
        'profileName': profile.get('name'),
        'profileDescription': profile.get('description', ''),
        'endpoint': claw.get('endpoint', ''),
        'apiKey': claw.get('apiKey', ''),
        'model': claw.get('model') or profile.get('model', ''),
        'thinking': claw.get('thinking') or profile.get('thinking', ''),
        'soul': claw.get('soul') or profile.get('soul', ''),
        'skills': claw.get('skills') or profile.get('skills', ''),
    }


def effective_network_config(cfg: dict | None = None) -> dict:
    network = (cfg or {}).get('network', {}) if isinstance(cfg, dict) else {}
    proxy = (network.get('proxy') or '').strip()
    no_proxy = (network.get('noProxy') or DEFAULT_NO_PROXY or '').strip()
    return {
        'proxy': proxy,
        'noProxy': no_proxy,
    }


def sanitize_upload_filename(filename: str | None, fallback: str = 'initial-requirement.json') -> str:
    raw = Path((filename or '').strip()).name.strip() or fallback
    safe = re.sub(r'[^A-Za-z0-9._-]+', '-', raw).strip('-.')
    if not safe:
        safe = fallback
    if not safe.lower().endswith('.json'):
        safe += '.json'
    return safe


def extract_suggested_name_from_json(payload) -> str:
    if not isinstance(payload, dict):
        return ''
    for key in ['name', 'title', 'taskName', 'task_name', 'productName', 'product_name', 'projectName', 'project_name', 'ideaName', 'idea_name']:
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ''


def parse_initial_requirement_upload(upload: dict | None) -> dict | None:
    if not upload:
        return None
    raw_bytes = upload.get('content') or b''
    if not raw_bytes:
        return None
    if len(raw_bytes) > MAX_INITIAL_REQUIREMENT_BYTES:
        raise ValueError(f'Initial requirement JSON exceeds {MAX_INITIAL_REQUIREMENT_BYTES} bytes.')

    filename = sanitize_upload_filename(upload.get('filename'))
    try:
        raw_text = raw_bytes.decode('utf-8-sig')
    except UnicodeDecodeError:
        raise ValueError('Initial requirement JSON must be UTF-8 encoded.')

    try:
        payload = json.loads(raw_text)
    except Exception as exc:
        raise ValueError(f'Initial requirement file must be valid JSON: {exc}')

    pretty_json = json.dumps(payload, ensure_ascii=False, indent=2)
    prompt_payload = pretty_json
    truncated = False
    if len(prompt_payload) > MAX_INITIAL_REQUIREMENT_PROMPT_CHARS:
        prompt_payload = (
            prompt_payload[:MAX_INITIAL_REQUIREMENT_PROMPT_CHARS].rstrip()
            + '\n... (truncated in prompt; full file is saved under inputs/)'
        )
        truncated = True

    top_level_keys = [str(x) for x in list(payload.keys())[:12]] if isinstance(payload, dict) else []
    prompt_text = (
        f"Imported initial requirement JSON file: {filename}\n"
        f"Structured payload:\n{prompt_payload}"
    )
    return {
        'filename': filename,
        'contentType': (upload.get('content_type') or 'application/json').strip() or 'application/json',
        'sizeBytes': len(raw_bytes),
        'uploadedAt': now_iso(),
        'topLevelType': type(payload).__name__,
        'topLevelKeys': top_level_keys,
        'suggestedName': extract_suggested_name_from_json(payload),
        'promptText': prompt_text,
        'prettyJson': pretty_json,
        'truncatedInPrompt': truncated,
    }


def persist_initial_requirement_upload(base_dir: Path, parsed_upload: dict | None) -> dict | None:
    if not parsed_upload:
        return None
    inputs_dir = base_dir / 'inputs'
    inputs_dir.mkdir(parents=True, exist_ok=True)
    filename = sanitize_upload_filename(parsed_upload.get('filename'))
    target = inputs_dir / filename
    stem = target.stem
    suffix = target.suffix
    i = 2
    while target.exists():
        target = inputs_dir / f'{stem}-{i}{suffix}'
        i += 1
    target.write_text((parsed_upload.get('prettyJson') or '').rstrip() + '\n', encoding='utf-8')
    meta = {
        'source': 'json-upload',
        'filename': filename,
        'storedRelativePath': str(target.relative_to(base_dir)),
        'contentType': parsed_upload.get('contentType', 'application/json'),
        'sizeBytes': int(parsed_upload.get('sizeBytes') or 0),
        'uploadedAt': parsed_upload.get('uploadedAt') or now_iso(),
        'topLevelType': parsed_upload.get('topLevelType') or 'unknown',
        'topLevelKeys': parsed_upload.get('topLevelKeys') or [],
        'suggestedName': parsed_upload.get('suggestedName') or '',
        'promptText': parsed_upload.get('promptText') or '',
        'truncatedInPrompt': bool(parsed_upload.get('truncatedInPrompt')),
    }
    return meta


def effective_goal_text(cfg: dict | None) -> str:
    cfg = cfg if isinstance(cfg, dict) else {}
    manual_goal = (cfg.get('goal') or '').strip()
    imported_goal = ((cfg.get('initialRequirement') or {}).get('promptText') or '').strip()
    if manual_goal and imported_goal:
        return manual_goal + '\n\n' + imported_goal
    return manual_goal or imported_goal


def list_products():
    items = []
    for d in sorted(PRODUCTS.iterdir() if PRODUCTS.exists() else []):
        if not d.is_dir():
            continue
        cfg = load_product_config(d.name)
        st = load_product_state(d.name)
        items.append({'id': d.name, 'config': cfg, 'state': st, 'effectiveClaw': effective_claw_config(cfg)})
    return items


def mask_present(value: str | None) -> str:
    return 'yes' if value else 'no'


def proxy_bypass_match(hostname: str | None, no_proxy: str | None) -> bool:
    host = (hostname or '').strip().lower()
    entries = [(x or '').strip().lower() for x in (no_proxy or '').split(',')]
    entries = [x for x in entries if x]
    if not host:
        return False
    for entry in entries:
        token = entry
        if token == '*':
            return True
        if token.startswith('[') and token.endswith(']'):
            token = token[1:-1]
        if ':' in token and token.count(':') == 1:
            token = token.split(':', 1)[0]
        token = token.lstrip('.')
        if not token:
            continue
        if host == token:
            return True
        if host.endswith('.' + token):
            return True
    return False


def open_url(req_or_url, timeout: int = 10, proxy: str | None = None, no_proxy: str | None = None):
    target = req_or_url.full_url if isinstance(req_or_url, Request) else str(req_or_url)
    parsed = urlparse(target)
    handlers = []
    if proxy and not proxy_bypass_match(parsed.hostname, no_proxy):
        handlers.append(ProxyHandler({'http': proxy, 'https': proxy}))
    else:
        handlers.append(ProxyHandler({}))
    opener = build_opener(*handlers)
    return opener.open(req_or_url, timeout=timeout)


def build_models_url(base: str) -> str:
    base = (base or '').rstrip('/')
    if not base:
        return ''
    if base.endswith('/models'):
        return base
    return f'{base}/models'


def probe_openai_like_endpoint(
    base_url: str,
    api_key: str | None = None,
    proxy: str | None = None,
    no_proxy: str | None = None,
) -> dict:
    models_url = build_models_url(base_url)
    if not models_url:
        return {'ok': False, 'detail': 'missing base url'}
    headers = {}
    if api_key:
        headers['Authorization'] = f'Bearer {api_key}'
    req = Request(models_url, headers=headers, method='GET')
    try:
        with open_url(req, timeout=10, proxy=proxy, no_proxy=no_proxy) as resp:
            body = resp.read(1200).decode('utf-8', 'ignore')
            ok = 200 <= resp.status < 300
            return {'ok': ok, 'detail': f'HTTP {resp.status}: {body[:400]}'}
    except HTTPError as e:
        body = e.read(400).decode('utf-8', 'ignore') if hasattr(e, 'read') else ''
        return {'ok': False, 'detail': f'HTTPError {e.code}: {body}'}
    except URLError as e:
        return {'ok': False, 'detail': f'URLError: {e}'}
    except Exception as e:
        return {'ok': False, 'detail': str(e)}


def create_product(form: dict[str, str], initial_requirement_upload: dict | None = None) -> str:
    parsed_upload = parse_initial_requirement_upload(initial_requirement_upload)
    raw_name = form.get('name', '')
    if parsed_upload and not str(raw_name or '').strip() and parsed_upload.get('suggestedName'):
        raw_name = parsed_upload.get('suggestedName', '')
    name, product_folder, inferred_from_name_path = normalize_product_identity(
        raw_name,
        form.get('productFolder', ''),
    )
    try:
        max_turns = int((form.get('maxTurns') or '').strip() or '8')
    except Exception:
        max_turns = 8
    if max_turns < 1:
        max_turns = 1
    if max_turns > 99:
        max_turns = 99
    product_id = slugify(name)
    d = product_dir(product_id)
    i = 2
    while d.exists():
        product_id = f"{slugify(name)}-{i}"
        d = product_dir(product_id)
        i += 1
    d.mkdir(parents=True, exist_ok=True)
    initial_requirement_meta = persist_initial_requirement_upload(d, parsed_upload)

    profile = load_claw_profile(form.get('clawProfileId') or DEFAULT_PROFILE_ID)
    cfg = {
        'id': product_id,
        'name': name,
        'goal': form.get('goal', '').strip(),
        'productFolder': product_folder,
        'maxTurns': max_turns,
        'claw': {
            'endpoint': form.get('clawEndpoint', '').strip() or DEFAULT_AGENT_ENDPOINT,
            'apiKey': form.get('clawApiKey', '').strip() or DEFAULT_AGENT_API_KEY,
            'profileId': profile.get('id'),
            'model': form.get('clawModel', '').strip(),
            'thinking': form.get('clawThinking', '').strip(),
            'soul': form.get('clawSoul', '').strip(),
            'skills': form.get('clawSkills', '').strip(),
        },
        'codex': {
            'endpoint': form.get('codexEndpoint', '').strip() or DEFAULT_CODEX_ENDPOINT,
            'apiKey': form.get('codexApiKey', '').strip() or DEFAULT_CODEX_API_KEY,
            'model': form.get('codexModel', '').strip() or 'gpt-5.4-medium',
            'thinking': form.get('codexThinking', '').strip() or 'medium',
            'planMode': form.get('codexPlanMode', '') == 'on',
            'maxPermission': form.get('codexMaxPermission', '') == 'on',
            'sessionName': f'oc-product-{product_id}',
        },
        'network': {
            'proxy': form.get('proxy', '').strip(),
            'noProxy': form.get('noProxy', '').strip() or DEFAULT_NO_PROXY,
        },
        'createdAt': now_iso(),
    }
    if initial_requirement_meta:
        cfg['initialRequirement'] = initial_requirement_meta
    st = {
        'status': 'idle',
        'createdAt': now_iso(),
        'updatedAt': now_iso(),
        'lastRunId': None,
        'lastError': None,
        'selfTest': {
            'status': 'not-run',
            'updatedAt': None,
            'checks': {},
        },
        'conversation': [],
        'conversations': {
            'userClaw': [],
            'clawCodex': [],
        },
        'stopRequested': False,
    }
    # Record initial Agent message in the persisted dialogue.
    st.setdefault('conversations', {}).setdefault('userClaw', []).append({
        'ts': now_iso(),
        'role': 'claw',
        'text': f"Agent profile '{profile.get('name')}' attached to this product. Ready for user instructions.",
    })
    if initial_requirement_meta:
        st.setdefault('conversations', {}).setdefault('userClaw', []).append({
            'ts': now_iso(),
            'role': 'claw',
            'text': f"Structured initial requirement JSON '{initial_requirement_meta.get('filename')}' was imported and added to the starting context.",
        })
    save_product_config(product_id, cfg)
    save_product_state(product_id, st)
    workspace_ok, workspace_detail = ensure_workspace_path(product_folder)
    append_log(d / 'logs' / 'claw.log', f'[{now_iso()}] Product created.')
    append_log(d / 'logs' / 'codex.log', f'[{now_iso()}] Product created.')
    append_log(
        d / 'logs' / 'claw.log',
        f'[{now_iso()}] Workspace {"ready" if workspace_ok else "create-failed"}: {workspace_detail}',
    )
    if inferred_from_name_path:
        append_log(d / 'logs' / 'claw.log', f'[{now_iso()}] Interpreted product name as a filesystem path and normalized to name={name!r}, productFolder={product_folder!r}.')
    return product_id



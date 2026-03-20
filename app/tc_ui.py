#!/usr/bin/env python3
from __future__ import annotations

import html

def language_switch_html(current_lang: str, base_path: str) -> str:
    return f"""
    <div class="flex items-center p-1 bg-slate-100 dark:bg-zinc-800 rounded-full border border-slate-200 dark:border-zinc-700">
      <a href="{html.escape(base_path)}?lang=en" class="px-3 py-1 rounded-full text-xs font-semibold {'bg-white dark:bg-zinc-700 shadow-sm text-slate-800 dark:text-slate-100' if current_lang == 'en' else 'text-slate-500 dark:text-zinc-400 hover:text-slate-800 dark:hover:text-slate-200 transition'}">EN</a>
      <a href="{html.escape(base_path)}?lang=zh" class="px-3 py-1 rounded-full text-xs font-semibold {'bg-white dark:bg-zinc-700 shadow-sm text-slate-800 dark:text-slate-100' if current_lang == 'zh' else 'text-slate-500 dark:text-zinc-400 hover:text-slate-800 dark:hover:text-slate-200 transition'}">中</a>
    </div>
    """


def page_template(title: str, body: str, lang: str, path: str = '/') -> bytes:
    html_lang = 'zh-CN' if lang == 'zh' else 'en'
    lang_switch = language_switch_html(lang, path)
    return f"""
<!doctype html>
<html lang="{html.escape(html_lang)}" class="light">
<head>
  <meta charset='utf-8'>
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{html.escape(title)}</title>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
  <script src="https://cdn.tailwindcss.com"></script>
  <script>
    tailwind.config = {{
      darkMode: 'class',
      theme: {{
        extend: {{
          fontFamily: {{
            sans: ['Inter', 'system-ui', 'sans-serif'],
            mono: ['JetBrains Mono', 'monospace'],
          }},
          colors: {{
            brand: {{ 50: '#eff6ff', 100: '#dbeafe', 500: '#3b82f6', 600: '#2563eb', 700: '#1d4ed8', 900: '#1e3a8a', 950: '#172554' }},
            darkbg: '#09090b',
            darkcard: '#18181b',
          }}
        }}
      }}
    }}
  </script>
  <style type="text/tailwindcss">
    @layer components {{
      .badge {{ @apply inline-flex items-center px-2.5 py-1 rounded-full text-xs font-bold whitespace-nowrap border; }}
      .badge-running {{ @apply bg-blue-100 text-blue-700 dark:bg-blue-500/20 dark:text-blue-400 border-blue-200 dark:border-blue-500/30; }}
      .badge-delivered {{ @apply bg-emerald-100 text-emerald-700 dark:bg-emerald-500/20 dark:text-emerald-400 border-emerald-200 dark:border-emerald-500/30; }}
      .badge-failed {{ @apply bg-red-100 text-red-700 dark:bg-red-500/20 dark:text-red-400 border-red-200 dark:border-red-500/30; }}
      .badge-idle {{ @apply bg-slate-100 text-slate-500 dark:bg-zinc-800 dark:text-zinc-400 border-slate-200 dark:border-zinc-700; }}
      .badge-stopped {{ @apply bg-amber-100 text-amber-700 dark:bg-amber-500/20 dark:text-amber-400 border-amber-200 dark:border-amber-500/30; }}
    }}
  </style>
  <style>
    ::-webkit-scrollbar {{ width: 8px; height: 8px; }}
    ::-webkit-scrollbar-track {{ background: transparent; }}
    ::-webkit-scrollbar-thumb {{ background: #cbd5e1; border-radius: 999px; }}
    .dark ::-webkit-scrollbar-thumb {{ background: #3f3f46; }}
    ::-webkit-scrollbar-thumb:hover {{ background: #94a3b8; }}
    .terminal-body::-webkit-scrollbar-thumb {{ background: #475569; }}
    body {{ -webkit-font-smoothing: antialiased; }}
    .chat-bubble-user {{ border-bottom-right-radius: 4px; }}
    .chat-bubble-bot {{ border-bottom-left-radius: 4px; }}
    .terminal-dot {{ width: 12px; height: 12px; border-radius: 999px; flex-shrink: 0; }}
    .dot-r {{ background: #ff5f56; box-shadow: 0 0 4px rgba(255,95,86,0.3); }}
    .dot-y {{ background: #ffbd2e; box-shadow: 0 0 4px rgba(255,189,46,0.3); }}
    .dot-g {{ background: #27c93f; box-shadow: 0 0 4px rgba(39,201,63,0.3); }}
    .copied {{ background: rgba(39,201,63,0.16) !important; border-color: rgba(39,201,63,0.28) !important; color: #d1fae5 !important; }}
  </style>
</head>
<body class="bg-slate-50 text-slate-900 dark:bg-darkbg dark:text-slate-100 transition-colors duration-200">
  <header class="sticky top-0 z-40 w-full backdrop-blur-md bg-white/80 dark:bg-darkcard/80 border-b border-slate-200 dark:border-zinc-800 transition-colors">
    <div class="max-w-[1460px] mx-auto px-6 h-16 flex items-center justify-between">
      <a href="/?lang={html.escape(lang)}" class="flex items-center gap-3 font-bold text-lg cursor-pointer hover:opacity-80 transition">
        <svg class="w-6 h-6 text-brand-600 dark:text-brand-500" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"></path><polyline points="3.27 6.96 12 12.01 20.73 6.96"></polyline><line x1="12" y1="22.08" x2="12" y2="12"></line></svg>
        <span>TaskCaptain <span class="font-medium text-slate-500 dark:text-zinc-400">Workspace</span></span>
      </a>
      <div class="flex items-center gap-4">
        {lang_switch}
        <button onclick="toggleTheme()" class="p-2 rounded-full hover:bg-slate-100 dark:hover:bg-zinc-800 text-slate-600 dark:text-zinc-400 transition" title="Toggle Light/Dark Theme">
          <svg id="icon-sun" class="w-5 h-5 hidden" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="5"></circle><line x1="12" y1="1" x2="12" y2="3"></line><line x1="12" y1="21" x2="12" y2="23"></line><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"></line><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"></line><line x1="1" y1="12" x2="3" y2="12"></line><line x1="21" y1="12" x2="23" y2="12"></line><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"></line><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"></line></svg>
          <svg id="icon-moon" class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"></path></svg>
        </button>
      </div>
    </div>
  </header>

  <main class="max-w-[1460px] mx-auto px-6 py-8">
    {body}
  </main>

  <script>
    function applyTheme(theme) {{
      const root = document.documentElement;
      const sun = document.getElementById('icon-sun');
      const moon = document.getElementById('icon-moon');
      if (theme === 'dark') {{
        root.classList.add('dark'); root.classList.remove('light');
        if(sun) sun.classList.remove('hidden');
        if(moon) moon.classList.add('hidden');
      }} else {{
        root.classList.add('light'); root.classList.remove('dark');
        if(sun) sun.classList.add('hidden');
        if(moon) moon.classList.remove('hidden');
      }}
      localStorage.setItem('taskcaptain-theme', theme);
    }}
    function toggleTheme() {{
      const isDark = document.documentElement.classList.contains('dark');
      applyTheme(isDark ? 'light' : 'dark');
    }}
    (function() {{
      const saved = localStorage.getItem('taskcaptain-theme') || 'light';
      applyTheme(saved);
    }})();
    function toggleAllCheckboxes(source) {{
      document.querySelectorAll('.item-checkbox:not([disabled])').forEach(cb => cb.checked = source.checked);
    }}
    function initTabs(root) {{
      (root || document).querySelectorAll('[data-tab-group]').forEach(group => {{
        if (group.dataset.tabsBound === '1') return;
        group.dataset.tabsBound = '1';
        const groupName = group.getAttribute('data-tab-group');
        const storageKey = 'taskcaptain-tab-' + groupName;
        const buttons = Array.from(group.querySelectorAll('[data-tab-target]'));
        const panels = Array.from(document.querySelectorAll(`[data-tab-panel="${{groupName}}"]`));
        function activate(targetId, persist = true) {{
          buttons.forEach(btn => {{
            const active = btn.getAttribute('data-tab-target') === targetId;
            btn.classList.toggle('bg-white', active);
            btn.classList.toggle('dark:bg-zinc-700', active);
            btn.classList.toggle('shadow-sm', active);
            btn.classList.toggle('text-slate-500', !active);
            btn.classList.toggle('dark:text-zinc-400', !active);
          }});
          panels.forEach(panel => {{
            panel.classList.toggle('hidden', panel.id !== targetId);
          }});
          if (persist) {{
            localStorage.setItem(storageKey, targetId);
          }}
        }}
        buttons.forEach(btn => btn.addEventListener('click', () => activate(btn.getAttribute('data-tab-target'))));
        const saved = localStorage.getItem(storageKey);
        const savedBtn = buttons.find(btn => btn.getAttribute('data-tab-target') === saved && !btn.disabled);
        const first = buttons.find(btn => !btn.disabled);
        if (savedBtn) {{
          activate(savedBtn.getAttribute('data-tab-target'), false);
        }} else if (first) {{
          activate(first.getAttribute('data-tab-target'), false);
        }}
      }});
    }}
    document.addEventListener('DOMContentLoaded', () => initTabs(document));
  </script>
</body>
</html>
""".encode('utf-8')


def badge_class_for(status: str) -> str:
    if status == 'running':
        return 'badge-running'
    if status in {'delivered', 'passed'}:
        return 'badge-delivered'
    if status == 'failed':
        return 'badge-failed'
    if status == 'stopped':
        return 'badge-stopped'
    return 'badge-idle'



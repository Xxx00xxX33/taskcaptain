#!/usr/bin/env python3
from __future__ import annotations

import html
import json

try:
    from tc_core import (
        DEFAULT_AGENT_API_KEY,
        DEFAULT_AGENT_ENDPOINT,
        DEFAULT_CODEX_API_KEY,
        DEFAULT_CODEX_ENDPOINT,
        DEFAULT_NO_PROXY,
        DEFAULT_PRODUCT_FOLDER,
        DEFAULT_PROXY,
        DEFAULT_PROFILE_ID,
        I18N,
        effective_goal_text,
        list_claw_profiles,
        list_products,
        load_claw_profile,
        t,
    )
    from tc_runtime import active_run_info
    from tc_ui import badge_class_for, page_template
except ModuleNotFoundError:
    from app.tc_core import (
        DEFAULT_AGENT_API_KEY,
        DEFAULT_AGENT_ENDPOINT,
        DEFAULT_CODEX_API_KEY,
        DEFAULT_CODEX_ENDPOINT,
        DEFAULT_NO_PROXY,
        DEFAULT_PRODUCT_FOLDER,
        DEFAULT_PROXY,
        DEFAULT_PROFILE_ID,
        I18N,
        effective_goal_text,
        list_claw_profiles,
        list_products,
        load_claw_profile,
        t,
    )
    from app.tc_runtime import active_run_info
    from app.tc_ui import badge_class_for, page_template


def render_index_page(lang: str, create_error: str = '') -> bytes:
    items = list_products()
    profiles = list_claw_profiles()
    default_profile = load_claw_profile(DEFAULT_PROFILE_ID)

    product_rows = []
    for item in items:
        cfg = item['config']
        st = item['state']
        claw_eff = item['effectiveClaw']
        pid = cfg.get('id')
        status = st.get('status', 'idle')
        is_running = status == 'running' and bool(active_run_info(pid))
        initial_requirement = cfg.get('initialRequirement') or {}
        manual_goal = (cfg.get('goal') or '').strip()
        if manual_goal:
            goal_text = effective_goal_text(cfg)
        elif initial_requirement:
            goal_text = f"{t(lang, 'initial_requirement_imported')}: {initial_requirement.get('filename', '-')}"
        else:
            goal_text = '-'
        product_rows.append(
            f"""
        <label class='group flex gap-4 p-5 hover:bg-slate-50 dark:hover:bg-zinc-800/40 transition cursor-pointer' onclick="if(event.target.type!=='checkbox')window.location='/product/{pid}?lang={lang}'">
          <input class='mt-1 rounded border-slate-300 text-brand-600 focus:ring-brand-500 bg-white dark:bg-zinc-900 item-checkbox' type='checkbox' name='productIds' value='{html.escape(pid)}' {'disabled' if is_running else ''} onclick='event.stopPropagation()' />
          <div class='flex-1 min-w-0'>
            <div class='flex justify-between items-start gap-4 mb-1'>
              <div>
                <h3 class='text-lg font-semibold text-slate-900 dark:text-slate-100 group-hover:text-brand-600 dark:group-hover:text-brand-400 transition'>{html.escape(cfg.get('name', t(lang, 'untitled')))}</h3>
                <p class='text-xs text-slate-500 mt-0.5'>{html.escape(t(lang, 'profile_label'))}: {html.escape(claw_eff.get('profileName', '-'))}</p>
              </div>
              <span class='badge {badge_class_for(status)}'>
                {html.escape(t(lang, status) if status in I18N[lang] else status)}
              </span>
            </div>
            <p class='text-sm text-slate-600 dark:text-zinc-400 line-clamp-2 leading-relaxed mb-3'>{html.escape(goal_text)}</p>
            <div class='flex flex-wrap gap-x-4 gap-y-2 text-xs text-slate-500 dark:text-zinc-500'>
              <span>{html.escape(t(lang, 'created_at'))}: {html.escape(cfg.get('createdAt', ''))}</span>
              <span>Agent: {html.escape(claw_eff.get('model', '-'))}</span>
              <span>Codex: {html.escape(cfg.get('codex', {}).get('model', '-'))}</span>
            </div>
          </div>
        </label>
        """
        )

    profiles_html = ''.join(
        f"""
        <div class='bg-white dark:bg-darkcard border border-slate-200 dark:border-zinc-800 rounded-2xl p-5 shadow-sm hover:shadow-md transition'>
          <div class='flex justify-between items-start gap-4 mb-3'>
            <h3 class='font-bold text-base'>{html.escape(p.get('name', ''))}</h3>
            <div class='text-right bg-slate-50 dark:bg-zinc-800/50 px-2 py-1.5 rounded-lg border border-slate-100 dark:border-zinc-700 text-xs'>
              <span class='font-semibold block text-slate-700 dark:text-slate-300'>{html.escape(p.get('model', ''))}</span>
              <span class='text-slate-400 dark:text-zinc-500'>Thinking: {html.escape(p.get('thinking', ''))}</span>
            </div>
          </div>
          <p class='text-sm text-slate-500 dark:text-zinc-400 line-clamp-2'>{html.escape(p.get('description', ''))}</p>
        </div>
        """
        for p in profiles
    ) or f'<div class="col-span-2 text-center py-8 text-slate-500 border border-dashed border-slate-300 dark:border-zinc-700 rounded-2xl">{html.escape(t(lang, "no_profiles"))}</div>'

    profile_options = ''.join(
        f"<option value='{html.escape(p.get('id', ''))}'>{html.escape(p.get('name', ''))}</option>" for p in profiles
    )

    input_cls = "w-full bg-slate-50 dark:bg-zinc-900 border border-slate-200 dark:border-zinc-700 rounded-xl px-3.5 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 transition"
    label_cls = "block text-xs font-semibold mb-1 text-slate-700 dark:text-slate-300"
    btn_primary_cls = "w-full bg-slate-900 hover:bg-black dark:bg-brand-600 dark:hover:bg-brand-500 text-white font-medium py-2.5 rounded-xl shadow-sm transition active:scale-[0.98]"
    btn_secondary_cls = "w-full px-4 py-2 font-semibold text-sm bg-white dark:bg-zinc-800 border border-slate-200 dark:border-zinc-700 rounded-xl shadow-sm hover:bg-slate-50 dark:hover:bg-zinc-700 transition active:scale-95"

    error_html = ''
    if create_error:
        error_html = f"""
<div class='mb-5 rounded-2xl border border-red-200 bg-red-50 text-red-700 px-4 py-3 text-sm dark:border-red-500/30 dark:bg-red-500/10 dark:text-red-300'>
  {html.escape(t(lang, 'create_error_prefix'))}{html.escape(create_error)}
</div>
"""

    body = f"""
{error_html}
<div class='mb-6'>
  <h1 class='text-3xl font-bold tracking-tight mb-2'>{html.escape(t(lang, 'app_title'))}</h1>
  <p class='text-slate-500 dark:text-zinc-400 max-w-4xl'>{html.escape(t(lang, 'app_subtitle'))}</p>
</div>

<div class='grid grid-cols-1 xl:grid-cols-[minmax(0,1fr)_390px] gap-6 xl:h-[calc(100vh-210px)]'>
  <section class='bg-white dark:bg-darkcard border border-slate-200 dark:border-zinc-800 rounded-2xl shadow-sm overflow-hidden flex flex-col min-h-[680px] xl:min-h-0'>
    <div class='px-5 py-4 border-b border-slate-200 dark:border-zinc-800 flex flex-wrap items-center justify-between gap-3'>
      <div>
        <h2 class='text-lg font-bold'>{html.escape(t(lang, 'active_products'))}</h2>
        <p class='text-xs text-slate-500 dark:text-zinc-400'>{html.escape(t(lang, 'claw_identity_body'))}</p>
      </div>
      <div class='inline-flex items-center gap-1 rounded-xl bg-slate-100 dark:bg-zinc-800 p-1' data-tab-group='dashboard-left'>
        <button type='button' data-tab-target='tasks-panel' class='px-3 py-1.5 text-sm font-semibold rounded-lg bg-white dark:bg-zinc-700 shadow-sm'>{html.escape(t(lang, 'tasks_tab'))}</button>
        <button type='button' data-tab-target='profiles-panel' class='px-3 py-1.5 text-sm font-semibold rounded-lg text-slate-500 dark:text-zinc-400'>{html.escape(t(lang, 'profiles_tab'))}</button>
      </div>
    </div>

    <div id='tasks-panel' data-tab-panel='dashboard-left' class='flex-1 min-h-0 flex flex-col'>
      <form method='post' action='/bulk-delete' onsubmit='return confirm({json.dumps(t(lang, 'bulk_delete_confirm'))});' class='flex-1 min-h-0 flex flex-col'>
        <input type='hidden' name='lang' value='{html.escape(lang)}' />
        <div class='px-5 py-3 border-b border-slate-200 dark:border-zinc-800 flex flex-wrap items-center justify-between gap-3 bg-slate-50/60 dark:bg-zinc-800/30'>
          <label class='flex items-center gap-2 text-sm font-medium cursor-pointer'>
            <input type='checkbox' class='rounded border-slate-300 text-brand-600 focus:ring-brand-500 bg-white dark:bg-zinc-900' onchange='toggleAllCheckboxes(this)'>
            <span>{html.escape(t(lang, 'select_for_bulk_delete'))}</span>
          </label>
          <div class='flex items-center gap-3'>
            <span class='text-xs text-slate-400'>{html.escape(t(lang, 'running_skip_note'))}</span>
            <button type='submit' class='text-xs font-semibold px-3 py-1.5 bg-red-50 text-red-600 hover:bg-red-100 dark:bg-red-500/10 dark:text-red-400 dark:hover:bg-red-500/20 rounded-lg transition'>{html.escape(t(lang, 'bulk_delete'))}</button>
          </div>
        </div>
        <div class='flex-1 min-h-0 overflow-y-auto divide-y divide-slate-100 dark:divide-zinc-800'>
          {''.join(product_rows) if product_rows else f"<div class='p-8 text-center text-slate-500'>{html.escape(t(lang, 'no_products'))}</div>"}
        </div>
      </form>
    </div>

    <div id='profiles-panel' data-tab-panel='dashboard-left' class='hidden flex-1 min-h-0 overflow-y-auto p-5'>
      <div class='grid grid-cols-1 md:grid-cols-2 gap-4 w-full'>
        {profiles_html}
      </div>
    </div>
  </section>

  <aside class='bg-white dark:bg-darkcard border border-slate-200 dark:border-zinc-800 rounded-2xl shadow-sm overflow-hidden flex flex-col min-h-[680px] xl:min-h-0'>
    <div class='px-5 py-4 border-b border-slate-200 dark:border-zinc-800 flex items-center justify-between gap-3'>
      <div>
        <h2 class='text-lg font-bold'>{html.escape(t(lang, 'create_product'))}</h2>
        <p class='text-xs text-slate-500 dark:text-zinc-400'>{html.escape(t(lang, 'network_setting'))}</p>
      </div>
      <div class='inline-flex items-center gap-1 rounded-xl bg-slate-100 dark:bg-zinc-800 p-1' data-tab-group='dashboard-right'>
        <button type='button' data-tab-target='create-task-panel' class='px-3 py-1.5 text-sm font-semibold rounded-lg bg-white dark:bg-zinc-700 shadow-sm'>{html.escape(t(lang, 'task_form_tab'))}</button>
        <button type='button' data-tab-target='create-profile-panel' class='px-3 py-1.5 text-sm font-semibold rounded-lg text-slate-500 dark:text-zinc-400'>{html.escape(t(lang, 'profile_form_tab'))}</button>
      </div>
    </div>

    <div id='create-task-panel' data-tab-panel='dashboard-right' class='flex-1 min-h-0 overflow-y-auto p-5'>
      <form method='post' action='/create' enctype='multipart/form-data' class='space-y-4' id='create-task-form'>
        <input type='hidden' name='lang' value='{html.escape(lang)}' />
        <div>
          <label class='{label_cls} text-sm'>{html.escape(t(lang, 'product_name'))}</label>
          <input id='create-task-name' name='name' placeholder='e.g. My Awesome App' class='{input_cls} py-2.5' />
        </div>
        <div>
          <label class='{label_cls} text-sm'>{html.escape(t(lang, 'goal'))}</label>
          <textarea id='create-task-goal' name='goal' rows='3' placeholder='{html.escape(t(lang, 'goal_placeholder'))}' class='{input_cls} py-2.5 resize-y'></textarea>
        </div>
        <div class='bg-slate-50/50 dark:bg-zinc-800/30 border border-slate-200 dark:border-zinc-800 rounded-xl p-4 space-y-3'>
          <div class='flex items-center justify-between gap-3'>
            <div>
              <label class='{label_cls} text-sm mb-0'>{html.escape(t(lang, 'initial_requirement_json'))}</label>
              <p class='mt-1 text-xs text-slate-500 dark:text-zinc-400 leading-relaxed'>{html.escape(t(lang, 'initial_requirement_json_help'))}</p>
            </div>
            <span class='text-[11px] font-semibold uppercase tracking-wider text-slate-400'>JSON</span>
          </div>
          <input id='initial-requirement-file' type='file' name='initialRequirementFile' accept='.json,application/json' class='{input_cls} file:mr-4 file:rounded-lg file:border-0 file:bg-slate-900 file:px-3 file:py-2 file:text-sm file:font-semibold file:text-white hover:file:bg-black dark:file:bg-brand-600 dark:hover:file:bg-brand-500' />
          <p class='text-xs text-slate-500 dark:text-zinc-400'>{html.escape(t(lang, 'initial_requirement_json_hint'))}</p>
          <div class='rounded-xl border border-dashed border-slate-300 dark:border-zinc-700 bg-white/70 dark:bg-zinc-900/40 px-3 py-2.5 text-sm text-slate-600 dark:text-zinc-300'>
            <div class='text-[11px] font-bold uppercase tracking-wider text-slate-400 mb-1'>{html.escape(t(lang, 'initial_requirement_json_preview'))}</div>
            <div id='initial-requirement-preview'>{html.escape(t(lang, 'initial_requirement_json_empty'))}</div>
          </div>
        </div>
        <div class='grid grid-cols-1 sm:grid-cols-2 gap-3'>
          <div>
            <label class='{label_cls} text-sm'>{html.escape(t(lang, 'max_turns'))}</label>
            <input type='number' name='maxTurns' min='1' max='99' value='8' class='{input_cls}' />
          </div>
          <div>
            <label class='{label_cls} text-sm'>{html.escape(t(lang, 'product_folder'))}</label>
            <input name='productFolder' value='' placeholder='{html.escape(DEFAULT_PRODUCT_FOLDER)}' class='{input_cls}' />
          </div>
        </div>
        <p class='text-xs text-slate-500 dark:text-zinc-400 -mt-2 leading-relaxed'>{html.escape(t(lang, 'max_turns_help'))}</p>

        <div class='bg-slate-50/50 dark:bg-zinc-800/30 border border-slate-200 dark:border-zinc-800 rounded-xl p-4 space-y-3'>
          <h4 class='text-xs font-bold text-slate-400 uppercase tracking-wider'>{html.escape(t(lang, 'claw_setting'))}</h4>
          <div>
            <label class='{label_cls}'>{html.escape(t(lang, 'claw_profile_select'))}</label>
            <select name='clawProfileId' class='w-full bg-white dark:bg-zinc-900 border border-slate-200 dark:border-zinc-700 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500'>{profile_options}</select>
          </div>
          <div class='grid grid-cols-1 sm:grid-cols-2 gap-3'>
            <div><label class='{label_cls}'>{html.escape(t(lang, 'claw_endpoint'))}</label><input name='clawEndpoint' value='{html.escape(DEFAULT_AGENT_ENDPOINT)}' class='{input_cls}' /></div>
            <div><label class='{label_cls}'>{html.escape(t(lang, 'claw_api_key'))}</label><input type='password' name='clawApiKey' value='{html.escape(DEFAULT_AGENT_API_KEY)}' class='{input_cls}' /></div>
          </div>
          <div class='grid grid-cols-1 sm:grid-cols-2 gap-3'>
            <div><label class='{label_cls}'>{html.escape(t(lang, 'claw_model'))}</label><input name='clawModel' placeholder='{html.escape(default_profile.get('model', ''))}' class='{input_cls}' /></div>
            <div><label class='{label_cls}'>{html.escape(t(lang, 'claw_thinking'))}</label>
              <select name='clawThinking' class='{input_cls}'>
                <option value=''>inherit({html.escape(default_profile.get('thinking', ''))})</option>
                <option value='low'>low</option>
                <option value='medium'>medium</option>
                <option value='high'>high</option>
                <option value='xhigh'>xhigh</option>
              </select></div>
          </div>
        </div>

        <div class='bg-slate-50/50 dark:bg-zinc-800/30 border border-slate-200 dark:border-zinc-800 rounded-xl p-4 space-y-3'>
          <h4 class='text-xs font-bold text-slate-400 uppercase tracking-wider'>{html.escape(t(lang, 'codex_setting'))}</h4>
          <div class='grid grid-cols-1 sm:grid-cols-2 gap-3'>
            <div><label class='{label_cls}'>{html.escape(t(lang, 'codex_endpoint'))}</label><input name='codexEndpoint' value='{html.escape(DEFAULT_CODEX_ENDPOINT)}' class='{input_cls}' /></div>
            <div><label class='{label_cls}'>{html.escape(t(lang, 'codex_api_key'))}</label><input type='password' name='codexApiKey' value='{html.escape(DEFAULT_CODEX_API_KEY)}' class='{input_cls}' /></div>
          </div>
          <div class='grid grid-cols-1 sm:grid-cols-2 gap-3'>
            <div><label class='{label_cls}'>{html.escape(t(lang, 'codex_model'))}</label><input name='codexModel' value='gpt-5.4-medium' class='{input_cls}' /></div>
            <div><label class='{label_cls}'>{html.escape(t(lang, 'codex_thinking'))}</label>
                <select name='codexThinking' class='{input_cls}'>
                  <option value='low'>low</option>
                  <option value='medium' selected>medium</option>
                  <option value='high'>high</option>
                  <option value='xhigh'>xhigh</option>
                </select></div>
          </div>
          <div class='flex flex-col gap-2 sm:flex-row sm:gap-4 mt-2'>
            <label class='flex items-center gap-2 text-sm font-medium cursor-pointer'>
              <input type='checkbox' name='codexPlanMode' checked class='rounded border-slate-300 text-brand-600 focus:ring-brand-500 bg-white dark:bg-zinc-900'>
              <span>{html.escape(t(lang, 'enable_plan'))}</span>
            </label>
            <label class='flex items-center gap-2 text-sm font-medium cursor-pointer'>
              <input type='checkbox' name='codexMaxPermission' checked class='rounded border-slate-300 text-brand-600 focus:ring-brand-500 bg-white dark:bg-zinc-900'>
              <span>{html.escape(t(lang, 'enable_max_permission'))}</span>
            </label>
          </div>
        </div>

        <div class='bg-slate-50/50 dark:bg-zinc-800/30 border border-slate-200 dark:border-zinc-800 rounded-xl p-4 space-y-3'>
          <h4 class='text-xs font-bold text-slate-400 uppercase tracking-wider'>{html.escape(t(lang, 'network_setting'))}</h4>
          <div class='grid grid-cols-1 sm:grid-cols-2 gap-3'>
            <div><label class='{label_cls}'>{html.escape(t(lang, 'proxy_url'))}</label><input name='proxy' value='{html.escape(DEFAULT_PROXY)}' placeholder='http://127.0.0.1:7897' class='{input_cls}' /></div>
            <div><label class='{label_cls}'>{html.escape(t(lang, 'no_proxy'))}</label><input name='noProxy' value='{html.escape(DEFAULT_NO_PROXY)}' class='{input_cls}' /></div>
          </div>
          <p class='text-xs text-slate-500 dark:text-zinc-400'>{html.escape(t(lang, 'proxy_help'))}</p>
        </div>

        <button type='submit' class='{btn_primary_cls}'>{html.escape(t(lang, 'create_button'))}</button>
      </form>
    </div>

    <div id='create-profile-panel' data-tab-panel='dashboard-right' class='hidden flex-1 min-h-0 overflow-y-auto p-5'>
      <form method='post' action='/profiles/create' class='space-y-4'>
        <input type='hidden' name='lang' value='{html.escape(lang)}' />
        <div><label class='{label_cls}'>{html.escape(t(lang, 'profile_name'))}</label><input name='profileName' placeholder='e.g. Sandrone Network Auditor' class='{input_cls}' /></div>
        <div><label class='{label_cls}'>{html.escape(t(lang, 'profile_description'))}</label><input name='profileDescription' placeholder='{html.escape(t(lang, 'profile_desc_placeholder'))}' class='{input_cls}' /></div>
        <div class='grid grid-cols-2 gap-3'>
          <div><label class='{label_cls}'>{html.escape(t(lang, 'profile_model_hint'))}</label><input name='profileModel' value='{html.escape(default_profile.get('model', ''))}' class='{input_cls}' /></div>
          <div><label class='{label_cls}'>{html.escape(t(lang, 'profile_thinking_hint'))}</label><input name='profileThinking' value='{html.escape(default_profile.get('thinking', ''))}' class='{input_cls}' /></div>
        </div>
        <div><label class='{label_cls}'>{html.escape(t(lang, 'claw_soul'))}</label><textarea name='profileSoul' rows='3' class='{input_cls}'>{html.escape(default_profile.get('soul', ''))}</textarea></div>
        <div><label class='{label_cls}'>{html.escape(t(lang, 'claw_skills'))}</label><textarea name='profileSkills' rows='3' class='{input_cls}'>{html.escape(default_profile.get('skills', ''))}</textarea></div>
        <button type='submit' class='{btn_secondary_cls} mt-2'>{html.escape(t(lang, 'create_profile_button'))}</button>
      </form>
    </div>
  </aside>
</div>

<script>
  (function() {{
    const fileInput = document.getElementById('initial-requirement-file');
    const preview = document.getElementById('initial-requirement-preview');
    const nameInput = document.getElementById('create-task-name');
    if (!fileInput || !preview) return;

    const emptyText = {json.dumps(t(lang, 'initial_requirement_json_empty'))};
    const invalidText = {json.dumps(t(lang, 'initial_requirement_json_invalid'))};
    const readyTemplate = {json.dumps(t(lang, 'initial_requirement_json_ready', filename='__FILENAME__', size='__SIZE__'))};

    function formatSize(size) {{
      if (!Number.isFinite(size)) return '-';
      if (size < 1024) return `${{size}} B`;
      if (size < 1024 * 1024) return `${{(size / 1024).toFixed(1)}} KB`;
      return `${{(size / (1024 * 1024)).toFixed(1)}} MB`;
    }}

    fileInput.addEventListener('change', async () => {{
      const file = fileInput.files && fileInput.files[0];
      if (!file) {{
        preview.textContent = emptyText;
        return;
      }}
      try {{
        const raw = await file.text();
        const parsed = JSON.parse(raw);
        const summary = readyTemplate
          .replace('__FILENAME__', file.name)
          .replace('__SIZE__', formatSize(file.size));
        const extra = [];
        if (parsed && typeof parsed === 'object' && !Array.isArray(parsed)) {{
          const keys = Object.keys(parsed).slice(0, 8);
          if (keys.length) extra.push(`keys: ${{keys.join(', ')}}`);
          const nameCandidate = parsed.name || parsed.title || parsed.taskName || parsed.productName || parsed.projectName;
          if (!nameInput.value.trim() && typeof nameCandidate === 'string' && nameCandidate.trim()) {{
            nameInput.value = nameCandidate.trim();
          }}
        }}
        preview.textContent = extra.length ? `${{summary}}\\n${{extra.join('\\n')}}` : summary;
      }} catch (err) {{
        preview.textContent = invalidText;
      }}
    }});
  }})();
</script>
"""
    return page_template(t(lang, 'app_title'), body, lang, '/')

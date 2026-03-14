#!/usr/bin/env python3
from __future__ import annotations

import html
import json

try:
    from tc_core import (
        DEFAULT_AGENT_ENDPOINT,
        DEFAULT_CODEX_ENDPOINT,
        DEFAULT_PRODUCT_FOLDER,
        DEFAULT_PROFILE_ID,
        I18N,
        effective_claw_config,
        list_claw_profiles,
        list_products,
        load_claw_profile,
        load_product_config,
        load_product_state,
        mask_present,
        t,
    )
    from tc_runtime import active_run_info
    from tc_ui import badge_class_for, build_product_live_payload, page_template
except ModuleNotFoundError:
    from app.tc_core import (
        DEFAULT_AGENT_ENDPOINT,
        DEFAULT_CODEX_ENDPOINT,
        DEFAULT_PRODUCT_FOLDER,
        DEFAULT_PROFILE_ID,
        I18N,
        effective_claw_config,
        list_claw_profiles,
        list_products,
        load_claw_profile,
        load_product_config,
        load_product_state,
        mask_present,
        t,
    )
    from app.tc_runtime import active_run_info
    from app.tc_ui import badge_class_for, build_product_live_payload, page_template

def render_index_page(lang: str) -> bytes:
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
        goal_text = cfg.get('goal', '') or '—'
        product_rows.append(f"""
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
        """)

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

    body = f"""
<div class='mb-8'>
  <h1 class='text-3xl font-bold tracking-tight mb-2'>{html.escape(t(lang, 'app_title'))}</h1>
  <p class='text-slate-500 dark:text-zinc-400'>{html.escape(t(lang, 'app_subtitle'))}</p>
</div>

<div class='grid grid-cols-1 xl:grid-cols-[1fr_420px] gap-8 items-start'>
  <div class='space-y-10'>

<section>
  <div class='flex items-center justify-between mb-4'>
    <h2 class='text-xl font-bold flex items-center gap-2'>{html.escape(t(lang, 'active_products'))}</h2>
  </div>
  
  <form method='post' action='/bulk-delete' onsubmit='return confirm({json.dumps(t(lang, 'bulk_delete_confirm'))});'>
    <input type='hidden' name='lang' value='{html.escape(lang)}' />
    <div class='bg-white dark:bg-darkcard border border-slate-200 dark:border-zinc-800 rounded-2xl shadow-sm overflow-hidden'>
      <div class='bg-slate-50/50 dark:bg-zinc-800/20 px-4 py-3 border-b border-slate-200 dark:border-zinc-800 flex justify-between items-center'>
        <label class='flex items-center gap-2 text-sm font-medium cursor-pointer'>
          <input type='checkbox' class='rounded border-slate-300 text-brand-600 focus:ring-brand-500 bg-white dark:bg-zinc-900' onchange='toggleAllCheckboxes(this)'>
          <span>{html.escape(t(lang, 'select_for_bulk_delete'))}</span>
        </label>
        <div class='flex items-center gap-3'>
          <span class='text-xs text-slate-400'>{html.escape(t(lang, 'running_skip_note'))}</span>
          <button type='submit' class='text-xs font-semibold px-3 py-1.5 bg-red-50 text-red-600 hover:bg-red-100 dark:bg-red-500/10 dark:text-red-400 dark:hover:bg-red-500/20 rounded-lg transition'>{html.escape(t(lang, 'bulk_delete'))}</button>
        </div>
      </div>
      <div class='divide-y divide-slate-100 dark:divide-zinc-800'>
        {''.join(product_rows) if product_rows else f"<div class='p-8 text-center text-slate-500'>{html.escape(t(lang, 'no_products'))}</div>"}
      </div>
    </div>
  </form>
</section>

<section>
  <div class='flex items-center justify-between mb-4'>
    <h2 class='text-xl font-bold'>{html.escape(t(lang, 'reusable_claw_profiles'))}</h2>
  </div>
  <p class='text-sm text-slate-500 dark:text-zinc-400 mb-4 max-w-3xl leading-relaxed'>{html.escape(t(lang, 'claw_identity_body'))}</p>
  <div class='grid grid-cols-1 md:grid-cols-2 gap-4'>
    {profiles_html}
  </div>
</section>

  </div>

  <div class='xl:sticky xl:top-24 space-y-6'>

<div class='bg-white dark:bg-darkcard border border-slate-200 dark:border-zinc-800 rounded-2xl shadow-sm overflow-hidden flex flex-col'>
  <div class='bg-slate-50/80 dark:bg-zinc-800/40 px-5 py-4 border-b border-slate-200 dark:border-zinc-800'>
    <h3 class='font-bold text-[0.95rem] flex items-center gap-2 tracking-wide uppercase'>
      <span class='text-brand-500'>✦</span> {html.escape(t(lang, 'create_product'))}
    </h3>
  </div>
  <div class='p-5 flex-1'>
    <form method='post' action='/create' class='space-y-4'>
      <input type='hidden' name='lang' value='{html.escape(lang)}' />
      <div>
        <label class='{label_cls} text-sm'>{html.escape(t(lang, 'product_name'))}</label>
        <input name='name' placeholder='e.g. My Awesome App' class='{input_cls} py-2.5' />
      </div>
      <div>
        <label class='{label_cls} text-sm'>{html.escape(t(lang, 'goal'))}</label>
        <textarea name='goal' rows='2' placeholder='{html.escape(t(lang, 'goal_placeholder'))}' class='{input_cls} py-2.5 resize-y'></textarea>
      </div>
      <div>
        <label class='{label_cls} text-sm'>{html.escape(t(lang, 'max_turns'))}</label>
        <input type='number' name='maxTurns' min='1' max='99' value='8' class='{input_cls}' />
        <p class='text-xs text-slate-500 dark:text-zinc-400 mt-1 leading-relaxed'>{html.escape(t(lang, 'max_turns_help'))}</p>
      </div>
      <div>
        <label class='{label_cls} text-sm'>{html.escape(t(lang, 'product_folder'))}</label>
        <input name='productFolder' value='' placeholder='{html.escape(DEFAULT_PRODUCT_FOLDER)}' class='{input_cls}' />
      </div>
      
      <div class='bg-slate-50/50 dark:bg-zinc-800/30 border border-slate-200 dark:border-zinc-800 rounded-xl p-4 space-y-3'>
        <h4 class='text-xs font-bold text-slate-400 uppercase tracking-wider'>{html.escape(t(lang, 'claw_setting'))}</h4>
        <div>
          <label class='{label_cls}'>{html.escape(t(lang, 'claw_profile_select'))}</label>
          <select name='clawProfileId' class='w-full bg-white dark:bg-zinc-900 border border-slate-200 dark:border-zinc-700 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500'>{profile_options}</select>
        </div>
        <details class='group'>
          <summary class='text-xs font-medium text-brand-600 dark:text-brand-400 cursor-pointer hover:underline outline-none select-none'>+ 展开高级配置 (API, Model, Soul...)</summary>
          <div class='pt-3 space-y-3'>
            <div class='grid grid-cols-2 gap-3'>
              <div><label class='{label_cls}'>{html.escape(t(lang, 'claw_endpoint'))}</label><input name='clawEndpoint' value='{html.escape(DEFAULT_AGENT_ENDPOINT)}' class='{input_cls}' /></div>
              <div><label class='{label_cls}'>{html.escape(t(lang, 'claw_api_key'))}</label><input type='password' name='clawApiKey' class='{input_cls}' /></div>
            </div>
            <div class='grid grid-cols-2 gap-3'>
              <div><label class='{label_cls}'>{html.escape(t(lang, 'claw_model'))}</label><input name='clawModel' placeholder='{html.escape(default_profile.get('model', ''))}' class='{input_cls}' /></div>
              <div><label class='{label_cls}'>{html.escape(t(lang, 'claw_thinking'))}</label>
                <select name='clawThinking' class='{input_cls}'>
                  <option value=''>inherit({html.escape(default_profile.get('thinking',''))})</option>
                  <option value='low'>low</option>
                  <option value='medium'>medium</option>
                  <option value='high'>high</option>
                  <option value='xhigh'>xhigh</option>
                </select></div>
            </div>
            <div><label class='{label_cls}'>{html.escape(t(lang, 'claw_soul'))}</label><textarea name='clawSoul' rows='2' placeholder='{html.escape(t(lang, 'profile_soul_placeholder'))}' class='{input_cls}'></textarea></div>
            <div><label class='{label_cls}'>{html.escape(t(lang, 'claw_skills'))}</label><textarea name='clawSkills' rows='2' placeholder='{html.escape(t(lang, 'profile_skills_placeholder'))}' class='{input_cls}'></textarea></div>
          </div>
        </details>
      </div>

      <div class='bg-slate-50/50 dark:bg-zinc-800/30 border border-slate-200 dark:border-zinc-800 rounded-xl p-4 space-y-3'>
        <h4 class='text-xs font-bold text-slate-400 uppercase tracking-wider'>{html.escape(t(lang, 'codex_setting'))}</h4>
        <div class='grid grid-cols-2 gap-3'>
          <div><label class='{label_cls}'>{html.escape(t(lang, 'codex_endpoint'))}</label><input name='codexEndpoint' value='{html.escape(DEFAULT_CODEX_ENDPOINT)}' class='{input_cls}' /></div>
          <div><label class='{label_cls}'>{html.escape(t(lang, 'codex_api_key'))}</label><input type='password' name='codexApiKey' class='{input_cls}' /></div>
        </div>
        <div class='grid grid-cols-2 gap-3'>
          <div><label class='{label_cls}'>{html.escape(t(lang, 'codex_model'))}</label><input name='codexModel' value='gpt-5.4-medium' class='{input_cls}' /></div>
          <div><label class='{label_cls}'>{html.escape(t(lang, 'codex_thinking'))}</label>
              <select name='codexThinking' class='{input_cls}'>
                <option value='low'>low</option>
                <option value='medium' selected>medium</option>
                <option value='high'>high</option>
                <option value='xhigh'>xhigh</option>
              </select></div>
        </div>
        <div class='flex gap-4 mt-2'>
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

      <button type='submit' class='{btn_primary_cls}'>{html.escape(t(lang, 'create_button'))}</button>
    </form>
  </div>
</div>

<div class='bg-white dark:bg-darkcard border border-slate-200 dark:border-zinc-800 rounded-2xl shadow-sm overflow-hidden flex flex-col'>
  <div class='bg-slate-50/80 dark:bg-zinc-800/40 px-5 py-4 border-b border-slate-200 dark:border-zinc-800'>
    <h3 class='font-bold text-[0.95rem] flex items-center gap-2 tracking-wide uppercase'>
      <span class='text-slate-400'>+</span> {html.escape(t(lang, 'create_profile'))}
    </h3>
  </div>
  <div class='p-5 flex-1'>
    <form method='post' action='/profiles/create' class='space-y-4'>
      <input type='hidden' name='lang' value='{html.escape(lang)}' />
      <div><label class='{label_cls}'>{html.escape(t(lang, 'profile_name'))}</label><input name='profileName' placeholder='e.g. Sandrone Network Auditor' class='{input_cls}' /></div>
      <div><label class='{label_cls}'>{html.escape(t(lang, 'profile_description'))}</label><input name='profileDescription' placeholder='{html.escape(t(lang, 'profile_desc_placeholder'))}' class='{input_cls}' /></div>
      <div class='grid grid-cols-2 gap-3'>
        <div><label class='{label_cls}'>{html.escape(t(lang, 'profile_model_hint'))}</label><input name='profileModel' value='{html.escape(default_profile.get('model', ''))}' class='{input_cls}' /></div>
        <div><label class='{label_cls}'>{html.escape(t(lang, 'profile_thinking_hint'))}</label><input name='profileThinking' value='{html.escape(default_profile.get('thinking', ''))}' class='{input_cls}' /></div>
      </div>
      <div><label class='{label_cls}'>{html.escape(t(lang, 'claw_soul'))}</label><textarea name='profileSoul' rows='2' class='{input_cls}'>{html.escape(default_profile.get('soul', ''))}</textarea></div>
      <div><label class='{label_cls}'>{html.escape(t(lang, 'claw_skills'))}</label><textarea name='profileSkills' rows='2' class='{input_cls}'>{html.escape(default_profile.get('skills', ''))}</textarea></div>
      <button type='submit' class='{btn_secondary_cls} mt-2'>{html.escape(t(lang, 'create_profile_button'))}</button>
    </form>
  </div>
</div>

  </div>
</div>
"""
    return page_template(t(lang, 'app_title'), body, lang, '/')

def render_product_page(pid: str, lang: str) -> bytes:
    cfg = load_product_config(pid)
    st = load_product_state(pid)
    claw_eff = effective_claw_config(cfg)
    live = build_product_live_payload(pid, lang)
    profile = load_claw_profile(claw_eff.get('profileId'))

    input_cls = "w-full bg-slate-50 dark:bg-zinc-900 border border-slate-200 dark:border-zinc-700 rounded-xl px-3.5 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 transition"
    label_cls = "block text-xs font-semibold mb-1 text-slate-700 dark:text-slate-300"
    btn_secondary_cls = "px-4 py-2 font-semibold text-sm bg-white dark:bg-zinc-800 border border-slate-200 dark:border-zinc-700 rounded-xl shadow-sm hover:bg-slate-50 dark:hover:bg-zinc-700 transition active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed"

    body = f"""
<a href='/?lang={lang}' class='inline-flex items-center gap-2 text-sm font-semibold text-slate-500 hover:text-slate-900 dark:text-zinc-400 dark:hover:text-slate-100 mb-6 transition'>
  <svg class='w-4 h-4' fill='none' viewBox='0 0 24 24' stroke='currentColor' stroke-width='2'><path stroke-linecap='round' stroke-linejoin='round' d='M10 19l-7-7m0 0l7-7m-7 7h18' /></svg>
  {html.escape(t(lang, 'back'))}
</a>

<div class='flex flex-wrap items-start justify-between gap-6 mb-8'>
  <div>
<h1 class='text-3xl font-bold flex items-center flex-wrap gap-3 mb-2'>
  {html.escape(cfg.get('name', t(lang, 'untitled')))}
  <span class='badge {live['statusClass']}' id='product-status-badge'>{html.escape(live['statusLabel'])}</span>
  <span class='badge {live['selfTestStatusClass']}' id='self-test-status-badge' data-label-prefix='{html.escape(t(lang, 'self_test'))}: '>{html.escape(t(lang, 'self_test'))}: {html.escape(live['selfTestStatusLabel'])}</span>
  <span class='badge badge-idle' id='turn-progress-badge' data-label-prefix='{html.escape(t(lang, 'turn_progress'))}: '>{html.escape(t(lang, 'turn_progress'))}: {int(st.get('currentTurn') or 0)}/{int(cfg.get('maxTurns') or 8)}</span>
</h1>
<div class='font-mono text-sm text-slate-500 dark:text-zinc-400 flex gap-4 flex-wrap'>
  <span>ID: {html.escape(pid)}</span>
  <span>Dir: {html.escape(cfg.get('productFolder', ''))}</span>
</div>
  </div>
  
  <div class='flex flex-wrap items-center gap-3'>
<form method='post' action='/selftest/{html.escape(pid)}' class='m-0'>
  <input type='hidden' name='lang' value='{html.escape(lang)}' />
  <button type='submit' class='{btn_secondary_cls}' id='run-self-test-btn' {'disabled' if live['selfTestRunning'] else ''}>{html.escape(t(lang, 'run_self_test'))}</button>
</form>
<form method='post' action='/start/{html.escape(pid)}' class='m-0'>
  <input type='hidden' name='lang' value='{html.escape(lang)}' />
  <button type='submit' class='px-4 py-2 font-semibold text-sm bg-slate-900 hover:bg-black dark:bg-brand-600 dark:hover:bg-brand-500 text-white rounded-xl shadow-sm transition active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed' id='start-run-btn' {'disabled' if live['isRunning'] else ''}>{html.escape(t(lang, 'start_continue_run'))}</button>
</form>
<form method='post' action='/stop/{html.escape(pid)}' class='m-0'>
  <input type='hidden' name='lang' value='{html.escape(lang)}' />
  <button type='submit' class='{btn_secondary_cls}' id='stop-run-btn' {'disabled' if not live['isRunning'] else ''}>{html.escape(t(lang, 'stop_run'))}</button>
</form>
<form method='post' action='/delete/{html.escape(pid)}' class='m-0' onsubmit='return confirm({json.dumps(t(lang, 'delete_confirm'))});'>
  <input type='hidden' name='lang' value='{html.escape(lang)}' />
  <button type='submit' class='p-2 bg-red-50 text-red-600 hover:bg-red-100 dark:bg-red-500/10 dark:text-red-400 dark:hover:bg-red-500/20 rounded-xl transition active:scale-95 ml-2 disabled:opacity-50 disabled:cursor-not-allowed' id='delete-product-btn' {'disabled' if live['isRunning'] else ''} title='{html.escape(t(lang, 'delete_product'))}'>
    <svg class='w-5 h-5' fill='none' viewBox='0 0 24 24' stroke='currentColor' stroke-width='2'><path stroke-linecap='round' stroke-linejoin='round' d='M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16' /></svg>
  </button>
</form>
  </div>
</div>

<div class='bg-white dark:bg-darkcard border border-slate-200 dark:border-zinc-800 rounded-2xl shadow-sm mb-6 overflow-hidden'>
  <div class='bg-slate-50/80 dark:bg-zinc-800/40 px-5 py-4 border-b border-slate-200 dark:border-zinc-800'>
<h3 class='font-bold uppercase tracking-wider text-sm'>{html.escape(t(lang, 'configuration_details'))}</h3>
  </div>
  <div class='grid grid-cols-1 md:grid-cols-3 divide-y md:divide-y-0 md:divide-x divide-slate-100 dark:divide-zinc-800 p-5 gap-6 md:gap-0'>
<div class='md:pr-6'>
  <h4 class='text-xs font-bold text-slate-400 uppercase tracking-wider mb-2'>{html.escape(t(lang, 'goal'))}</h4>
  <div class='text-sm bg-slate-50 dark:bg-zinc-800/50 p-3 rounded-xl border border-slate-100 dark:border-zinc-800 leading-relaxed whitespace-pre-wrap'>{html.escape(cfg.get('goal', ''))}</div>
</div>
<div class='md:px-6'>
  <h4 class='text-xs font-bold text-slate-400 uppercase tracking-wider mb-2'>{html.escape(t(lang, 'claw_setting'))}</h4>
  <ul class='text-sm space-y-2'>
    <li><b class='text-slate-700 dark:text-slate-300'>{html.escape(t(lang, 'profile_label'))}:</b> {html.escape(claw_eff.get('profileName', ''))}</li>
    <li><b class='text-slate-700 dark:text-slate-300'>{html.escape(t(lang, 'model'))}:</b> {html.escape(claw_eff.get('model', ''))} <span class='text-slate-400'>({html.escape(claw_eff.get('thinking', ''))})</span></li>
    <li>
      <b class='text-slate-700 dark:text-slate-300'>{html.escape(t(lang, 'claw_thinking'))}:</b>
      <form method='post' action='/set-claw-thinking/{html.escape(pid)}' class='inline-flex items-center gap-2 ml-2 align-middle'>
        <input type='hidden' name='lang' value='{html.escape(lang)}' />
        <select name='thinking' class='bg-slate-50 dark:bg-zinc-900 border border-slate-200 dark:border-zinc-700 rounded-lg px-2 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 transition'>
          <option value=''>inherit({html.escape(profile.get('thinking',''))})</option>
          <option value='low' {'selected' if (claw_eff.get('thinking')=='low') else ''}>low</option>
          <option value='medium' {'selected' if (claw_eff.get('thinking')=='medium') else ''}>medium</option>
          <option value='high' {'selected' if (claw_eff.get('thinking')=='high') else ''}>high</option>
          <option value='xhigh' {'selected' if (claw_eff.get('thinking')=='xhigh') else ''}>xhigh</option>
        </select>
        <button type='submit' class='px-2.5 py-1 text-xs font-semibold bg-white dark:bg-zinc-800 border border-slate-200 dark:border-zinc-700 rounded-lg hover:bg-slate-50 dark:hover:bg-zinc-700 transition'>保存</button>
      </form>
    </li>
    <li><b class='text-slate-700 dark:text-slate-300'>{html.escape(t(lang, 'api_key_present'))}:</b> <span class='{'text-emerald-600 bg-emerald-50 dark:bg-emerald-900/30' if claw_eff.get('apiKey') else 'text-red-600 bg-red-50 dark:bg-red-900/30'} px-1.5 rounded text-xs'>{html.escape(t(lang, mask_present(claw_eff.get('apiKey'))))}</span></li>
    <li class='font-mono text-xs text-slate-500 mt-1 break-all'>{html.escape(claw_eff.get('endpoint', ''))}</li>
  </ul>
</div>
<div class='md:pl-6'>
  <h4 class='text-xs font-bold text-slate-400 uppercase tracking-wider mb-2'>{html.escape(t(lang, 'codex_setting'))}</h4>
  <ul class='text-sm space-y-2'>
    <li><b class='text-slate-700 dark:text-slate-300'>{html.escape(t(lang, 'model'))}:</b> {html.escape(cfg.get('codex', {}).get('model', ''))} <span class='text-slate-400'>({html.escape(cfg.get('codex', {}).get('thinking', ''))})</span></li>
    <li>
      <b class='text-slate-700 dark:text-slate-300'>{html.escape(t(lang, 'codex_thinking'))}:</b>
      <form method='post' action='/set-codex-thinking/{html.escape(pid)}' class='inline-flex items-center gap-2 ml-2 align-middle'>
        <input type='hidden' name='lang' value='{html.escape(lang)}' />
        <select name='thinking' class='bg-slate-50 dark:bg-zinc-900 border border-slate-200 dark:border-zinc-700 rounded-lg px-2 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 transition'>
          <option value='low' {'selected' if (cfg.get('codex', {}).get('thinking')=='low') else ''}>low</option>
          <option value='medium' {'selected' if (cfg.get('codex', {}).get('thinking')=='medium') else ''}>medium</option>
          <option value='high' {'selected' if (cfg.get('codex', {}).get('thinking')=='high') else ''}>high</option>
          <option value='xhigh' {'selected' if (cfg.get('codex', {}).get('thinking')=='xhigh') else ''}>xhigh</option>
        </select>
        <button type='submit' class='px-2.5 py-1 text-xs font-semibold bg-white dark:bg-zinc-800 border border-slate-200 dark:border-zinc-700 rounded-lg hover:bg-slate-50 dark:hover:bg-zinc-700 transition'>保存</button>
      </form>
    </li>
    <li><b class='text-slate-700 dark:text-slate-300'>{html.escape(t(lang, 'api_key_present'))}:</b> <span class='{'text-emerald-600 bg-emerald-50 dark:bg-emerald-900/30' if cfg.get('codex', {}).get('apiKey') else 'text-red-600 bg-red-50 dark:bg-red-900/30'} px-1.5 rounded text-xs'>{html.escape(t(lang, mask_present(cfg.get('codex', {}).get('apiKey'))))}</span></li>
    <li class='font-mono text-xs text-slate-500 mt-1 break-all'>{html.escape(cfg.get('codex', {}).get('endpoint', ''))}</li>
    <li>
      <b class='text-slate-700 dark:text-slate-300'>{html.escape(t(lang, 'max_turns'))}:</b>
      <form method='post' action='/set-max-turns/{html.escape(pid)}' class='inline-flex items-center gap-2 ml-2 align-middle'>
        <input type='hidden' name='lang' value='{html.escape(lang)}' />
        <input type='number' name='maxTurns' min='1' max='99' value='{html.escape(str(int(cfg.get('maxTurns') or 8)))}' class='w-20 bg-slate-50 dark:bg-zinc-900 border border-slate-200 dark:border-zinc-700 rounded-lg px-2 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 transition' />
        <button type='submit' class='px-2.5 py-1 text-xs font-semibold bg-white dark:bg-zinc-800 border border-slate-200 dark:border-zinc-700 rounded-lg hover:bg-slate-50 dark:hover:bg-zinc-700 transition'>保存</button>
      </form>
    </li>

    <li class='flex gap-2 mt-2'>
      <span class='text-[10px] uppercase font-bold bg-slate-100 dark:bg-zinc-800 px-2 py-0.5 rounded border border-slate-200 dark:border-zinc-700'>Plan: {cfg.get('codex', {}).get('planMode')}</span>
      <span class='text-[10px] uppercase font-bold bg-slate-100 dark:bg-zinc-800 px-2 py-0.5 rounded border border-slate-200 dark:border-zinc-700'>MaxPerm: {cfg.get('codex', {}).get('maxPermission')}</span>
    </li>
  </ul>
</div>
  </div>
</div>

<div class='grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6'>
  
  <div class='bg-white dark:bg-darkcard border border-slate-200 dark:border-zinc-800 rounded-2xl shadow-sm flex flex-col h-[500px]'>
<div class='bg-slate-50/80 dark:bg-zinc-800/40 px-5 py-4 border-b border-slate-200 dark:border-zinc-800 shrink-0'>
  <h3 class='font-bold uppercase tracking-wider text-sm flex items-center justify-between'>
    {html.escape(t(lang, 'user_claw_dialogue'))}
    <span class='w-2 h-2 rounded-full bg-brand-500 animate-pulse {'hidden' if not live['isRunning'] else ''}'></span>
  </h3>
</div>
<div id='user-claw-dialogue' class='flex-1 overflow-y-auto bg-slate-50/30 dark:bg-zinc-900/30'>{live['userClawHtml']}</div>
<div class='p-4 border-t border-slate-200 dark:border-zinc-800 bg-white dark:bg-darkcard rounded-b-2xl shrink-0'>
  <form method='post' action='/append-user/{html.escape(pid)}' class='flex gap-3 m-0'>
    <input type='hidden' name='lang' value='{html.escape(lang)}' />
    <input type='text' name='message' placeholder='{html.escape(t(lang, 'append_placeholder'))}' required class='flex-1 bg-slate-50 dark:bg-zinc-900 border border-slate-200 dark:border-zinc-700 rounded-xl px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 transition'>
    <button type='submit' class='px-5 py-2 bg-brand-600 hover:bg-brand-700 text-white text-sm font-semibold rounded-xl shadow-sm transition active:scale-95 whitespace-nowrap'>{html.escape(t(lang, 'append_button'))}</button>
  </form>
</div>
  </div>

  <div class='bg-white dark:bg-darkcard border border-slate-200 dark:border-zinc-800 rounded-2xl shadow-sm flex flex-col h-[500px]'>
<div class='bg-slate-50/80 dark:bg-zinc-800/40 px-5 py-4 border-b border-slate-200 dark:border-zinc-800 shrink-0'>
  <h3 class='font-bold uppercase tracking-wider text-sm'>{html.escape(t(lang, 'claw_codex_dialogue'))}</h3>
</div>
<div id='claw-codex-dialogue' class='flex-1 overflow-y-auto bg-slate-50/30 dark:bg-zinc-900/30 rounded-b-2xl'>{live['clawCodexHtml']}</div>
  </div>

</div>

<div class='grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8'>
  
  <div class='bg-white dark:bg-darkcard border border-slate-200 dark:border-zinc-800 rounded-2xl shadow-sm flex flex-col'>
<div class='bg-slate-50/80 dark:bg-zinc-800/40 px-5 py-4 border-b border-slate-200 dark:border-zinc-800'>
  <h3 class='font-bold uppercase tracking-wider text-sm'>{html.escape(t(lang, 'save_current_claw_profile'))}</h3>
</div>
<div class='p-5'>
  <p class='text-sm text-slate-500 dark:text-zinc-400 mb-4'>{html.escape(t(lang, 'profile_saved_hint'))}</p>
  <form method='post' action='/save-profile/{html.escape(pid)}' class='space-y-4 m-0'>
    <input type='hidden' name='lang' value='{html.escape(lang)}' />
    <div><label class='{label_cls}'>{html.escape(t(lang, 'profile_name'))}</label><input name='profileName' placeholder='{html.escape(claw_eff.get('profileName', ''))}' class='{input_cls}' /></div>
    <div><label class='{label_cls}'>{html.escape(t(lang, 'profile_description'))}</label><input name='profileDescription' placeholder='{html.escape(t(lang, 'profile_desc_placeholder'))}' class='{input_cls}' /></div>
    <button type='submit' class='{btn_secondary_cls} w-full mt-2'>{html.escape(t(lang, 'save_profile_button'))}</button>
  </form>
</div>
  </div>

  <div class='bg-white dark:bg-darkcard border border-slate-200 dark:border-zinc-800 rounded-2xl shadow-sm flex flex-col'>
<div class='bg-slate-50/80 dark:bg-zinc-800/40 px-5 py-4 border-b border-slate-200 dark:border-zinc-800 flex justify-between items-center'>
  <h3 class='font-bold uppercase tracking-wider text-sm'>{html.escape(t(lang, 'self_test_details'))}</h3>
  <span class='badge {live['selfTestStatusClass']}' id='self-test-details-badge'>{html.escape(live['selfTestStatusLabel'])}</span>
</div>
<div class='flex-1 overflow-y-auto max-h-[300px]'>
  <table class='w-full text-left border-collapse'>
    <thead class='bg-slate-50 dark:bg-zinc-900/50 text-xs uppercase text-slate-400 border-b border-slate-200 dark:border-zinc-800 sticky top-0'>
      <tr>
        <th class='py-3 pl-5 pr-4 font-semibold w-1/4'>{html.escape(t(lang, 'check'))}</th>
        <th class='py-3 px-4 font-semibold w-24'>{html.escape(t(lang, 'result'))}</th>
        <th class='py-3 px-5 font-semibold'>{html.escape(t(lang, 'detail'))}</th>
      </tr>
    </thead>
    <tbody id='self-test-checks-body' class='divide-y divide-slate-100 dark:divide-zinc-800 px-5 text-sm'>
      {live['checksHtml']}
    </tbody>
  </table>
</div>
<div class='p-4 border-t border-slate-200 dark:border-zinc-800 bg-slate-50/30 dark:bg-zinc-900/30 rounded-b-2xl'>
  <form method='post' action='/selftest/{html.escape(pid)}' class='m-0'>
    <input type='hidden' name='lang' value='{html.escape(lang)}' />
    <button type='submit' class='{btn_secondary_cls} w-full' id='run-self-test-btn-bottom' {'disabled' if live['selfTestRunning'] else ''}>{html.escape(t(lang, 'run_self_test'))}</button>
  </form>
</div>
  </div>

</div>

<div class='grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8'>
  
  <div class='bg-[#0f172a] dark:bg-[#000000] border border-slate-800 rounded-2xl overflow-hidden shadow-xl flex flex-col h-[360px]'>
<div class='flex justify-between items-center px-4 py-2.5 bg-white/5 border-b border-white/10 shrink-0'>
  <div class='flex items-center gap-2'>
    <div class='flex gap-1.5 mr-3'>
      <div class='terminal-dot dot-r'></div><div class='terminal-dot dot-y'></div><div class='terminal-dot dot-g'></div>
    </div>
    <span class='text-xs font-mono text-slate-400'>~/{html.escape(t(lang, 'claw_log'))}</span>
  </div>
  <button type='button' class='text-[11px] font-mono text-slate-300 bg-white/10 hover:bg-white/20 border border-white/10 rounded-full px-2.5 py-1 transition copy-btn' data-copy-target='claw-log-body'>复制全部</button>
</div>
<div class='flex-1 p-4 overflow-y-auto font-mono text-[13px] text-slate-300 leading-relaxed terminal-body whitespace-pre-wrap break-all' id='claw-log-body'>{html.escape(live['clawLog'])}</div>
  </div>

  <div class='bg-[#0f172a] dark:bg-[#000000] border border-slate-800 rounded-2xl overflow-hidden shadow-xl flex flex-col h-[360px]'>
<div class='flex justify-between items-center px-4 py-2.5 bg-white/5 border-b border-white/10 shrink-0'>
  <div class='flex items-center gap-2'>
    <div class='flex gap-1.5 mr-3'>
      <div class='terminal-dot dot-r'></div><div class='terminal-dot dot-y'></div><div class='terminal-dot dot-g'></div>
    </div>
    <span class='text-xs font-mono text-slate-400'>~/{html.escape(t(lang, 'codex_log'))}</span>
  </div>
  <button type='button' class='text-[11px] font-mono text-slate-300 bg-white/10 hover:bg-white/20 border border-white/10 rounded-full px-2.5 py-1 transition copy-btn' data-copy-target='codex-log-body'>复制全部</button>
</div>
<div class='flex-1 p-4 overflow-y-auto font-mono text-[13px] text-slate-300 leading-relaxed terminal-body whitespace-pre-wrap break-all' id='codex-log-body'>{html.escape(live['codexLog'])}</div>
  </div>

</div>

<script>
(function() {{
  function preserveScroll(el, updater) {{
if (!el) return;
const fromBottom = el.scrollHeight - el.scrollTop - el.clientHeight;
updater();
el.scrollTop = Math.max(0, el.scrollHeight - el.clientHeight - fromBottom);
  }}

  function wireCopyButtons() {{
document.querySelectorAll('[data-copy-target]').forEach(btn => {{
  if (btn.dataset.copyBound === '1') return;
  btn.dataset.copyBound = '1';
  btn.addEventListener('click', async () => {{
    const el = document.getElementById(btn.getAttribute('data-copy-target'));
    if (!el) return;
    const original = btn.textContent;
    try {{
      await navigator.clipboard.writeText(el.innerText || el.textContent || '');
      btn.textContent = '已复制';
      btn.classList.add('copied');
    }} catch (e) {{
      btn.textContent = '失败';
    }}
    setTimeout(() => {{
      btn.textContent = original;
      btn.classList.remove('copied');
    }}, 1200);
  }});
}});
  }}

  async function refreshProductLive() {{
try {{
  const resp = await fetch('/api/product-live/{html.escape(pid)}?lang={html.escape(lang)}', {{ cache: 'no-store' }});
  if (!resp.ok) return;
  const data = await resp.json();

  const statusBadge = document.getElementById('product-status-badge');
  if (statusBadge) {{
    statusBadge.className = 'badge ' + data.statusClass;
    statusBadge.textContent = data.statusLabel;
  }}


  const turnProgressBadge = document.getElementById('turn-progress-badge');
  if (turnProgressBadge) {{
    const prefix = turnProgressBadge.dataset.labelPrefix || '';
    const currentTurn = (data.currentTurn || 0);
    const maxTurns = (data.maxTurns || 0);
    turnProgressBadge.textContent = prefix + currentTurn + '/' + (maxTurns || '-');
    turnProgressBadge.className = 'badge ' + (data.isRunning ? 'badge-running' : 'badge-idle');
  }}

  const selfTestBadge = document.getElementById('self-test-status-badge');
  if (selfTestBadge) {{
    selfTestBadge.className = 'badge ' + data.selfTestStatusClass;
    selfTestBadge.textContent = (selfTestBadge.dataset.labelPrefix || '') + data.selfTestStatusLabel;
  }}

  const selfTestDetailsBadge = document.getElementById('self-test-details-badge');
  if (selfTestDetailsBadge) {{
    selfTestDetailsBadge.className = 'badge ' + data.selfTestStatusClass;
    selfTestDetailsBadge.textContent = data.selfTestStatusLabel;
  }}

  const runSelfTestBtn = document.getElementById('run-self-test-btn');
  if (runSelfTestBtn) runSelfTestBtn.disabled = !!data.selfTestRunning;
  const runSelfTestBtnBottom = document.getElementById('run-self-test-btn-bottom');
  if (runSelfTestBtnBottom) runSelfTestBtnBottom.disabled = !!data.selfTestRunning;
  const startRunBtn = document.getElementById('start-run-btn');
  if (startRunBtn) startRunBtn.disabled = !!data.isRunning;
  const stopRunBtn = document.getElementById('stop-run-btn');
  if (stopRunBtn) stopRunBtn.disabled = !data.isRunning;
  const deleteBtn = document.getElementById('delete-product-btn');
  if (deleteBtn) deleteBtn.disabled = !!data.isRunning;

  const userClaw = document.getElementById('user-claw-dialogue');
  preserveScroll(userClaw, () => {{ if (userClaw) userClaw.innerHTML = data.userClawHtml; }});
  const clawCodex = document.getElementById('claw-codex-dialogue');
  preserveScroll(clawCodex, () => {{ if (clawCodex) clawCodex.innerHTML = data.clawCodexHtml; }});
  const checksBody = document.getElementById('self-test-checks-body');
  if (checksBody) checksBody.innerHTML = data.checksHtml;
  const clawLog = document.getElementById('claw-log-body');
  preserveScroll(clawLog, () => {{ if (clawLog) clawLog.textContent = data.clawLog; }});
  const codexLog = document.getElementById('codex-log-body');
  preserveScroll(codexLog, () => {{ if (codexLog) codexLog.textContent = data.codexLog; }});
}} catch (e) {{}}
  }}

  wireCopyButtons();
  setInterval(refreshProductLive, 5000);
}})();
</script>
"""
    return page_template(cfg.get('name', pid), body, lang, f'/product/{pid}')

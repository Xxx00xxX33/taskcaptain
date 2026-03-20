#!/usr/bin/env python3
from __future__ import annotations

import html
import json

try:
    from tc_core import (
        effective_claw_config,
        effective_network_config,
        load_claw_profile,
        load_product_config,
        load_product_state,
        mask_present,
        t,
    )
    from tc_live import build_product_live_payload
    from tc_ui import page_template
except ModuleNotFoundError:
    from app.tc_core import (
        effective_claw_config,
        effective_network_config,
        load_claw_profile,
        load_product_config,
        load_product_state,
        mask_present,
        t,
    )
    from app.tc_live import build_product_live_payload
    from app.tc_ui import page_template


def render_product_page(pid: str, lang: str) -> bytes:
    cfg = load_product_config(pid)
    st = load_product_state(pid)
    claw_eff = effective_claw_config(cfg)
    network = effective_network_config(cfg)
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

<div class='flex flex-wrap items-start justify-between gap-4 mb-6'>
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
      <span>{html.escape(t(lang, 'updated_at'))}: <span id='product-updated-inline'>{html.escape(live.get('updatedAt') or '-')}</span></span>
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
      <button type='submit' class='p-2 bg-red-50 text-red-600 hover:bg-red-100 dark:bg-red-500/10 dark:text-red-400 dark:hover:bg-red-500/20 rounded-xl transition active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed' id='delete-product-btn' {'disabled' if live['isRunning'] else ''} title='{html.escape(t(lang, 'delete_product'))}'>
        <svg class='w-5 h-5' fill='none' viewBox='0 0 24 24' stroke='currentColor' stroke-width='2'><path stroke-linecap='round' stroke-linejoin='round' d='M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16' /></svg>
      </button>
    </form>
  </div>
</div>

<div class='grid grid-cols-1 xl:grid-cols-[360px_minmax(0,1fr)] gap-6 xl:h-[calc(100vh-240px)]'>
  <aside class='bg-white dark:bg-darkcard border border-slate-200 dark:border-zinc-800 rounded-2xl shadow-sm overflow-hidden flex flex-col min-h-[760px] xl:min-h-0'>
    <div class='px-5 py-4 border-b border-slate-200 dark:border-zinc-800'>
      <h3 class='font-bold uppercase tracking-wider text-sm'>{html.escape(t(lang, 'configuration_details'))}</h3>
    </div>
    <div class='flex-1 min-h-0 overflow-y-auto p-5 space-y-4'>
      <section class='rounded-2xl border border-slate-200 dark:border-zinc-800 bg-slate-50/70 dark:bg-zinc-900/30 p-4 space-y-3'>
        <div>
          <div class='text-xs font-bold uppercase tracking-wider text-slate-400 mb-1'>{html.escape(t(lang, 'goal'))}</div>
          <div class='text-sm leading-relaxed whitespace-pre-wrap text-slate-700 dark:text-slate-300'>{html.escape(cfg.get('goal', ''))}</div>
        </div>
        <div class='grid grid-cols-2 gap-2 text-xs'>
          <div class='rounded-xl bg-white dark:bg-zinc-900 border border-slate-200 dark:border-zinc-800 p-3'>
            <div class='text-slate-400 uppercase tracking-wider mb-1'>Agent</div>
            <div class='font-semibold break-all'>{html.escape(claw_eff.get('model', '-'))}</div>
            <div class='text-slate-500 mt-1'>{html.escape(claw_eff.get('thinking', '-'))}</div>
          </div>
          <div class='rounded-xl bg-white dark:bg-zinc-900 border border-slate-200 dark:border-zinc-800 p-3'>
            <div class='text-slate-400 uppercase tracking-wider mb-1'>Codex</div>
            <div class='font-semibold break-all'>{html.escape(cfg.get('codex', {}).get('model', '-'))}</div>
            <div class='text-slate-500 mt-1'>{html.escape(cfg.get('codex', {}).get('thinking', '-'))}</div>
          </div>
        </div>
        <div class='flex flex-wrap gap-2 text-[11px] uppercase font-bold'>
          <span class='bg-slate-100 dark:bg-zinc-800 px-2 py-1 rounded-lg border border-slate-200 dark:border-zinc-700'>Plan: {html.escape(str(cfg.get('codex', {}).get('planMode')))}</span>
          <span class='bg-slate-100 dark:bg-zinc-800 px-2 py-1 rounded-lg border border-slate-200 dark:border-zinc-700'>MaxPerm: {html.escape(str(cfg.get('codex', {}).get('maxPermission')))}</span>
          <span class='bg-slate-100 dark:bg-zinc-800 px-2 py-1 rounded-lg border border-slate-200 dark:border-zinc-700'>{html.escape(t(lang, 'profile_label'))}: {html.escape(claw_eff.get('profileName', '-'))}</span>
        </div>
      </section>

      <section class='rounded-2xl border border-slate-200 dark:border-zinc-800 p-4 space-y-3'>
        <h4 class='text-sm font-bold'>{html.escape(t(lang, 'runtime_setting'))}</h4>
        <form method='post' action='/save-runtime-settings/{html.escape(pid)}' class='space-y-3 m-0'>
          <input type='hidden' name='lang' value='{html.escape(lang)}' />
          <div>
            <label class='{label_cls}'>{html.escape(t(lang, 'max_turns'))}</label>
            <input type='number' name='maxTurns' min='1' max='99' value='{html.escape(str(int(cfg.get('maxTurns') or 8)))}' class='{input_cls}' />
          </div>
          <div>
            <label class='{label_cls}'>{html.escape(t(lang, 'claw_thinking'))}</label>
            <select name='clawThinking' class='{input_cls}'>
              <option value=''>inherit({html.escape(profile.get('thinking', ''))})</option>
              <option value='low' {'selected' if ((cfg.get('claw', {}).get('thinking') or '') == 'low') else ''}>low</option>
              <option value='medium' {'selected' if ((cfg.get('claw', {}).get('thinking') or '') == 'medium') else ''}>medium</option>
              <option value='high' {'selected' if ((cfg.get('claw', {}).get('thinking') or '') == 'high') else ''}>high</option>
              <option value='xhigh' {'selected' if ((cfg.get('claw', {}).get('thinking') or '') == 'xhigh') else ''}>xhigh</option>
            </select>
          </div>
          <div>
            <label class='{label_cls}'>{html.escape(t(lang, 'codex_thinking'))}</label>
            <select name='codexThinking' class='{input_cls}'>
              <option value='low' {'selected' if (cfg.get('codex', {}).get('thinking') == 'low') else ''}>low</option>
              <option value='medium' {'selected' if (cfg.get('codex', {}).get('thinking') == 'medium') else ''}>medium</option>
              <option value='high' {'selected' if (cfg.get('codex', {}).get('thinking') == 'high') else ''}>high</option>
              <option value='xhigh' {'selected' if (cfg.get('codex', {}).get('thinking') == 'xhigh') else ''}>xhigh</option>
            </select>
          </div>
          <button type='submit' class='{btn_secondary_cls} w-full'>{html.escape(t(lang, 'save_runtime_button'))}</button>
        </form>
      </section>

      <section class='rounded-2xl border border-slate-200 dark:border-zinc-800 p-4 space-y-3'>
        <h4 class='text-sm font-bold'>{html.escape(t(lang, 'connection_setting'))}</h4>
        <form method='post' action='/save-connection-settings/{html.escape(pid)}' class='space-y-3 m-0'>
          <input type='hidden' name='lang' value='{html.escape(lang)}' />
          <div><label class='{label_cls}'>{html.escape(t(lang, 'claw_endpoint'))}</label><input name='clawEndpoint' value='{html.escape(cfg.get('claw', {}).get('endpoint', ''))}' class='{input_cls}' /></div>
          <div><label class='{label_cls}'>{html.escape(t(lang, 'claw_api_key'))}</label><input type='password' name='clawApiKey' value='{html.escape(cfg.get('claw', {}).get('apiKey', ''))}' class='{input_cls}' /></div>
          <div><label class='{label_cls}'>{html.escape(t(lang, 'codex_endpoint'))}</label><input name='codexEndpoint' value='{html.escape(cfg.get('codex', {}).get('endpoint', ''))}' class='{input_cls}' /></div>
          <div><label class='{label_cls}'>{html.escape(t(lang, 'codex_api_key'))}</label><input type='password' name='codexApiKey' value='{html.escape(cfg.get('codex', {}).get('apiKey', ''))}' class='{input_cls}' /></div>
          <div><label class='{label_cls}'>{html.escape(t(lang, 'proxy_url'))}</label><input name='proxy' value='{html.escape(network.get('proxy', ''))}' placeholder='http://127.0.0.1:7897' class='{input_cls}' /></div>
          <div><label class='{label_cls}'>{html.escape(t(lang, 'no_proxy'))}</label><input name='noProxy' value='{html.escape(network.get('noProxy', ''))}' class='{input_cls}' /></div>
          <p class='text-xs text-slate-500 dark:text-zinc-400'>{html.escape(t(lang, 'proxy_help'))}</p>
          <button type='submit' class='{btn_secondary_cls} w-full'>{html.escape(t(lang, 'save_connection_button'))}</button>
        </form>
      </section>

      <section class='rounded-2xl border border-slate-200 dark:border-zinc-800 p-4 space-y-3'>
        <h4 class='text-sm font-bold'>{html.escape(t(lang, 'save_current_claw_profile'))}</h4>
        <p class='text-sm text-slate-500 dark:text-zinc-400'>{html.escape(t(lang, 'profile_saved_hint'))}</p>
        <form method='post' action='/save-profile/{html.escape(pid)}' class='space-y-3 m-0'>
          <input type='hidden' name='lang' value='{html.escape(lang)}' />
          <div><label class='{label_cls}'>{html.escape(t(lang, 'profile_name'))}</label><input name='profileName' placeholder='{html.escape(claw_eff.get('profileName', ''))}' class='{input_cls}' /></div>
          <div><label class='{label_cls}'>{html.escape(t(lang, 'profile_description'))}</label><input name='profileDescription' placeholder='{html.escape(t(lang, 'profile_desc_placeholder'))}' class='{input_cls}' /></div>
          <button type='submit' class='{btn_secondary_cls} w-full'>{html.escape(t(lang, 'save_profile_button'))}</button>
        </form>
      </section>
    </div>
  </aside>

  <section class='bg-white dark:bg-darkcard border border-slate-200 dark:border-zinc-800 rounded-2xl shadow-sm overflow-hidden flex flex-col min-h-[760px] xl:min-h-0'>
    <div class='px-5 py-4 border-b border-slate-200 dark:border-zinc-800 flex flex-wrap items-center justify-between gap-3'>
      <h3 class='font-bold uppercase tracking-wider text-sm'>{html.escape(t(lang, 'overview_tab'))}</h3>
      <div class='inline-flex items-center gap-1 rounded-xl bg-slate-100 dark:bg-zinc-800 p-1' data-tab-group='product-main'>
        <button type='button' data-tab-target='product-overview-panel' class='px-3 py-1.5 text-sm font-semibold rounded-lg bg-white dark:bg-zinc-700 shadow-sm'>{html.escape(t(lang, 'overview_tab'))}</button>
        <button type='button' data-tab-target='product-dialogue-panel' class='px-3 py-1.5 text-sm font-semibold rounded-lg text-slate-500 dark:text-zinc-400'>{html.escape(t(lang, 'dialogue_tab'))}</button>
        <button type='button' data-tab-target='product-logs-panel' class='px-3 py-1.5 text-sm font-semibold rounded-lg text-slate-500 dark:text-zinc-400'>{html.escape(t(lang, 'logs_tab'))}</button>
      </div>
    </div>

    <div id='product-overview-panel' data-tab-panel='product-main' class='flex-1 min-h-0 p-5'>
      <div class='grid grid-cols-1 xl:grid-cols-[minmax(0,1fr)_340px] gap-5 h-full'>
        <div class='rounded-2xl border border-slate-200 dark:border-zinc-800 overflow-hidden flex flex-col min-h-[320px] xl:min-h-0'>
          <div class='px-5 py-4 border-b border-slate-200 dark:border-zinc-800 bg-slate-50/80 dark:bg-zinc-800/40 flex justify-between items-center'>
            <h4 class='font-bold uppercase tracking-wider text-sm'>{html.escape(t(lang, 'self_test_details'))}</h4>
            <span class='badge {live['selfTestStatusClass']}' id='self-test-details-badge'>{html.escape(live['selfTestStatusLabel'])}</span>
          </div>
          <div class='flex-1 min-h-0 overflow-y-auto'>
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
        </div>

        <div class='space-y-4 overflow-y-auto pr-1'>
          <div class='rounded-2xl border border-slate-200 dark:border-zinc-800 p-4'>
            <div class='text-xs font-bold uppercase tracking-wider text-slate-400 mb-3'>{html.escape(t(lang, 'quick_signals'))}</div>
            <div class='grid grid-cols-2 gap-3'>
              <div class='rounded-xl border border-slate-200 dark:border-zinc-800 bg-slate-50/60 dark:bg-zinc-900/30 p-3'>
                <div class='text-[11px] uppercase tracking-wider text-slate-400'>{html.escape(t(lang, 'artifact_count'))}</div>
                <div id='artifact-count' class='mt-1 text-lg font-bold text-slate-800 dark:text-slate-100'>{int(live.get('artifactCount') or 0)}</div>
              </div>
              <div class='rounded-xl border border-slate-200 dark:border-zinc-800 bg-slate-50/60 dark:bg-zinc-900/30 p-3'>
                <div class='text-[11px] uppercase tracking-wider text-slate-400'>{html.escape(t(lang, 'live_sync'))}</div>
                <div id='product-updated-at' class='mt-1 text-sm font-semibold text-slate-800 dark:text-slate-100 break-all'>{html.escape(live.get('updatedAt') or '-')}</div>
              </div>
              <div class='rounded-xl border border-slate-200 dark:border-zinc-800 bg-slate-50/60 dark:bg-zinc-900/30 p-3'>
                <div class='text-[11px] uppercase tracking-wider text-slate-400'>{html.escape(t(lang, 'log_mode'))}</div>
                <div id='fastview-label' class='mt-1 text-sm font-semibold text-slate-800 dark:text-slate-100'>{html.escape(live.get('fastviewLabel') or '-')}</div>
              </div>
              <div class='rounded-xl border border-slate-200 dark:border-zinc-800 bg-slate-50/60 dark:bg-zinc-900/30 p-3'>
                <div class='text-[11px] uppercase tracking-wider text-slate-400'>{html.escape(t(lang, 'recent_tail'))}</div>
                <div id='tail-window-label' class='mt-1 text-sm font-semibold text-slate-800 dark:text-slate-100'>{html.escape(live.get('tailWindowLabel') or '-')}</div>
              </div>
            </div>
          </div>

          <div class='rounded-2xl border border-slate-200 dark:border-zinc-800 p-4'>
            <div class='flex items-center justify-between gap-3 mb-3'>
              <div class='text-xs font-bold uppercase tracking-wider text-slate-400'>{html.escape(t(lang, 'recent_artifacts'))}</div>
              <div class='text-[11px] font-semibold text-slate-500 dark:text-zinc-400'>{int(live.get('artifactCount') or 0)}</div>
            </div>
            <div id='recent-artifacts' class='space-y-3'>
              {live['artifactHtml']}
            </div>
          </div>

          <div class='rounded-2xl border border-slate-200 dark:border-zinc-800 p-4'>
            <div class='text-xs font-bold uppercase tracking-wider text-slate-400 mb-2'>{html.escape(t(lang, 'claw_setting'))}</div>
            <ul class='space-y-2 text-sm'>
              <li><b class='text-slate-700 dark:text-slate-300'>{html.escape(t(lang, 'profile_label'))}:</b> {html.escape(claw_eff.get('profileName', ''))}</li>
              <li><b class='text-slate-700 dark:text-slate-300'>{html.escape(t(lang, 'model'))}:</b> {html.escape(claw_eff.get('model', ''))}</li>
              <li><b class='text-slate-700 dark:text-slate-300'>{html.escape(t(lang, 'api_key_present'))}:</b> {html.escape(t(lang, mask_present(claw_eff.get('apiKey'))))}</li>
              <li class='font-mono text-xs text-slate-500 break-all'>{html.escape(claw_eff.get('endpoint', ''))}</li>
            </ul>
          </div>
          <div class='rounded-2xl border border-slate-200 dark:border-zinc-800 p-4'>
            <div class='text-xs font-bold uppercase tracking-wider text-slate-400 mb-2'>{html.escape(t(lang, 'codex_setting'))}</div>
            <ul class='space-y-2 text-sm'>
              <li><b class='text-slate-700 dark:text-slate-300'>{html.escape(t(lang, 'model'))}:</b> {html.escape(cfg.get('codex', {}).get('model', ''))}</li>
              <li><b class='text-slate-700 dark:text-slate-300'>{html.escape(t(lang, 'api_key_present'))}:</b> {html.escape(t(lang, mask_present(cfg.get('codex', {}).get('apiKey'))))}</li>
              <li class='font-mono text-xs text-slate-500 break-all'>{html.escape(cfg.get('codex', {}).get('endpoint', ''))}</li>
            </ul>
          </div>
          <div class='rounded-2xl border border-slate-200 dark:border-zinc-800 p-4'>
            <div class='text-xs font-bold uppercase tracking-wider text-slate-400 mb-2'>{html.escape(t(lang, 'network_setting'))}</div>
            <ul class='space-y-2 text-sm'>
              <li><b class='text-slate-700 dark:text-slate-300'>{html.escape(t(lang, 'proxy_url'))}:</b> {html.escape(network.get('proxy', '') or 'direct')}</li>
              <li><b class='text-slate-700 dark:text-slate-300'>{html.escape(t(lang, 'no_proxy'))}:</b></li>
              <li class='font-mono text-xs text-slate-500 break-all'>{html.escape(network.get('noProxy', ''))}</li>
            </ul>
          </div>
        </div>
      </div>
    </div>

    <div id='product-dialogue-panel' data-tab-panel='product-main' class='hidden flex-1 min-h-0 p-5'>
      <div class='grid grid-cols-1 xl:grid-cols-2 gap-5 h-full'>
        <div class='bg-white dark:bg-darkcard border border-slate-200 dark:border-zinc-800 rounded-2xl shadow-sm flex flex-col min-h-[320px] xl:min-h-0'>
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

        <div class='bg-white dark:bg-darkcard border border-slate-200 dark:border-zinc-800 rounded-2xl shadow-sm flex flex-col min-h-[320px] xl:min-h-0'>
          <div class='bg-slate-50/80 dark:bg-zinc-800/40 px-5 py-4 border-b border-slate-200 dark:border-zinc-800 shrink-0'>
            <h3 class='font-bold uppercase tracking-wider text-sm'>{html.escape(t(lang, 'claw_codex_dialogue'))}</h3>
          </div>
          <div id='claw-codex-dialogue' class='flex-1 overflow-y-auto bg-slate-50/30 dark:bg-zinc-900/30 rounded-b-2xl'>{live['clawCodexHtml']}</div>
        </div>
      </div>
    </div>

    <div id='product-logs-panel' data-tab-panel='product-main' class='hidden flex-1 min-h-0 p-5'>
      <div class='grid grid-cols-1 xl:grid-cols-2 gap-5 h-full'>
        <div class='bg-[#0f172a] dark:bg-[#000000] border border-slate-800 rounded-2xl overflow-hidden shadow-xl flex flex-col min-h-[320px] xl:min-h-0'>
          <div class='flex justify-between items-center px-4 py-2.5 bg-white/5 border-b border-white/10 shrink-0'>
            <div class='flex items-center gap-2'>
              <div class='flex gap-1.5 mr-3'>
                <div class='terminal-dot dot-r'></div><div class='terminal-dot dot-y'></div><div class='terminal-dot dot-g'></div>
              </div>
              <span class='text-xs font-mono text-slate-400'>~/{html.escape(t(lang, 'claw_log'))}</span>
              <span class='text-[11px] font-mono text-slate-500' id='claw-log-note'>{html.escape(live.get('clawLogNote') or '')}</span>
            </div>
            <button type='button' class='text-[11px] font-mono text-slate-300 bg-white/10 hover:bg-white/20 border border-white/10 rounded-full px-2.5 py-1 transition copy-btn' data-copy-target='claw-log-body'>复制全部</button>
          </div>
          <div class='flex-1 p-4 overflow-y-auto font-mono text-[13px] text-slate-300 leading-relaxed terminal-body whitespace-pre-wrap break-all' id='claw-log-body'>{html.escape(live['clawLog'])}</div>
        </div>

        <div class='bg-[#0f172a] dark:bg-[#000000] border border-slate-800 rounded-2xl overflow-hidden shadow-xl flex flex-col min-h-[320px] xl:min-h-0'>
          <div class='flex justify-between items-center px-4 py-2.5 bg-white/5 border-b border-white/10 shrink-0'>
            <div class='flex items-center gap-2'>
              <div class='flex gap-1.5 mr-3'>
                <div class='terminal-dot dot-r'></div><div class='terminal-dot dot-y'></div><div class='terminal-dot dot-g'></div>
              </div>
              <span class='text-xs font-mono text-slate-400'>~/{html.escape(t(lang, 'codex_log'))}</span>
              <span class='text-[11px] font-mono text-slate-500' id='codex-log-note'>{html.escape(live.get('codexLogNote') or '')}</span>
            </div>
            <button type='button' class='text-[11px] font-mono text-slate-300 bg-white/10 hover:bg-white/20 border border-white/10 rounded-full px-2.5 py-1 transition copy-btn' data-copy-target='codex-log-body'>复制全部</button>
          </div>
          <div class='flex-1 p-4 overflow-y-auto font-mono text-[13px] text-slate-300 leading-relaxed terminal-body whitespace-pre-wrap break-all' id='codex-log-body'>{html.escape(live['codexLog'])}</div>
        </div>
      </div>
    </div>
  </section>
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
    document.querySelectorAll('[data-copy-target], [data-copy-text]').forEach(btn => {{
      if (btn.dataset.copyBound === '1') return;
      btn.dataset.copyBound = '1';
      btn.addEventListener('click', async () => {{
        const original = btn.textContent;
        try {{
          const literal = btn.getAttribute('data-copy-text');
          if (literal !== null) {{
            await navigator.clipboard.writeText(literal);
          }} else {{
            const el = document.getElementById(btn.getAttribute('data-copy-target'));
            if (!el) return;
            await navigator.clipboard.writeText(el.innerText || el.textContent || '');
          }}
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
      const updatedInline = document.getElementById('product-updated-inline');
      if (updatedInline) updatedInline.textContent = data.updatedAt || '-';
      const updatedCard = document.getElementById('product-updated-at');
      if (updatedCard) updatedCard.textContent = data.updatedAt || '-';
      const artifactCount = document.getElementById('artifact-count');
      if (artifactCount) artifactCount.textContent = String(data.artifactCount || 0);
      const fastviewLabel = document.getElementById('fastview-label');
      if (fastviewLabel) fastviewLabel.textContent = data.fastviewLabel || '-';
      const tailWindowLabel = document.getElementById('tail-window-label');
      if (tailWindowLabel) tailWindowLabel.textContent = data.tailWindowLabel || '-';

      const selfTestDetailsBadge = document.getElementById('self-test-details-badge');
      if (selfTestDetailsBadge) {{
        selfTestDetailsBadge.className = 'badge ' + data.selfTestStatusClass;
        selfTestDetailsBadge.textContent = data.selfTestStatusLabel;
      }}

      const runSelfTestBtn = document.getElementById('run-self-test-btn');
      if (runSelfTestBtn) runSelfTestBtn.disabled = !!data.selfTestRunning;
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
      const recentArtifacts = document.getElementById('recent-artifacts');
      if (recentArtifacts) recentArtifacts.innerHTML = data.artifactHtml;
      const checksBody = document.getElementById('self-test-checks-body');
      if (checksBody) checksBody.innerHTML = data.checksHtml;
      const clawLog = document.getElementById('claw-log-body');
      preserveScroll(clawLog, () => {{ if (clawLog) clawLog.textContent = data.clawLog; }});
      const clawLogNote = document.getElementById('claw-log-note');
      if (clawLogNote) clawLogNote.textContent = data.clawLogNote || '';
      const codexLog = document.getElementById('codex-log-body');
      preserveScroll(codexLog, () => {{ if (codexLog) codexLog.textContent = data.codexLog; }});
      const codexLogNote = document.getElementById('codex-log-note');
      if (codexLogNote) codexLogNote.textContent = data.codexLogNote || '';
      wireCopyButtons();
    }} catch (e) {{}}
  }}

  wireCopyButtons();
  setInterval(refreshProductLive, 5000);
}})();
</script>
"""
    return page_template(cfg.get('name', pid), body, lang, f'/product/{pid}')

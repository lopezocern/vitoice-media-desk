/* ============================================================
   MediaDesk · 应用逻辑：hash 路由 + 壳层激活 + 视图注入 + 交互
   （纯 vanilla，无依赖，离线可开）
   ============================================================ */

/* ---------- 内联 SVG 图标库（Lucide 风格，stroke currentColor） ---------- */
const ICONS = {
  overview: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/></svg>',
  compress: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M21 8v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/><circle cx="11" cy="13" r="2.5"/></svg>',
  cut: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="6" cy="6" r="2.5"/><circle cx="6" cy="18" r="2.5"/><path d="M8.1 7.6 21 20M8.1 16.4 21 4"/></svg>',
  concat: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M8 4L3 9l5 5M3 9h13"/><path d="M16 20l5-5-5-5M21 15H8"/></svg>',
  convert: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M4 6l4-2 4 2 4-2 4 2v14l-4 2-4-2-4 2-4-2z"/><path d="M8 10v4M16 10v4"/></svg>',
  rename: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><path d="M12 12h6M12 16h4"/></svg>',
  settings: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 1 1-4 0v-.09a1.65 1.65 0 0 0-1-1.51 1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 1 1 0-4h.09a1.65 1.65 0 0 0 1.51-1 1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33h0a1.65 1.65 0 0 0 1-1.51V3a2 2 0 1 1 4 0v.09a1.65 1.65 0 0 0 1 1.51h0a1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82v0a1.65 1.65 0 0 0 1.51 1H21a2 2 0 1 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>',
  menu: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M4 6h16M4 12h16M4 18h16"/></svg>',
  film: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2"/><path d="M7 3v18M17 3v18M3 8h4M3 16h4M17 8h4M17 16h4"/></svg>',
  upload: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M12 16V4m0 0-4 4m4-4 4 4"/><path d="M4 20h16"/></svg>',
  plus: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M12 5v14M5 12h14"/></svg>',
  play: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M6 4l14 8-14 8z"/></svg>',
  grip: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="9" cy="6" r="1"/><circle cx="15" cy="6" r="1"/><circle cx="9" cy="12" r="1"/><circle cx="15" cy="12" r="1"/><circle cx="9" cy="18" r="1"/><circle cx="15" cy="18" r="1"/></svg>',
  clock: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 3"/></svg>',
  check: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 13l4 4L19 7"/></svg>',
  xclose: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"><path d="M6 6l12 12M18 6 6 18"/></svg>',
  arrow: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M12 5v14m0 0 5-5m-5 5-5-5"/></svg>',
  folder: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/></svg>',
  trash: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M4 7h16M9 7V5a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2M6 7l1 13a1 1 0 0 0 1 1h8a1 1 0 0 0 1-1l1-13"/></svg>',
  refresh: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M20 12a8 8 0 1 1-2.3-5.7"/><path d="M20 3v4h-4"/></svg>',
  alert: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="9"/><path d="M12 8v4m0 4h.01"/></svg>',
  hash: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><path d="M10 4 8 20M16 4l-2 16M4 8h16M3 16h16"/></svg>',
  gpu: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><rect x="4" y="4" width="16" height="16" rx="2"/><circle cx="12" cy="12" r="3"/></svg>',
  file: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M14 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"/><path d="M14 3v6h6"/></svg>',
};

/* 渲染时把所有 data-icon 占位替换成具体 SVG */
function hydrateIcons(root) {
  root.querySelectorAll('[data-icon]').forEach((el) => {
    const k = el.getAttribute('data-icon');
    if (ICONS[k]) el.innerHTML = ICONS[k];
  });
}

/* ---------- 通用小工具 ---------- */
const $ = (sel, root = document) => root.querySelector(sel);
const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));

function toast(msg, type = 'ok') {
  const wrap = $('#toastWrap');
  const t = document.createElement('div');
  t.className = `toast ${type}`;
  t.innerHTML = `<span>${ICONS[type === 'err' ? 'alert' : 'check']}</span>${msg}`;
  wrap.appendChild(t);
  setTimeout(() => { t.style.opacity = '0'; t.style.transition = 'opacity .3s'; }, 2200);
  setTimeout(() => t.remove(), 2600);
}

/* ---------- 任务进度模拟（推流式） ---------- */
function startCompressSim(rows, opts = {}) {
  const queue = rows.slice();
  let running = 0;
  const MAX = 2;
  function pump() {
    while (running < MAX && queue.length) {
      const row = queue.shift();
      running++;
      if (MD.files[row.key]) continue;
      MD.run++;
      runOne(row);
    }
  }
  function finish(k, ok) {
    running--;
    MD.run--;
    const row = rows.find((r) => r.key === k);
    if (row) { row.status = ok ? 'done' : 'err'; row.pct = ok ? 100 : 0; row.state = true; }
    MD.done += ok ? 1 : 0;
    MD.fail += ok ? 0 : 1;
    syncStatus();
    pump();
  }
  function runOne(row) {
    let pct = 0;
    const id = setInterval(() => {
      if (pct >= 100) { clearInterval(id); finish(row.key, true); if (row.onDone) row.onDone(); return; }
      pct = Math.min(pct + (opts.fast ? 9 : 5) + Math.random() * 4, 100);
      if (row.setProg) row.setProg(Math.round(pct));
    }, 140);
    row.timer = id;
  }
  pump();
}

/* 停止全部：把所有未完成任务置为取消 */
function stopAllTasks(rows) {
  rows.forEach((r) => {
    if (r.timer && !r.state) {
      clearInterval(r.timer);
      r.status = 'wait'; r.pct = 0; r.state = true;
      if (r.setProg) r.setProg(0);
      if (r.setWait) r.setWait();
      MD.run = Math.max(0, MD.run - 1);
    }
  });
  syncStatus();
  toast('已停止全部未完成任务', 'ok');
}

function syncStatus() {
  $('#statRun b').textContent = MD.run;
  $('#statDone b').textContent = MD.done;
  $('#statFail b').textContent = MD.fail;
}

/* ============================================================
   VIEW 渲染函数 — 每个返回内容区 HTML + 挂载后回调(可在 content 参数接入)
   ============================================================ */

/* ---------- 总览 ---------- */
async function renderOverview(content) {
  const env = (await probeEnv()).data;
  MD.env = env;
  content.innerHTML = `
    <div class="page">
      <div class="page-head reveal">
        <div><div class="page-title">总览</div><div class="page-sub">把零散的 FFmpeg 能力收拢到一个统一的桌面客户端。</div></div>
        <span class="chip"><span>${ICONS.gpu}</span>环境正常</span>
      </div>

      <div class="section-title reveal">环境状态</div>
      <div class="card env-strip reveal">
        <div class="env-item"><span class="env-dot ok"></span><b style="font-weight:600">FFmpeg</b> 可用</div>
        <div class="env-item"><span>编码器</span><span class="pill gpu" id="ovEnc">${env.encoder}</span></div>
        <div class="env-item"><span>压缩预设</span><b>${env.crf}</b></div>
        <div style="flex:1"></div>
        <div class="env-item" style="color:var(--text-faint);font-size:12px;cursor:pointer" id="ovRedetect">
          ${ICONS.refresh} 重新检测
        </div>
      </div>

      <div class="section-title reveal">模块</div>
      <div class="mod-grid" id="modGrid"></div>
    </div>`;
  // 模块卡
  const grid = $('#modGrid', content);
  grid.innerHTML = DB.modules.map((m) => `
    <a class="mod-card reveal" href="#${m.key}">
      <div class="mod-head">
        <span class="mod-icon">${ICONS[m.key] || ICONS.folder}</span>
        <span class="mod-badge${m.badge === '已可用' ? ' ok' : ''}">${m.badge}</span>
      </div>
      <h3>${m.name}</h3><p>${m.desc}</p>
    </a>`).join('');
  $('#ovRedetect', content).onclick = async () => {
    toast('正在检测环境…', 'ok');
    const e2 = (await probeEnv()).data;
    $('#ovEnc', content).textContent = e2.encoder;
    toast('环境检测完成', 'ok');
  };
  // 同步到侧栏/底部
  updateShellEnv(env);
}

/* ---------- 视频压缩 ---------- */
function taskRowHTML(f, extra) {
  const st = f.status || 'idle';
  const pct = f.pct ?? 0;
  const barCls = st === 'done' ? 'ok' : st === 'err' ? 'err' : st === 'wait' ? 'wait' : '';
  const pctTxt = st === 'done' ? '完成' : st === 'err' ? '失败' : st === 'wait' ? '等待中' : `${pct}%`;
  return `<div class="task-row" data-key="${f.key}" ${f.state ? 'data-locked=""' : ''}>
    <div class="tname"><span style="color:var(--text-faint)">${ICONS.file}</span><em>${f.name}</em></div>
    <div class="sz">${f.size}</div>
    <div class="bar"><i class="${barCls}" style="width:${Math.max(pct, st==='done'?100:2)}%"></i></div>
    <div class="pct ${barCls}">${pctTxt}</div>
    ${f.state ? '<button class="btn-danger-ghost" data-del>&times;</button>'
             : `<button class="btn-danger-ghost" data-cancel>${ICONS.xclose}</button>`}
  </div>`;
}

async function renderCompress(content) {
  const param = DB.preset;
  const files = DB.compressFiles.map((f, i) => ({ ...f, key: 'c' + i, status: 'idle', pct: 0 }));
  MD.files.compress = files;
  content.innerHTML = `
    <div class="page">
      <div class="page-head reveal">
        <div><div class="page-title">视频压缩</div><div class="page-sub">多文件拖入，硬件加速，实时进度</div></div>
        <button class="btn btn-ghost" id="addFiles">${ICONS.plus} 追加文件</button>
      </div>

      <div class="dropzone reveal" id="dz">
        <span class="dz-ico">${ICONS.upload}</span>
        <span class="big">把多个视频拖到这里，或点击下方按钮添加</span>
        <span class="small">支持批量 · mp4 / mkv / mov / webm / avi / ts</span>
      </div>

      <div class="section-title reveal">任务列表</div>
      <div class="task-list reveal" id="taskList">
        ${files.map(taskRowHTML).join('') || emptyHTML('compress','尚未添加文件')}
      </div>

      <div class="section-title reveal">压缩参数</div>
      <div class="param-card reveal">
        <div class="param-row">
          <div class="field"><span class="flabel">处理速度</span>
            <div class="seg" id="speedSeg"></div>
            <span class="help" title="处理速度与压缩成效的取舍档，平衡适合绝大多数情况。">?</span>
          </div>
          <div class="field"><span class="flabel">编码器</span>
            <span class="pill gpu" id="encPill">${(MD.env?.encoder) || 'hevc_nvenc'}</span>
            <span class="help" title="由硬件自动检测（优先 NVIDIA），无 GPU 自动回退软件编码。">?</span>
          </div>
        </div>
        <div style="height:12px"></div>
        <div class="param-row">
          <button class="combo" data-combo="crf">CRF（画质） <b>${param.crf}</b> <span class="caret">&#9662;</span></button>
          <button class="combo" data-combo="res">分辨率 <span>${param.res}</span> <span class="caret">&#9662;</span></button>
          <button class="combo" data-combo="fps">帧率 <span>${param.fps}</span> <span class="caret">&#9662;</span></button>
          <div style="flex:1"></div>
          <button class="btn btn-ghost" id="resetParam">重置</button>
        </div>
      </div>

      <div class="page-foot" style="display:flex;align-items:center;justify-content:space-between;margin-top:18px">
        <span class="env-hint">提示：改动参数会取舍画质 / 体积 / 速度，默认值已可用。</span>
        <div style="display:flex;gap:8px">
          <button class="btn btn-ghost" id="addFiles2">${ICONS.plus} 追加文件</button>
          <button class="btn btn-primary" id="startCompress">${ICONS.play} 开始压缩</button>
        </div>
      </div>
    </div>`;

  // 速度分段
  $('#speedSeg', content).innerHTML = param.speedOptions.map((o) =>
    `<span data-v="${o.v}" class="${o.v === param.speed ? 'on' : ''}">${o.label}</span>`).join('');
  bindSeg('#speedSeg', content, (v) => { param.speed = v; });

  // 下拉（简单切换，不建菜单浮层，循环选项）
  bindCombo('[data-combo=crf]', content, '#primary-soft', ['18','24','28','32'], (v) => { param.crf = v; }, 'CRF（画质） <b>%s</b>');
  bindCombo('[data-combo=res]', content, '', ['保持原始','1080P','720P'], (v) => { param.res = v; }, '分辨率 <span>%s</span>');
  bindCombo('[data-combo=fps]', content, '', ['保持原始','60','30','24'], (v) => { param.fps = v; }, '帧率 <span>%s</span>');

  $('#resetParam', content).onclick = () => { location.reload(); };

  // 拖拽区
  setupDropzone(content, (names) => addFiles(names));

  // 追加文件（模拟）
  const addFiles = (extraNames) => {
    const list = $('#taskList', content);
    const em = list.querySelector('.empty-state');
    if (em) em.remove();
    if (extraNames?.length) {
      extraNames.forEach((nm, i) => {
        const f = { name: nm, size: `${(100 + i * 40)} MB`, key: 'add' + files.length + i, status: 'idle', pct: 0 };
        files.push(f);
        list.insertAdjacentHTML('beforeend', taskRowHTML(f));
      });
    }
    toast('已添加文件', 'ok');
  };

  $('#addFiles', content).onclick = () => addFiles();
  $('#addFiles2', content).onclick = () => addFiles();

  // 开始压缩
  $('#startCompress', content).onclick = () => {
    const pending = files.filter((f) => !f.state && !f.timer);
    if (!pending.length) { toast('没有待压缩的任务', 'err'); return; }
    pending.forEach((f) => { f.setProg = (p) => { f.pct = p; const bar = listRow(content, f.key); if (bar) bar.querySelector('.pct').textContent = p + '%'; bar.querySelector('.bar i').style.width = p + '%'; }; });
    toast(`已提交 ${pending.length} 个压缩任务`, 'ok');
    startCompressSim(pending, { fast: false });
  };

  // 删除 / 取消
  $('#taskList', content).addEventListener('click', (e) => {
    const row = e.target.closest('.task-row'); if (!row) return;
    const f = files.find((x) => x.key === row.dataset.key);
    if (!f) return;
    if (e.target.closest('[data-del]') || e.target.closest('[data-cancel]')) {
      if (e.target.closest('[data-cancel]')) { clearInterval(f.timer); f.status = 'wait'; if (f.setProg) { f.setProg(0); row.querySelector('.bar i').style.width = '0%'; } f.state = true; toast('已取消', 'ok'); return; }
      files.splice(files.indexOf(f), 1); row.remove();
    }
  });
}

function listRow(content, key) { return $('.task-row[data-key="' + key + '"]', content); }
function emptyHTML(k, title, sub) {
  return `<div class="empty-state"><span>${ICONS.folder}</span><div class="es-title">${title}</div><div class="es-sub">${sub || ''}</div></div>`;
}

/* ---------- 视频切割 ---------- */
async function renderCut(content) {
  const files = DB.cutFiles.map((f, i) => ({ ...f, key: 'k' + i, status: 'idle', pct: 0, segs: f.segs }));
  MD.files.cut = files;
  content.innerHTML = `
    <div class="page">
      <div class="page-head reveal">
        <div><div class="page-title">视频切割</div><div class="page-sub">按时间段切割，支持快速流复制 / 精确重编码</div></div>
        <button class="btn btn-ghost" id="addCut">${ICONS.plus} 添加文件</button>
      </div>
      <div class="dropzone reveal" id="dzCut">
        <span class="dz-ico">${ICONS.cut}</span>
        <span class="big">把视频拖到这里，逐个设置时间段</span>
        <span class="small">一个文件可设多个时间段，每段输出 「源名_序号」</span>
      </div>
      <div class="section-title reveal">切割任务</div>
      <div class="task-list reveal" id="cutList"></div>
    </div>`;
  const cutRows = () => $('#cutList', content);
  function draw() {
    cutRows().innerHTML = files.map((f) => `
      <div class="task-row" data-key="${f.key}">
        <div class="tname"><span style="color:var(--text-faint)">${ICONS.file}</span>${f.name}</div>
        <div class="sz">${f.size}</div>
        <span class="pill" style="background:var(--primary-soft);color:var(--primary)">${f.segs} 段</span>
        ${f.mode ? `<span class="pill soft">${f.mode}</span>` : ''}
        <button class="btn btn-ghost btn-sm" data-edit>时间段</button>
        <button class="btn-danger-ghost" data-del>&times;</button>
      </div>`).join('') || emptyHTML('cut', '尚未添加文件');
  }
  draw();
  setupDropzone($('#dzCut', content).parentElement || content, () => {
    files.push({ name: '新增素材.mp4', size: '660 MB', key: 'k' + files.length, status: 'idle', pct: 0, segs: 1 });
    draw(); toast('已添加文件', 'ok');
  });
  $('#addCut', content).onclick = () => { files.push({ name: '新增素材.mp4', size: '660 MB', key: 'k' + files.length, status: 'idle', pct: 0, segs: 1 }); draw(); };
  $('#cutList', content).addEventListener('click', (e) => {
    const row = e.target.closest('.task-row'); if (!row) return;
    const f = files.find((x) => x.key === row.dataset.key);
    if (e.target.closest('[data-del]')) { files.splice(files.indexOf(f), 1); draw(); return; }
    if (e.target.closest('[data-edit]')) { openTimeDialog(content, f, () => draw()); }
  });
}

/* ---------- 时间工具（HH:MM:SS） ---------- */
function timeToSec(t) {
  const p = String(t).trim().split(':').map((x) => parseInt(x, 10));
  if (p.length < 2 || p.some((x) => isNaN(x))) return NaN;
  return (p[0] || 0) * 3600 + (p[1] || 0) * 60 + (p[2] || 0);
}
function secToTime(s) {
  const h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60), sec = Math.floor(s % 60);
  return [h, m, sec].map((x) => String(x).padStart(2, '0')).join(':');
}

function openTimeDialog(content, f, onSave) {
  const overlay = document.createElement('div');
  overlay.className = 'modal-overlay';
  const modeTxt = { copy: '快速流复制', reencode: '精确重编码' };
  let mode = f.mode === '精确重编码' ? 'reencode' : 'copy';
  // 以源文件帧间隔估算默认分段（每段 75s，从 0 起顺延）
  const rows = seedSegs();

  overlay.innerHTML = `
    <div class="modal">
      <div class="modal-head">
        <div><b>${f.name}</b><span class="modal-sub">设置切割时间段 · 每个时间段各输出一个「源名_序号」文件</span></div>
        <button class="btn-danger-ghost" data-close>${ICONS.xclose}</button>
      </div>
      <div class="modal-body">
        <div class="seg-mode">
          <span class="flabel">切割精度</span>
          <div class="seg" id="segMode">
            <span class="${mode === 'copy' ? 'on' : ''}" data-m="copy">快速流复制</span>
            <span class="${mode === 'reencode' ? 'on' : ''}" data-m="reencode">精确重编码</span>
          </div>
          <span class="help" title="快速流复制：不重编码、速度快，只能切在关键帧附近；精确重编码：逐帧精确、耗时更长。">?</span>
        </div>
        <div class="seg-head">时间段<em style="font-weight:400;color:var(--text-faint)">（起点 / 终点 / 时长）</em></div>
        <div id="segRows"></div>
        <div style="margin-top:8px"><button class="btn btn-ghost btn-sm" id="addSeg">${ICONS.plus} 添加时间段</button></div>
      </div>
      <div class="modal-foot">
        <span class="env-hint" id="segSummary"></span>
        <div style="flex:1"></div>
        <button class="btn btn-ghost" data-close>取消</button>
        <button class="btn btn-primary" id="segSave">${ICONS.check} 保存</button>
      </div>
    </div>`;
  document.body.appendChild(overlay);
  const segWrap = $('#segRows', overlay);

  function seedSegs() {
    const n = Math.max(1, f.segs || 1);
    const arr = []; let s = 0;
    for (let i = 0; i < n; i++) { arr.push({ start: secToTime(s), end: secToTime(s + 75) }); s += 75; }
    return arr;
  }
  function bindRow(el, r) {
    const iS = el.querySelector('[data-k=s]');
    const iE = el.querySelector('[data-k=e]');
    const dur = el.querySelector('.seg-dur');
    el.querySelector('.seg-idx').textContent = String(rows.indexOf(r) + 1);
    function durUpd() {
      const a = timeToSec(iS.value), b = timeToSec(iE.value);
      const ok = !isNaN(a) && !isNaN(b) && b > a;
      dur.textContent = ok ? '时长 ' + secToTime(b - a) : '';
      iS.classList.toggle('bad', String(iS.value).trim() !== '' && isNaN(a));
      iE.classList.toggle('bad', String(iE.value).trim() !== '' && isNaN(b));
    }
    iS.addEventListener('input', durUpd);
    iE.addEventListener('input', durUpd);
    durUpd();
    el.querySelector('[data-del-seg]').onclick = () => {
      if (rows.length > 1) { const i = rows.indexOf(r); if (i >= 0) { rows.splice(i, 1); el.remove(); } }
      updateSummary();
    };
  }
  function drawRow(r) {
    const el = document.createElement('div');
    el.className = 'seg-line';
    el.innerHTML = segRowHTML(r.start, r.end);
    segWrap.appendChild(el);
    bindRow(el, r);
  }
  function updateSummary() {
    let tot = 0, valid = true;
    rows.forEach((r) => { const a = timeToSec(r.start), b = timeToSec(r.end); if (isNaN(a) || isNaN(b) || b <= a) valid = false; else tot += (b - a); });
    $('#segSummary', overlay).textContent = `${rows.length} 段${valid ? ' · 总时长 ' + secToTime(tot) : ' · 存在无效时间段'}`;
  }

  // 切割精度切换
  $('#segMode', overlay).addEventListener('click', (e) => {
    const s = e.target.closest('span[data-m]'); if (!s) return;
    mode = s.dataset.m;
    $$('#segMode span', overlay).forEach((x) => x.classList.toggle('on', x === s));
  });
  // 添加时间段：以上一段终点为起点
  $('#addSeg', overlay).onclick = () => {
    const last = rows[rows.length - 1];
    const ns = last ? last.end : '00:00:00';
    const r = { start: ns, end: secToTime(timeToSec(ns) + 75) };
    rows.push(r); drawRow(r); updateSummary();
  };
  // 保存 + 校验
  $('#segSave', overlay).onclick = () => {
    $$('.seg-line', segWrap).forEach((el, i) => { const r = rows[i]; if (r) { r.start = el.querySelector('[data-k=s]').value; r.end = el.querySelector('[data-k=e]').value; } });
    const bad = rows.some((r) => { const a = timeToSec(r.start), b = timeToSec(r.end); return isNaN(a) || isNaN(b) || b <= a; });
    if (bad) { toast('时间段无效：每个终点需晚于其起点', 'err'); return; }
    f.segs = rows.length; f.mode = modeTxt[mode];
    overlay.remove(); onSave();
    toast(`已设置 ${rows.length} 个时间段（${modeTxt[mode]}）`, 'ok');
  };
  // 取消 / 遮罩关闭
  overlay.querySelectorAll('[data-close]').forEach((b) => b.onclick = () => overlay.remove());
  overlay.addEventListener('click', (e) => { if (e.target === overlay) overlay.remove(); });

  rows.forEach(drawRow);
  updateSummary();
}
function segRowHTML(start, end) {
  return `<div class="seg-line">
    <span class="seg-idx">#</span>
    <span class="seg-lbl">起点</span>
    <input class="seg-t" type="text" data-k="s" value="${start}" spellcheck="false">
    <span class="seg-lbl">终点</span>
    <input class="seg-t" type="text" data-k="e" value="${end}" spellcheck="false">
    <span class="seg-dur"></span>
    <button class="btn-danger-ghost" data-del-seg title="移除该段">${ICONS.xclose}</button>
  </div>`;
}

/* ---------- 视频拼接 ---------- */
async function renderConcat(content) {
  const files = DB.concatFiles.map((f, i) => ({ ...f, key: 'j' + i }));
  MD.files.concat = files;
  content.innerHTML = `
    <div class="page">
      <div class="page-head reveal">
        <div><div class="page-title">视频拼接</div><div class="page-sub">多视频按序拼接，快速流复制 / 统一重编码</div></div>
        <button class="btn btn-ghost" id="addConcat">${ICONS.plus} 添加片段</button>
      </div>
      <div class="section-title reveal">片段顺序（拖动调整）</div>
      <div class="sort-list card reveal" id="sortList"></div>
      <div class="section-title reveal">拼接方式</div>
      <div class="param-card reveal">
        <div class="param-row">
          <div class="field"><span class="flabel">拼接模式</span>
            <div class="seg"><span class="on">快速流复制</span><span>统一重编码</span></div>
          </div>
          <div class="field"><span class="flabel">输出格式</span><span class="pill gpu">mp4</span></div>
          <div style="flex:1"></div>
          <button class="btn btn-primary" id="goConcat">${ICONS.concat} 开始拼接</button>
        </div>
      </div>
    </div>`;
  function draw() {
    $('#sortList', content).innerHTML = files.map((f, i) => `
      <div class="sort-row" data-key="${f.key}" draggable="true">
        <span class="grip">${ICONS.grip}</span>
        <span class="fname">${i + 1}. ${f.name}</span>
        <span class="fsize">${f.size}</span>
        <button class="btn-danger-ghost" data-del>&times;</button>
      </div>`).join('') || emptyHTML('concat', '暂无片段');
  }
  draw();
  // 拖动调整顺序
  const sortEl = $('#sortList', content);
  let dragKey = null;
  sortEl.addEventListener('dragstart', (e) => {
    const row = e.target.closest('.sort-row'); if (!row) return;
    dragKey = row.dataset.key; row.classList.add('dragging');
    e.dataTransfer.effectAllowed = 'move';
  });
  sortEl.addEventListener('dragover', (e) => {
    e.preventDefault();
    const row = e.target.closest('.sort-row'); if (!row || !dragKey || row.dataset.key === dragKey) return;
    $$('.sort-row', sortEl).forEach((r) => r.classList.remove('drag-over'));
    row.classList.add('drag-over');
  });
  sortEl.addEventListener('dragend', () => {
    $$('.sort-row', sortEl).forEach((r) => r.classList.remove('dragging', 'drag-over'));
    dragKey = null;
  });
  sortEl.addEventListener('drop', (e) => {
    e.preventDefault();
    const row = e.target.closest('.sort-row'); if (!row || !dragKey || row.dataset.key === dragKey) return;
    const from = files.findIndex((x) => x.key === dragKey);
    const to = files.findIndex((x) => x.key === row.dataset.key);
    if (from >= 0 && to >= 0) { const [m] = files.splice(from, 1); files.splice(to, 0, m); draw(); }
  });
  sortEl.addEventListener('click', (e) => {
    if (e.target.closest('[data-del]')) { const row = e.target.closest('.sort-row'); files.splice(files.findIndex((x) => x.key === row.dataset.key), 1); draw(); }
  });
  $('#addConcat', content).onclick = () => { files.push({ name: `片段_${String(files.length + 1).padStart(2, '0')}_新.mp4`, size: '64 MB', key: 'j' + files.length }); draw(); };
  $('#goConcat', content).onclick = async () => {
    await submitConcat(files.map((f) => f.name));
    toast(`已提交 ${files.length} 个片段开始拼接`, 'ok');
    MD.done++; syncStatus();
  };
}

/* ---------- 格式转换 ---------- */
async function renderConvert(content) {
  const files = DB.convertFiles.map((f, i) => ({ ...f, key: 'v' + i, status: 'idle', pct: 0 }));
  MD.files.convert = files;
  const formats = [
    { k: 'mp4',  label: 'MP4 · H.264',      tip: '通用格式，兼容性最好' },
    { k: 'webm', label: 'WebM · VP8/VP9',   tip: '网页/直播，占用小' },
    { k: 'mkv',  label: 'MKV · H.265',      tip: '高清收藏，封装自由' },
    { k: 'mp4x', label: 'MP4 · H.265',      tip: '体积小，画质高' },
  ];
  content.innerHTML = `
    <div class="page">
      <div class="page-head reveal">
        <div><div class="page-title">格式转换</div><div class="page-sub">mp4 / webm / mkv，分辨率 / 画质 / GPU / 提取音频</div></div>
      </div>
      <div class="dropzone reveal" id="dzConvert">
        <span class="dz-ico">${ICONS.convert}</span>
        <span class="big">把视频拖到这里，选择输出格式</span>
        <span class="small">输出到同源目录 /out</span>
      </div>
      <div class="section-title reveal">输出格式</div>
      <div class="mod-grid reveal" id="fmtGrid"></div>
      <div class="param-card reveal" style="margin-top:14px">
        <div class="param-row">
          <div class="field"><span class="flabel">分辨率</span><span class="pill soft">保持原始</span></div>
          <div class="field"><span class="flabel">画质</span><span class="pill soft">高</span></div>
          <div class="check"><input type="checkbox" id="useGpu" checked> 使用 GPU 加速</div>
          <div class="check"><input type="checkbox" id="extractAudio"> 仅提取音频</div>
          <div style="flex:1"></div>
          <button class="btn btn-primary" id="goConvert">${ICONS.convert} 开始转换</button>
        </div>
      </div>
      <div class="section-title reveal">转换任务</div>
      <div class="task-list reveal" id="convertList"></div>
    </div>`;
  // 格式网格：默认选中第一个
  let selFmt = 'mp4';
  const fmtGrid = $('#fmtGrid', content);
  fmtGrid.innerHTML = formats.map((f) => `
    <div class="mod-card" data-fmt="${f.k}" style="${f.k === 'mp4' ? 'border-color:var(--primary);box-shadow:var(--shadow-md)' : ''}">
      <div class="mod-head"><span class="mod-icon">${ICONS.convert}</span>
        ${f.k === 'mp4' ? '<span class="mod-badge ok">推荐</span>' : ''}</div>
      <h3>${f.label}</h3><p>${f.tip}</p>
    </div>`).join('');
  fmtGrid.addEventListener('click', (e) => {
    const card = e.target.closest('.mod-card'); if (!card) return;
    selFmt = card.dataset.fmt;
    $$('.mod-card', fmtGrid).forEach((c) => { c.style.borderColor = ''; c.style.boxShadow = ''; });
    card.style.borderColor = 'var(--primary)'; card.style.boxShadow = 'var(--shadow-md)';
  });

  function drawConvert() {
    $('#convertList', content).innerHTML = files.map((f) => taskRowHTML(f)).join('') ||
      emptyHTML('convert', '尚无转换任务');
  }
  drawConvert();
  setupDropzone($('#dzConvert', content), () => { files.push({ name: '新增素材.mov', size: '2.0 GB', key: 'v' + files.length, status: 'idle', pct: 0 }); drawConvert(); toast('已添加文件', 'ok'); });

  $('#goConvert', content).onclick = () => {
    const pending = files.filter((f) => !f.state);
    pending.forEach((f) => { f.setProg = (p) => { const bar = $('.task-row[data-key="' + f.key + '"]', content); if (bar) { bar.querySelector('.pct').textContent = p + '%'; bar.querySelector('.bar i').style.width = p + '%'; } }; });
    if (!pending.length) { toast('没有待转换文件', 'err'); return; }
    toast(`正在转换为 ${selFmt.toUpperCase()}…`, 'ok');
    startCompressSim(pending, { fast: true });
  };
}

/* ---------- 文件整理 ---------- */
async function renderRename(content) {
  let plans = DB.renamePlans.slice();
  let mode = 'dry'; // dry=干跑 preview / apply=应用
  content.innerHTML = `
    <div class="page">
      <div class="page-head reveal">
        <div><div class="page-title">文件整理</div><div class="page-sub">中文名加拼音前缀，垃圾清理，干跑预览</div></div>
        <div><button class="btn btn-ghost" id="scanDir">${ICONS.refresh} 重新扫描</button></div>
      </div>

      <div class="section-title reveal">模式</div>
      <div class="mode-switch reveal" id="modeSwitch" style="display:inline-flex">
        <button class="on" data-m="dry">干跑预览</button>
        <button data-m="apply">应用更改</button>
      </div>

      <div class="section-title reveal">整理计划</div>
      <div class="card reveal" style="padding:0;overflow:hidden">
        <table class="plan-table" id="planTbl">
          <thead><tr><th>类型</th><th>原文件名</th><th></th><th>改后 / 处理</th><th>说明</th></tr></thead>
          <tbody></tbody>
        </table>
      </div>
      <div class="env-hint reveal" style="margin-top:10px" id="planHint"></div>
    </div>`;

  function draw() {
    const tbody = $('#planTbl tbody', content);
    tbody.innerHTML = plans.map((p, i) => `
      <tr>
        <td><span class="kind-tag ${p.kind === 'clean' ? 'clean' : 'rename'}">${p.kind === 'clean' ? '清理' : '重命名'}</span></td>
        <td style="max-width:240px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${p.old}</td>
        <td><span class="arrow">→</span></td>
        <td>${p.new || '<span style="color:var(--text-faint)">删除该项</span>'}</td>
        <td style="color:var(--text-sub);font-size:12px">${p.note}</td>
      </tr>`).join('');
    const clean = plans.filter((p) => p.kind === 'clean').length;
    $('#planHint', content).textContent = `共 ${plans.length} 项 · 重命名 ${plans.length - clean} · 清理 ${clean}（${mode === 'dry' ? '干跑：不会真正改动' : '将执行更改'}）`;
  }
  draw();

  // 模式切换
  $('#modeSwitch', content).addEventListener('click', (e) => {
    const b = e.target.closest('button'); if (!b) return;
    mode = b.dataset.m;
    $$('#modeSwitch button', content).forEach((x) => x.classList.toggle('on', x === b));
    draw(); toast(mode === 'dry' ? '已切换为干跑预览' : '已切换为应用更改', 'ok');
  });
  $('#scanDir', content).onclick = async () => {
    toast('正在扫描目录…', 'ok');
    await delay(400);
    const e2 = { old: '未命名剪辑_1.mp4', new: 'C 未命名剪辑_1.mp4', kind: 'rename', note: '拼音首字母：C' };
    plans = [e2, ...plans];
    draw(); toast('扫描完成，发现新文件', 'ok');
  };

  // 核准执行
  const foot = document.createElement('div');
  foot.style.marginTop = '14px';
  foot.innerHTML = `<button class="btn btn-primary" id="applyPlan">${ICONS.check} 核准并执行</button>`;
  content.querySelector('.page').appendChild(foot);
  $('#applyPlan', content).onclick = async () => {
    if (mode === 'dry') { toast('当前为干跑模式，切换到“应用更改”后执行', 'err'); return; }
    await applyRename(plans, true);
    MD.done += plans.length; syncStatus();
    toast(`已处理 ${plans.length} 项`, 'ok');
    plans = []; draw();
  };
}

/* ---------- 全局设置 ---------- */
async function renderSettings(content) {
  const env = MD.env || DB.env;
  content.innerHTML = `
    <div class="page">
      <div class="page-head reveal">
        <div><div class="page-title">全局设置</div><div class="page-sub">FFmpeg 路径 / GPU / 输出目录 / 并发</div></div>
      </div>

      <div class="setting-card reveal">
        <div class="sc-title">${ICONS.folder} FFmpeg 路径 <span class="help" title="留空用系统 PATH；指定后优先使用该路径 ffmpeg。">?</span></div>
        <div class="setting-row">
          <input type="text" id="setFfmpeg" placeholder="留空 = 使用系统 PATH 中的 ffmpeg" class="grow">
          <button class="btn btn-ghost" data-browse>浏览…</button>
        </div>
        <div class="env-hint" style="margin-top:8px">当前：${env.encoder} · ${env.crf}</div>
      </div>

      <div class="setting-card reveal">
        <div class="sc-title">${ICONS.gpu} 硬件加速 <span class="help" title="关闭后压缩使用软件编码（最稳，速度较慢）。">?</span></div>
        <label class="check"><input type="checkbox" id="setGpu" checked> 允许 GPU 硬件编码（NVENC，需 NVIDIA 显卡）</label>
      </div>

      <div class="setting-card reveal">
        <div class="sc-title">${ICONS.folder} 输出目录默认 <span class="help" title="压缩默认输出位置；模块内可临时覆盖。">?</span></div>
        <div class="setting-row">
          <button class="combo" id="odCombo">同源目录 /out <span class="caret">&#9662;</span></button>
          <input type="text" id="odDir" placeholder="选择输出目录…" class="grow" disabled>
        </div>
      </div>

      <div class="setting-card reveal">
        <div class="sc-title">${ICONS.clock} 默认同时压缩（路）</div>
        <div style="display:flex;align-items:center;gap:10px">
          <button class="combo" id="concCombo">自动 <span class="caret">&#9662;</span></button>
          <span class="env-hint">0 表示自动（min 4, CPU核）</span>
        </div>
      </div>

      <div class="setting-card reveal">
        <div class="sc-title">${ICONS.refresh} 环境自检</div>
        <div class="env-strip" style="padding:6px 0">
          <div class="env-item"><span class="env-dot ok"></span>FFmpeg 可用</div>
          <div class="env-item"><span>编码器</span><span class="pill gpu">${env.encoder}</span></div>
          <div style="flex:1"></div>
          <button class="btn btn-primary" id="redetect">${ICONS.refresh} 重新检测</button>
        </div>
      </div>
    </div>`;

  // 简化单值切换（循环演示）
  let gpu = true;
  $('#setGpu', content).onchange = (e) => { gpu = e.target.checked; toast(gpu ? '已启用 GPU 加速' : '已关闭，将使用软件编码', 'ok'); };
  $('#odCombo', content).onclick = () => { const on = $('#odDir', content); on.disabled = !on.disabled; };
  $('#redetect', content).onclick = async () => { toast('正在检测环境…', 'ok'); await probeEnv(); toast('环境正常', 'ok'); };
  $$('[data-browse]', content).forEach((b) => b.onclick = () => toast('演示环境：已选择 ffmpeg 路径', 'ok'));
}

/* ---------- 下拉循环演示（点击在选项间切换） ---------- */
function bindCombo(sel, content, unused, options, onPick, tpl) {
  const el = $(sel, content); if (!el) return;
  // 初始值即 options[0]，用 data-idx 记录当前档位，点击循环切换
  el.dataset.idx = '0';
  el.onclick = () => {
    let i = parseInt(el.dataset.idx || '0', 10);
    i = (i + 1) % options.length;
    el.dataset.idx = String(i);
    const next = options[i];
    onPick(next);
    el.innerHTML = tpl.replace('%s', next) + `<span class="caret">&#9662;</span>`;
  };
}
function bindSeg(sel, content, cb) {
  $(sel, content).addEventListener('click', (e) => {
    const s = e.target.closest('span'); if (!s || !s.dataset.v) return;
    $$(`${sel} span`, content).forEach((x) => x.classList.remove('on'));
    s.classList.add('on'); cb(s.dataset.v);
  });
}

/* ---------- 拖拽导入 ---------- */
function setupDropzone(target, cb) {
  // 目标为 dropzone 或其容器；绑定到 dropzone 与页面级别
  const drop = target.closest('.dropzone') || $('.dropzone', target) || target;
  document.addEventListener('dragover', (e) => { e.preventDefault(); drop.classList.add('drag'); });
  document.addEventListener('dragleave', (e) => { if (!drop.contains(e.relatedTarget)) drop.classList.remove('drag'); });
  document.addEventListener('drop', (e) => {
    e.preventDefault(); drop.classList.remove('drag');
    const names = Array.from(e.dataTransfer?.files || []).map((f) => f.name);
    if (names.length) cb(names);
  });
}

/* ---------- 壳层环境更新 ---------- */
function updateShellEnv(env) {
  const navEl = $('#navEnvText');
  navEl.textContent = env.ffmpeg ? `FFmpeg · ${env.encoder}` : '需指定 FFmpeg';
  $('#tbEnvCaps').textContent = env.ffmpeg ? `${env.encoder} 可用` : '未检测到 FFmpeg';
  $('#envHint').textContent = env.gpu ? `硬件加速 · ${env.encoder}` : `软件编码 · ${env.encoder}`;
}

/* ---------- hash 路由 ---------- */
const routes = {
  overview: renderOverview,
  compress: renderCompress,
  cut: renderCut,
  concat: renderConcat,
  convert: renderConvert,
  rename: renderRename,
  settings: renderSettings,
};

function router() {
  const key = (location.hash || '#overview').replace('#', '');
  const render = routes[key] || renderOverview;
  const content = $('#content');
  content.innerHTML = '<div class="page" style="padding-top:30px;color:var(--text-faint)">加载中…</div>';
  // 激活 nav
  $$('.nav-item').forEach((a) => {
    a.classList.toggle('active', a.dataset.nav === key);
  });
  document.body.dataset.page = key;
  $('#tbTitle').textContent = DB.modules.find((m) => m.key === key)?.name || '媒体工作台';
  render(content).then(() => hydrateIcons(content)).catch((err) => { console.error(err); });
}

/* ---------- 初始化 ---------- */
function init() {
  hydrateIcons(document);
  // 刚启动时先探测一次环境（总览/壳层）
  probeEnv().then((env) => updateShellEnv(env.data));

  // 折叠侧栏
  $('#collapseBtn').onclick = () => document.querySelector('.app-nav').classList.toggle('collapsed');

  // 停止全部：对压缩/转换页生效（跨页不行，简单提示）
  $('#stopAll').onclick = () => { stopAllTasks(MD.files.compress || [], MD.files.convert || [], MD.files.compress || []); };

  window.addEventListener('hashchange', router);
  router();
  syncStatus();
}

document.addEventListener('DOMContentLoaded', init);
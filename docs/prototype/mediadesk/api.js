/* ============================================================
   MediaDesk · API 桩层（stub only）
   仅返回 mock，签名/延迟/错误形态对齐未来真实 API；
   接入真实后端时替换实现，保持签名不变。
   参考路径（示例）：
     GET  /api/env                      -> probeEnv()
     GET  /api/modules                  -> getModules()
     POST /tasks/compress {files,param} -> runCompress(files, param)
   ============================================================ */
const delay = (ms) => new Promise((r) => setTimeout(r, ms));

async function probeEnv() {
  await delay(350); // 模拟环境检测耗时
  // TODO: replace with GET /api/env
  return { code: 0, data: DB.env };
}

async function getModules() {
  await delay(150);
  // TODO: replace with GET /api/modules
  return { code: 0, data: DB.modules };
}

/** 提交压缩任务：返回任务 id，进度走全局 MD.files（模拟推流）。 */
async function runCompress(files, param) {
  await delay(120);
  // TODO: replace with POST /tasks/compress
  return { code: 0, data: { accepted: files.length, param } };
}

/** 拼接排序落库。 */
async function submitConcat(order) {
  await delay(200);
  // TODO: replace with POST /tasks/concat
  return { code: 0, data: { order } };
}

/** 文件整理（干跑或应用）。 */
async function applyRename(plans, execute) {
  await delay(260);
  // TODO: replace with POST /tasks/rename
  return { code: 0, data: { executed: execute, plans: plans.length } };
}

async function saveSettings(patch) {
  await delay(180);
  // TODO: replace with PATCH /settings
  return { code: 0, data: patch };
}
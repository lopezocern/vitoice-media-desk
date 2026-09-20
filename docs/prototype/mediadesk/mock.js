/* ============================================================
   MediaDesk · 集中 mock 数据源（单一数据源，各页读取）
   ============================================================ */
const DB = {
  // 概览模块
  modules: [
    { key: 'compress', name: '视频压缩', badge: '已可用', hot: true,  desc: '多文件拖入，硬件加速，实时进度' },
    { key: 'cut',      name: '视频切割', badge: '已可用', hot: false, desc: '按时间段切割，快速 / 精确重编码' },
    { key: 'concat',   name: '视频拼接', badge: '已可用', hot: false, desc: '多视频按序拼接，快速 / 统一重编码' },
    { key: 'convert',  name: '格式转换', badge: '已可用', hot: false, desc: 'mp4/webm/mkv，分辨率/画质/GPU/音频' },
    { key: 'rename',   name: '文件整理', badge: '已可用', hot: false, desc: '中文名加拼音前缀，垃圾清理，干跑预览' },
    { key: 'settings', name: '全局设置', badge: '可配置', hot: false, desc: 'FFmpeg 路径 / GPU / 输出目录 / 并发' },
  ],

  // 压缩任务种子
  compressFiles: [
    { name: '演唱会_开场高清.mp4', size: '512 MB', res: '1280×720' },
    { name: 'Vlog_海边日落.mov',   size: '1.2 GB', res: '1920×1080' },
    { name: '产品演示_2025.webm',  size: '89 MB',  res: '1280×720' },
    { name: '课程录制_第12节.mp4', size: '340 MB', res: '1920×1080' },
  ],

  // 切割文件（含时间段）
  cutFiles: [
    { name: '采访_完整版.mp4', size: '2.4 GB', segs: 2 },
    { name: '会议录像_2026Q1.mov', size: '980 MB', segs: 1 },
  ],

  // 拼接文件（有序）
  concatFiles: [
    { name: '片段_01_片头.mp4',   size: '45 MB' },
    { name: '片段_02_正片.mp4',   size: '320 MB' },
    { name: '片段_03_片尾.mp4',   size: '28 MB' },
  ],

  // 格式转换文件
  convertFiles: [
    { name: '原始素材_prores.mov', size: '3.6 GB' },
    { name: '绿幕抠像_mkv',       size: '1.1 GB' },
  ],

  // 文件整理计划（干跑）
  renamePlans: [
    { old: '测试视频.mp4',          new: 'C 测试视频.mp4',        kind: 'rename', note: '拼音首字母：C' },
    { old: '2026_产品发布会.mp4',   new: 'C 2026_产品发布会.mp4', kind: 'rename', note: '拼音首字母：C' },
    { old: 'Thumbs.db',             new: '',                      kind: 'clean',  note: 'Windows 缩略图缓存' },
    { old: '婚礼记录_desktop.ini', new: '',                      kind: 'clean',  note: '桌面配置文件' },
  ],

  // 环境
  env: { ffmpeg: true, gpu: true, encoder: 'hevc_nvenc', crf: '平衡 · CRF 18' },
  preset: {
    speed: 'balanced',
    speedOptions: [
      { v: 'ultrafast', label: '超快' },
      { v: 'balanced',  label: '平衡（默认）' },
      { v: 'fast',      label: '快速' },
    ],
    crf: 18,
    res: '保持原始',
    fps: '保持原始',
  },
};

// 全局任务计数（运行中/完成/失败）— 跨页共享
window.MD = window.MD || { run: 0, done: 0, fail: 0, files: {} };
/* MediaDesk PRD interactive product demo — panel switching + simulated runs */
(function () {
  var PANELS = {
    dashboard: ['dashboard'],
    compress: ['compress'],
    cut: ['cut'],
    splice: ['splice'],
    transcode: ['transcode'],
    rename: ['rename'],
    mkdir: ['mkdir'],
    settings: ['settings']
  };

  var $ = function (sel) { return document.querySelector(sel); };
  var $$ = function (sel, root) { return Array.prototype.slice.call((root || document).querySelectorAll(sel)); };

  /* nav switching */
  $$('.sidenav .item').forEach(function (item) {
    item.addEventListener('click', function () {
      var p = item.getAttribute('data-p');
      $$('.sidenav .item').forEach(function (i) { i.classList.remove('on'); });
      item.classList.add('on');
      $$('.pview').forEach(function (v) { v.hidden = true; });
      var target = $('.pview[data-v="' + p + '"]');
      if (target) target.hidden = false;
    });
  });

  window.goPanel = function (p) {
    var item = $('.sidenav .item[data-p="' + p + '"]');
    if (item) item.click();
  };

  /* GPU toggle in settings */
  var gpu = $('#set-gpu');
  if (gpu) {
    gpu.addEventListener('click', function () {
      gpu.classList.toggle('on');
      $('#set-gpu-txt').textContent = gpu.classList.contains('on')
        ? '已启用（当前检测到 hevc_nvenc）'
        : '已关闭（将使用软件编码）';
    });
  }

  /* cut range -> segment count live parse */
  var cutInput = $('#cut-range');
  if (cutInput) {
    cutInput.addEventListener('input', function () {
      var m = cutInput.value.match(/\d{2}:\d{2}:\d{2}-\d{2}:\d{2}:\d{2}/g);
      $('#cut-count').textContent = m ? m.length : 0;
    });
  }

  var MOCK = {
    compress: [['录屏_会议_2026-08-30.mp4', '1.8 GB'], ['宣传片_最终版.mp4', '3.4 GB'], ['产品演示_竖版.mp4', '2.1 GB']],
    cut: [['长片_正片.mp4', '12.4 GB']],
    splice: [['F-925-CPart01.mp4', '.5 GB'], ['F-925-CPart02.mp4', '.5 GB'], ['F-925-CPart03.mp4', '.5 GB']],
    transcode: [['nightshow_raw.mp4', '4.6 GB'], ['intro_source.mp4', '1.1 GB']],
    rename: [['IMG_001.jpg', '2 MB'], ['IMG_002.jpg', '3 MB'], ['IMG_003.jpg', '1 MB'], ['IMG_004.jpg', '2 MB']],
    mkdir: [['01_拍摄素材'], ['02_剪辑工程'], ['03_成片'], ['04_备份']]
  };

  var IDX = { compress: 0, cut: 0, splice: 0, transcode: 0, rename: 0, mkdir: 0 };

  window.addMock = function (p) {
    var pool = MOCK[p];
    if (!pool) return;
    var file = pool[IDX[p] % pool.length];
    if (pool[p] && pool[p].indexOf(file.nm) > -1) {} // no-op guard
    IDX[p]++;

    if (p === 'mkdir') {
      addMkdirRow(file[0]);
      return;
    }
    addFileRow(p, file[0], file[1]);
  };

  function addFileRow(p, name, size) {
    var list = $('#' + p + '-files');
    if (!list) return;
    var li = document.createElement('li');
    li.innerHTML = '<span class="nm"></span><span class="sz"></span><span class="del">×</span>';
    li.querySelector('.nm').textContent = name;
    li.querySelector('.sz').textContent = size;
    li.querySelector('.del').addEventListener('click', function () { li.remove(); });
    list.appendChild(li);
  }

  function addMkdirRow(name) {
    var list = $('#mk-files');
    if (!list) return;
    var li = document.createElement('li');
    li.innerHTML = '<span class="fld">▸</span><span></span><span class="sz" style="margin-left:auto;"></span>';
    li.children[1].textContent = name;
    li.children[2].textContent = '待创建';
    list.appendChild(li);
  }

  function progressEl(label) {
    var wrap = document.createElement('div');
    wrap.className = 'prow';
    var nm = document.createElement('span');
    nm.className = 'nm';
    nm.textContent = label;
    var bar = document.createElement('div');
    bar.className = 'bar';
    var fill = document.createElement('i');
    bar.appendChild(fill);
    var pct = document.createElement('span');
    pct.className = 'pct';
    pct.textContent = '0%';
    wrap.appendChild(nm); wrap.appendChild(bar); wrap.appendChild(pct);
    return { wrap: wrap, fill: fill, pct: pct };
  }

  window.runMock = function (p, msg) {
    var box = $('#' + p + '-progress');
    if (!box) return;
    box.innerHTML = '';
    var rows = [];
    var labels;
    if (p === 'mkdir') {
      labels = $$('#mk-files li').map(function (li) { return li.children[1].textContent; });
    } else {
      labels = $$('#' + p + '-files .nm').map(function (n) { return n.textContent; });
    }
    if (!labels.length) {
      var hint = document.createElement('div');
      hint.style.cssText = 'font-size:12px;color:var(--muted);padding:6px 0;';
      hint.textContent = '请先添加文件（点“+ 添加文件”），再开始处理。';
      box.appendChild(hint);
      return;
    }
    labels.forEach(function (l) {
      var r = progressEl(l);
      box.appendChild(r.wrap);
      rows.push(r);
    });
    var k = 0;
    var timer = setInterval(function () {
      var done = true;
      rows.forEach(function (r) {
        var w = parseFloat(r.fill.style.width) || 0;
        if (w < 100) {
          w = Math.min(100, w + 7 + Math.random() * 12);
          r.fill.style.width = w + '%';
          r.pct.textContent = Math.round(w) + '%';
          if (w < 100) done = false;
        }
      });
      k++;
      if (done) {
        clearInterval(timer);
        rows.forEach(function (r) { r.pct.textContent = '✓'; });
        var fin = document.createElement('div');
        fin.style.cssText = 'font-size:12px;color:#5b8a3c;font-weight:700;margin-top:8px;';
        fin.textContent = '完成：' + msg + '，' + rows.length + ' 项全部处理成功（演示）。';
        box.appendChild(fin);
      }
    }, 180);
  };

  /* seed a few default rows on load */
  addFileRow('compress', '录屏_会议_2026-08-30.mp4', '1.8 GB');
  addFileRow('compress', '宣传片_最终版.mp4', '3.4 GB');
  addFileRow('splice', 'F-925-CPart01.mp4', '.5 GB');
  addFileRow('splice', 'F-925-CPart02.mp4', '.5 GB');
  addFileRow('splice', 'F-925-CPart03.mp4', '.5 GB');
  addMkdirRow('01_拍摄素材');
  addMkdirRow('02_剪辑工程');
  addMkdirRow('03_成片');
  addMkdirRow('04_备份');
})();
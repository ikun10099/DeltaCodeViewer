/* 三角洲行动 · 改枪码库 — Android H5 逻辑
   分类规则 / 任务判定 / 排序 / 缓存结构与桌面版 app.py 逐条对齐 */

(function () {
  'use strict';

  /* ── 常量（与 app.py 同源） ─────────────────────────── */

  var QUEST_ORDER = ['金枪客'];
  var QUEST_KEYS = { '金枪客': ['金枪客'] };
  var QUEST_HINT = { '金枪客': 'S11 · 金枪客任务链（上交 / 击杀 / 备用）' };

  var FAMILY_RULES = [
    ['套装', ['套装']],
    ['狙击枪', ['awm', 'm700', 'r93', 'sv-98', 'sv98', 'm82', '巴雷特', 'psg-1', 'psg1']],
    ['射手步枪', ['sr-25', 'sr25', 'svd', 'svch', 'm14', 'sks', 'mini', 'vss', '杠杆', 'm417']],
    ['冲锋枪', ['mp5', 'mp7', 'p90', 'vector', 'smg', 'mk4', '汤姆逊', '野牛', 'qcq', '勇士', 'uzi']],
    ['轻机枪', ['pkm', 'm249', 'm250', 'qjb', 'm60', '机枪']],
    ['霰弹枪', ['s12k', 'm1014', 'fs-12', 'fs12', '霰弹', 'ks23', 'saw']],
    ['手枪', ['93r', '沙鹰', 'deagle', 'g18', 'p226', '手枪']],
    ['特殊', ['弓', '弩', '火箭', '榴弹']],
    ['突击步枪', ['ak', 'm4', 'm7', 'mk47', 'k416', 'k437', 'qbz', 'sg552', 'aug', 'scar',
      'ash-12', 'an94', 'ar-57', 'ar57', 'car-15', 'm16', 'g3', 'ptr-32', 'rm277',
      '腾龙', 'mdr', 'as val', 'sr-3m', 'kc17']]
  ];

  var FAMILY_COLORS = {
    '突击步枪': '#f97316', '冲锋枪': '#22c55e', '射手步枪': '#3b82f6',
    '狙击枪': '#a855f7', '轻机枪': '#eab308', '霰弹枪': '#ef4444',
    '手枪': '#14b8a6', '套装': '#f0a030', '特殊': '#ec4899', '其他': '#7f8ea6',
    '金枪客': '#f43f5e'
  };

  var ACTIONS = ['上交', '提交', '击杀', '备用', '丐版', '性价比', '机动',
    '双修', '中远程', '23W', '24W', '21W', '45W'];

  var STEP_RE = /金枪客\s*([0-9]+(?:\s*\/\s*[0-9]+)?)\s*$/;

  var SORT_COLS = { 'updatedAt': 1, 'price': 1, 'copy_times': 1, 'quest_step': 1 };
  var SORT_DESC_DEFAULT = { 'updatedAt': true, 'price': true, 'copy_times': true, 'quest_step': false };

  /* ── 工具函数 ──────────────────────────────────────── */

  function fmt(v) {
    if (v === null || v === undefined) return '';
    if (Array.isArray(v)) return v.map(function (x) { return String(x); }).join(' / ');
    return String(v);
  }

  function fmtPrice(v) {
    var n = parseInt(v, 10);
    if (!isFinite(n)) return fmt(v);
    return n.toLocaleString('en-US');
  }

  function fmtDate(v) {
    var s = fmt(v).trim();
    if (s.length >= 10 && s.charAt(4) === '-' && s.charAt(7) === '-') return s.slice(5, 10);
    return s;
  }

  function classify(weapon) {
    var w = String(weapon || '').toLowerCase().trim();
    if (!w) return '其他';
    var best = null, bestLen = 0;
    for (var i = 0; i < FAMILY_RULES.length; i++) {
      var fam = FAMILY_RULES[i][0], keys = FAMILY_RULES[i][1];
      for (var j = 0; j < keys.length; j++) {
        var k = keys[j];
        if (w.indexOf(k) >= 0 && k.length > bestLen) {
          best = fam; bestLen = k.length;
        }
      }
    }
    return best || '其他';
  }

  function matchQuest(it) {
    if (!it || typeof it !== 'object') return null;
    var blob = (fmt(it.tags) + ' ' + fmt(it.name) + ' ' + fmt(it.player) + ' ' +
      fmt(it.core) + ' ' + fmt(it.slug)).toLowerCase();
    for (var i = 0; i < QUEST_ORDER.length; i++) {
      var name = QUEST_ORDER[i], keys = QUEST_KEYS[name] || [];
      for (var j = 0; j < keys.length; j++) {
        if (blob.indexOf(keys[j]) >= 0) return name;
      }
    }
    return null;
  }

  function questStep(it) {
    var step = '', action = '';
    var tags = (it && it.tags) || [];
    if (!Array.isArray(tags)) tags = [tags];
    for (var i = 0; i < tags.length; i++) {
      var m = STEP_RE.exec(String(tags[i]).trim());
      if (m) { step = m[1].replace(/\s+/g, ''); break; }
    }
    for (var j = 0; j < tags.length; j++) {
      var s = String(tags[j]).trim();
      if (ACTIONS.indexOf(s) >= 0) { action = s; break; }
    }
    return [step, action];
  }

  function bucketOf(it) {
    var q = matchQuest(it);
    if (q) return q;
    return classify(it && it.weapon);
  }

  function itemKey(it) {
    return String((it && (it.id || it.code)) || '');
  }

  function esc(s) {
    return String(s === null || s === undefined ? '' : s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }

  /* ── 状态 ──────────────────────────────────────────── */

  var S = {
    items: [],
    filtered: [],
    fam: '全部',
    q: '',
    sortKey: 'updatedAt',
    sortRev: true,
    savedAt: '',
    selected: '',
    theme: 'dark',
    loading: false,
    daily: null,
    dailyLoading: false
  };

  var native = (typeof window.Native !== 'undefined') ? window.Native : null;

  function hasNative() { return !!native; }

  /* ── DOM ───────────────────────────────────────────── */

  var $ = function (id) { return document.getElementById(id); };
  var elList, elQ, elClear, elFam, elSortChips, elDir, elChipStep,
      elLoading, elBarFill, elLText, elStLeft, elStMid, elStRight,
      elSheetWrap, elSheet, elMask, elS = {}, elToast;

  /* ── 侧栏（家族横滑） ──────────────────────────────── */

  function rebuildFamilies() {
    var counts = {}, questCounts = {};
    for (var i = 0; i < S.items.length; i++) {
      var it = S.items[i];
      var q = matchQuest(it);
      if (q) { questCounts[q] = (questCounts[q] || 0) + 1; }
      else {
        var f = classify(it.weapon);
        counts[f] = (counts[f] || 0) + 1;
      }
    }

    var html = [];
    html.push(chipHtml('全部', S.items.length, '全部', false));
    for (var qi = 0; qi < QUEST_ORDER.length; qi++) {
      var qn = QUEST_ORDER[qi];
      if (questCounts[qn]) html.push(chipHtml(qn, questCounts[qn], qn, true));
    }
    var fams = Object.keys(counts).sort(function (a, b) { return counts[b] - counts[a]; });
    for (var fi = 0; fi < fams.length; fi++) {
      html.push(chipHtml(fams[fi], counts[fams[fi]], fams[fi], false));
    }
    elFam.innerHTML = html.join('');
  }

  function chipHtml(name, n, fam, isQuest) {
    var color = FAMILY_COLORS[fam] || FAMILY_COLORS['其他'];
    var on = (S.fam === fam) ? ' on' : '';
    var dq = isQuest ? ' quest' : '';
    var glyph = isQuest ? '◆' : '●';
    return '<button class="fchip' + on + dq + '" data-fam="' + esc(fam) + '">' +
      '<span class="fc-dot" style="background:' + color + '"></span>' +
      '<span>' + glyph + ' ' + esc(name) + '</span>' +
      '<span class="fc-n">' + n + '</span></button>';
  }

  function inFamily(it, fam) {
    if (fam === '全部') return true;
    if (QUEST_KEYS[fam]) return matchQuest(it) === fam;
    return classify(it.weapon) === fam;
  }

  /* ── 过滤 / 排序 ───────────────────────────────────── */

  function applyFilter() {
    var q = S.q.trim().toLowerCase();
    var out = [];
    for (var i = 0; i < S.items.length; i++) {
      var it = S.items[i];
      if (!inFamily(it, S.fam)) continue;
      if (q) {
        var blob = (fmt(it.weapon) + ' ' + fmt(it.name) + ' ' + fmt(it.player) + ' ' +
          fmt(it.code) + ' ' + fmt(it.tags) + ' ' + fmt(it.core)).toLowerCase();
        if (blob.indexOf(q) < 0) continue;
      }
      out.push(it);
    }
    S.filtered = out;
    sortFiltered();
  }

  function sortValue(it, key) {
    if (key === 'quest_step') {
      var st = questStep(it)[0];
      var n = parseInt(st, 10);
      return isFinite(n) ? n : 9999;
    }
    if (key === 'price' || key === 'copy_times') {
      var v = parseInt(it[key], 10);
      return isFinite(v) ? v : 0;
    }
    return fmt(it[key]);
  }

  function sortFiltered() {
    var key = S.sortKey, rev = S.sortRev;
    S.filtered.sort(function (a, b) {
      var va = sortValue(a, key), vb = sortValue(b, key);
      var c;
      if (typeof va === 'number' && typeof vb === 'number') c = va - vb;
      else c = String(va) < String(vb) ? -1 : (String(va) > String(vb) ? 1 : 0);
      return rev ? -c : c;
    });
  }

  /* ── 渲染 ──────────────────────────────────────────── */

  function render() {
    var rows = [];
    for (var i = 0; i < S.filtered.length; i++) {
      var it = S.filtered[i];
      var fam = bucketOf(it);
      var isQ = !!matchQuest(it);
      var color = FAMILY_COLORS[fam] || FAMILY_COLORS['其他'];
      var stepInfo = isQ ? questStep(it) : ['', ''];
      var key = itemKey(it);
      var sel = (key && key === S.selected) ? ' sel' : '';
      var glyphCls = isQ ? 'diamond' : 'circle';
      var glyphStyle = isQ
        ? 'background:' + color + ';width:8px;height:8px'
        : 'background:' + color;

      var priceTxt = fmtPrice(it.price);
      var codeTxt = fmt(it.code);

      rows.push(
        '<div class="row' + sel + '" data-key="' + esc(key) + '">' +
          '<div class="left">' +
            '<div class="rw">' +
              '<span class="glyph ' + glyphCls + '" style="' + glyphStyle + '"></span>' +
              '<span class="wname" style="color:' + color + '">' + esc(fmt(it.weapon) || '—') + '</span>' +
              (stepInfo[0] ? '<span class="step">' + esc(stepInfo[0]) + '</span>' : '') +
            '</div>' +
            '<div class="rn">' + esc(fmt(it.name) || '（未命名配装）') + '</div>' +
            '<div class="rsub">' +
              '<span class="au">' + esc(fmt(it.player)) + '</span>' +
              (priceTxt && priceTxt !== '0' ? '<span class="pr">' + esc(priceTxt) + '</span>' : '') +
              '<span class="cp">⎘ ' + esc(fmt(it.copy_times) || '0') + '</span>' +
              '<span class="dt">' + esc(fmtDate(it.updatedAt)) + '</span>' +
            '</div>' +
          '</div>' +
          '<div class="right">' +
            '<button class="mini" data-copy="' + esc(key) + '">⎘</button>' +
          '</div>' +
        '</div>'
      );
    }

    if (!rows.length) {
      rows.push('<div class="empty"><span class="big">◌</span>' +
        (S.loading ? '正在加载…' : '没有匹配的配装') + '</div>');
    }
    elList.innerHTML = rows.join('');
    updateStatus();
  }

  function updateStatus() {
    var total = S.items.length;
    var shown = S.filtered.length;
    var isQ = !!QUEST_KEYS[S.fam];
    var left = S.fam === '全部' ? ('全部配装 · ' + total + ' 条') : (S.fam + ' · ' + shown + ' 条');
    if (isQ) left = QUEST_HINT[S.fam] || left;
    elStLeft.textContent = left;
    elStMid.textContent = shown + ' / ' + total;
  }

  /* ── 详情抽屉 ──────────────────────────────────────── */

  function findItem(key) {
    for (var i = 0; i < S.items.length; i++) {
      if (itemKey(S.items[i]) === key) return S.items[i];
    }
    return null;
  }

  function openSheet(it) {
    if (!it) return;
    S.selected = itemKey(it);
    var fam = bucketOf(it);
    var isQ = !!matchQuest(it);
    var color = FAMILY_COLORS[fam] || FAMILY_COLORS['其他'];

    elS.badge.innerHTML = (isQ ? '◆' : '●') + ' ' + esc(isQ ? '金枪客任务' : fam);
    elS.badge.style.color = color;
    elS.badge.style.borderColor = color + '55';
    elS.badge.style.background = color + '18';

    elS.title.textContent = fmt(it.name) || '（未命名配装）';

    var meta = [];
    if (isQ) {
      var st = questStep(it);
      var txt = '金枪客任务' + (st[0] ? ' · 第 ' + st[0] + ' 步' : '') + (st[1] ? ' · ' + st[1] : '');
      meta.push(['任务', txt, true]);
    }
    meta.push(['武器', fmt(it.weapon) || '—', false]);
    meta.push(['作者', fmt(it.player) || '—', false]);
    if (fmt(it.price)) meta.push(['造价', fmtPrice(it.price), false]);
    if (fmt(it.updatedAt)) meta.push(['更新', fmt(it.updatedAt), false]);
    meta.push(['复制', fmt(it.copy_times) || '0', false]);
    if (fmt(it.collect_times)) meta.push(['收藏', fmt(it.collect_times), false]);

    elS.meta.innerHTML = meta.map(function (r) {
      return '<div class="mrow"><span class="mk">' + esc(r[0]) + '</span>' +
        '<span class="mv' + (r[2] ? ' quest' : '') + '">' + esc(r[1]) + '</span></div>';
    }).join('');

    var tags = Array.isArray(it.tags) ? it.tags : (it.tags ? [it.tags] : []);
    elS.tags.innerHTML = tags.map(function (t) {
      return '<span class="tg">' + esc(t) + '</span>';
    }).join('');

    elS.code.textContent = fmt(it.code) || '（无改枪码）';
    elS.copy.textContent = '⎘ 复制改枪码';
    elS.copy.classList.remove('done');

    elSheetWrap.hidden = false;
    // 强制 reflow 后再加 open，保证过渡动画生效
    void elSheet.offsetHeight;
    elSheetWrap.classList.add('open');

    render();
  }

  function closeSheet() {
    elSheetWrap.classList.remove('open');
    setTimeout(function () {
      elSheetWrap.hidden = true;
    }, 280);
  }

  /* ── 复制 ──────────────────────────────────────────── */

  function doCopy(key) {
    var it = key ? findItem(key) : findItem(S.selected);
    if (!it) return;
    var code = fmt(it.code);
    if (!code) { toast('这条没有改枪码'); return; }
    if (hasNative() && native.copy) {
      native.copy(code);
    } else {
      try {
        if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(code);
      } catch (e) { /* ignore */ }
    }
    var head = code.length > 32 ? code.slice(0, 32) + '…' : code;
    toast('✓ 已复制：' + head);
    if (elS.copy) {
      elS.copy.textContent = '✓ 已复制';
      elS.copy.classList.add('done');
      setTimeout(function () {
        if (elS.copy) {
          elS.copy.textContent = '⎘ 复制改枪码';
          elS.copy.classList.remove('done');
        }
      }, 1800);
    }
  }

  var toastTimer = null;
  function toast(msg) {
    elToast.textContent = msg;
    elToast.hidden = false;
    void elToast.offsetHeight;
    elToast.classList.add('show');
    if (toastTimer) clearTimeout(toastTimer);
    toastTimer = setTimeout(function () {
      elToast.classList.remove('show');
      setTimeout(function () { elToast.hidden = true; }, 220);
    }, 1800);
  }

  /* ── 今日密码卡 ───────────────────────────────────── */

  var elDaily, elDWhen, elDGrid, elDHint;

  function renderDaily() {
    var d = S.daily;
    if (!elDaily) return;
    if (!d || !d.items || !d.items.length) {
      elDGrid.innerHTML = '<div class="dempty">暂无数据</div>';
      elDWhen.textContent = '';
      return;
    }
    var html = [];
    for (var i = 0; i < d.items.length && i < 6; i++) {
      var it = d.items[i];
      html.push('<div class="dcell">' +
        '<div class="dn">' + esc(it.name) + '</div>' +
        '<div class="dc">' + esc(it.code) + '</div></div>');
    }
    elDGrid.innerHTML = html.join('');

    var bits = [];
    if (d.updatedText) bits.push('官方 ' + d.updatedText);
    else if (d.date) bits.push('官方 ' + d.date);
    if (d.fetchedAt) bits.push('拉取 ' + d.fetchedAt);
    elDWhen.textContent = bits.join('  ·  ');
    elDaily.hidden = false;
  }

  function loadDailyCache() {
    if (!hasNative() || !native.loadDaily) return;
    var raw = '';
    try { raw = native.loadDaily() || ''; } catch (e) { return; }
    if (!raw) return;
    try {
      S.daily = JSON.parse(raw);
      renderDaily();
    } catch (e) { /* ignore */ }
  }

  function startDailyFetch() {
    if (S.dailyLoading) return;
    S.dailyLoading = true;
    if (elDHint) { elDHint.textContent = '正在获取…'; elDHint.className = 'dhint'; }
    if (hasNative() && native.startDailyFetch) native.startDailyFetch();
  }

  function onDailyPayload(raw) {
    S.dailyLoading = false;
    try {
      // Java 侧 emit("onDaily", obj.toString()) 传进来的已经是对象字面量；
      // 从缓存读的是字符串。两种都接。
      var d = (typeof raw === 'string') ? JSON.parse(raw) : raw;
      if (!d || !d.items) throw new Error('bad payload');
      S.daily = d;
      renderDaily();
      if (elDHint) {
        var stamp = d.fetchedAt || '';
        elDHint.textContent = '✓ 已更新' + (stamp ? ' · ' + stamp : '');
        elDHint.className = 'dhint ok';
      }
    } catch (e) {
      if (elDHint) { elDHint.textContent = '⚠ 数据解析失败'; elDHint.className = 'dhint err'; }
    }
  }

  function onDailyFail(msg) {
    S.dailyLoading = false;
    if (elDHint) {
      elDHint.textContent = S.daily && S.daily.items && S.daily.items.length
        ? ('⚠ 刷新失败，显示缓存 · ' + msg)
        : ('⚠ 获取失败 · ' + msg);
      elDHint.className = 'dhint err';
    }
  }

  /* 跨天自动换密码：每分钟检查一次缓存的 date 是否为今天 */
  var dailyTick = null;
  function scheduleDailyTick() {
    if (dailyTick) return;
    dailyTick = setInterval(function () {
      var today = isoToday();
      var cur = (S.daily && S.daily.date) || '';
      if (cur !== today && !S.dailyLoading) startDailyFetch();
    }, 60000);
  }

  function isoToday() {
    var d = new Date();
    var m = String(d.getMonth() + 1), dd = String(d.getDate());
    if (m.length < 2) m = '0' + m;
    if (dd.length < 2) dd = '0' + dd;
    return d.getFullYear() + '-' + m + '-' + dd;
  }

  /* ── 主题 ──────────────────────────────────────────── */

  function applyTheme(t) {
    S.theme = (t === 'light') ? 'light' : 'dark';
    document.body.className = S.theme === 'light' ? 'theme-light' : 'theme-dark';
    if (hasNative() && native.writePref) native.writePref('theme', S.theme);
  }

  function toggleTheme() {
    applyTheme(S.theme === 'light' ? 'dark' : 'light');
  }

  /* ── 加载 / 刷新 ───────────────────────────────────── */

  function loadCache() {
    if (!hasNative() || !native.loadCache) { render(); return; }
    var raw = native.loadCache();
    if (!raw) { render(); return; }
    try {
      var o = JSON.parse(raw);
      S.items = Array.isArray(o.items) ? o.items : [];
      S.savedAt = o.saved_at || '';
      rebuildFamilies();
      applyFilter();
      render();
      if (S.items.length) setDot('ok', '缓存 ' + S.savedAt);
    } catch (e) { /* ignore */ }
  }

  function setDot(kind, text) {
    elStRight.className = 'dot ' + kind;
    if (text) elStRight.title = text;
  }

  function startFetch() {
    if (S.loading) return;
    S.loading = true;
    elLoading.hidden = false;
    elBarFill.style.width = '0%';
    elLText.textContent = '正在拉取数据…';
    $('btnRefresh').classList.add('spin');
    render();
    if (hasNative() && native.startFetch) {
      native.startFetch();
    } else {
      onError('此环境不支持联网拉取（缺少原生桥）');
    }
  }

  /* 原生回调（必须是全局函数） */
  window.__native = {
    onProgress: function (pages, page, total, got) {
      S.loading = true;
      elLoading.hidden = false;
      elLText.textContent = '正在拉取第 ' + page + ' / ' + pages + ' 页 · 已获取 ' + got + ' 条';
      var pct = pages > 0 ? Math.min(100, Math.round(page * 100 / pages)) : 0;
      elBarFill.style.width = pct + '%';
    },
    onDaily: function (raw) { onDailyPayload(raw); },
    onDailyError: function (msg) { onDailyFail(fmt(msg)); },
    onDone: function (savedAt, count, failed) {
      S.loading = false;
      elLoading.hidden = true;
      $('btnRefresh').classList.remove('spin');
      S.savedAt = savedAt || '';
      loadCache();
      var nFail = (failed && failed.length) ? failed.length : 0;
      if (nFail > 0) {
        setDot('warn', '部分失败');
        elStRight.textContent = '●';
        toast('⚠ ' + nFail + ' 页失败，已用缓存补全');
      } else {
        setDot('ok', '已更新');
        elStRight.textContent = '●';
        toast('✓ 已更新 ' + (count || S.items.length) + ' 条');
      }
    },
    onError: function (msg) {
      onError(msg);
    }
  };

  function onError(msg) {
    S.loading = false;
    elLoading.hidden = true;
    $('btnRefresh').classList.remove('spin');
    setDot('err', '失败');
    elStRight.textContent = '●';
    toast('获取失败：' + msg);
    render();
  }

  /* ── 事件绑定 ──────────────────────────────────────── */

  function bind() {
    elList.addEventListener('click', function (e) {
      var mini = e.target.closest ? e.target.closest('.mini') : null;
      if (mini) {
        e.stopPropagation();
        doCopy(mini.getAttribute('data-copy'));
        return;
      }
      var row = e.target.closest ? e.target.closest('.row') : null;
      if (!row) return;
      var it = findItem(row.getAttribute('data-key'));
      if (it) openSheet(it);
    });

    elFam.addEventListener('click', function (e) {
      var b = e.target.closest ? e.target.closest('.fchip') : null;
      if (!b) return;
      setFamily(b.getAttribute('data-fam'));
    });

    elQ.addEventListener('input', function () {
      S.q = elQ.value || '';
      elClear.hidden = !S.q;
      applyFilter();
      render();
    });

    elClear.addEventListener('click', function () {
      elQ.value = '';
      S.q = '';
      elClear.hidden = true;
      applyFilter();
      render();
      elQ.focus();
    });

    elSortChips.addEventListener('click', function (e) {
      var b = e.target.closest ? e.target.closest('.schip') : null;
      if (!b) return;
      var k = b.getAttribute('data-k');
      if (!SORT_COLS[k]) return;
      if (S.sortKey === k) {
        S.sortRev = !S.sortRev;
      } else {
        S.sortKey = k;
        S.sortRev = !!SORT_DESC_DEFAULT[k];
      }
      syncSortUI();
      sortFiltered();
      render();
    });

    elDir.addEventListener('click', function () {
      S.sortRev = !S.sortRev;
      syncSortUI();
      sortFiltered();
      render();
    });

    $('btnRefresh').addEventListener('click', function () { startFetch(); });
    $('btnTheme').addEventListener('click', toggleTheme);

    elMask.addEventListener('click', closeSheet);
    elS.close.addEventListener('click', closeSheet);
    elS.copy.addEventListener('click', function () { doCopy(S.selected); });

    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') closeSheet();
    });
  }

  function setFamily(fam) {
    S.fam = fam || '全部';
    var isQ = !!QUEST_KEYS[S.fam];
    elChipStep.hidden = !isQ;
    if (isQ) {
      S.sortKey = 'quest_step';
      S.sortRev = false;
    } else if (S.sortKey === 'quest_step') {
      S.sortKey = 'updatedAt';
      S.sortRev = true;
    }
    syncSortUI();
    applyFilter();
    render();
    var on = elFam.querySelector('.fchip.on');
    if (on && on.scrollIntoView) {
      try { on.scrollIntoView({ block: 'nearest', inline: 'center', behavior: 'smooth' }); } catch (e) { }
    }
  }

  function syncSortUI() {
    var chips = elSortChips.querySelectorAll('.schip');
    for (var i = 0; i < chips.length; i++) {
      var on = chips[i].getAttribute('data-k') === S.sortKey;
      chips[i].className = 'schip' + (on ? ' on' : '');
    }
    elDir.textContent = S.sortRev ? '▼' : '▲';
  }

  /* ── 启动 ──────────────────────────────────────────── */

  function boot() {
    elList = $('list');
    elQ = $('q');
    elClear = $('btnClear');
    elFam = $('famrow');
    elSortChips = $('sortchips');
    elDir = $('btnDir');
    elChipStep = $('chipStep');
    elLoading = $('loading');
    elBarFill = $('lbarfill');
    elLText = document.querySelector('.ltext');
    elStLeft = $('stLeft');
    elStMid = $('stMid');
    elStRight = $('stRight');
    elSheetWrap = $('sheetWrap');
    elSheet = $('sheet');
    elMask = $('sheetMask');
    elToast = $('toast');
    elDaily = $('daily');
    elDWhen = $('dWhen');
    elDGrid = $('dGrid');
    elDHint = $('dHint');
    elS = {
      badge: $('sBadge'), title: $('sTitle'), meta: $('sMeta'),
      tags: $('sTags'), code: $('sCode'), copy: $('btnCopy'), close: $('btnClose')
    };

    bind();

    var savedTheme = 'dark';
    if (hasNative() && native.readPref) {
      try { savedTheme = native.readPref('theme', 'dark') || 'dark'; } catch (e) { }
    }
    applyTheme(savedTheme);

    syncSortUI();
    loadCache();
    loadDailyCache();
    // 缓存里不是今天的就立刻拉一次；是今天的就只等 0 点后的轮询
    if (!S.daily || S.daily.date !== isoToday()) {
      startDailyFetch();
    } else if (elDHint) {
      elDHint.textContent = '每日 0 点后自动更新';
      elDHint.className = 'dhint';
    }
    scheduleDailyTick();

    // 有缓存先显示，随后静默刷新；无缓存则直接拉取
    setTimeout(function () {
      if (!S.loading) startFetch();
    }, S.items.length ? 400 : 60);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }
})();

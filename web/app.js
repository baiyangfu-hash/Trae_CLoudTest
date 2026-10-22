/* 英语随身练 - 手机网页版（PWA）
 * 纯前端、无构建步骤。数据：data/phrases.js（场景句库）+ data/dialogs.js（桌面版导出的对话）
 * 学习记录保存在本机 localStorage。
 */
(function () {
  "use strict";

  // ============================================================
  // 工具
  // ============================================================
  const $ = (sel, el = document) => el.querySelector(sel);
  const esc = (s) =>
    String(s == null ? "" : s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const DAY = 86400000;

  function hash(str) {
    let h = 5381;
    for (let i = 0; i < str.length; i++) h = ((h << 5) + h + str.charCodeAt(i)) | 0;
    return (h >>> 0).toString(36);
  }

  function today(ts = Date.now()) {
    const d = new Date(ts);
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
  }

  function shuffle(arr) {
    for (let i = arr.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [arr[i], arr[j]] = [arr[j], arr[i]];
    }
    return arr;
  }

  // ============================================================
  // 存储
  // ============================================================
  const STORE_KEY = "ec.v1";
  const DEFAULT_STATE = {
    cards: {}, // id -> {s, d, due, last, reps, lapses}
    stars: [], // 收藏的句子 id（优先进入练习）
    log: {}, // 日期 -> 当天练习次数
    daily: { date: "", news: [] }, // 当天已引入的新句
    notes: [], // 句子本：{id, zh, en, kind: "s"|"h", created}
    lastExport: [], // 上次“复制给 Claude”时的句子 id 顺序，导入时按编号对应
    settings: { newPerDay: 5, voice: "", rate: 0.95, hideZh: false },
  };

  function loadState() {
    try {
      const raw = localStorage.getItem(STORE_KEY);
      if (raw) {
        const s = JSON.parse(raw);
        return { ...DEFAULT_STATE, ...s, settings: { ...DEFAULT_STATE.settings, ...(s.settings || {}) } };
      }
    } catch (e) {
      /* 无痕模式等情况下读不到，直接用默认值 */
    }
    return JSON.parse(JSON.stringify(DEFAULT_STATE));
  }

  let state = loadState();

  function save() {
    try {
      localStorage.setItem(STORE_KEY, JSON.stringify(state));
    } catch (e) {
      /* 写不进去就算了，本次会话内仍可用 */
    }
  }

  // ============================================================
  // 数据整理
  // ============================================================
  const P = window.PHRASES;
  const DIALOGS = window.DIALOGS || {};
  const SCENES = [P.rescue, ...P.scenes];
  const SCENE_MAP = {};
  const ITEMS = {}; // id -> item
  const SCENE_ITEMS = {}; // sceneId -> [item]

  SCENES.forEach((sc) => {
    SCENE_MAP[sc.id] = sc;
    SCENE_ITEMS[sc.id] = [];
    sc.sections.forEach((sec) => {
      sec.items.forEach((raw) => {
        const kind = raw.s ? "s" : "h";
        const en = raw.s || raw.h;
        const item = {
          id: "p" + hash(en),
          kind,
          en,
          zh: raw.z,
          sounds: raw.f || "",
          reply: raw.r || null,
          scene: sc.id,
          section: sec.title,
        };
        raw._id = item.id;
        ITEMS[item.id] = item;
        SCENE_ITEMS[sc.id].push(item);
      });
    });
  });

  // 句子本：补好英文的条目当作普通句子参与练习和搜索
  const NOTES_SCENE = { id: "mine", name: "句子本", icon: "📒", sections: [] };
  SCENE_MAP.mine = NOTES_SCENE;

  function rebuildNoteItems() {
    Object.keys(ITEMS).forEach((id) => {
      if (ITEMS[id].scene === "mine") delete ITEMS[id];
    });
    SCENE_ITEMS.mine = state.notes
      .filter((n) => n.en)
      .map((n) => {
        const item = { id: n.id, kind: n.kind, en: n.en, zh: n.zh, sounds: "", reply: null, scene: "mine", section: n.kind === "h" ? "我听到的" : "我想说的" };
        ITEMS[n.id] = item;
        return item;
      });
  }
  rebuildNoteItems();

  // ============================================================
  // FSRS-4.5 间隔重复（标准公式）
  // 评分：1=忘了 2=模糊 3=会了 4=很简单
  // ============================================================
  const FSRS = (() => {
    const w = [0.4872, 1.4003, 3.7145, 13.8206, 5.1618, 1.2298, 0.8975, 0.031, 1.6474, 0.1367, 1.0461, 2.1072, 0.0793, 0.3246, 1.587, 0.2272, 2.8755];
    const DECAY = -0.5;
    const FACTOR = 19 / 81;
    const RETENTION = 0.9;
    const MAX_DAYS = 365;
    const clampD = (d) => Math.min(10, Math.max(1, d));
    const initD = (g) => clampD(w[4] - (g - 3) * w[5]);
    const retrievability = (t, s) => Math.pow(1 + (FACTOR * t) / s, DECAY);
    const intervalDays = (s) => Math.min(MAX_DAYS, Math.max(1, Math.round((s / FACTOR) * (Math.pow(RETENTION, 1 / DECAY) - 1))));

    function next(card, g, now = Date.now()) {
      let s, d;
      let lapses = card ? card.lapses : 0;
      if (!card) {
        s = w[g - 1];
        d = initD(g);
      } else {
        const t = Math.max(0, (now - card.last) / DAY);
        const r = retrievability(t, card.s);
        d = clampD(w[7] * initD(3) + (1 - w[7]) * (card.d - w[6] * (g - 3)));
        if (g === 1) {
          s = w[11] * Math.pow(card.d, -w[12]) * (Math.pow(card.s + 1, w[13]) - 1) * Math.exp(w[14] * (1 - r));
          s = Math.min(s, card.s);
          lapses += 1;
        } else {
          const hard = g === 2 ? w[15] : 1;
          const easy = g === 4 ? w[16] : 1;
          s = card.s * (1 + Math.exp(w[8]) * (11 - d) * Math.pow(card.s, -w[9]) * (Math.exp(w[10] * (1 - r)) - 1) * hard * easy);
        }
      }
      // 忘了：本次练习结束前再来一遍，明天再复习
      const days = g === 1 ? 0 : intervalDays(s);
      return {
        s,
        d,
        last: now,
        due: g === 1 ? now : now + days * DAY,
        reps: (card ? card.reps : 0) + 1,
        lapses,
        days,
      };
    }

    return { next };
  })();

  function describeDays(days) {
    if (days <= 0) return "再来一遍";
    if (days < 30) return `${days}天后`;
    if (days < 365) return `${Math.round(days / 30)}个月后`;
    return "1年后";
  }

  // ============================================================
  // 朗读（iOS Safari 自带的 speechSynthesis）
  // ============================================================
  const TTS = (() => {
    const NOVELTY = /albert|bad news|bahh|bells|boing|bubbles|cellos|good news|jester|organ|superstar|trinoids|whisper|wobble|zarvox|junior|ralph|fred|kathy|eddy|flo|grandma|grandpa|reed|rocko|sandy|shelley/i;
    let voices = [];
    let current = null; // 防止 Safari 把 utterance 回收导致 onend 不触发
    const supported = "speechSynthesis" in window;

    function load() {
      if (!supported) return;
      voices = speechSynthesis
        .getVoices()
        .filter((v) => /^en[-_]US/i.test(v.lang) && !NOVELTY.test(v.name))
        .sort((a, b) => score(b) - score(a));
    }

    function score(v) {
      let n = 0;
      if (/premium/i.test(v.name)) n += 30;
      if (/enhanced/i.test(v.name)) n += 20;
      if (/samantha|ava|allison|evan|nathan|zoe|tom/i.test(v.name)) n += 10;
      if (v.localService) n += 2;
      return n;
    }

    if (supported) {
      load();
      speechSynthesis.addEventListener && speechSynthesis.addEventListener("voiceschanged", load);
    }

    function pick(alt) {
      if (!voices.length) load();
      const chosen = voices.find((v) => v.name === state.settings.voice) || voices[0];
      if (!alt) return chosen;
      return voices.find((v) => v !== chosen) || chosen;
    }

    function speak(text, opts = {}) {
      if (!supported) {
        toast("这个浏览器不支持朗读");
        return;
      }
      speechSynthesis.cancel();
      const u = new SpeechSynthesisUtterance(text);
      const v = pick(opts.alt);
      if (v) u.voice = v;
      u.lang = "en-US";
      u.rate = opts.slow ? 0.6 : state.settings.rate;
      if (opts.onend) {
        u.onend = opts.onend;
        u.onerror = opts.onend;
      }
      current = u;
      speechSynthesis.speak(u);
    }

    function stop() {
      if (supported) speechSynthesis.cancel();
      current = null;
    }

    return { speak, stop, list: () => voices, supported, reload: load };
  })();

  // ============================================================
  // 练习队列
  // ============================================================
  function resetDailyIfNeeded() {
    if (state.daily.date !== today()) {
      state.daily = { date: today(), news: [] };
      save();
    }
  }

  function dueIds(filterScene) {
    const now = Date.now();
    return Object.keys(state.cards)
      .filter((id) => ITEMS[id] && state.cards[id].due <= now && (!filterScene || ITEMS[id].scene === filterScene))
      .sort((a, b) => state.cards[a].due - state.cards[b].due);
  }

  // 新句：收藏优先，其余在各场景之间轮流挑，避免一直卡在同一个场景
  function newCandidates(filterScene) {
    const unseen = (id) => !state.cards[id];
    const stars = state.stars.filter((id) => ITEMS[id] && unseen(id) && (!filterScene || ITEMS[id].scene === filterScene));
    const sceneIds = filterScene ? [filterScene] : SCENES.map((s) => s.id);
    const mine = filterScene ? [] : SCENE_ITEMS.mine.filter((it) => unseen(it.id) && !stars.includes(it.id)).map((it) => it.id);
    const pools = sceneIds.map((sid) => SCENE_ITEMS[sid].filter((it) => unseen(it.id) && !stars.includes(it.id)).map((it) => it.id));
    const out = [...stars, ...mine];
    let added = true;
    while (added) {
      added = false;
      pools.forEach((pool) => {
        if (pool.length) {
          out.push(pool.shift());
          added = true;
        }
      });
    }
    // 同一句话可能出现在多个场景里（如 “Can I see your ID?”），只练一次
    return [...new Set(out)];
  }

  function newLeftToday() {
    resetDailyIfNeeded();
    return Math.max(0, state.settings.newPerDay - state.daily.news.length);
  }

  function buildSession(sceneId) {
    resetDailyIfNeeded();
    const due = dueIds(sceneId).slice(0, 30);
    const newLimit = sceneId === "mine" ? 15 : sceneId ? 8 : newLeftToday();
    const news = newCandidates(sceneId).slice(0, newLimit);
    return [...due, ...news];
  }

  function todayCount() {
    return dueIds().length + Math.min(newLeftToday(), newCandidates().length);
  }

  function logPractice() {
    const d = today();
    state.log[d] = (state.log[d] || 0) + 1;
  }

  function streak() {
    let n = 0;
    let t = Date.now();
    if (!state.log[today(t)]) t -= DAY; // 今天还没练不打断连续天数
    while (state.log[today(t)]) {
      n++;
      t -= DAY;
    }
    return n;
  }

  // ============================================================
  // 通用 UI 片段
  // ============================================================
  function toast(msg) {
    const el = $("#toast");
    el.textContent = msg;
    el.classList.add("show");
    clearTimeout(toast._t);
    toast._t = setTimeout(() => el.classList.remove("show"), 1800);
  }

  function playButtons(text) {
    return `<button class="icon-btn" data-say="${esc(text)}" aria-label="朗读">▶</button>
            <button class="icon-btn" data-say="${esc(text)}" data-slow="1" aria-label="慢速朗读">🐢</button>`;
  }

  function itemCard(it) {
    const starred = state.stars.includes(it.id);
    const tag = it.kind === "s" ? `<span class="tag say">🗣 我说</span>` : `<span class="tag hear">👂 对方说</span>`;
    const sounds = it.sounds ? `<div class="sounds">听起来像：${esc(it.sounds)}</div>` : "";
    const reply = it.reply
      ? `<div class="reply"><div class="reply-label">↪ 我可以回</div>
           <div class="reply-row"><div><div class="en small">${esc(it.reply[0])}</div><div class="zh">${esc(it.reply[1])}</div></div>
           <div class="btns">${playButtons(it.reply[0])}</div></div></div>`
      : "";
    return `<div class="card item ${it.kind}">
      <div class="item-top">${tag}<button class="star ${starred ? "on" : ""}" data-star="${it.id}" aria-label="收藏">${starred ? "★" : "☆"}</button></div>
      <div class="item-main" data-say="${esc(it.en)}">
        <div class="en">${esc(it.en)}</div>
        <div class="zh">${esc(it.zh)}</div>
      </div>
      ${sounds}
      <div class="btns">${playButtons(it.en)}</div>
      ${reply}
    </div>`;
  }

  // ============================================================
  // 页面：首页
  // ============================================================
  function viewHome() {
    const n = todayCount();
    const st = streak();
    const tiles = SCENES.map(
      (sc) => `<a class="tile ${sc.id === "rescue" ? "rescue" : ""}" href="#/scene/${sc.id}">
        <span class="tile-icon">${sc.icon}</span><span class="tile-name">${esc(sc.name)}</span>
        <span class="tile-count">${SCENE_ITEMS[sc.id].length} 句</span></a>`
    ).join("");
    return `
      <header class="hero">
        <div class="hero-row">
          <div><h1>英语随身练</h1><div class="sub">${st ? `🔥 已连续 ${st} 天` : "每天 3 分钟，开口不慌"}</div></div>
        </div>
        <a class="cta" href="#/practice">
          <span>今日练习</span><span class="cta-num">${n ? `${n} 句` : "已完成 ✓"}</span>
        </a>
      </header>
      <div class="search-wrap">
        <input id="search" type="search" placeholder="搜一句话：中文或英文，如“打包”" autocomplete="off" />
      </div>
      <div id="search-results"></div>
      <section id="home-main">
        <h2 class="section-title">场景速查</h2>
        <div class="tiles">${tiles}</div>
      </section>`;
  }

  function bindHome() {
    const input = $("#search");
    const out = $("#search-results");
    const main = $("#home-main");
    input.addEventListener("input", () => {
      const q = input.value.trim().toLowerCase();
      if (!q) {
        out.innerHTML = "";
        main.style.display = "";
        return;
      }
      main.style.display = "none";
      const hits = Object.values(ITEMS).filter(
        (it) => it.en.toLowerCase().includes(q) || it.zh.includes(q) || (it.reply && (it.reply[0].toLowerCase().includes(q) || it.reply[1].includes(q)))
      );
      out.innerHTML = hits.length
        ? hits.slice(0, 40).map((it) => `<div class="hit-scene">${SCENE_MAP[it.scene].icon} ${esc(SCENE_MAP[it.scene].name)} · ${esc(it.section)}</div>${itemCard(it)}`).join("")
        : `<div class="empty">没找到。可以换个说法试试。</div>`;
    });
  }

  // ============================================================
  // 页面：场景
  // ============================================================
  function viewScene(id, filter) {
    const sc = SCENE_MAP[id];
    if (!sc) return viewHome();
    filter = filter || "all";
    const tabs = [
      ["all", "全部"],
      ["s", "🗣 我说"],
      ["h", "👂 对方说"],
    ]
      .map(([k, label]) => `<a class="seg ${filter === k ? "on" : ""}" href="#/scene/${id}/${k}">${label}</a>`)
      .join("");
    const sections = sc.sections
      .map((sec) => {
        const items = sec.items.map((raw) => ITEMS[raw._id]).filter((it) => filter === "all" || it.kind === filter);
        if (!items.length) return "";
        return `<h3 class="sec-title">${esc(sec.title)}</h3>${items.map(itemCard).join("")}`;
      })
      .join("");
    const dialogs = (sc.dialogs || [])
      .filter((d) => DIALOGS[d])
      .map((d) => `<a class="list-link" href="#/dialog/${d}"><span>💬 ${esc(DIALOGS[d].title)}</span><span class="muted">${DIALOGS[d].lines.length} 句 ›</span></a>`)
      .join("");
    return `
      <div class="topbar"><a class="back" href="#/">‹ 返回</a><span class="title">${sc.icon} ${esc(sc.name)}</span><span></span></div>
      <div class="tip">💡 ${esc(sc.tip)}</div>
      <a class="cta small" href="#/practice/${id}"><span>只练这个场景</span><span class="cta-num">${dueIds(id).length + Math.min(8, newCandidates(id).length)} 句 ›</span></a>
      <div class="segs">${tabs}</div>
      ${sections}
      ${dialogs ? `<h3 class="sec-title">完整对话</h3><div class="card list">${dialogs}</div>` : ""}`;
  }

  // ============================================================
  // 页面：完整对话
  // ============================================================
  let dialogPlaying = false;

  function viewDialog(id) {
    const d = DIALOGS[id];
    if (!d) return viewHome();
    const hide = state.settings.hideZh;
    const lines = d.lines
      .map((l, i) => {
        const me = /^you$/i.test(l.speaker);
        return `<div class="line ${me ? "me" : ""}" data-line="${i}">
          <div class="speaker">${esc(me ? "我" : l.speaker)}</div>
          <div class="bubble" data-say="${esc(l.text)}" ${me ? "" : 'data-alt="1"'}>
            <div class="en">${esc(l.text)}</div>
            <div class="zh ${hide ? "blur" : ""}">${esc(l.translation)}</div>
          </div></div>`;
      })
      .join("");
    return `
      <div class="topbar"><a class="back" href="javascript:history.back()">‹ 返回</a><span class="title">${esc(d.title)}</span><span></span></div>
      <div class="dialog-tools">
        <button class="btn" id="play-all">▶ 从头播放</button>
        <button class="btn ghost" id="toggle-zh">${hide ? "显示中文" : "遮住中文"}</button>
      </div>
      <div class="muted center">点任意一句单独播放${hide ? "，点模糊的中文可查看" : ""}</div>
      <div class="dialog">${lines}</div>`;
  }

  function bindDialog(id) {
    const d = DIALOGS[id];
    $("#toggle-zh").addEventListener("click", () => {
      state.settings.hideZh = !state.settings.hideZh;
      save();
      render();
    });
    $("#play-all").addEventListener("click", (e) => {
      if (dialogPlaying) {
        dialogPlaying = false;
        TTS.stop();
        e.target.textContent = "▶ 从头播放";
        document.querySelectorAll(".line.playing").forEach((x) => x.classList.remove("playing"));
        return;
      }
      dialogPlaying = true;
      e.target.textContent = "■ 停止";
      const step = (i) => {
        document.querySelectorAll(".line.playing").forEach((x) => x.classList.remove("playing"));
        if (!dialogPlaying || i >= d.lines.length || !$(`[data-line="${i}"]`)) {
          dialogPlaying = false;
          const b = $("#play-all");
          if (b) b.textContent = "▶ 从头播放";
          return;
        }
        const el = $(`[data-line="${i}"]`);
        el.classList.add("playing");
        el.scrollIntoView({ block: "center", behavior: "smooth" });
        const me = /^you$/i.test(d.lines[i].speaker);
        TTS.speak(d.lines[i].text, { alt: !me, onend: () => setTimeout(() => step(i + 1), 400) });
      };
      step(0);
    });
  }

  // ============================================================
  // 页面：练习
  // ============================================================
  let session = null; // {queue, idx, done, scene, revealed}

  function startSession(sceneId) {
    session = { queue: buildSession(sceneId), done: 0, again: 0, scene: sceneId || "", revealed: false };
  }

  function viewPractice(sceneId) {
    if (!session || session.scene !== (sceneId || "")) startSession(sceneId);
    const sc = sceneId ? SCENE_MAP[sceneId] : null;
    const backHref = !sc ? "#/" : sc.id === "mine" ? "#/notes" : `#/scene/${sc.id}`;
    const top = `<div class="topbar"><a class="back" href="${backHref}">‹ ${sc ? "返回" : "首页"}</a><span class="title">${sc ? sc.icon + " " + esc(sc.name) : "今日练习"}</span><span class="muted">${session.queue.length ? session.done + "/" + (session.done + session.queue.length) : ""}</span></div>`;

    if (!session.queue.length) {
      const st = streak();
      return `${top}
        <div class="done">
          <div class="done-icon">🎉</div>
          <h2>${session.done ? `完成 ${session.done} 句！` : "今天的练习已经做完了"}</h2>
          <p class="muted">${st ? `已连续练习 ${st} 天` : ""}</p>
          <p class="muted">${session.done ? "明天会按记忆曲线把该复习的句子推给你。" : "想多练可以进场景页点“只练这个场景”。"}</p>
          <div class="done-actions">
            <a class="btn" href="#/">回首页</a>
            ${session.done ? `<button class="btn ghost" id="more">再来一组</button>` : ""}
          </div>
        </div>`;
    }

    const it = ITEMS[session.queue[0]];
    const card = state.cards[it.id];
    const isNew = !card;
    const badge = isNew ? `<span class="tag new">新句</span>` : `<span class="tag">复习</span>`;
    const where = `<span class="muted small">${SCENE_MAP[it.scene].icon} ${esc(SCENE_MAP[it.scene].name)} · ${esc(it.section)}</span>`;

    let body;
    if (it.kind === "s") {
      body = `
        <div class="prompt-label">用英语怎么说？</div>
        <div class="prompt-zh">${esc(it.zh)}</div>
        ${session.revealed ? `<div class="answer"><div class="en big">${esc(it.en)}</div><div class="btns center">${playButtons(it.en)}</div></div>` : `<div class="hint">先在心里或小声说一遍，再看答案</div>`}`;
    } else {
      body = `
        <div class="prompt-label">👂 对方这么说，你听懂了吗？</div>
        <button class="listen-btn" data-say="${esc(it.en)}">▶ 再听一遍</button>
        <button class="listen-btn slow" data-say="${esc(it.en)}" data-slow="1">🐢 慢速</button>
        ${
          session.revealed
            ? `<div class="answer"><div class="en big">${esc(it.en)}</div><div class="zh">${esc(it.zh)}</div>
               ${it.sounds ? `<div class="sounds">听起来像：${esc(it.sounds)}</div>` : ""}
               ${it.reply ? `<div class="reply"><div class="reply-label">↪ 我可以回</div><div class="reply-row"><div><div class="en small">${esc(it.reply[0])}</div><div class="zh">${esc(it.reply[1])}</div></div><div class="btns">${playButtons(it.reply[0])}</div></div></div>` : ""}</div>`
            : `<div class="hint">先只听不看，想想意思和怎么回</div>`
        }`;
    }

    let actions;
    if (!session.revealed) {
      actions = `<button class="btn wide" id="reveal">看答案</button>`;
    } else {
      const label = (g, text) => `${text}<small>${describeDays(FSRS.next(card, g).days)}</small>`;
      actions = `<div class="rates">
        <button class="rate r1" data-rate="1">${label(1, "忘了")}</button>
        <button class="rate r2" data-rate="2">${label(2, "模糊")}</button>
        <button class="rate r3" data-rate="3">${label(3, "会了")}</button>
      </div>`;
    }

    return `${top}
      <div class="card practice">
        <div class="item-top">${badge}${where}</div>
        ${body}
      </div>
      <div class="practice-actions">${actions}</div>`;
  }

  function bindPractice(sceneId) {
    const it = session.queue.length ? ITEMS[session.queue[0]] : null;
    const more = $("#more");
    if (more) more.addEventListener("click", () => {
      startSession(sceneId);
      if (!session.queue.length) {
        // 今天新句额度用完了：再给一组新句
        session.queue = newCandidates(sceneId).slice(0, 5);
      }
      render();
    });
    if (!it) return;
    if (it.kind === "h" && !session.revealed && !session.autoplayed) {
      session.autoplayed = true;
      setTimeout(() => TTS.speak(it.en), 250);
    }
    const reveal = $("#reveal");
    if (reveal) reveal.addEventListener("click", () => {
      session.revealed = true;
      render();
      if (it.kind === "s") TTS.speak(it.en);
    });
    document.querySelectorAll("[data-rate]").forEach((b) =>
      b.addEventListener("click", () => {
        const g = Number(b.dataset.rate);
        const wasNew = !state.cards[it.id];
        state.cards[it.id] = FSRS.next(state.cards[it.id], g);
        delete state.cards[it.id].days;
        if (wasNew) {
          resetDailyIfNeeded();
          if (!state.daily.news.includes(it.id)) state.daily.news.push(it.id);
        }
        logPractice();
        save();
        session.queue.shift();
        if (g === 1) {
          // 忘了：隔几句再来一次
          session.queue.splice(Math.min(3, session.queue.length), 0, it.id);
        } else {
          session.done++;
        }
        session.revealed = false;
        session.autoplayed = false;
        TTS.stop();
        render();
      })
    );
  }

  // ============================================================
  // 页面：句子本
  // ============================================================
  let noteKind = "s";

  function noteId() {
    return "u" + Date.now().toString(36) + Math.random().toString(36).slice(2, 5);
  }

  function addNote(zh, en, kind) {
    state.notes.unshift({ id: noteId(), zh: zh.trim(), en: (en || "").trim(), kind: kind || "s", created: Date.now() });
  }

  function deleteNote(id) {
    state.notes = state.notes.filter((n) => n.id !== id);
    delete state.cards[id];
    state.stars = state.stars.filter((x) => x !== id);
  }

  // 给 Claude 的批量请求：只包含还没有英文的句子
  function exportPrompt() {
    const pending = state.notes.filter((n) => !n.en);
    state.lastExport = pending.map((n) => n.id);
    save();
    const lines = pending.map((n, i) => `${i + 1}. ${n.kind === "h" ? "【我听到】" : "【我想说】"}${n.zh}`);
    return (
      "我在美国生活，下面是我遇到但不会用英语表达的话。请写成自然、口语化的美式英语，简短好记。" +
      "“我听到”的是别人对我说的话，请写出对方最可能的原话。\n" +
      "请严格按这个格式回复，每行一句：编号. 中文 | English\n\n" +
      lines.join("\n")
    );
  }

  // 解析 “编号. 中文 | English” 或 “中文 | English”
  // 先按中文原文对应，剩下的再按编号对应（Claude 偶尔会改动中文），同一句不会被填两次
  function importLines(text) {
    const rows = [];
    text.split(/\r?\n/).forEach((line) => {
      const m = line.match(/^\s*(?:(\d+)\s*[.、)）]\s*)?(?:【(?:我听到|我想说)】)?(.+?)\s*[|｜]\s*(.+?)\s*$/);
      if (!m) return;
      const [, num, zh, en] = m;
      if (!/[a-z]/i.test(en) || en.trim() === "English") return; // 跳过格式说明那一行
      rows.push({ num: num ? Number(num) : 0, zh: zh.trim(), en: en.trim(), target: null });
    });
    const used = new Set();
    rows.forEach((r) => {
      const n = state.notes.find((x) => x.zh === r.zh && !used.has(x.id));
      if (n) {
        r.target = n;
        used.add(n.id);
      }
    });
    rows.forEach((r) => {
      if (r.target || !r.num) return;
      const n = state.notes.find((x) => x.id === state.lastExport[r.num - 1]);
      if (n && !used.has(n.id)) {
        r.target = n;
        used.add(n.id);
      }
    });
    let filled = 0;
    let added = 0;
    rows.forEach((r) => {
      if (r.target) {
        r.target.en = r.en;
        filled++;
      } else {
        addNote(r.zh, r.en, "s");
        added++;
      }
    });
    return { filled, added };
  }

  function viewNotes() {
    const pending = state.notes.filter((n) => !n.en);
    const done = state.notes.filter((n) => n.en);
    const kindBtn = (k, label) => `<button class="seg ${noteKind === k ? "on" : ""}" data-kind="${k}">${label}</button>`;
    const pendingHtml = pending
      .map(
        (n) => `<div class="card note" data-note="${n.id}">
          <div class="item-top"><span class="tag ${n.kind === "h" ? "hear" : "say"}">${n.kind === "h" ? "👂 我听到" : "🗣 我想说"}</span>
            <button class="link danger" data-del="${n.id}">删除</button></div>
          <div class="zh-main">${esc(n.zh)}</div>
          <div class="fill-row">
            <input class="fill-en" placeholder="填英文" autocapitalize="sentences" />
            <button class="btn small" data-fill="${n.id}">保存</button>
          </div>
          <a class="link" href="https://translate.google.com/?sl=zh-CN&tl=en&op=translate&text=${encodeURIComponent(n.zh)}" target="_blank" rel="noopener">🌐 谷歌翻译查一下</a>
        </div>`
      )
      .join("");
    const doneHtml = done
      .map(
        (n) => `${itemCard(ITEMS[n.id])}<div class="note-actions"><button class="link" data-edit="${n.id}">改英文</button><button class="link danger" data-del="${n.id}">删除</button></div>`
      )
      .join("");
    const dueMine = dueIds("mine").length + Math.min(8, newCandidates("mine").length);
    return `
      <div class="topbar"><span></span><span class="title">📒 句子本</span><span></span></div>
      <div class="card form">
        <div class="segs">${kindBtn("s", "🗣 我想说")}${kindBtn("h", "👂 我听到")}</div>
        <textarea id="note-zh" rows="2" placeholder="${noteKind === "h" ? "对方说了什么？用中文描述，如：收银员问我要不要办什么卡" : "想说但不会说的话，如：我想把这个退了换大一号"}"></textarea>
        <input id="note-en" placeholder="英文（会就填，不会留空）" autocapitalize="sentences" />
        <button class="btn wide" id="note-add">记下来</button>
      </div>

      ${done.length ? `<a class="cta small" href="#/practice/mine"><span>练习句子本</span><span class="cta-num">${dueMine} 句 ›</span></a>` : ""}

      <h3 class="sec-title">待补英文（${pending.length}）</h3>
      ${
        pending.length
          ? `<button class="btn ghost wide" id="note-export">📋 复制给 Claude 补英文</button>
             <p class="muted small">复制后发给 Claude，把回复整段复制回来，粘到下面“导入”框里。</p>${pendingHtml}`
          : `<div class="empty">没有待补的句子。在外面卡壳了就记下来。</div>`
      }

      <h3 class="sec-title">导入 Claude 的回复</h3>
      <div class="card form">
        <textarea id="note-import" rows="4" placeholder="粘贴格式：1. 中文 | English（每行一句）"></textarea>
        <button class="btn ghost wide" id="note-import-btn">导入</button>
      </div>

      <h3 class="sec-title">已加入练习（${done.length}）</h3>
      ${doneHtml || `<div class="empty">补好英文的句子会出现在这里，并优先进入每日练习。</div>`}`;
  }

  function bindNotes() {
    document.querySelectorAll("[data-kind]").forEach((b) =>
      b.addEventListener("click", () => {
        noteKind = b.dataset.kind;
        const zh = $("#note-zh").value;
        const en = $("#note-en").value;
        render();
        $("#note-zh").value = zh;
        $("#note-en").value = en;
      })
    );
    $("#note-add").addEventListener("click", () => {
      const zh = $("#note-zh").value.trim();
      const en = $("#note-en").value.trim();
      if (!zh) {
        toast("先写中文");
        return;
      }
      addNote(zh, en, noteKind);
      save();
      rebuildNoteItems();
      toast(en ? "已加入练习" : "已记下，记得补英文");
      render();
    });
    document.querySelectorAll("[data-fill]").forEach((b) =>
      b.addEventListener("click", () => {
        const n = state.notes.find((x) => x.id === b.dataset.fill);
        const en = b.closest(".note").querySelector(".fill-en").value.trim();
        if (!n || !en) return;
        n.en = en;
        save();
        rebuildNoteItems();
        toast("已加入练习");
        render();
      })
    );
    document.querySelectorAll("[data-edit]").forEach((b) =>
      b.addEventListener("click", () => {
        const n = state.notes.find((x) => x.id === b.dataset.edit);
        if (!n) return;
        const en = prompt(n.zh, n.en);
        if (en == null) return;
        n.en = en.trim();
        save();
        rebuildNoteItems();
        render();
      })
    );
    document.querySelectorAll("[data-del]").forEach((b) =>
      b.addEventListener("click", () => {
        if (!confirm("删除这一句？")) return;
        deleteNote(b.dataset.del);
        save();
        rebuildNoteItems();
        render();
      })
    );
    const exp = $("#note-export");
    if (exp) exp.addEventListener("click", async () => {
      const text = exportPrompt();
      try {
        await navigator.clipboard.writeText(text);
        toast("已复制，发给 Claude 吧");
      } catch (e) {
        $("#note-import").value = text;
        $("#note-import").select();
        toast("请手动复制下面框里的内容");
      }
    });
    $("#note-import-btn").addEventListener("click", () => {
      const { filled, added } = importLines($("#note-import").value);
      if (!filled && !added) {
        toast("没识别到，格式：1. 中文 | English");
        return;
      }
      save();
      rebuildNoteItems();
      toast(`补好 ${filled} 句${added ? `，新增 ${added} 句` : ""}`);
      render();
    });
  }

  // ============================================================
  // 页面：我的
  // ============================================================
  function viewMe() {
    const learned = Object.keys(state.cards).filter((id) => ITEMS[id]).length;
    const total = Object.keys(ITEMS).length;
    const mastered = Object.values(state.cards).filter((c) => c.s >= 21).length;
    const days = Object.keys(state.log).length;
    const voices = TTS.list();
    const voiceOpts = voices.length
      ? voices.map((v) => `<option value="${esc(v.name)}" ${v.name === state.settings.voice ? "selected" : ""}>${esc(v.name)}</option>`).join("")
      : `<option value="">（系统默认）</option>`;
    const perDay = [3, 5, 8, 10, 15].map((n) => `<option value="${n}" ${n === state.settings.newPerDay ? "selected" : ""}>${n} 句</option>`).join("");
    const rates = [
      [0.8, "偏慢"],
      [0.95, "正常"],
      [1.05, "偏快（接近真人）"],
    ]
      .map(([r, l]) => `<option value="${r}" ${r === state.settings.rate ? "selected" : ""}>${l}</option>`)
      .join("");
    const starred = state.stars.filter((id) => ITEMS[id]);
    return `
      <div class="topbar"><span></span><span class="title">我的</span><span></span></div>
      <div class="stats">
        <div class="stat"><b>${streak()}</b><span>连续天数</span></div>
        <div class="stat"><b>${learned}</b><span>学过 / ${total}</span></div>
        <div class="stat"><b>${mastered}</b><span>已牢记</span></div>
        <div class="stat"><b>${days}</b><span>练习天数</span></div>
      </div>

      <h3 class="sec-title">设置</h3>
      <div class="card form">
        <label>每天新句<select id="set-new">${perDay}</select></label>
        <label>朗读声音<select id="set-voice">${voiceOpts}</select></label>
        <label>朗读速度<select id="set-rate">${rates}</select></label>
        <button class="btn ghost wide" id="test-voice">▶ 试听</button>
        <p class="muted small">想要更自然的声音：iPhone 设置 → 辅助功能 → 朗读内容 → 声音 → 英语，下载带“增强/高级”的声音（如 Ava、Evan），回来刷新这页再选。</p>
      </div>

      <h3 class="sec-title">收藏（${starred.length}）</h3>
      ${starred.length ? starred.map((id) => itemCard(ITEMS[id])).join("") : `<div class="empty">在场景里点 ☆ 收藏，收藏的句子会优先进入每日练习。</div>`}

      <h3 class="sec-title">备份</h3>
      <div class="card form">
        <p class="muted small">学习记录只存在这台手机的浏览器里。换手机或清理 Safari 数据前，先复制备份存到备忘录。</p>
        <button class="btn ghost wide" id="export">复制备份</button>
        <textarea id="import-text" rows="3" placeholder="把备份粘贴到这里"></textarea>
        <button class="btn ghost wide" id="import">恢复备份</button>
      </div>
      <p class="muted center small">英语随身练 · 数据保存在本机</p>`;
  }

  function bindMe() {
    $("#set-new").addEventListener("change", (e) => {
      state.settings.newPerDay = Number(e.target.value);
      save();
      toast("已保存");
    });
    $("#set-voice").addEventListener("change", (e) => {
      state.settings.voice = e.target.value;
      save();
      TTS.speak("Hi, how's it going?");
    });
    $("#set-rate").addEventListener("change", (e) => {
      state.settings.rate = Number(e.target.value);
      save();
      TTS.speak("Hi, how's it going?");
    });
    $("#test-voice").addEventListener("click", () => TTS.speak("Hi, did you find everything okay today?"));
    $("#export").addEventListener("click", async () => {
      const text = JSON.stringify(state);
      try {
        await navigator.clipboard.writeText(text);
        toast("已复制，粘贴到备忘录保存");
      } catch (e) {
        $("#import-text").value = text;
        $("#import-text").select();
        toast("请手动复制文本框里的内容");
      }
    });
    $("#import").addEventListener("click", () => {
      try {
        const data = JSON.parse($("#import-text").value);
        if (!data || typeof data.cards !== "object") throw new Error("bad");
        if (!confirm("用备份覆盖当前学习记录？")) return;
        state = { ...DEFAULT_STATE, ...data, settings: { ...DEFAULT_STATE.settings, ...(data.settings || {}) } };
        save();
        rebuildNoteItems();
        toast("已恢复");
        render();
      } catch (e) {
        toast("备份内容不对，请检查");
      }
    });
  }

  // ============================================================
  // 路由 + 全局事件
  // ============================================================
  function render() {
    const parts = (location.hash.replace(/^#\/?/, "") || "").split("/");
    const route = parts[0] || "";
    const view = $("#view");
    let html;
    let bind = null;
    let tab = "home";

    if (route !== "dialog") {
      dialogPlaying = false;
    }

    switch (route) {
      case "scene":
        html = viewScene(parts[1], parts[2]);
        break;
      case "dialog":
        html = viewDialog(parts[1]);
        bind = () => DIALOGS[parts[1]] && bindDialog(parts[1]);
        break;
      case "practice":
        html = viewPractice(parts[1]);
        bind = () => bindPractice(parts[1]);
        tab = "practice";
        break;
      case "notes":
        html = viewNotes();
        bind = bindNotes;
        tab = "notes";
        break;
      case "me":
        html = viewMe();
        bind = bindMe;
        tab = "me";
        break;
      default:
        html = viewHome();
        bind = bindHome;
    }
    view.innerHTML = html;
    document.querySelectorAll(".tabbar a").forEach((a) => a.classList.toggle("on", a.dataset.tab === tab));
    if (bind) bind();
  }

  let lastRoute = "";
  window.addEventListener("hashchange", () => {
    const route = location.hash;
    // 离开练习页再回来时重新组队列
    if (!route.startsWith("#/practice")) session = null;
    TTS.stop();
    render();
    if (route !== lastRoute) window.scrollTo(0, 0);
    lastRoute = route;
  });

  document.addEventListener("click", (e) => {
    const star = e.target.closest("[data-star]");
    if (star) {
      const id = star.dataset.star;
      const i = state.stars.indexOf(id);
      if (i >= 0) state.stars.splice(i, 1);
      else state.stars.unshift(id);
      save();
      const on = state.stars.includes(id);
      document.querySelectorAll(`[data-star="${id}"]`).forEach((b) => {
        b.classList.toggle("on", on);
        b.textContent = on ? "★" : "☆";
      });
      toast(on ? "已收藏，会优先进入练习" : "已取消收藏");
      return;
    }
    const blur = e.target.closest(".zh.blur");
    if (blur) {
      blur.classList.remove("blur");
      return;
    }
    const say = e.target.closest("[data-say]");
    if (say) {
      say.classList.add("pressed");
      setTimeout(() => say.classList.remove("pressed"), 200);
      TTS.speak(say.dataset.say, { slow: !!say.dataset.slow, alt: !!say.dataset.alt });
    }
  });

  if ("serviceWorker" in navigator && location.protocol !== "file:") {
    window.addEventListener("load", () => navigator.serviceWorker.register("sw.js").catch(() => {}));
  }

  render();
})();

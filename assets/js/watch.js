/* صفحة المجلس — تشغيل متزامن مع النص */
"use strict";

const params = new URLSearchParams(location.search);
const lecId = String(params.get("id") || "071").padStart(3, "0");

let indexData = null;
let lecData = null;
let timedSegs = [];          // [{start, end, el, words:[{start,end,el}]}]
let currentIdx = -1;
let mode = "video";
let ytPlayer = null;
let ytReady = false;
let autoScroll = true;
let userScrolledAt = 0;
let versesOpen = false;
let saveTimer = 0;
let ended = false;

const $ = sel => document.querySelector(sel);

init();

async function init() {
  try {
    indexData = await loadIndex();
    const known = indexData.lectures.find(l => l.id === lecId);
    if (!known) throw new Error("معرّف المجلس غير معروف: " + lecId);
    lecData = await fetchJSON(`data/${lecId}.json`);
  } catch (err) {
    showFatal(err);
    return;
  }
  renderHead();
  renderTranscript();
  bindControls();
  bindTicker();
  setupYouTube();
  setupAudio();
  setupResume();
}

/* ---------- العرض ---------- */

function renderHead() {
  document.title = `${lecData.title} | تفسير سورة الأنعام`;
  $("#lecTitle").textContent = lecData.title;
  const range = ayahRange(lecData.title);
  const chips = [
    el("span", { class: "chip gold", text: "⏱ " + fmtTime(lecData.duration) }),
    range ? el("span", { class: "chip", text: "الآيات " + range }) : null,
    el("span", { class: "chip", text: lecData.speaker }),
  ].filter(Boolean);
  $("#lecMeta").replaceChildren(...chips);

  // وضع الصوت
  $("#audioLecNum").textContent = "المجلس " + toArabicDigits(lecId);
  $("#audioTitle").textContent = lecData.title;
  $("#audioSpeaker").textContent = lecData.speaker;
  $("#metaDuration").textContent = "المدة: " + fmtTime(lecData.duration);
  $("#metaAyahs").textContent = range ? "الآيات: " + range : "";
  $("#ytLink").href = lecData.youtube_url;

  // أزرار السابق/التالي
  const list = indexData.lectures;
  const i = list.findIndex(l => l.id === lecId);
  const prev = list[i - 1], next = list[i + 1];
  const prevBtn = $("#prevLec"), nextBtn = $("#nextLec");
  if (prev) { prevBtn.disabled = false; prevBtn.onclick = () => (location.href = `watch.html?id=${prev.id}`); }
  else prevBtn.disabled = true;
  if (next) { nextBtn.disabled = false; nextBtn.onclick = () => (location.href = `watch.html?id=${next.id}`); }
  else nextBtn.disabled = true;

  // بطاقة النهاية
  const endBtn = $("#endNextBtn");
  if (next) endBtn.href = `watch.html?id=${next.id}`;
  else { endBtn.textContent = "عودة إلى فهرس المجالس"; endBtn.href = "index.html"; }
}

function renderTranscript() {
  const host = $("#transcript");
  const frag = document.createDocumentFragment();
  const jump = $("#jumpSelect");
  timedSegs = [];

  for (const seg of lecData.segments) {
    if (seg.type === "heading") {
      frag.append(el("div", { class: "h-divider" }, [el("span", { text: seg.text })]));
      continue;
    }
    if (seg.type === "quran") {
      frag.append(buildVerse(seg, jump));
      continue;
    }
    // مقطع منطوق
    const p = el("p", { class: "seg", "data-start": seg.start, "data-end": seg.end, tabindex: "0", role: "button", "aria-label": "الانتقال إلى هذه الجملة" });
    const wordNodes = [];
    for (const w of seg.words) {
      const span = el("span", { class: "w", text: w.text, "data-start": w.start, "data-end": w.end });
      p.append(span, document.createTextNode(" "));
      wordNodes.push({ start: w.start, end: w.end, el: span });
    }
    frag.append(p);
    timedSegs.push({ start: seg.start, end: seg.end, el: p, words: wordNodes });
  }
  host.replaceChildren(frag);
}

function buildVerse(seg, jumpSelect) {
  const box = el("div", { class: "verse" });
  const btn = el("button", { class: "verse-toggle", "aria-expanded": "false", type: "button" });
  const ornament = el("span", { class: "ornament", text: "﴿ ﴾", "aria-hidden": "true" });
  const title = el("span", { class: "vt-title", text: "عرض الآية الكريمة" });
  const ref = el("span", { class: "vt-ref", text: seg.ref || "الآية" });
  const chevron = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  chevron.setAttribute("viewBox", "0 0 24 24");
  chevron.setAttribute("width", "16"); chevron.setAttribute("height", "16");
  chevron.setAttribute("class", "chevron"); chevron.setAttribute("aria-hidden", "true");
  const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
  path.setAttribute("d", "M6 9l6 6 6-6");
  path.setAttribute("fill", "none"); path.setAttribute("stroke", "currentColor");
  path.setAttribute("stroke-width", "2"); path.setAttribute("stroke-linecap", "round"); path.setAttribute("stroke-linejoin", "round");
  chevron.append(path);
  btn.append(ornament, title, ref, chevron);

  const body = el("div", { class: "verse-body" });
  const inner = el("div", { class: "verse-body-inner" });
  inner.append(
    el("p", { class: "verse-text", text: seg.text }),
    el("div", { class: "verse-ref", text: seg.ref ? `[${seg.ref}]` : "" })
  );
  body.append(inner);
  box.append(btn, body);

  const toggle = () => {
    const open = box.classList.toggle("open");
    btn.setAttribute("aria-expanded", String(open));
    title.textContent = open ? "إخفاء الآية" : "عرض الآية الكريمة";
  };
  btn.addEventListener("click", toggle);

  // خيار في قائمة «انتقل إلى آية»
  const opt = el("option", { value: String(jumpSelect.options.length), text: seg.ref || "آية" });
  jumpSelect.append(opt);
  box.dataset.jumpIndex = String(jumpSelect.options.length - 1);
  return box;
}

/* ---------- التحكم ---------- */

function bindControls() {
  $("#autoScroll").addEventListener("change", e => {
    autoScroll = e.target.checked;
    if (autoScroll && currentIdx >= 0) scrollToSegment(timedSegs[currentIdx]);
  });

  const tvBtn = $("#toggleVerses");
  tvBtn.addEventListener("click", () => {
    versesOpen = !versesOpen;
    document.querySelectorAll(".verse").forEach(v => {
      v.classList.toggle("open", versesOpen);
      const b = v.querySelector(".verse-toggle");
      b.setAttribute("aria-expanded", String(versesOpen));
      b.querySelector(".vt-title").textContent = versesOpen ? "إخفاء الآية" : "عرض الآية الكريمة";
    });
    tvBtn.setAttribute("aria-expanded", String(versesOpen));
    tvBtn.querySelector("span:last-child").textContent = versesOpen ? "طيّ كل الآيات" : "توسيع كل الآيات";
  });

  // النقر على الجمل/الكلمات
  $("#transcript").addEventListener("click", e => {
    const w = e.target.closest(".w");
    if (w) { seekTo(Number(w.dataset.start)); return; }
    const seg = e.target.closest(".seg");
    if (seg) seekTo(Number(seg.dataset.start));
  });
  $("#transcript").addEventListener("keydown", e => {
    if (e.key === "Enter" && e.target.classList.contains("seg")) seekTo(Number(e.target.dataset.start));
  });

  // الانتقال إلى آية
  $("#jumpSelect").addEventListener("change", e => {
    if (e.target.value === "") return;
    const idx = Number(e.target.value);
    if (!Number.isFinite(idx)) return;
    const target = document.querySelector(`.verse[data-jump-index="${idx}"]`);
    if (target) {
      if (!target.classList.contains("open")) target.querySelector(".verse-toggle").click();
      target.scrollIntoView({ behavior: prefersReducedMotion() ? "auto" : "smooth", block: "center" });
    }
  });

  // شريط التقدم
  const bar = $("#progressBar");
  const seekFromEvent = e => {
    const rect = bar.getBoundingClientRect();
    const x = (e.touches ? e.touches[0].clientX : e.clientX) - rect.left;
    const frac = Math.min(1, Math.max(0, 1 - x / rect.width));   // RTL: الامتلاء من اليمين
    seekTo(frac * totalDuration());
  };
  bar.addEventListener("pointerdown", seekFromEvent);
  bar.addEventListener("keydown", e => {
    const step = totalDuration() * 0.02;
    if (e.key === "ArrowLeft") { seekTo(getTime() - step); e.preventDefault(); }
    if (e.key === "ArrowRight") { seekTo(getTime() + step); e.preventDefault(); }
  });

  // رصد تمرير المستخدم
  const mark = () => { userScrolledAt = Date.now(); };
  window.addEventListener("wheel", mark, { passive: true });
  window.addEventListener("touchstart", mark, { passive: true });
  window.addEventListener("keydown", e => {
    if (["ArrowUp", "ArrowDown", "PageUp", "PageDown", "Home", "End"].includes(e.key)) mark();
  });

  // الزر العائم
  $("#followFab").addEventListener("click", () => {
    userScrolledAt = 0;
    if (currentIdx >= 0) scrollToSegment(timedSegs[currentIdx]);
  });

  // التبديل صوت/فيديو
  $("#tabVideo").addEventListener("click", () => switchMode("video"));
  $("#tabAudio").addEventListener("click", () => switchMode("audio"));

  // لوحة المفاتيح
  window.addEventListener("keydown", e => {
    if (e.target.matches("input, select, textarea, button, a[href]")) return;
    if (e.code === "Space") { togglePlay(); e.preventDefault(); }
    else if (e.key === "ArrowRight" || e.key === "ArrowLeft") {
      // في RTL: السهم الأيسر رجوع واليمين تقدّم؟ نعتمد المعيار الزمني: يمين=+5 ث يسار=−5 ث
      seekTo(getTime() + (e.key === "ArrowRight" ? 5 : -5));
      e.preventDefault();
    }
  });

  // حفظ الموضع عند مغادرة الصفحة
  window.addEventListener("pagehide", () => { if (!ended) savePosition(lecId, getTime()); });
}

function prefersReducedMotion() {
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

function scrollToSegment(seg) {
  seg.el.scrollIntoView({ behavior: prefersReducedMotion() ? "auto" : "smooth", block: "center" });
}

/* ---------- المشغل ---------- */

function totalDuration() {
  if (mode === "audio") {
    const d = $("#audioEl").duration;
    return Number.isFinite(d) ? d : (lecData.duration || 0);
  }
  return lecData.duration || 0;
}
function getTime() {
  if (mode === "audio") return $("#audioEl").currentTime || 0;
  if (ytReady && ytPlayer && typeof ytPlayer.getCurrentTime === "function") {
    try { return ytPlayer.getCurrentTime() || 0; } catch (_) { return 0; }
  }
  return 0;
}
function seekTo(t) {
  if (mode === "audio") { $("#audioEl").currentTime = Math.max(0, t); return; }
  if (ytReady && ytPlayer && typeof ytPlayer.seekTo === "function") ytPlayer.seekTo(Math.max(0, t), true);
}
function togglePlay() {
  if (mode === "audio") {
    const a = $("#audioEl");
    if (a.paused) a.play().catch(() => {}); else a.pause();
    return;
  }
  if (!ytReady || !ytPlayer) return;
  try {
    const state = ytPlayer.getPlayerState();
    if (state === 1) ytPlayer.pauseVideo(); else ytPlayer.playVideo();
  } catch (_) {}
}
function switchMode(next) {
  if (next === mode) return;
  const t = getTime();
  mode = next;
  $("#tabVideo").setAttribute("aria-selected", String(mode === "video"));
  $("#tabAudio").setAttribute("aria-selected", String(mode === "audio"));
  $("#videoPane").hidden = mode !== "video";
  $("#audioPane").hidden = mode !== "audio";
  // إيقاف/مزامنة
  if (mode === "audio") {
    if (ytReady && ytPlayer && ytPlayer.pauseVideo) { try { ytPlayer.pauseVideo(); } catch (_) {} }
    const a = $("#audioEl");
    a.currentTime = t;
  } else {
    $("#audioEl").pause();
    if (ytReady && ytPlayer && ytPlayer.seekTo) { try { ytPlayer.seekTo(t, true); } catch (_) {} }
  }
}

function setupYouTube() {
  // يُستدعى من سكربت iframe_api عند الجاهزية (انظر الأسفل) أو فورًا إن كان محمّلًا
  window.onYouTubeIframeAPIReady = () => createYtPlayer();
  if (window.YT && window.YT.Player) createYtPlayer();
}
function createYtPlayer() {
  if (ytPlayer) return;
  try {
    ytPlayer = new YT.Player("ytplayer", {
      videoId: lecData.youtube_id,
      playerVars: { rel: 0, modestbranding: 1, playsinline: 1 },
      events: {
        onReady: () => { ytReady = true; },
        onStateChange: e => {
          if (e.data === YT.PlayerState.ENDED) onEnded();
        },
        onError: () => switchMode("audio"),
      },
    });
  } catch (_) {
    switchMode("audio");
  }
}
function setupAudio() {
  const a = $("#audioEl");
  a.src = `audio/${lecId}.mp3`;
  a.addEventListener("ended", onEnded);
  a.addEventListener("play", () => { ended = false; $("#endCard").hidden = true; });
}

/* ---------- المزامنة ---------- */

function bindTicker() {
  setInterval(tick, 200);
}

function tick() {
  const t = getTime();
  const dur = totalDuration();
  $("#timeCur").textContent = fmtTime(t);
  $("#timeDur").textContent = fmtTime(dur);
  const pct = dur > 0 ? Math.min(100, (t / dur) * 100) : 0;
  $("#progressFill").style.width = pct + "%";
  $("#progressBar").setAttribute("aria-valuenow", String(Math.round(pct)));

  // احفظ الموضع كل 5 ثوانٍ
  const now = Date.now();
  if (now - saveTimer > 5000 && t > 0 && !ended) { saveTimer = now; savePosition(lecId, t); }

  updateHighlight(t);
}

function updateHighlight(t) {
  // تقدّم المؤشر على المقاطع
  let idx = -1;
  for (let i = 0; i < timedSegs.length; i++) {
    if (t >= timedSegs[i].start && t < timedSegs[i].end) { idx = i; break; }
    if (t >= timedSegs[i].end) idx = i;
  }
  if (idx !== currentIdx) {
    if (currentIdx >= 0) timedSegs[currentIdx].el.classList.remove("active");
    if (idx >= 0) {
      timedSegs[idx].el.classList.add("active");
      // تمرير تلقائي إن لم يتدخل المستخدم مؤخرًا
      const idle = Date.now() - userScrolledAt > 2500;
      if (autoScroll && idle && !document.hidden) scrollToSegment(timedSegs[idx]);
    }
    currentIdx = idx;
  }
  // كلمات المقطع الحالي
  if (idx >= 0) {
    for (const w of timedSegs[idx].words) {
      const spoken = t >= w.end;
      const current = t >= w.start && t < w.end;
      if (spoken) w.el.classList.add("spoken"); else w.el.classList.remove("spoken");
      w.el.classList.toggle("current", current);
    }
  }
  // الزر العائم
  const fab = $("#followFab");
  if (currentIdx >= 0) {
    const r = timedSegs[currentIdx].el.getBoundingClientRect();
    const visible = r.top < window.innerHeight * 0.75 && r.bottom > window.innerHeight * 0.25;
    fab.classList.toggle("show", !visible && !document.hidden);
  } else {
    fab.classList.remove("show");
  }
}

function onEnded() {
  ended = true;
  clearPosition(lecId);
  $("#endCard").hidden = false;
  $("#endCard").scrollIntoView({ behavior: "smooth", block: "center" });
}

/* ---------- المتابعة من موضع سابق ---------- */

function setupResume() {
  const pos = loadPosition(lecId);
  const dur = lecData.duration || 0;
  if (pos > 30 && pos < dur - 30) {
    const toast = $("#resumeToast");
    toast.innerHTML = "";
    toast.append(
      el("span", { text: `توقفتَ عند ${fmtTime(pos)} — متابعة؟` }),
      el("button", { class: "primary", text: "متابعة", onclick: () => { seekTo(pos); toast.hidden = true; } }),
      el("button", { class: "ghost", text: "من البداية", onclick: () => { clearPosition(lecId); toast.hidden = true; } })
    );
    toast.hidden = false;
  }
}

/* ---------- الأخطاء ---------- */

function showFatal(err) {
  console.error(err);
  const host = $("#transcript");
  const box = el("div", { class: "end-card" }, [
    el("h3", { text: "تعذر تحميل هذا المجلس" }),
    el("p", { text: String(err.message || err) }),
    el("a", { class: "btn btn-gold", href: "index.html", text: "← فهرس المجالس" }),
  ]);
  host.replaceChildren(box);
}

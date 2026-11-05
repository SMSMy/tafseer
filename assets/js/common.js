/* أدوات مشتركة بين الصفحات */
"use strict";

const AR_DIGITS = "٠١٢٣٤٥٦٧٨٩";
/** تحويل الأرقام اللاتينية إلى مشرقية */
function toArabicDigits(s) {
  return String(s).replace(/[0-9]/g, d => AR_DIGITS[+d]);
}

/** ثوانٍ → h:mm:ss بأرقام مشرقية (تُسقط الساعات إن كانت صفرًا) */
function fmtTime(sec) {
  if (!Number.isFinite(sec) || sec < 0) sec = 0;
  const s = Math.floor(sec % 60);
  const m = Math.floor((sec / 60) % 60);
  const h = Math.floor(sec / 3600);
  const pad = n => String(n).padStart(2, "0");
  return toArabicDigits(h > 0 ? `${h}:${pad(m)}:${pad(s)}` : `${m}:${pad(s)}`);
}

/** دقائق → «٤١ دقيقة» بأرقام مشرقية */
function fmtMinutes(sec) {
  const m = Math.round((sec || 0) / 60);
  return toArabicDigits(m) + " دقيقة";
}

/** استنتاج نطاق الآيات من عنوان المجلس: «من الآية 19 إلى الآية 38» → «١٩–٣٨» */
function ayahRange(title) {
  const m = title.match(/([0-9]+)\s*إلى\s*الآية\s*([0-9]+|نهاية)/);
  if (!m) return null;
  return toArabicDigits(m[1]) + "–" + (m[2] === "نهاية" ? "نهاية السورة" : toArabicDigits(m[2]));
}

/** جلب index.json مع معامل مقاومة للتخزين المؤقت */
async function fetchJSON(url) {
  const res = await fetch(url, { cache: "no-cache" });
  if (!res.ok) throw new Error(`تعذر تحميل ${url} (${res.status})`);
  return res.json();
}

/** تحميل index.json ثم ملف المجلس */
async function loadIndex() {
  return fetchJSON("index.json");
}

/** مفتاح التخزين المحلي لموضع كل مجلس */
function progressKey(id) { return `tafseer-anam:${id}`; }

function savePosition(id, seconds) {
  try { localStorage.setItem(progressKey(id), String(Math.floor(seconds))); } catch (_) {}
}
function loadPosition(id) {
  try {
    const v = Number(localStorage.getItem(progressKey(id)));
    return Number.isFinite(v) && v > 0 ? v : 0;
  } catch (_) { return 0; }
}
function clearPosition(id) {
  try { localStorage.removeItem(progressKey(id)); } catch (_) {}
}

/** إنشاء عنصر بخصائص مختصرة */
function el(tag, attrs = {}, children = []) {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === "class") node.className = v;
    else if (k === "text") node.textContent = v;
    else if (k.startsWith("on") && typeof v === "function") node.addEventListener(k.slice(2), v);
    else node.setAttribute(k, v);
  }
  for (const child of [].concat(children)) node.append(child);
  return node;
}

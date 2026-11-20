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

/** جلب ملفات البيانات — قائمة سماح صارمة: فهرس الموقع أو ملف مجلس فقط */
async function fetchJSON(url) {
  if (!/^(index\.json|data\/[0-9]{3}\.json)$/.test(url)) {
    throw new Error("مسار بيانات غير مسموح: " + url);
  }
  const res = await fetch(url, { cache: "no-cache" });
  if (!res.ok) throw new Error(`تعذر تحميل ${url} (${res.status})`);
  return res.json();
}

/** تحميل index.json */
async function loadIndex() {
  return fetchJSON("index.json");
}

/** تحميل ملف مجلس — الجلب هنا مباشرة بعد قائمة السماح (بلا وساطة) */
async function loadLectureData(entry) {
  if (!/^(data\/[0-9]{3}\.json)$/.test(entry.data)) {
    throw new Error("مسار بيانات غير مسموح: " + entry.data);
  }
  const res = await fetch(entry.data, { cache: "no-cache" });
  if (!res.ok) throw new Error(`تعذر تحميل ${entry.data} (${res.status})`);
  return res.json();
}

/** البحث عن مجلس في كل السور: يعيد {sura, lecture} أو null */
function findLecture(idx, id) {
  for (const s of (idx.suras || [])) {
    const lec = (s.lectures || []).find(x => x.id === id);
    if (lec) return { sura: s, lecture: lec };
  }
  return null;
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

/* فهرس مجالس السورة الحالية (يُحدَّد من data-sura على <body>) */
"use strict";

(async function () {
  const grid = document.getElementById("cards");
  const suraSlug = document.body.dataset.sura;
  try {
    const idx = await loadIndex();
    const sura = (idx.suras || []).find(s => s.slug === suraSlug);
    if (!sura) throw new Error("سورة غير معروفة: " + suraSlug);
    const frag = document.createDocumentFragment();
    for (const lec of sura.lectures) {
      const range = ayahRange(lec.title);
      const card = el("a", { class: "card", href: `watch.html?id=${lec.id}`, "aria-label": "استمع إلى " + lec.title });
      const num = el("div", { class: "num", text: "المجلس " + toArabicDigits(lec.id) });
      const h3 = el("h3", { text: lec.title });
      const speaker = el("div", { class: "speaker", text: lec.speaker });
      const meta = el("div", { class: "meta" });
      meta.append(
        el("span", { class: "chip gold", text: "⏱ " + fmtTime(lec.duration) }),
        range ? el("span", { class: "chip", text: "الآيات " + range }) : document.createDocumentFragment(),
        el("span", { class: "play-hint", text: "استمع الآن ←" })
      );
      card.append(num, h3, speaker, meta);
      frag.append(card);
    }
    grid.append(frag);
  } catch (err) {
    grid.append(el("p", { text: "تعذر تحميل فهرس المجالس. تأكد أن index.json موجود بجانب الصفحة.", style: "color:#a33" }));
    console.error(err);
  }
})();

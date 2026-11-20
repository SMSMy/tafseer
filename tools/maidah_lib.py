# -*- coding: utf-8 -*-
"""مكتبة مسار سورة المائدة: تطبيع، مطابقة التلاوات، تجزئة، بناء المهذب وdata.
كل قراءة الملفات بمسارات مركّبة حرفيًا؛ الكتابة في سكربتات الاستدعاء فقط."""
import json
import re

REPO = "C:/Code-backup/tafseer-al-anam"
SURA_NAME = "المائدة"
SURA_NUM = 5

ORDINALS = ["الأول", "الثاني", "الثالث", "الرابع", "الخامس", "السادس",
            "السابع", "الثامن", "التاسع", "العاشر", "الحادي عشر"]

# تصحيحات معجمية على مستوى الكلمة (أخطاء تفريغ متكررة فقط)
LEXICON = {
    "الإترجة": "الأترجة",
    "الإتروج": "الأترجة",
    "الأتروج": "الأترجة",
    "المائة": "المائدة",
    "المائئدة": "المائدة",
    "المائئده": "المائدة",
}

AR_DIGITS = "٠١٢٣٤٥٦٧٨٩"

DIAC = re.compile(r"[\u0610-\u061A\u064B-\u065F\u0670\u06D6-\u06ED\u06DC\u08D3-\u08FF]")
PUNCT_END = (".", "؟", "!", "؟؟", "..")


def normalize(s):
    s = s.replace("\u0670", "ا")  # الألف الخنجرية تنطق ألفًا
    s = DIAC.sub("", s)
    s = s.replace("\u0640", "")  # المدّة
    s = s.replace("ٱ", "ا").replace("أ", "ا").replace("إ", "ا").replace("آ", "ا")
    s = s.replace("ى", "ي").replace("ة", "ه").replace("ؤ", "و").replace("ئ", "ي")
    s = s.replace("ء", "")
    s = "".join(c for c in s if __import__("unicodedata").category(c) not in ("Mn", "Me", "Cf"))
    return s


def edit1(a, b):
    """هل يفصل بين النصين تعديل واحد (إدراج/حذف/استبدال)?"""
    if a == b:
        return True
    la, lb = len(a), len(b)
    if abs(la - lb) > 1:
        return False
    if la == lb:
        return sum(1 for x, y in zip(a, b) if x != y) <= 1
    if la > lb:
        a, b, la, lb = b, a, lb, la
    i = 0
    while i < la and a[i] == b[i]:
        i += 1
    return a[i:] == b[i + 1:]


def token_match(a, b):
    """مطابقة توكن متسامحة: تطابق تام أو تعديل واحد لكلمات طويلة."""
    if a == b:
        return True
    if len(a) >= 3 and len(b) >= 3:
        return edit1(a, b)
    return False


def to_arabic_digits(s):
    return "".join(AR_DIGITS[int(c)] if c.isdigit() else c for c in str(s))


def load_verses():
    """يعيد [{num:int, text:str}] نص الآيات العثماني لسورة المائدة (الترتيب التسلسلي)."""
    d = json.load(open(REPO + "/_media/maidah-uthmani.json", "r", encoding="utf-8"))
    out = []
    for i, v in enumerate(d["verses"]):
        out.append({"num": i + 1, "text": v["text_uthmani"].strip()})
    return out


def core_word(w):
    """نواة الكلمة بدون ترقيم لتطبيق المعجم."""
    return w.strip("،.؟!؛:«»()[]\"'…" + "\u200f\u200e")


def apply_lexicon(words):
    for w in words:
        c = core_word(w["text"])
        if c in LEXICON:
            w["text"] = w["text"].replace(c, LEXICON[c])
    return words


def find_recitations(tokens, verses, min_words=10):
    """مطابقات تلاوة متجاورة غير متداخلة: [(i0, i1, verse_num, matched)]
    توكن فارغ في ntok يعني شفافية: يتجاوز دون أكل ميزانية التخطي."""
    n = len(tokens)
    raw_ntok = [normalize(t["text"]) for t in tokens]
    # دمج «يا + أيها» المنطوقة في كلمتين متجاورتين: تُطابق كلمة عثمانية واحدة (يَـٰٓأَيُّهَا)
    ntok = []
    i2 = 0
    while i2 < len(raw_ntok):
        if raw_ntok[i2] == "يا" and i2 + 1 < len(raw_ntok) and raw_ntok[i2 + 1] == "ايها":
            ntok.append("")
            ntok.append("ايها")
            i2 += 2
        else:
            ntok.append(raw_ntok[i2])
            i2 += 1
    vtok = []
    for v in verses:
        vt = []
        for x in v["text"].split():
            nx = normalize(x)
            if nx == "ياايها":
                nx = "ايها"
            if nx:
                vt.append(nx)
        vtok.append(vt)
    matches = []
    for i in range(n):
        best = None
        for vi, vt in enumerate(vtok):
            j = 0
            k = i
            skips = 0
            while k < n and j < len(vt):
                if ntok[k] == "":
                    k += 1
                    continue
                if token_match(ntok[k], vt[j]):
                    j += 1
                    k += 1
                else:
                    skips += 1
                    if skips > 3:
                        break
                    k += 1
            if j >= min_words and (best is None or j > best[0]):
                best = (j, vi, k)
        if best:
            matches.append((i, best[2], verses[best[1]]["num"], best[0]))
    matches.sort(key=lambda x: -(x[1] - x[0]))
    chosen = []
    for s, e, num, m in matches:
        if any(not (e <= s2 or s >= e2) for s2, e2, _, _ in chosen):
            continue
        chosen.append((s, e, num, m))
    chosen.sort()
    return chosen


def split_sentences(tokens):
    """تقسيم تدفق الكلمات إلى جمل حسب علامات النهاية المرفقة بالكلمات."""
    sents = []
    cur = []
    for t in tokens:
        cur.append(t)
        txt = t["text"].strip()
        if txt.endswith(PUNCT_END):
            sents.append(cur)
            cur = []
    if cur:
        if sents and len(cur) <= 2:
            sents[-1].extend(cur)
        else:
            sents.append(cur)
    return sents


def cap_sentence(sent, max_words=30):
    """تقسيم الجملة الطويلة عند أقرب فاصلة للمنتصف."""
    if len(sent) <= max_words:
        return [sent]
    commas = [i for i, t in enumerate(sent) if t["text"].strip().endswith("،")]
    if not commas:
        return [sent]
    mid = len(sent) // 2
    best = min(commas, key=lambda i: abs(i - mid))
    if best <= 3 or best >= len(sent) - 3:
        return [sent]
    return [sent[: best + 1], sent[best + 1 :]]


def sentence_text(sent):
    return " ".join(t["text"] for t in sent).strip()


def lecture_title(cfg_lec):
    frm = cfg_lec["verse_from"]
    to = cfg_lec["verse_to"]
    if to is None:
        return "تفسير سورة المائدة من الآية %d إلى نهاية السورة" % frm
    return "تفسير سورة المائدة من الآية %d إلى الآية %d" % (frm, to)


def build_flow(words, verses, min_words=10):
    """من كلمات Scribe إلى بنية: فقرات منطوقة + كتل آيات.
    يعيد (blocks, timed_words_used)
    blocks: [("text", [sentence,...]), ("verse", {num,text,ref})]"""
    words = apply_lexicon(words)
    matches = find_recitations(words, verses, min_words)
    match_at = {}
    seen_nums = set()
    for s, e, num, m in matches:
        if num in seen_nums:
            continue  # أول تلاوة للآية فقط داخل المجلس
        seen_nums.add(num)
        match_at[s] = (s, e, num)
    blocks = []
    para_sents = []
    i = 0
    n = len(words)
    while i < n:
        if i in match_at:
            s, e, num = match_at[i]
            v = next(v for v in verses if v["num"] == num)
            if para_sents:
                blocks.append(("text", para_sents))
                para_sents = []
            blocks.append(("verse", {"num": num, "text": "﴿ " + v["text"] + " ﴾"}))
            i = e
            continue
        # جملة واحدة على الأقل حتى أول مطابقة
        j = i
        while j < n and j not in match_at:
            j += 1
        chunk = words[i:j]
        sents = []
        for sent in split_sentences(chunk):
            sents.extend(cap_sentence(sent))
        para_sents.extend(sents)
        i = j
    if para_sents:
        blocks.append(("text", para_sents))
    return blocks


def group_paragraphs(sents, max_sents=5):
    """تجميع الجمل في فقرات للعرض النصي."""
    paras = []
    cur = []
    for s in sents:
        cur.append(s)
        if len(cur) >= max_sents or s[-1]["text"].strip().endswith(("؟", "!")):
            paras.append(cur)
            cur = []
    if cur:
        if paras and len(cur) <= 1:
            paras[-1].extend(cur)
        else:
            paras.append(cur)
    return paras


def render_txt(lid, title, speaker, blocks):
    """صياغة النص المهذب بصيغة مجلد «نصوص» المرجعية."""
    ordw = ORDINALS[int(lid) - 60]
    H1 = "=" * 80
    H2 = "═" * 80
    H3 = "-" * 80
    lines = []
    lines.append(H1)
    lines.append("❖ دورة الأترجة القرآنية • المجالس التفسيرية ❖")
    lines.append("تفسير سورة المائدة")
    lines.append("المجلس %s : %s" % (ordw, title.replace("تفسير سورة المائدة ", "")))
    lines.append("فضيلة الشيخ الدكتور / " + speaker)
    lines.append(H1)
    lines.append("")
    lines.append(H2)
    lines.append("■ المقدمة والمدخل إلى موضوع المجلس:")
    lines.append(H2)
    lines.append("")
    first = True
    for kind, payload in blocks:
        if kind == "text":
            for para in group_paragraphs(payload):
                if not first:
                    lines.append("")
                lines.append(sentence_text([t for s in para for t in s]))
                first = False
        else:
            lines.append("")
            lines.append(H3)
            lines.append("◈ تفسير الآية الكريمة رقم (%d):" % payload["num"])
            lines.append("﴿ %s ﴾ [%s: %s]" % (payload["text"][2:-2].strip(), SURA_NAME, to_arabic_digits(payload["num"])))
            lines.append(H3)
            lines.append("")
            first = True
    return "\n".join(lines).rstrip() + "\n"


def segments_from_blocks(blocks):
    """بناء segments بصيغة data: heading + text موقوت + quran ثابت."""
    segs = []
    segs.append({"type": "heading", "timed": False, "text": "المقدمة والمدخل إلى موضوع المجلس"})
    sid = 1
    for kind, payload in blocks:
        if kind == "verse":
            segs.append({"type": "heading", "timed": False,
                         "text": "تفسير الآية الكريمة رقم (%d)" % payload["num"]})
            segs.append({"type": "quran", "timed": False,
                         "ref": "%s %s" % (SURA_NAME, to_arabic_digits(payload["num"])),
                         "text": payload["text"]})
            continue
        for sent in payload:
            words_out = []
            for t in sent:
                words_out.append({"text": t["text"], "start": t.get("start"), "end": t.get("end")})
            seg = {"id": sid, "type": "text", "timed": True,
                   "start": words_out[0]["start"], "end": words_out[-1]["end"],
                   "text": sentence_text(sent), "words": words_out}
            if seg["start"] is None or seg["end"] is None:
                seg["timed"] = False
                seg.pop("start", None)
                seg.pop("end", None)
                seg.pop("words", None)
            segs.append(seg)
            sid += 1
    return segs


def align_sentences(sents, scribe_words, state=None):
    """محاذاة جمل النص المنقح مع كلمات Scribe بمؤشر مشترك بين الكتل.
    state: {'ptr','total','matched'} — يُنشأ إن لم يُمرَّر. يعيد (sents, state)."""
    if state is None:
        state = {"ptr": 0, "total": 0, "matched": 0}
    sw = state.get("sw")
    if sw is None:
        sw = [(normalize(core_word(w["text"])), w["start"], w["end"]) for w in scribe_words]
        state["sw"] = sw
    nsw = len(sw)
    ptr = state["ptr"]
    for sent in sents:
        for t in sent:
            state["total"] += 1
            tn = normalize(core_word(t["text"]))
            found = -1
            # أقرب مطابقة متسامحة من الموضع الحالي (التسلسلي هو الصحيح)
            for k in range(ptr, min(nsw, ptr + 40)):
                if token_match(sw[k][0], tn):
                    found = k
                    break
            if found >= 0:
                state["matched"] += 1
                t["start"] = sw[found][1]
                t["end"] = sw[found][2]
                ptr = found + 1
            else:
                t["start"] = None
                t["end"] = None
    state["ptr"] = ptr
    # ملء الكلمات غير المطابقة خطيًا بين أقرب مطابقتين
    flat = [t for s in sents for t in s]
    known = [(i, t["start"], t["end"]) for i, t in enumerate(flat) if t["start"] is not None]
    for i, t in enumerate(flat):
        if t["start"] is None:
            prev = next(((j, a, b) for j, a, b in reversed(known) if j < i), None)
            nxt = next(((j, a, b) for j, a, b in known if j > i), None)
            if prev and nxt:
                frac = (i - prev[0]) / max(1, nxt[0] - prev[0])
                t["start"] = prev[1] + frac * (nxt[1] - prev[1])
                t["end"] = prev[2] + frac * (nxt[2] - prev[2])
            elif prev:
                t["start"] = prev[2]
                t["end"] = prev[2] + 0.3
            elif nxt:
                t["start"] = max(0, nxt[1] - 0.3)
                t["end"] = nxt[1]
            else:
                t["start"] = 0.0
                t["end"] = 0.3
    return sents, state


def parse_txt(txt):
    """قراءة النص المهذب وإعادة البنية: (blocks) نفس بنية build_flow.
    يُتجاهل كل شيء قبل سطر «■ ...:» (رأس الملف)، وأسطر «■» فواصل أقسام تُهمل."""
    blocks = []
    lines = txt.split("\n")
    i = 0
    cur_paras = []
    started = False
    while i < len(lines):
        ln = lines[i].rstrip()
        if ln.startswith("■ "):
            started = True
            i += 1
            continue
        if not started:
            i += 1
            continue
        if ln.startswith("◈ تفسير الآية الكريمة رقم ("):
            m = re.search(r"رقم \((\d+)\)", ln)
            num = int(m.group(1))
            verse_line = ""
            j = i + 1
            while j < len(lines) and not lines[j].startswith("-"):
                if "﴿" in lines[j]:
                    verse_line = lines[j]
                j += 1
            mt = re.search(r"﴿ (.+?) ﴾", verse_line)
            if cur_paras:
                blocks.append(("text", cur_paras))
                cur_paras = []
            blocks.append(("verse", {"num": num, "text": "﴿ " + mt.group(1) + " ﴾"}))
            i = j
            continue
        if ln and not ln.startswith(("═", "=", "-", "❖", "◈", "﴿", "[")):
            cur_paras.append(ln)
        i += 1
    if cur_paras:
        blocks.append(("text", cur_paras))
    return blocks


def build_segments_from_txt(txt, scribe_words, start_ptr=0):
    """من النص المنقح (بعد المراجعة) إلى segments موقوتة + نسبة المحاذاة.
    المحاذاة عالمية عبر difflib (مقاومة للحذف/الإضافة/الانترو ولا تنجراف)."""
    import difflib
    blocks = parse_txt(txt)
    segs = [{"type": "heading", "timed": False, "text": "المقدمة والمدخل إلى موضوع المجلس"}]
    sid = 1
    # كل جمل النص متسلسلة مع فهرس كلماتها المسطح
    all_sents = []
    for kind, payload in blocks:
        if kind == "verse":
            all_sents.append(("verse", payload, None))
            continue
        sents = []
        for para in payload:
            words = [{"text": wt, "start": None, "end": None} for wt in para.split()]
            if not words:
                continue
            for sent in split_sentences(words):
                sents.extend(cap_sentence(sent))
        for sent in sents:
            all_sents.append(("sent", None, sent))
    # التسلسل المسطح للمطابقة
    txt_norms = []
    txt_owner = []  # (index في all_sents، index داخل الجملة)
    for si, (kind, payload, sent) in enumerate(all_sents):
        if kind != "sent":
            continue
        for wi, t in enumerate(sent):
            txt_norms.append(normalize(core_word(t["text"])))
            txt_owner.append((si, wi))
    sw_norms = [normalize(core_word(w["text"])) for w in scribe_words]
    sm = difflib.SequenceMatcher(None, txt_norms, sw_norms, autojunk=False)
    matched = 0
    total = len(txt_norms)
    for blk in sm.get_matching_blocks():
        for off in range(blk.size):
            si, wi = txt_owner[blk.a + off]
            w = scribe_words[blk.b + off]
            t = all_sents[si][2][wi]
            t["start"] = w["start"]
            t["end"] = w["end"]
            matched += 1
    # ملء الكلمات غير المطابقة خطيًا بين أقرب مطابقتين
    flat = [t for kind, _, sent in all_sents if kind == "sent" for t in sent]
    known = [(i, t["start"], t["end"]) for i, t in enumerate(flat) if t["start"] is not None]
    for i, t in enumerate(flat):
        if t["start"] is None:
            prev = next(((j, a, b) for j, a, b in reversed(known) if j < i), None)
            nxt = next(((j, a, b) for j, a, b in known if j > i), None)
            if prev and nxt:
                frac = (i - prev[0]) / max(1, nxt[0] - prev[0])
                t["start"] = prev[1] + frac * (nxt[1] - prev[1])
                t["end"] = prev[2] + frac * (nxt[2] - prev[2])
            elif prev:
                t["start"] = prev[2]
                t["end"] = prev[2] + 0.3
            elif nxt:
                t["start"] = max(0, nxt[1] - 0.3)
                t["end"] = nxt[1]
            else:
                t["start"] = 0.0
                t["end"] = 0.3
    # بناء المقاطع
    for kind, payload, sent in all_sents:
        if kind == "verse":
            segs.append({"type": "heading", "timed": False,
                         "text": "تفسير الآية الكريمة رقم (%d)" % payload["num"]})
            segs.append({"type": "quran", "timed": False,
                         "ref": "%s %s" % (SURA_NAME, to_arabic_digits(payload["num"])),
                         "text": payload["text"]})
            continue
        words_out = [{"text": t["text"], "start": round(t["start"], 2), "end": round(t["end"], 2)} for t in sent]
        seg = {"id": sid, "type": "text", "timed": True,
               "start": words_out[0]["start"], "end": words_out[-1]["end"],
               "text": sentence_text(sent), "words": words_out}
        segs.append(seg)
        sid += 1
    r = matched / max(1, total)
    return segs, r


def make_data(lid, cfg_lec, duration, youtube_id, segments, source_editions):
    title = lecture_title(cfg_lec)
    yurl = "https://www.youtube.com/watch?v=" + youtube_id
    return {
        "id": lid,
        "title": title,
        "speaker": cfg_lec["speaker"],
        "series": "تفسير سورة المائدة",
        "channel": "دورة الأترجة القرآنية",
        "language": "ar",
        "duration": round(float(duration), 3),
        "youtube_id": youtube_id,
        "youtube_url": yurl,
        "embed_url": "https://www.youtube.com/embed/" + youtube_id,
        "source_editions": source_editions,
        "segments": segments,
    }

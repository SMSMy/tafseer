# -*- coding: utf-8 -*-
"""إعادة بناء data لمجلس واحد من النص المهذب/المنقح (stdin) مع المحاذاة الكلمية مع Scribe.
يطبع JSON إلى stdout (يُوجَّه إلى data/NNN.json).
الاستخدام: python tools/build_data.py 061 < texts/061.txt > data/061.json"""
import json
import re
import sys

sys.path.insert(0, "C:/Code-backup/tafseer-al-anam/tools")
import maidah_lib

REPO = "C:/Code-backup/tafseer-al-anam"


def main():
    lid = sys.argv[1] if len(sys.argv) > 1 else ""
    if not re.fullmatch(r"0(6[0-9]|70)", lid):
        print("bad lecture id", file=sys.stderr)
        sys.exit(2)
    cfg = json.load(open(REPO + "/tools/config.json", "r", encoding="utf-8"))
    lec = None
    for item in cfg["lectures"]:
        if item["id"] == lid:
            lec = item
            break
    if lec is None:
        print("lecture not in config", file=sys.stderr)
        sys.exit(1)
    raw = json.load(open(REPO + "/raw/" + lid + ".json", "r", encoding="utf-8"))
    txt = sys.stdin.read()
    if len(txt.strip()) < 100:
        print("empty text on stdin", file=sys.stderr)
        sys.exit(1)

    scribe_words = [w for w in raw["words"] if w.get("type") == "word"]

    # مرساة بداية الدرس: تخطي شارة الدورة في سلسلة التفريغ
    # الشهري يبدأ «بسم الله»، والخضيري يبدأ «إن الحمد لله نحمده»
    sw_norm = [maidah_lib.normalize(maidah_lib.core_word(w["text"])) for w in scribe_words]
    anchor_seq = ["بسم", "الله"] if "الشهري" in lec["speaker"] else ["ان", "الحمد", "لله", "نحمده"]
    anchor_seq_n = [maidah_lib.normalize(x) for x in anchor_seq]
    anchor = 0
    for k in range(len(sw_norm) - len(anchor_seq_n)):
        if sw_norm[k:k + len(anchor_seq_n)] == anchor_seq_n:
            anchor = k  # بداية التسلسل نفسها — أول كلمات الدرس تبقى في النص
            break

    segs, ratio = maidah_lib.build_segments_from_txt(txt, scribe_words, start_ptr=anchor)
    data = maidah_lib.make_data(lid, lec, raw.get("audio_duration_secs", lec["duration"]),
                                lec["youtube_id"], segs,
                                ["scribe_v2 (timestamps)", "scribe_polished + reviewed (text)"])
    json.dump(data, sys.stdout, ensure_ascii=False, indent=1)
    n_text = sum(1 for s in segs if s["type"] == "text")
    n_quran = sum(1 for s in segs if s["type"] == "quran")
    flag = "OK" if ratio >= 0.95 else "LOW"
    print("", file=sys.stderr)
    print("%s: align=%d%% [%s], text=%d quran=%d" % (lid, round(ratio * 100), flag, n_text, n_quran), file=sys.stderr)


if __name__ == "__main__":
    main()

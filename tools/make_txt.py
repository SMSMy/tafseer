# -*- coding: utf-8 -*-
"""بناء مسودة النص المهذب لمجلس واحد — يطبع TXT إلى stdout (يُوجَّه إلى texts/NNN.txt).
الاستخدام: python tools/make_txt.py 061 > texts/061.txt"""
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
        print("lecture not in config:", lid, file=sys.stderr)
        sys.exit(1)
    raw = json.load(open(REPO + "/raw/" + lid + ".json", "r", encoding="utf-8"))
    verses = maidah_lib.load_verses()

    words = [w for w in raw["words"] if w.get("type") == "word"]
    blocks = maidah_lib.build_flow(words, verses)
    title = maidah_lib.lecture_title(lec)
    txt = maidah_lib.render_txt(lid, title, lec["speaker"], blocks)
    sys.stdout.write(txt)


if __name__ == "__main__":
    main()

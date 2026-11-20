# -*- coding: utf-8 -*-
"""التحقق من كتل الآيات في data مقابل طبعة quran-uthmani — تقرير إلى stdout."""
import json
import re
import sys

sys.path.insert(0, "C:/Code-backup/tafseer-al-anam/tools")
import maidah_lib

REPO = "C:/Code-backup/tafseer-al-anam"
AR = "٠١٢٣٤٥٦٧٨٩"


def ar_to_int(s):
    return int("".join(str(AR.index(c)) for c in s))


verses = {v["num"]: v["text"] for v in maidah_lib.load_verses()}
total = ok = warn = bad = 0
details = []
for i in range(60, 71):
    d = json.load(open(REPO + "/data/%03d.json" % i, "r", encoding="utf-8"))
    for s in d["segments"]:
        if s.get("type") != "quran":
            continue
        total += 1
        num = ar_to_int(s["ref"].split()[1])
        inner = re.search(r"﴿ (.+?) ﴾", s["text"]).group(1)
        want = verses.get(num, "")
        a = maidah_lib.normalize(inner)
        b = maidah_lib.normalize(want)
        if a == b:
            ok += 1
        else:
            wa = set(a.split())
            wb = set(b.split())
            extra = sorted(wa - wb)
            missing = sorted(wb - wa)
            if not extra and not missing:
                warn += 1
                details.append("%s آية %d: فرق رسم فقط" % (d["id"], num))
            else:
                bad += 1
                details.append("%s آية %d: زائد=%s ناقص=%s" % (d["id"], num, extra[:4], missing[:4]))

print("كتل الآيات: %d | مطابقة تامة: %d | فرق رسم: %d | فروق جوهرية: %d" % (total, ok, warn, bad))
for x in details:
    print("  -", x)
sys.exit(0 if bad == 0 else 1)

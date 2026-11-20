# -*- coding: utf-8 -*-
"""جلب بيانات قائمة تشغيل سورة المائدة بالعناوين الدقيقة ومددها.
لا تكتب أي ملفات — تطبع JSON إلى stdout (يُوجَّه عبر shell إلى tools/config.json)."""
import json
import re
import subprocess
import sys

YT_DLP = "C:/yt-dlp/yt-dlp.exe"
PLAYLIST = "https://www.youtube.com/playlist?list=PLIJ8GEGgVY0R8Ctd_anLCbBzPgpvsIkTL"

SP_ALSHEHRI = "د. عبد الرحمن بن معاضة الشهري"
SP_ALKHUDAYRI = "د. محمد بن عبد العزيز الخضيري"


def norm_speaker(title):
    t = re.sub(r"\s+", " ", title)
    if re.search(r"Al-?Shehri|Mo.?adah|Mua.?dah|bin Ma|معاضة|الشهري|Abdulrahman|عبد الرحمن", t, re.I):
        return SP_ALSHEHRI
    if re.search(r"Al-?Khud|الخضيري|Muhammad bin|محمد بن", t, re.I):
        return SP_ALKHUDAYRI
    return None


def parse_range(title):
    """استخراج نطاق الآيات من العنوان. يعيد (من، إلى أو None لنهاية السورة)."""
    t = re.sub(r"\s+", "", title)
    m = re.search(r"[Vv]erses?(\d+)[-–](\d+)", t)
    if m:
        return int(m.group(1)), int(m.group(2))
    m = re.search(r"[Vv]erses?(\d+)\s*tos?\s*(\d+)", t, re.I)
    if m:
        return int(m.group(1)), int(m.group(2))
    if m := re.search(r"fromverse(\d+)totheendoftheSurah", t, re.I):
        return int(m.group(1)), None
    if m := re.search(r"fromverse(\d+)toverse(\d+)", t, re.I):
        return int(m.group(1)), int(m.group(2))
    if m := re.search(r"الآية(\d+).*?إلى.*?(\d+)", t):
        return int(m.group(1)), int(m.group(2))
    return None


def main():
    out = subprocess.run(
        [YT_DLP, "-J", "--flat-playlist", PLAYLIST],
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300,
    )
    if out.returncode != 0:
        print("yt-dlp -J failed:", out.stderr[-2000:], file=sys.stderr)
        sys.exit(1)
    pl = json.loads(out.stdout)
    entries = pl.get("entries", [])
    print("videos:", len(entries), file=sys.stderr)

    lectures = []
    for i, e in enumerate(entries):
        title = (e.get("title") or "").strip()
        spk = norm_speaker(title)
        rng = parse_range(title)
        if not spk or rng is None:
            print("  !! title not parsed:", repr(title), file=sys.stderr)
        lectures.append({
            "id": "%03d" % (60 + i),
            "youtube_id": e.get("id"),
            "title_raw": title,
            "speaker": spk,
            "verse_from": rng[0] if rng else None,
            "verse_to": rng[1] if rng else None,
            "duration": e.get("duration"),
        })

    config = {
        "playlist": PLAYLIST,
        "sura": {"number": 5, "name": "المائدة",
                 "url": "https://www.youtube.com/playlist?list=PLIJ8GEGgVY0R8Ctd_anLCbBzPgpvsIkTL"},
        "channel": "دورة الأترجة القرآنية",
        "quran_json": "_media/quran-uthmani.json",
        "lectures": lectures,
    }
    json.dump(config, sys.stdout, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()

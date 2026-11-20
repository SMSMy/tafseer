# -*- coding: utf-8 -*-
"""توليد index.json لكل السور — يطبع JSON إلى stdout (يُوجَّه إلى index.json).
الاستخدام: python tools/gen_index.py > index.json"""
import datetime
import json
import sys

REPO = "C:/Code-backup/tafseer-al-anam"


def lec_entry(d):
    return {
        "id": d["id"],
        "title": d["title"],
        "speaker": d["speaker"],
        "youtube_id": d["youtube_id"],
        "youtube_url": d["youtube_url"],
        "duration": d["duration"],
        "data": "data/NNN.json".replace("NNN", d["id"]),
    }


def main():
    maidah = []
    for i in range(60, 71):
        d = json.load(open(REPO + "/data/" + ("%03d" % i) + ".json", "r", encoding="utf-8"))
        maidah.append(lec_entry(d))
    anam = []
    for i in range(71, 83):
        d = json.load(open(REPO + "/data/" + ("%03d" % i) + ".json", "r", encoding="utf-8"))
        anam.append(lec_entry(d))
    index = {
        "site": "المجالس التفسيرية",
        "channel": "دورة الأترجة القرآنية",
        "channel_url": "https://www.youtube.com/results?search_query=%D8%AF%D9%88%D8%B1%D8%A9+%D8%A7%D9%84%D8%A3%D8%AA%D8%B1%D8%AC%D8%A9+%D8%A7%D9%84%D9%82%D8%B1%D8%A2%D9%86%D9%8A%D8%A9",
        "generated": datetime.date.today().isoformat(),
        "suras": [
            {"slug": "maidah", "number": 5, "name": "المائدة", "page": "maidah.html", "lectures": maidah},
            {"slug": "anam", "number": 6, "name": "الأنعام", "page": "anam.html", "lectures": anam},
        ],
    }
    json.dump(index, sys.stdout, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()

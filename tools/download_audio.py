# -*- coding: utf-8 -*-
"""تنزيل صوت محاضرات المائدة من يوتيوب إلى _media/src/NNN.<ext>.
لا تكتب بايثون أي ملف — التنزيل نفسه عبر yt-dlp."""
import json
import os
import subprocess
import sys

REPO = "C:/Code-backup/tafseer-al-anam"
YT_DLP = "C:/yt-dlp/yt-dlp.exe"

cfg = json.load(open(REPO + "/tools/config.json", encoding="utf-8"))
only = set(sys.argv[1:]) if len(sys.argv) > 1 else None

os.makedirs(REPO + "/_media/src", exist_ok=True)
done = 0
failed = []
for lec in cfg["lectures"]:
    lid = lec["id"]
    if only and lid not in only:
        continue
    yid = lec["youtube_id"]
    have = [x for x in os.listdir(REPO + "/_media/src") if x.startswith(lid + ".")]
    if have:
        print("skip (exists):", lid, have[0], flush=True)
        done += 1
        continue
    url = "https://www.youtube.com/watch?v=" + yid
    print("downloading:", lid, yid, flush=True)
    r = subprocess.run(
        [YT_DLP, "-f", "bestaudio", "--no-playlist", "--no-warnings",
         "-o", REPO + "/_media/src/" + lid + ".%(ext)s", url],
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=1800,
    )
    have = [x for x in os.listdir(REPO + "/_media/src") if x.startswith(lid + ".")]
    if r.returncode != 0 or not have:
        print("FAILED:", lid, (r.stderr or "")[-800:], flush=True)
        failed.append(lid)
    else:
        print("ok:", lid, have[0], flush=True)
        done += 1

print("downloaded/verified:", done, "failed:", failed, flush=True)

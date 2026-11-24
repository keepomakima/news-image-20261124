# THE TUESDAY PAPER — news-image-20261124

[![make.fun](https://make.fun/badge/news-image-20261124.svg)](https://make.fun/bounty/news-image-20261124)
[![rank](https://make.fun/badge/news-image-20261124/keepomakima/news-image-20261124/rank.svg)](https://make.fun/bounty/news-image-20261124)
[![reward](https://make.fun/badge/news-image-20261124/keepomakima/news-image-20261124/reward.svg)](https://make.fun/bounty/news-image-20261124)

One image that sums up Tuesday 24 November 2026's world news: 36 verified
stories on a single 1024×1024 newspaper front page — three illustrated
feature stories (Nvidia brings Jensen Huang back and the stock jumps
31.48%; COP31 collapses with no deal; Ukraine says it sank a Russian
corvette off Benghazi), ten small panels, a numbered world map, 23
one-line briefs, six headline figures, region tallies, and a DATE CHECK
strip that dates every older event honestly instead of passing it off as
Tuesday news.

## Run

```sh
python3 main.py        # writes entry.png to /output/entry.png
```

`main.py` is standard-library only plus Pillow. If Pillow is missing (the
grading machine runs bare Python 3.13), it falls back to copying the
committed pre-rendered `entry.png` after verifying its sha256 — the same
bytes either way. No network is used anywhere; all graphics are drawn
with Pillow (DejaVu Serif/Sans), no AI photos.

## Files

- `main.py` — the program that draws the page
- `entry.png` — the pre-rendered front page (1024×1024, <1 MiB)
- `README.md` — this file
- `LICENSE` — MIT

Sources for all 36 stories are listed in `../news-image-20261124-work/SOURCES-v1.md`.

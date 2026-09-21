import colorsys
import re
from datetime import date

RANGE = re.compile(r"(20\d{2})[/.-](\d{1,2})[/.-](\d{1,2})[~–—-](20\d{2})[/.-](\d{1,2})[/.-](\d{1,2})")
def norm(value):
    return "".join(x for x in re.split(r"[^A-Z0-9]+", value.upper()) if x and x != "RG")

def analyze(words, size):
    tokens = [dict(text=r["text"].strip(), x=int(r["left"])/2, y=int(r["top"])/2,
                   w=int(r["width"])/2,h=int(r["height"])/2,conf=float(r.get("conf",0)))
              for r in words if r.get("text","").strip()]
    lines=[]
    for t in sorted(tokens,key=lambda t:(t["y"],t["x"])):
        line=next((l for l in lines if abs(l[0]["y"]-t["y"])<=max(5,t["h"]*.5)),None)
        if line is None: lines.append([t])
        else: line.append(t)
    titles=[]
    for line in lines:
        line.sort(key=lambda t:t["x"])
        text=" ".join(t["text"] for t in line)
        match=RANGE.search(re.sub(r"\s+","",text))
        if match and re.search(r"speed\s+summary",text,re.I): titles.append((line,match))
    if len(titles)!=1:
        # Cadangan: judul dapat terpecah bila label sidebar hampir sejajar dengan judul grafik
        # (mis. "Logs & Alarms" pada halaman HQ). Jangkarkan pada token tanggal, lalu ambil
        # token satu baris visual di sebelah kanannya.
        anchored = []
        for anchor in tokens:
            if not RANGE.fullmatch(re.sub(r"\s+", "", anchor["text"])):
                continue
            centre = anchor["y"] + anchor["h"] / 2
            row = sorted((t for t in tokens if t["x"] >= anchor["x"] - 2
                          and abs((t["y"] + t["h"] / 2) - centre) <= max(6, anchor["h"])),
                         key=lambda t: t["x"])
            row_text = " ".join(t["text"] for t in row)
            found = RANGE.search(re.sub(r"\s+", "", row_text))
            if found and re.search(r"speed\s+summary", row_text, re.I):
                anchored.append((row, found))
        if len(anchored) == 1:
            titles = anchored
    if len(titles)!=1:
        raise ValueError("Tanggal dan Speed Summary tidak terbaca tunggal. Sertakan satu grafik lengkap.")
    title,match=titles[0]
    # Sidebar labels can share the same y-coordinate as the chart heading.
    date_tokens = [t for t in title if re.search(r'20\d{2}[/.-]\d', t['text'])]
    if date_tokens:
        title = [t for t in title if t['x'] >= min(v['x'] for v in date_tokens)]
    vals=[int(v) for v in match.groups()]
    start,end=date(*vals[:3]),date(*vals[3:])
    if end<start: raise ValueError("Rentang tanggal OCR tidak valid.")
    top=min(t["y"] for t in title)
    # Header suggestions require a unique sheet match and user confirmation.
    # Correct device headers can have low OCR confidence (WAGUBSU: 43.66).
    candidates={t["text"].strip("•●:") for t in tokens if t["y"]<top and t["conf"]>=0
                and re.fullmatch(r"\d{1,3}[-–][A-Za-z0-9]+(?:[-–][A-Za-z0-9]+)+",t["text"].strip("•●:"))}
    links=set()
    for desc in tokens:
        if desc["text"].rstrip(":").casefold()!="description" or desc["conf"]<75 or desc["y"]>=top: continue
        for t in tokens:
            if t["x"]>desc["x"]+desc["w"] and abs(t["y"]-desc["y"])<=max(6,desc["h"]) and t["conf"]>=75:
                if t["text"].casefold() in {"metro","broadband"}: links.add(t["text"].upper())
    # Only inspect Speed Summary; other cards can independently show No Data.
    boundaries = [min(t['y'] for t in line) for line in lines
                  if min(t['y'] for t in line) > top
                  and re.search(r'(?:Link|DNS)\s+Probe\s+Trend',
                                ' '.join(t['text'] for t in line), re.I)]
    section_end = min(boundaries) if boundaries else size[1]
    empty=[l for l in lines if top < min(t['y'] for t in l) < section_end
           and re.search(r'\bno\s+data\b',' '.join(t['text'] for t in l),re.I)]
    legends=[t for t in tokens if top < t['y'] < section_end
             and t['text'].casefold() in {'uplink','downlink'}]
    if empty: bottom=max(t["y"]+t["h"] for l in empty for t in l)+48
    elif {t["text"].casefold() for t in legends}=={"uplink","downlink"}:
        bottom=max(t["y"]+t["h"] for t in legends)+8
    else: raise ValueError("Batas grafik tidak terbaca. Sertakan legenda Uplink/Downlink atau tulisan No Data.")
    box=(max(0,int(min(t["x"] for t in title))-8),max(0,int(top)-12),size[0],min(size[1],int(section_end),int(bottom)))
    return {"start_date":start,"date":end,"box":box,"no_data":bool(empty),"projects":candidates,"links":links}

# Explicit alias verified against the supplied device and workbook screenshots.
# Do not match by project number alone: different devices may share a prefix.
PROJECT_ALIASES = {
    norm("03-RG-WAGUBSU-SERVER"): norm("03-RUDIN WAGUBSU"),
}


def suggest_selection(info, sheets):
    """Return a unique exact/verified-alias suggestion; never choose by number only."""
    project = ""
    if len(info["projects"]) == 1:
        candidate = norm(next(iter(info["projects"])))
        matches = [name for name in sheets if norm(name) == candidate]
        if not matches and candidate in PROJECT_ALIASES:
            matches = [name for name in sheets
                       if norm(name) == PROJECT_ALIASES[candidate]]
        if len(matches) == 1:
            project = matches[0]
    link = next(iter(info["links"])) if len(info["links"]) == 1 else ""
    return project, link


def resolve_selection(info, sheets):
    project, link = suggest_selection(info, sheets)
    return (project, link) if project and link else None


# ---------------------------------------------------------------------------
# Warna port terpilih (legenda Ruijie: hijau >100M, KUNING 10M/100M, hitam terputus)
# ---------------------------------------------------------------------------
PORT_HIGHLIGHT = (176, 205, 255)      # latar biru muda pada port yang sedang dipilih
PORT_SEARCH_REGION = (200, 300, 1200, 700)
YELLOW_MIN_PIXELS = 150


def _port_highlight_box(image):
    """Kotak sorotan port terpilih: komponen terbesar berwarna PORT_HIGHLIGHT."""
    x0, y0, x1, y1 = PORT_SEARCH_REGION
    x1, y1 = min(x1, image.width), min(y1, image.height)
    sub = image.convert('RGB').crop((x0, y0, x1, y1))
    width, data = sub.width, sub.tobytes()
    hr, hg, hb = PORT_HIGHLIGHT
    matches = set()
    for i in range(0, len(data), 3):
        if abs(data[i] - hr) <= 6 and abs(data[i + 1] - hg) <= 6 and abs(data[i + 2] - hb) <= 6:
            pos = i // 3
            matches.add((pos % width, pos // width))
    best, seen = [], set()
    for start in matches:
        if start in seen:
            continue
        stack, comp = [start], []
        seen.add(start)
        while stack:
            cx, cy = stack.pop()
            comp.append((cx, cy))
            for nb in ((cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)):
                if nb in matches and nb not in seen:
                    seen.add(nb)
                    stack.append(nb)
        if len(comp) > len(best):
            best = comp
    if len(best) < 1200:
        return None
    xs, ys = [p[0] for p in best], [p[1] for p in best]
    box = (min(xs) + x0, min(ys) + y0, max(xs) + x0 + 1, max(ys) + y0 + 1)
    if not (35 <= box[2] - box[0] <= 100 and 35 <= box[3] - box[1] <= 100):
        return None
    return box


def detect_port_color(image):
    """Deteksi warna ikon port yang sedang dipilih.

    Mengembalikan {'color','box','counts'} atau None bila sorotan port tidak ditemukan.
    color: 'yellow' (10M/100M), 'green' (>100M), 'dark' (terputus), atau 'unknown'.
    """
    box = _port_highlight_box(image)
    if not box:
        return None
    icon = image.convert('RGB').crop(box)
    data = icon.tobytes()
    counts = {'green': 0, 'yellow': 0, 'dark': 0}
    hr, hg, hb = PORT_HIGHLIGHT
    for i in range(0, len(data), 3):
        r, g, b = data[i], data[i + 1], data[i + 2]
        if abs(r - hr) <= 10 and abs(g - hg) <= 10 and abs(b - hb) <= 10:
            continue
        if r > 240 and g > 240 and b > 240:
            continue
        hue, sat, val = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
        hue *= 360
        if sat > .45 and val > .55:
            if 120 <= hue <= 175:
                counts['green'] += 1
            elif 30 <= hue <= 62:
                counts['yellow'] += 1
        elif sat < .2 and val < .5:
            counts['dark'] += 1
    if counts['yellow'] >= YELLOW_MIN_PIXELS and counts['yellow'] >= counts['green']:
        color = 'yellow'
    elif counts['green'] >= YELLOW_MIN_PIXELS:
        color = 'green'
    elif counts['dark'] >= 300:
        color = 'dark'
    else:
        color = 'unknown'
    return {'color': color, 'box': box, 'counts': counts}


def port_strip_box(box, size):
    """Area bukti: legenda warna + deretan port di sekitar port terpilih."""
    left, right = 240, 1155
    top = max(0, box[1] - 82)
    bottom = min(size[1], box[3] + 10)
    return (left, top, min(size[0], right), bottom)

"""Чтение, рендер и проверка use-case диаграммы EA (.qea). Координаты: y вниз."""
import math, re, sqlite3
from PIL import Image, ImageDraw, ImageFont

FONT = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf", 19)
_d = ImageDraw.Draw(Image.new("RGB", (5, 5)))
LH = 21  # высота строки Times New Roman 14pt при 96 dpi


def tw(s): return _d.textlength(s, font=FONT)


def wrap(text, width):
    lines, cur = [], ""
    for w in text.split():
        t = (cur + " " + w).strip()
        if tw(t) <= width or not cur: cur = t
        else: lines.append(cur); cur = w
    if cur: lines.append(cur)
    return lines


def fit_lines(text, w, h):
    """строки текста, если он влезает в эллипс w×h, иначе None"""
    a, b = w / 2, h / 2
    for n in range(1, 12):
        if LH * n > 2 * b * 0.92: return None
        y = (n - 1) / 2 * LH
        avail = 2 * a * math.sqrt(max(0, 1 - (y / b) ** 2)) - 10
        if avail <= 0: return None
        L = wrap(text, avail)
        if len(L) <= n and max(tw(l) for l in L) <= avail: return L
    return None


def min_size(text, aspect=1.5):
    h = 30
    while not fit_lines(text, round(h * aspect), h): h += 2
    return round(h * aspect) + 8, h + 6


def load(path, diagram=1):
    db = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    objs = {}
    for oid, name, typ, l, t, r, b in db.execute("""select d.Object_ID, o.Name, o.Object_Type, d.RectLeft, d.RectTop, d.RectRight, d.RectBottom
            from t_diagramobjects d join t_object o using(Object_ID) where d.Diagram_ID=?""", (diagram,)):
        if typ not in ("UseCase", "Actor"): continue
        objs[oid] = dict(name=(name or "").strip(), type=typ, w=r - l, h=t - b, cx=(l + r) / 2, cy=-(t + b) / 2)
    links = [dict(id=i, stereo=s, type=t, s=a, e=b) for i, t, s, a, b in db.execute(
        """select c.Connector_ID, c.Connector_Type, c.Stereotype, c.Start_Object_ID, c.End_Object_ID from t_connector c
           join t_diagramlinks l on l.ConnectorID=c.Connector_ID where l.DiagramID=?""", (diagram,)) if a in objs and b in objs]
    return objs, links


def save(path, objs, diagram=1):
    """записывает прямоугольники и сторону выхода связей (EDGE) обратно в .qea"""
    db = sqlite3.connect(path)
    R = {}
    for oid, o in objs.items():
        l, t, r, b = map(round, rect(o)); R[oid] = (l, t, r, b)
        db.execute("update t_diagramobjects set RectLeft=?, RectRight=?, RectTop=?, RectBottom=? where Diagram_ID=? and Object_ID=?",
                   (l, r, -t, -b, diagram, oid))
    for cid, s, e, geom in db.execute("""select l.ConnectorID, c.Start_Object_ID, c.End_Object_ID, l.Geometry from t_diagramlinks l
            join t_connector c on c.Connector_ID=l.ConnectorID where l.DiagramID=?""", (diagram,)).fetchall():
        if s not in R or e not in R or not geom: continue
        (l1, t1, r1, b1), (l2, t2, r2, b2) = R[s], R[e]
        dx, dy = (l2 + r2 - l1 - r1) / 2, (t2 + b2 - t1 - b1) / 2
        edge = (2 if dx > 0 else 4) if abs(dx) * (b1 - t1) > abs(dy) * (r1 - l1) else (3 if dy > 0 else 1)
        db.execute("update t_diagramlinks set Geometry=?, Path=NULL where DiagramID=? and ConnectorID=?",
                   (re.sub(r"EDGE=\d", f"EDGE={edge}", geom), diagram, cid))
    db.commit()
    return db.execute("pragma integrity_check").fetchone()[0]


def rect(o): return (o["cx"] - o["w"] / 2, o["cy"] - o["h"] / 2, o["cx"] + o["w"] / 2, o["cy"] + o["h"] / 2)


def actor_label(o):
    w = tw(o["name"]) + 6; l, t, r, b = rect(o)
    return (o["cx"] - w / 2, b + 2, o["cx"] + w / 2, b + 24)


def boundary(o, tx, ty):
    dx, dy = tx - o["cx"], ty - o["cy"]; a, b = o["w"] / 2, o["h"] / 2
    if o["type"] == "UseCase": k = 1 / math.sqrt((dx / a) ** 2 + (dy / b) ** 2)
    else: k = min(a / abs(dx) if dx else 1e9, b / abs(dy) if dy else 1e9)
    return (o["cx"] + dx * k, o["cy"] + dy * k)


def ends(objs, L):
    s, e = objs[L["s"]], objs[L["e"]]
    return boundary(s, e["cx"], e["cy"]), boundary(e, s["cx"], s["cy"])


def inside(o, x, y, grow=0):
    if o["type"] == "UseCase":
        return ((x - o["cx"]) / (o["w"] / 2 + grow)) ** 2 + ((y - o["cy"]) / (o["h"] / 2 + grow)) ** 2 < 1
    l, t, r, b = rect(o)
    if l - grow < x < r + grow and t - grow < y < b + grow: return True
    L = actor_label(o)
    return L[0] - grow < x < L[2] + grow and L[1] - grow < y < L[3] + grow


def lbox(p, q):
    mx, my = (p[0] + q[0]) / 2, (p[1] + q[1]) / 2
    return (mx - 36, my - 10, mx + 36, my + 11)


def box_hits(bx, o, grow=0):
    return any(inside(o, bx[0] + (bx[2] - bx[0]) * i / 8, bx[1] + (bx[3] - bx[1]) * j / 4, grow) for i in range(9) for j in range(5))


def xsect(p1, p2, p3, p4):
    c = lambda a, b, d: (d[1] - a[1]) * (b[0] - a[0]) - (b[1] - a[1]) * (d[0] - a[0])
    return c(p3, p4, p1) * c(p3, p4, p2) < 0 and c(p1, p2, p3) * c(p1, p2, p4) < 0


def check(objs, links, W=1880, H=870):
    P = []
    ids = list(objs)
    for oid, o in objs.items():
        l, t, r, b = rect(o)
        if o["type"] == "Actor": L = actor_label(o); l, r, b = min(l, L[0]), max(r, L[2]), L[3]
        if l < 3 or t < 3 or r > W or b > H: P.append(f"за границей {oid}")
        if o["type"] == "UseCase" and not fit_lines(o["name"], o["w"], o["h"]): P.append(f"текст не влезает {oid}")
    for i, a in enumerate(ids):
        for b in ids[i + 1:]:
            A, B = objs[a], objs[b]; hit = False
            for O1, O2 in ((A, B), (B, A)):
                if O1["type"] == "UseCase":
                    for k in range(48):
                        g = k * math.pi / 24
                        if inside(O2, O1["cx"] + (O1["w"] / 2 + 10) * math.cos(g), O1["cy"] + (O1["h"] / 2 + 10) * math.sin(g)): hit = True; break
                elif box_hits(rect(O1), O2, 10) or box_hits(actor_label(O1), O2, 6): hit = True
            if hit: P.append(f"тесно {a}-{b}")
    seg = {L["id"]: ends(objs, L) for L in links}
    for L in links:
        p, q = seg[L["id"]]
        if math.dist(p, q) < (50 if L["stereo"] else 25): P.append(f"короткая {L['id']} ({L['s']}->{L['e']})")
        for oid, o in objs.items():
            if oid in (L["s"], L["e"]): continue
            if any(inside(o, p[0] + (q[0] - p[0]) * i / 50, p[1] + (q[1] - p[1]) * i / 50, 4) for i in range(1, 50)):
                P.append(f"связь {L['id']} ({L['s']}->{L['e']}) через {oid}")
        if L["stereo"]:
            for oid, o in objs.items():
                if box_hits(lbox(p, q), o): P.append(f"подпись {L['id']} ({L['s']}->{L['e']}) на {oid}")
    X = [(a["id"], b["id"]) for i, a in enumerate(links) for b in links[i + 1:]
         if len({a["s"], a["e"], b["s"], b["e"]}) == 4 and xsect(*seg[a["id"]], *seg[b["id"]])]
    if X: P.append(f"пересечения {X}")
    return P


def render(objs, links, out, W=1880, H=870):
    img = Image.new("RGB", (W + 10, H + 10), "white"); d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, H], outline="#ccc")
    for oid, o in objs.items():
        l, t, r, b = rect(o)
        if o["type"] == "UseCase":
            d.ellipse([l, t, r, b], outline="black", fill="#fffbe0")
            L = fit_lines(o["name"], o["w"], o["h"]) or wrap(o["name"], o["w"] * 0.7)
            y = o["cy"] - LH * len(L) / 2
            for s in L: d.text((o["cx"], y), s, font=FONT, fill="black", anchor="ma"); y += LH
        else:
            cx = o["cx"]; h = b - t; rr = h * 0.12
            d.ellipse([cx - rr, t, cx + rr, t + 2 * rr], outline="black")
            d.line([(cx, t + 2 * rr), (cx, t + h * .62)], fill="black"); d.line([(l, t + h * .38), (r, t + h * .38)], fill="black")
            d.line([(cx, t + h * .62), (l, b)], fill="black"); d.line([(cx, t + h * .62), (r, b)], fill="black")
            d.text((cx, b + 2), o["name"], font=FONT, fill="black", anchor="ma")
        d.text((l, t - 11), str(oid), font=ImageFont.load_default(), fill="#c00")
    for L in links:
        p, q = ends(objs, L)
        col = {"extend": "#1f5fbf", "include": "#1a8a3a"}.get(L["stereo"], "black")
        if L["stereo"]:
            n = max(int(math.dist(p, q) // 6), 1)
            for i in range(0, n, 2):
                d.line([(p[0] + (q[0] - p[0]) * i / n, p[1] + (q[1] - p[1]) * i / n),
                        (p[0] + (q[0] - p[0]) * min(i + 1, n) / n, p[1] + (q[1] - p[1]) * min(i + 1, n) / n)], fill=col)
            bx = lbox(p, q); d.text(((bx[0] + bx[2]) / 2, (bx[1] + bx[3]) / 2), f"«{L['stereo']}»", font=FONT, fill=col, anchor="mm")
        else:
            d.line([p, q], fill=col)
        if L["type"] != "Association":
            g = math.atan2(q[1] - p[1], q[0] - p[0])
            for s in (-1, 1): d.line([q, (q[0] - 13 * math.cos(g + s * .4), q[1] - 13 * math.sin(g + s * .4))], fill=col, width=2)
    img.save(out)

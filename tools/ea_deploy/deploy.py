"""Deployment-диаграмма (лаба 2) для модели EA (.qea). Координаты: y вниз, 1 ед. = 1 px при масштабе 100%.
python deploy.py            — проверка раскладки и рендер в out/deploy.png
python deploy.py save       — то же + запись диаграммы в Lab2/Touragency.qea (бэкап в backups/)"""
import datetime, math, os, random, re, shutil, sqlite3, sys, uuid
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
QEA = os.path.join(HERE, "..", "..", "Lab2", "Touragency.qea")
BACKUPS = os.path.join(HERE, "..", "..", "backups")
W, H = 1880, 870                      # видимая область диаграммы на весь экран при 100%
DEPTH = 10                            # глубина 3D-грани узла
LH = 21                               # высота строки Times New Roman 14pt
FONT = ImageFont.truetype("C:/Windows/Fonts/timesbd.ttf", 19)
_d = ImageDraw.Draw(Image.new("RGB", (5, 5)))
STYLE = "font=Times New Roman;bold=1;black=0;italic=0;ul=0;charset=0;pitch=18;fontsz=140;"
DIAGRAM = "ПС «Онлайн сервис услуг турагентства»"
BROWSERS = "Chrome for Android, Safari for iOS, Chrome 109.0 (Windows)"

# (ключ, тип, имя, родитель, (left, top, right, bottom))
NODES = [
    ("operator", "Device", "Сервер туроператора", None, (10, 15, 210, 100)),
    ("payment", "Device", "Сервер платёжной системы", None, (10, 175, 210, 260)),
    ("sms", "Device", "Сервер сервиса отправки SMS-кодов", None, (10, 320, 210, 430)),
    ("inet", "Device", "Интернет-канал", None, (330, 290, 500, 345)),
    ("guest", "Device", "Рабочая станция гостя", None, (10, 590, 270, 840)),
    ("guest_b", "ExecutionEnvironment", BROWSERS, "guest", (25, 665, 245, 815)),
    ("user", "Device", "Рабочая станция авторизованного пользователя", None, (330, 545, 600, 840)),
    ("user_b", "ExecutionEnvironment", BROWSERS, "user", (345, 665, 575, 815)),
    ("router", "Device", "Роутер", None, (740, 290, 860, 345)),
    ("manager", "Device", "Рабочая станция менеджера", None, (430, 10, 720, 212)),
    ("manager_b", "ExecutionEnvironment", BROWSERS, "manager", (445, 72, 695, 200)),
    ("director", "Device", "Рабочая станция директора", None, (790, 10, 1080, 212)),
    ("director_b", "ExecutionEnvironment", BROWSERS, "director", (805, 72, 1055, 200)),
    ("printer", "Device", "Сетевой принтер", None, (980, 235, 1160, 290)),
    ("db", "Device", "Сервер базы данных, архитектура Intel, разрядность x64", None, (700, 470, 1120, 840)),
    ("db_os", "ExecutionEnvironment", "ОС Ubuntu Server 24.04.3 LTS (x64)", "db", (720, 555, 1090, 815)),
    ("dbms", "ExecutionEnvironment", "СУБД PostgreSQL 18 (x64)", "db_os", (740, 615, 1065, 790)),
    ("db_sql", "Artifact", "touragency_list.sql", "dbms", (790, 700, 1015, 750)),
    ("web", "Device", "Сервер веб-приложений, архитектура Intel, разрядность x64", None, (1240, 290, 1870, 840)),
    ("web_os", "ExecutionEnvironment", "ОС Ubuntu Server 24.04.3 LTS (x64)", "web", (1260, 375, 1845, 815)),
    ("nginx", "ExecutionEnvironment", "Веб-сервер Nginx 1.28 (обратный прокси)", "web_os", (1280, 440, 1820, 525)),
    ("kestrel", "ExecutionEnvironment", "Сервер приложений ASP.NET Core Kestrel 10.0", "web_os", (1280, 545, 1820, 630)),
    ("dotnet", "ExecutionEnvironment", "Среда выполнения .NET 10.0 LTS (x64), фреймворк ASP.NET Core 10.0", "web_os", (1280, 650, 1820, 735)),
    ("web_deb", "Artifact", "touragency_store.deb", "web_os", (1280, 750, 1820, 795)),
]
# (начало, конец, подпись)
LINKS = [
    ("operator", "inet", "HTTPS"),
    ("payment", "inet", "HTTPS"),
    ("sms", "inet", "HTTPS"),
    ("guest", "inet", "HTTPS"),
    ("user", "inet", "HTTPS"),
    ("inet", "router", "HTTPS"),
    ("manager", "router", "HTTPS"),
    ("director", "router", "HTTPS"),
    ("printer", "router", "IPP"),
    ("db", "router", "PostgreSQL Frontend/Backend Protocol"),
    ("web", "router", "HTTPS, PostgreSQL Frontend/Backend Protocol, IPP"),
]
LABEL_W = 240                         # подписи длиннее переносятся


def tw(s): return _d.textlength(s, font=FONT)


def wrap(text, width):
    lines, cur = [], ""
    for w in text.split():
        t = (cur + " " + w).strip()
        if tw(t) <= width or not cur: cur = t
        else: lines.append(cur); cur = w
    if cur: lines.append(cur)
    return lines


def face(n):
    """передняя грань узла (у артефакта — весь прямоугольник)"""
    l, t, r, b = n["rect"]
    return (l, t, r, b) if n["type"] == "Artifact" else (l, t + DEPTH, r - DEPTH, b)


def title(n):
    """строки имени и нижняя граница заголовка"""
    l, t, r, b = face(n)
    L = wrap(n["name"], r - l - 16)
    if n["type"] == "Artifact" or not n["kids"]: return L, None
    return L, t + 8 + LH * len(L) + 6


def boundary(r, tx, ty):
    l, t, rr, b = r; cx, cy = (l + rr) / 2, (t + b) / 2; dx, dy = tx - cx, ty - cy
    k = min((rr - l) / 2 / abs(dx) if dx else 1e9, (b - t) / 2 / abs(dy) if dy else 1e9)
    return cx + dx * k, cy + dy * k


def center(r): return (r[0] + r[2]) / 2, (r[1] + r[3]) / 2


def seg(L):
    a, b = N[L["s"]]["rect"], N[L["e"]]["rect"]
    return boundary(a, *center(b)), boundary(b, *center(a))


def label(L):
    """прямоугольник подписи: EA ставит её над серединой связи"""
    p, q = seg(L); mx, my = (p[0] + q[0]) / 2, (p[1] + q[1]) / 2
    lines = wrap(L["name"], LABEL_W); w = max(tw(s) for s in lines) + 8; h = LH * len(lines)
    ox, oy = L.get("off", (0, 0))
    return lines, (mx - w / 2 + ox, my - h - 2 + oy, mx + w / 2 + ox, my - 2 + oy)


def overlap(a, b, pad=0):
    return a[0] < b[2] + pad and b[0] < a[2] + pad and a[1] < b[3] + pad and b[1] < a[3] + pad


def inside(a, b): return b[0] <= a[0] and b[1] <= a[1] and a[2] <= b[2] and a[3] <= b[3]


def seg_hits_rect(p, q, r, pad=0):
    return any(r[0] - pad < p[0] + (q[0] - p[0]) * i / 60 < r[2] + pad and r[1] - pad < p[1] + (q[1] - p[1]) * i / 60 < r[3] + pad
               for i in range(1, 60))


def xsect(p1, p2, p3, p4):
    c = lambda a, b, d: (d[1] - a[1]) * (b[0] - a[0]) - (b[1] - a[1]) * (d[0] - a[0])
    return c(p3, p4, p1) * c(p3, p4, p2) < 0 and c(p1, p2, p3) * c(p1, p2, p4) < 0


N = {k: dict(key=k, type=t, name=n, parent=p, rect=r, kids=[]) for k, t, n, p, r in NODES}
for n in N.values():
    if n["parent"]: N[n["parent"]]["kids"].append(n["key"])
LK = [dict(s=s, e=e, name=nm) for s, e, nm in LINKS]
OFF = {("db", "router"): (-150, 40), ("web", "router"): (40, 0)}
for L in LK: L["off"] = OFF.get((L["s"], L["e"]), (0, 0))


def check():
    P = []
    top = [n for n in N.values() if not n["parent"]]
    for n in N.values():
        l, t, r, b = n["rect"]
        if l < 3 or t < 3 or r > W or b > H: P.append(f"за границей {n['key']}")
        lines, hb = title(n); fl, ft, fr, fb = face(n)
        if max(tw(s) for s in lines) > fr - fl - 12: P.append(f"имя шире {n['key']}")
        need = 8 + LH * len(lines) + 6
        if fb - ft < need: P.append(f"имя не влезает по высоте {n['key']}")
        if n["parent"]:
            pr = N[n["parent"]]; pl, pt, prr, pb = face(pr); _, phb = title(pr)
            if not inside(n["rect"], (pl + 8, phb + 6, prr - 8, pb - 8)): P.append(f"{n['key']} не внутри {pr['key']}")
    for i, a in enumerate(N.values()):
        for b in list(N.values())[i + 1:]:
            if a["parent"] == b["parent"] and overlap(a["rect"], b["rect"], 12): P.append(f"тесно {a['key']}-{b['key']}")
    labels = []
    for L in LK:
        p, q = seg(L)
        if math.dist(p, q) < 60: P.append(f"короткая {L['s']}-{L['e']}")
        for n in top:
            if n["key"] not in (L["s"], L["e"]) and seg_hits_rect(p, q, n["rect"], 6): P.append(f"связь {L['s']}-{L['e']} через {n['key']}")
        _, lb = label(L); labels.append((L, lb))
        for n in top:
            if overlap(lb, n["rect"], 4): P.append(f"подпись {L['s']}-{L['e']} на {n['key']}")
        for L2 in LK:
            if L2 is not L and seg_hits_rect(*seg(L2), lb, 2): P.append(f"подпись {L['s']}-{L['e']} на связи {L2['s']}-{L2['e']}")
    for i, (a, la) in enumerate(labels):
        for b, lb in labels[i + 1:]:
            if overlap(la, lb, 4): P.append(f"подписи {a['s']}-{a['e']} и {b['s']}-{b['e']}")
    for i, a in enumerate(LK):
        for b in LK[i + 1:]:
            if len({a["s"], a["e"], b["s"], b["e"]}) == 4 and xsect(*seg(a), *seg(b)): P.append(f"пересечение {a['s']}-{a['e']} и {b['s']}-{b['e']}")
    return P


FILL = {"Device": "#f6e9e1", "ExecutionEnvironment": "#cfe2f3", "Artifact": "#e2f2e6"}


def depth_of(n): return 0 if not n["parent"] else 1 + depth_of(N[n["parent"]])


def render(out):
    img = Image.new("RGB", (W + 10, H + 10), "white"); d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, H], outline="#bbb")
    for L in LK:
        p, q = seg(L); d.line([p, q], fill="#556")
        lines, (l, t, r, b) = label(L)
        for i, s in enumerate(lines): d.text(((l + r) / 2, t + i * LH), s, font=FONT, fill="black", anchor="ma")
    for n in sorted(N.values(), key=depth_of):
        l, t, r, b = n["rect"]; fl, ft, fr, fb = face(n); col = FILL[n["type"]]
        if n["type"] != "Artifact":
            d.polygon([(l, t + DEPTH), (l + DEPTH, t), (r, t), (r - DEPTH, t + DEPTH)], fill="#e8d8cc", outline="#866")
            d.polygon([(r - DEPTH, t + DEPTH), (r, t), (r, b - DEPTH), (r - DEPTH, b)], fill="#d8c4b8", outline="#866")
        d.rectangle([fl, ft, fr, fb], fill=col, outline="#866")
        lines, hb = title(n)
        y = ft + 8 if hb or n["type"] == "Artifact" and False else (ft + fb) / 2 - LH * len(lines) / 2
        if hb: y = ft + 8; d.line([(fl, hb), (fr, hb)], fill="#866")
        for s in lines: d.text(((fl + fr) / 2, y), s, font=FONT, fill="black", anchor="ma"); y += LH
    img.save(out)


def save():
    os.makedirs(BACKUPS, exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    shutil.copy2(QEA, os.path.join(BACKUPS, f"Touragency.before-deploy.{stamp}.qea"))
    db = sqlite3.connect(QEA); db.row_factory = sqlite3.Row
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    guid = lambda: "{" + str(uuid.uuid4()).upper() + "}"
    row = lambda q, *a: dict(db.execute(q, a).fetchone())
    nxt = lambda t, c: (db.execute(f"select max({c}) from {t}").fetchone()[0] or 0) + 1
    ins = lambda t, r: db.execute(f"insert into {t} ({','.join(r)}) values ({','.join('?' * len(r))})", list(r.values()))
    old = db.execute("select Diagram_ID, Package_ID from t_diagram where Diagram_Type='Deployment'").fetchall()
    if old: sys.exit(f"в модели уже есть deployment-диаграмма {[tuple(r) for r in old]} — удалите её в EA или восстановите бэкап")
    # пакет deployment рядом с use-case
    uc_pkg = row("select * from t_package where Package_ID=(select Package_ID from t_diagram where Diagram_Type='Use Case')")
    pid, pg = nxt("t_package", "Package_ID"), guid()
    p = dict(uc_pkg); p.update(Package_ID=pid, Name="deployment", ea_guid=pg, CreatedDate=now, ModifiedDate=now, TPos=2); ins("t_package", p)
    po = row("select * from t_object where Object_Type='Package' and PDATA1=?", str(uc_pkg["Package_ID"]))
    po.update(Object_ID=nxt("t_object", "Object_ID"), Name="deployment", PDATA1=str(pid), ea_guid=pg, CreatedDate=now, ModifiedDate=now, TPos=2); ins("t_object", po)
    # диаграмма: оформление как у use-case, свойства отображения как у принятых deployment-диаграмм
    dg = row("select * from t_diagram where Diagram_Type='Use Case'")
    did = nxt("t_diagram", "Diagram_ID")
    dg.update(Diagram_ID=did, Package_ID=pid, Diagram_Type="Deployment", Name=DIAGRAM, ea_guid=guid(), CreatedDate=now, ModifiedDate=now,
              PDATA=re.sub(r"ShowIcons=\d", "ShowIcons=0", re.sub(r"HideEStereo=\d", "HideEStereo=1", dg["PDATA"])))
    ins("t_diagram", dg)
    tpl = row("select * from t_object where Object_Type='UseCase' limit 1")
    for k in ("Classifier", "Stereotype", "Note", "Alias", "PDATA1", "PDATA2", "PDATA3", "PDATA4", "PDATA5", "Style", "StyleEx", "ParentID"):
        if k in tpl: tpl[k] = 0 if k in ("Classifier", "ParentID") else None
    seq = 1; inst = nxt("t_diagramobjects", "Instance_ID")
    base = nxt("t_object", "Object_ID")
    for i, n in enumerate(sorted(N.values(), key=depth_of)):       # родители получают id первыми (ParentID)
        n["oid"], n["duid"] = base + i, "%08X" % random.getrandbits(32)
    for n in sorted(N.values(), key=depth_of):
        o = dict(tpl)
        o.update(Object_ID=n["oid"], Object_Type=n["type"], Name=n["name"], Package_ID=pid, ea_guid=guid(), CreatedDate=now, ModifiedDate=now,
                 ParentID=N[n["parent"]]["oid"] if n["parent"] else 0, GenType="<none>")
        ins("t_object", o)
    for n in sorted(N.values(), key=lambda n: -depth_of(n)):
        l, t, r, b = n["rect"]
        ins("t_diagramobjects", dict(Diagram_ID=did, Object_ID=n["oid"], RectTop=-t, RectLeft=l, RectRight=r, RectBottom=-b,
                                     Sequence=seq, ObjectStyle=STYLE + f"DUID={n['duid']};", Instance_ID=inst)); seq += 1; inst += 1
    cid, linst = nxt("t_connector", "Connector_ID"), nxt("t_diagramlinks", "Instance_ID")
    for L in LK:
        s, e = N[L["s"]], N[L["e"]]; p, q = seg(L); lines, lb = label(L)
        (sx, sy), (ex, ey) = center(s["rect"]), center(e["rect"])
        dx, dy = ex - sx, ey - sy
        edge = (2 if dx > 0 else 4) if abs(dx) * (s["rect"][3] - s["rect"][1]) > abs(dy) * (s["rect"][2] - s["rect"][0]) else (3 if dy > 0 else 1)
        ins("t_connector", dict(Connector_ID=cid, Name=L["name"], Direction="Unspecified", Connector_Type="CommunicationPath",
                                SourceAccess="Public", DestAccess="Public", SourceContainment="Unspecified", DestContainment="Unspecified",
                                Start_Object_ID=s["oid"], End_Object_ID=e["oid"], Top_Mid_Label=L["name"], Start_Edge=0, End_Edge=0,
                                PtStartX=round(p[0]), PtStartY=-round(p[1]), PtEndX=round(q[0]), PtEndY=-round(q[1]), SeqNo=0, HeadStyle=0,
                                LineStyle=0, RouteStyle=3, IsBold=0, LineColor=-1, VirtualInheritance="0", DiagramID=0, ea_guid=guid(),
                                SourceIsAggregate=0, SourceIsOrdered=0, DestIsAggregate=0, DestIsOrdered=0, SourceIsNavigable=0, DestIsNavigable=0,
                                IsRoot=0, IsLeaf=0, IsSpec=0, SourceChangeable="none", DestChangeable="none", SourceTS="instance", DestTS="instance",
                                IsSignal=0, IsStimulus=0, Target2=0, SourceStyle="Union=0;Derived=0;AllowDuplicates=0;Owned=0;Navigable=Unspecified;",
                                DestStyle="Union=0;Derived=0;AllowDuplicates=0;Owned=0;Navigable=Non-Navigable;"))
        mx, my = (p[0] + q[0]) / 2, (p[1] + q[1]) / 2; ox, oy = L["off"]
        lmt = f"CX={round(lb[2] - lb[0])}:CY={round(lb[3] - lb[1])}:OX={ox}:OY={oy}:HDN=0:BLD=0:ITA=0:UND=0:CLR=-1:ALN=1:DIR=0:ROT=0;"
        ins("t_diagramlinks", dict(DiagramID=did, ConnectorID=cid, Geometry=f"SX=0;SY=0;EX=0;EY=0;EDGE={edge};$LLB=;LLT=;LMT={lmt}LMB=;LRT=;LRB=;IRHS=;ILHS=;",
                                   Style=f"Mode=3;EOID={e['duid']};SOID={s['duid']};Color=-1;LWidth=0;", Hidden=0, Instance_ID=linst))
        cid += 1; linst += 1
    db.commit()
    print("записано: диаграмма", did, "пакет", pid, "—", db.execute("pragma integrity_check").fetchone()[0])


if __name__ == "__main__":
    os.makedirs(os.path.join(HERE, "out"), exist_ok=True)
    P = check(); print("проблемы:", *P, sep="\n  ") if P else print("проблем нет")
    render(os.path.join(HERE, "out", "deploy.png"))
    if len(sys.argv) > 1 and sys.argv[1] == "save": save()

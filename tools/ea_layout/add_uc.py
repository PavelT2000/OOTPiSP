"""Добавить варианты использования с подбором мест только для них.
python add_uc.py '[["Имя", base_id], ...]' [save]   (связь extend base -> новый)"""
import json, sys, sqlite3, uuid, random, re, datetime, shutil
import numpy as np
import ea
from opt import Model
QEA = "../../Lab1/Touragency.qea"
spec = json.loads(sys.argv[1]); save = len(sys.argv) > 2 and sys.argv[2] == "save"
objs, links = ea.load(QEA)
tmp = {}
for i, (name, base) in enumerate(spec):
    k = 9000 + i; w, h = ea.min_size(name); tmp[k] = (name, base)
    objs[k] = dict(name=name, type="UseCase", w=w, h=h, cx=-9999, cy=-9999)
    links.append(dict(id=99000 + i, stereo="extend", type="UseCase", s=base, e=k))
m = Model(objs, links)
xs = np.arange(60, 1860, 15); ys = np.arange(50, 860, 15)
pos = m.pos.copy()
for it in range(2):
    for k in tmp:
        i = m.idx[k]; bv, bp = 1e18, None
        for x in xs:
            for y in ys:
                pos[i] = (x, y); v = m.penalty(pos)
                if v < bv: bv, bp = v, (x, y)
        pos[i] = bp
m.pos = pos; m.apply()
I = [s for s in ea.check(objs, links) if any(str(k) in s for k in list(tmp) + [99000 + i for i in range(len(tmp))])]
print("места:", {tmp[k][0]: (round(objs[k]["cx"]), round(objs[k]["cy"])) for k in tmp}); print("проблемы с новыми:", I or "нет")
ea.render(objs, links, "out/add.png")
if save:
    shutil.copy2(QEA, QEA.replace(".qea", ".before-add.qea"))
    db = sqlite3.connect(QEA); db.row_factory = sqlite3.Row
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    tpl_uc = db.execute("select Object_ID from t_object where Object_Type='UseCase' limit 1").fetchone()[0]
    to = dict(db.execute("select * from t_object where Object_ID=?", (tpl_uc,)).fetchone())
    td = dict(db.execute("select * from t_diagramobjects where Object_ID=?", (tpl_uc,)).fetchone())
    tcid = db.execute("select Connector_ID from t_connector where Stereotype='extend' limit 1").fetchone()[0]
    tc = dict(db.execute("select * from t_connector where Connector_ID=?", (tcid,)).fetchone()); tl = dict(db.execute("select * from t_diagramlinks where ConnectorID=?", (tcid,)).fetchone())
    ins = lambda t, r: db.execute(f"insert into {t} ({','.join(r)}) values ({','.join('?' * len(r))})", list(r.values()))
    duid = lambda o: re.search(r"DUID=(\w+)", db.execute("select ObjectStyle from t_diagramobjects where Object_ID=?", (o,)).fetchone()[0]).group(1)
    for k, (name, base) in tmp.items():
        o = objs[k]
        oid = db.execute("select max(Object_ID) from t_object").fetchone()[0] + 1
        r = dict(to); r.update(Object_ID=oid, Name=name, ea_guid="{" + str(uuid.uuid4()).upper() + "}", CreatedDate=now, ModifiedDate=now); ins("t_object", r)
        d = dict(td); d.update(Object_ID=oid, Instance_ID=db.execute("select max(Instance_ID) from t_diagramobjects").fetchone()[0] + 1,
                               Sequence=db.execute("select max(Sequence) from t_diagramobjects").fetchone()[0] + 1,
                               RectLeft=round(o["cx"] - o["w"] / 2), RectRight=round(o["cx"] + o["w"] / 2), RectTop=-round(o["cy"] - o["h"] / 2), RectBottom=-round(o["cy"] + o["h"] / 2),
                               ObjectStyle=re.sub(r"DUID=\w+", "DUID=%08X" % random.getrandbits(32), td["ObjectStyle"])); ins("t_diagramobjects", d)
        cid = db.execute("select max(Connector_ID) from t_connector").fetchone()[0] + 1
        c = dict(tc); c.update(Connector_ID=cid, Start_Object_ID=base, End_Object_ID=oid, ea_guid="{" + str(uuid.uuid4()).upper() + "}"); ins("t_connector", c)
        l = dict(tl); l.update(ConnectorID=cid, Instance_ID=db.execute("select max(Instance_ID) from t_diagramlinks").fetchone()[0] + 1, Path=None,
                               Style=re.sub(r"EOID=\w+", "EOID=" + duid(oid), re.sub(r"SOID=\w+", "SOID=" + duid(base), tl["Style"]))); ins("t_diagramlinks", l)
    db.commit(); print("записано,", db.execute("pragma integrity_check").fetchone()[0])

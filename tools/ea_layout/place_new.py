"""Подбор мест только для новых элементов (остальные стоят на месте)."""
import json, itertools
import numpy as np
import ea
from opt import Model
objs, links = ea.load("../../Lab1/Touragency.qea")
NEW = {201: "Подтвердить бронирование тура", 202: "Получить оплату за тур"}
for k, n in NEW.items():
    w, h = ea.min_size(n); objs[k] = dict(name=n, type="UseCase", w=w, h=h, cx=0, cy=0)
NL = [(301, "extend", "UseCase", 44, 201), (302, None, "UseCase", 17, 201), (303, "extend", "UseCase", 201, 202), (304, None, "UseCase", 17, 202)]
for cid, st, t, s, e in NL: links.append(dict(id=cid, stereo=st, type=t, s=s, e=e))
m = Model(objs, links)
i1, i2 = m.idx[201], m.idx[202]
xs = np.arange(60, 1860, 20); ys = np.arange(50, 850, 20)
pos = m.pos.copy()
# сначала N1 рядом с туроператором, потом N2, затем пара итераций
pos[i2] = (-5000, -5000)
best = None
for it in range(3):
    for i in (i1, i2):
        bv, bp = 1e18, None
        for x in xs:
            for y in ys:
                pos[i] = (x, y); v = m.penalty(pos)
                if v < bv: bv, bp = v, (x, y)
        pos[i] = bp
    P, X = m.penalty(pos, detail=True); print(it, round(sum(P.values())), "cross", X, pos[i1], pos[i2])
m.pos = pos; m.apply()
I = ea.check(objs, links)
new_issues = [s for s in I if any(str(k) in s for k in (201, 202, 301, 302, 303, 304))]
print("проблемы с новыми:", new_issues or "нет")
ea.render(objs, links, "out/new.png")
json.dump({str(k): [objs[k]["cx"], objs[k]["cy"], objs[k]["w"], objs[k]["h"]] for k in NEW}, open("out/new.json", "w"))

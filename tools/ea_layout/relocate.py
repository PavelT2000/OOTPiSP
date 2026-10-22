"""Жадный перенос элементов в лучшую точку сетки. python relocate.py START.json OUT_NAME [passes]"""
import json, sys, os
import numpy as np
import ea, opt
from opt import Model
objs, links = ea.load(os.path.join(os.path.dirname(__file__), "..", "..", "models", "Touragency.qea"))
for k, (x, y, w, h) in json.load(open(sys.argv[1]))["pos"].items():
    objs[int(k)].update(cx=x, cy=y, w=w, h=h)
m = Model(objs, links)
pos = m.pos.copy(); cur = m.penalty(pos)
xs = np.arange(40, opt.W_MAX - 30, 30); ys = np.arange(40, opt.H_MAX - 30, 25)
for p in range(int(sys.argv[3]) if len(sys.argv) > 3 else 3):
    improved = 0
    for i in range(m.n):
        best, bp = cur, pos[i].copy()
        for x in xs:
            for y in ys:
                pos[i] = (x, y); v = m.penalty(pos)
                if v < best: best, bp = v, pos[i].copy()
        pos[i] = bp
        if best < cur - 1: improved += 1; cur = best
    P, X = m.penalty(pos, detail=True)
    print(f"pass {p}: score {cur:.0f} cross {X} moved {improved}", flush=True)
    if not improved: break
m.pos = pos; m.anneal(20000, 1, T0=100, step0=15)   # мелкая доводка
m.apply()
P, X = m.penalty(m.pos, detail=True); issues = ea.check(objs, links)
json.dump({"score": float(sum(P.values())), "cross": X, "issues": issues,
           "pos": {str(k): [v["cx"], v["cy"], v["w"], v["h"]] for k, v in objs.items()}}, open(f"out/{sys.argv[2]}.json", "w"), ensure_ascii=False)
ea.render(objs, links, f"out/{sys.argv[2]}.png")
print(f"final score {sum(P.values()):.0f} cross {X} issues {len(issues)}"); print("\n".join(issues))

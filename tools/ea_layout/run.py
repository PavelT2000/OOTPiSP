"""python run.py SEED ITERS [ANCHOR] — одна попытка раскладки; результат в out/"""
import json, os, sys, time
import ea
from opt import Model
QEA = os.path.join(os.path.dirname(__file__), "..", "..", "Lab1", "Touragency.qea")
os.makedirs("out", exist_ok=True)
objs, links = ea.load(QEA)
for o in objs.values():
    if o["type"] == "Actor": o["w"], o["h"] = 45, 90
    else: o["w"], o["h"] = ea.min_size(o["name"])
seed, iters = int(sys.argv[1]), int(sys.argv[2])
START = os.environ.get("START")
if START:
    for k, (x, y, w, h) in json.load(open(START))["pos"].items():
        objs[int(k)].update(cx=x, cy=y, w=w, h=h)
T0, STEP = float(os.environ.get("T0", 6000)), float(os.environ.get("STEP", 150))
m = Model(objs, links, anchor_w=float(sys.argv[3]) if len(sys.argv) > 3 else 0.0)
t = time.time(); m.anneal(iters, seed, T0=T0, step0=STEP); P, X = m.penalty(m.pos, detail=True)
m.apply()
issues = ea.check(objs, links)
json.dump({"score": float(sum(P.values())), "cross": X, "issues": issues,
           "pos": {str(k): [v["cx"], v["cy"], v["w"], v["h"]] for k, v in objs.items()}}, open(f"out/pos_{os.environ.get('OUT', seed)}.json", "w"), ensure_ascii=False)
ea.render(objs, links, f"out/r_{os.environ.get('OUT', seed)}.png")
print(f"seed {seed}: {time.time() - t:.0f}s score {sum(P.values()):.0f} cross {X} issues {len(issues)}")

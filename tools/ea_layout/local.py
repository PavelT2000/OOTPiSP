"""Локальная доводка: двигаются только MOVE, остальные зафиксированы."""
import json, math, random, sys, os
import numpy as np
import ea
from opt import Model
objs, links = ea.load("../../Lab1/Touragency.qea")
NEW = {201: "Подтвердить бронирование тура", 202: "Получить оплату за тур"}
init = json.load(open("out/new.json"))
SEED = {201: (1680, 60), 202: (1840, 75), 17: (1690, 230), 16: (1820, 320), 18: (1720, 380), 14: (1560, 410)}
for k, n in NEW.items():
    x, y, w, h = init[str(k)]; objs[k] = dict(name=n, type="UseCase", w=w, h=h, cx=x, cy=y)
for k, (x, y) in SEED.items(): objs[k]["cx"], objs[k]["cy"] = x, y
if os.environ.get('START'):
    for k, (x, y, w, h) in json.load(open(os.environ['START']))['pos'].items(): objs[int(k)].update(cx=x, cy=y)
NL = [(301, "extend", "UseCase", 44, 201), (302, None, "UseCase", 17, 201), (303, "extend", "UseCase", 201, 202)]
for cid, st, t, s, e in NL: links.append(dict(id=cid, stereo=st, type=t, s=s, e=e))
import os
MOVE = [int(x) for x in os.environ.get('MOVE', '201,202,17,16,18,14,44,13,15,23,27').split(',')]
m = Model(objs, links, anchor_w=0.002)
mv = [m.idx[k] for k in MOVE]
seed = int(sys.argv[1]); rng = random.Random(seed)
pos = m.pos.copy(); cur = m.penalty(pos); best, bp = cur, pos.copy()
N = 40000
for k in range(N):
    f = k / N; T = 2000 * (3 / 2000) ** f; st = 80 * (3 / 80) ** f
    i = rng.choice(mv); old = pos[i].copy()
    pos[i] = old + [rng.gauss(0, st), rng.gauss(0, st)]
    v = m.penalty(pos)
    if v < cur or rng.random() < math.exp((cur - v) / T): cur = v
    else: pos[i] = old
    if cur < best: best, bp = cur, pos.copy()
m.pos = bp; m.apply()
P, X = m.penalty(bp, detail=True)
I = ea.check(objs, links)
json.dump({"score": float(best), "cross": X, "issues": I, "pos": {str(k): [objs[k]["cx"], objs[k]["cy"], objs[k]["w"], objs[k]["h"]] for k in objs}},
          open(f"out/local2_{seed}.json", "w"), ensure_ascii=False)
ea.render(objs, links, f"out/local2_{seed}.png")
print(f"seed {seed} score {best:.0f} cross {X} issues {len(I)}")

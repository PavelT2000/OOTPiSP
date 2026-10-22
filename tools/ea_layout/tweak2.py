import json, sys
import ea
objs, links = ea.load("../../models/Touragency.qea")
d = json.load(open(sys.argv[1]))
NEW = {201: "Подтвердить бронирование тура", 202: "Получить оплату за тур"}
for k, (x, y, w, h) in d["pos"].items():
    k = int(k)
    if k in NEW: objs[k] = dict(name=NEW[k], type="UseCase", w=w, h=h, cx=x, cy=y)
    else: objs[k].update(cx=x, cy=y, w=w, h=h)
links += [dict(id=301, stereo="extend", type="UseCase", s=44, e=201), dict(id=302, stereo=None, type="UseCase", s=17, e=201),
          dict(id=303, stereo="extend", type="UseCase", s=201, e=202)]
for k, (x, y) in json.loads(sys.argv[2]).items(): objs[int(k)].update(cx=x, cy=y)
I = [i for i in ea.check(objs, links) if "70 (48->24)" not in i]
print("\n".join(I) or "OK")
ea.render(objs, links, "out/tweak2.png")
json.dump({"pos": {str(k): [v["cx"], v["cy"], v["w"], v["h"]] for k, v in objs.items()}}, open("out/tweak2.json", "w"), ensure_ascii=False)

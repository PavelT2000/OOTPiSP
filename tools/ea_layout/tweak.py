import json, sys
import ea
objs, links = ea.load("../../models/Touragency.qea")
d = json.load(open(sys.argv[1]))
for k, (x, y, w, h) in d["pos"].items(): objs[int(k)].update(cx=x, cy=y, w=w, h=h)
for k, (x, y) in json.loads(sys.argv[2]).items(): objs[int(k)].update(cx=x, cy=y)
I = ea.check(objs, links); print("\n".join(I) or "OK")
ea.render(objs, links, "out/tweak.png")
json.dump({"pos": {str(k): [v["cx"], v["cy"], v["w"], v["h"]] for k, v in objs.items()}, "issues": I}, open("out/tweak.json", "w"), ensure_ascii=False)

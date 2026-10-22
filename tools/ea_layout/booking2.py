import json, sys
import ea
objs, links = ea.load("../../Lab1/Touragency.qea")
del objs[44]
links = [l for l in links if 44 not in (l["s"], l["e"]) and l["id"] != 73]
objs[51]["w"], objs[51]["h"] = ea.min_size(objs[51]["name"])
objs[940] = dict(objs[40]); objs[940]["w"], objs[940]["h"] = 45, 90     # второй экземпляр «Платежной системы»
links += [dict(id=901, stereo="extend", type="UseCase", s=13, e=50), dict(id=902, stereo="extend", type="UseCase", s=13, e=51),
          dict(id=903, stereo=None, type="Association", s=940, e=51)]
M = json.loads(sys.argv[1])
for k, (x, y) in M.items(): objs[int(k)].update(cx=x, cy=y)
I = [i for i in ea.check(objs, links) if "70 (48->24)" not in i]
print("\n".join(I) or "OK", "\n51 size", objs[51]["w"], objs[51]["h"])
ea.render(objs, links, "out/b2.png")
json.dump({k: [objs[int(k)]["cx"], objs[int(k)]["cy"], objs[int(k)]["w"], objs[int(k)]["h"]] for k in list(M) + ["51"]}, open("out/b2.json", "w"))

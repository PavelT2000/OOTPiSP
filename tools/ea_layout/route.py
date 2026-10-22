"""Маршрут связи в обход элементов (A* по сетке) с минимумом изгибов."""
import heapq, math, sys, sqlite3
import ea
CID = int(sys.argv[1]); STEP = 10
objs, links = ea.load("../../Lab1/Touragency.qea")
L = next(l for l in links if l["id"] == CID)
W, H = 1880, 880
nx, ny = W // STEP, H // STEP
def blocked(x, y, skip):
    for oid, o in objs.items():
        if oid in skip: continue
        if ea.inside(o, x, y, 12): return True
    return False
skip = {L["s"], L["e"]}
grid = [[blocked(i * STEP, j * STEP, skip) for j in range(ny)] for i in range(nx)]
# другие связи — мягкое препятствие (штраф за пересечение)
segs = [ea.ends(objs, l) for l in links if l["id"] != CID]
s, e = objs[L["s"]], objs[L["e"]]
start = (round(s["cx"] / STEP), round(s["cy"] / STEP)); goal = (round(e["cx"] / STEP), round(e["cy"] / STEP))
def free(c):
    i, j = c
    if not (0 <= i < nx and 0 <= j < ny): return False
    x, y = i * STEP, j * STEP
    if ea.inside(s, x, y) or ea.inside(e, x, y): return True
    return not grid[i][j]
D = [(1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)]
pq = [(0, 0, start, None)]; best = {(start, None): 0}; prev = {}
while pq:
    f, g, c, d = heapq.heappop(pq)
    if c == goal: break
    for dd in D:
        n = (c[0] + dd[0], c[1] + dd[1])
        if not free(n): continue
        ng = g + math.hypot(*dd) + (8 if d is not None and dd != d else 0)   # штраф за поворот
        key = (n, dd)
        if ng < best.get(key, 1e18):
            best[key] = ng; prev[key] = (c, d)
            heapq.heappush(pq, (ng + math.dist(n, goal), ng, n, dd))
key = (c, d); path = [c]
while key in prev:
    key = prev[key]; path.append(key[0])
path = [(x * STEP, y * STEP) for x, y in reversed(path)]
# точки изгиба
bends = [path[i] for i in range(1, len(path) - 1)
         if (path[i][0] - path[i - 1][0], path[i][1] - path[i - 1][1]) != (path[i + 1][0] - path[i][0], path[i + 1][1] - path[i][1])]
# упрощение: убираем изгибы, если отрезок между соседями свободен
def clear(a, b):
    n = int(math.dist(a, b) / 4) + 1
    return all(free((round((a[0] + (b[0] - a[0]) * k / n) / STEP), round((a[1] + (b[1] - a[1]) * k / n) / STEP))) for k in range(n + 1))
pts = [(s["cx"], s["cy"])] + bends + [(e["cx"], e["cy"])]
i = 0
while i < len(pts) - 2:
    if clear(pts[i], pts[i + 2]): pts.pop(i + 1)
    else: i += 1
bends = pts[1:-1]
print("изгибы:", bends)
if len(sys.argv) > 2 and sys.argv[2] == "save":
    db = sqlite3.connect("../../Lab1/Touragency.qea")
    db.execute("update t_diagramlinks set Path=? where ConnectorID=?", ("".join(f"{round(x)}:{-round(y)}$" for x, y in bends), CID))
    db.commit(); print("записано,", db.execute("pragma integrity_check").fetchone()[0])
# картинка
from PIL import ImageDraw, Image
ea.render(objs, links, "out/route.png")
img = Image.open("out/route.png"); d = ImageDraw.Draw(img)
d.line([(s["cx"], s["cy"])] + bends + [(e["cx"], e["cy"])], fill="red", width=3); img.save("out/route.png")

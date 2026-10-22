"""Имитация отжига для расстановки элементов use-case диаграммы."""
import math, random
import numpy as np
from ea import tw

W_MAX, H_MAX, PAD = 1880, 870, 6


class Model:
    def __init__(self, objs, links, anchor_w=0.0):
        self.ids = list(objs); self.idx = {o: i for i, o in enumerate(self.ids)}; self.n = len(self.ids)
        self.objs = objs
        self.W = np.array([objs[o]["w"] for o in self.ids], float); self.H = np.array([objs[o]["h"] for o in self.ids], float)
        self.is_uc = np.array([objs[o]["type"] == "UseCase" for o in self.ids])
        self.pos = np.array([[objs[o]["cx"], objs[o]["cy"]] for o in self.ids], float)
        self.anchor = self.pos.copy(); self.aw = anchor_w
        self.lw = np.array([tw(objs[o]["name"]) + 8 if objs[o]["type"] == "Actor" else 0 for o in self.ids])
        self.S = np.array([self.idx[l["s"]] for l in links]); self.E = np.array([self.idx[l["e"]] for l in links])
        self.has_label = np.array([bool(l["stereo"]) for l in links])
        self.lmin = np.where(self.has_label, 90.0, 50.0)
        m = len(links)
        self.cross_mask = np.array([[len({self.S[i], self.E[i], self.S[j], self.E[j]}) == 4 and i < j for j in range(m)] for i in range(m)])
        self.actors = np.where(~self.is_uc)[0]

    @staticmethod
    def rad(a, b, ell, ux, uy, exact=False):
        re = 1 / np.sqrt((ux / a) ** 2 + (uy / b) ** 2 + 1e-12)
        rb = (np.minimum(a / (np.abs(ux) + 1e-9), b / (np.abs(uy) + 1e-9)) if exact
              else 1 / np.sqrt((ux / (a * 1.3)) ** 2 + (uy / (b * 1.3)) ** 2 + 1e-12))
        return np.where(ell, re, rb)

    def penalty(self, pos, detail=False):
        P = {}
        cx, cy = pos[:, 0], pos[:, 1]; ac = self.actors
        # препятствия: фигуры + подписи актёров
        ocx = np.concatenate([cx, cx[ac]]); ocy = np.concatenate([cy, cy[ac] + self.H[ac] / 2 + 13])
        oa = np.concatenate([self.W / 2, self.lw[ac] / 2]); ob = np.concatenate([self.H / 2, np.full(len(ac), 11.0)])
        ell = np.concatenate([self.is_uc, np.zeros(len(ac), bool)]); own = np.concatenate([np.arange(self.n), ac])
        dx = ocx[None, :] - ocx[:, None]; dy = ocy[None, :] - ocy[:, None]; d = np.hypot(dx, dy) + 1e-9
        r1 = self.rad(oa[:, None], ob[:, None], ell[:, None], dx / d, dy / d)
        r2 = self.rad(oa[None, :], ob[None, :], ell[None, :], dx / d, dy / d)
        ov = np.maximum(0, r1 + r2 + 18 - d); ov[own[:, None] == own[None, :]] = 0
        P["overlap"] = 10 * np.sum(np.triu(ov, 1) ** 2)
        # отрезки связей между границами фигур
        s, e = pos[self.S], pos[self.E]; dd = e - s; L = np.hypot(dd[:, 0], dd[:, 1]) + 1e-9
        ux, uy = dd[:, 0] / L, dd[:, 1] / L
        rs = self.rad(self.W[self.S] / 2, self.H[self.S] / 2, self.is_uc[self.S], ux, uy, True)
        rE = self.rad(self.W[self.E] / 2, self.H[self.E] / 2, self.is_uc[self.E], ux, uy, True)
        p = s + np.stack([ux * rs, uy * rs], 1); q = e - np.stack([ux * rE, uy * rE], 1); glen = L - rs - rE
        # связь сквозь чужую фигуру
        A = (oa + 10)[None, :]; B = (ob + 10)[None, :]
        px = (p[:, :1] - ocx) / A; py = (p[:, 1:] - ocy) / B; qx = (q[:, :1] - ocx) / A; qy = (q[:, 1:] - ocy) / B
        vx, vy = qx - px, qy - py; t = np.clip(-(px * vx + py * vy) / (vx * vx + vy * vy + 1e-12), 0, 1)
        hit = np.maximum(0, 1 - np.hypot(px + t * vx, py + t * vy)) * np.minimum(A, B)
        endo = (own[None, :] == self.S[:, None]) | (own[None, :] == self.E[:, None])
        hit[endo & (np.arange(len(ocx))[None, :] < self.n)] = 0
        P["through"] = 150 * np.sum(hit ** 2)
        # подписи «extend»/«include» в середине связи
        mid = (p + q) / 2; lab = np.where(self.has_label)[0]; lcx, lcy = mid[lab, 0], mid[lab, 1]
        dx = ocx[None, :] - lcx[:, None]; dy = ocy[None, :] - lcy[:, None]; d = np.hypot(dx, dy) + 1e-9
        r1 = 1 / np.sqrt((dx / d / 40) ** 2 + (dy / d / 13) ** 2 + 1e-12)
        r2 = self.rad(oa[None, :], ob[None, :], ell[None, :], dx / d, dy / d)
        P["lab"] = 4 * np.sum(np.maximum(0, r1 + r2 + 2 - d) ** 2)
        dx = lcx[None, :] - lcx[:, None]; dy = lcy[None, :] - lcy[:, None]; d = np.hypot(dx, dy) + 1e-9
        r = 1 / np.sqrt((dx / d / 40) ** 2 + (dy / d / 13) ** 2 + 1e-12)
        P["labl"] = 4 * np.sum(np.triu(np.maximum(0, 2 * r + 2 - d), 1) ** 2)
        # пересечения связей
        c = lambda ax, ay, bx, by, x, y: (y - ay) * (bx - ax) - (by - ay) * (x - ax)
        a1, a2, b1, b2 = p[:, None, :], q[:, None, :], p[None, :, :], q[None, :, :]
        d1 = c(b1[..., 0], b1[..., 1], b2[..., 0], b2[..., 1], a1[..., 0], a1[..., 1])
        d2 = c(b1[..., 0], b1[..., 1], b2[..., 0], b2[..., 1], a2[..., 0], a2[..., 1])
        d3 = c(a1[..., 0], a1[..., 1], a2[..., 0], a2[..., 1], b1[..., 0], b1[..., 1])
        d4 = c(a1[..., 0], a1[..., 1], a2[..., 0], a2[..., 1], b2[..., 0], b2[..., 1])
        X = (d1 * d2 < 0) & (d3 * d4 < 0) & self.cross_mask
        P["cross"] = 20000 * np.sum(X)
        P["short"] = 6 * np.sum(np.maximum(0, self.lmin - glen) ** 2)
        P["spring"] = 0.01 * np.sum(glen ** 2)
        viol = (np.maximum(0, PAD - (ocx - oa)) + np.maximum(0, ocx + oa - W_MAX)
                + np.maximum(0, PAD - (ocy - ob)) + np.maximum(0, ocy + ob - H_MAX))
        P["bounds"] = 200 * np.sum(viol ** 2)
        P["anchor"] = self.aw * np.sum((pos - self.anchor) ** 2)
        return (P, int(X.sum())) if detail else sum(P.values())

    def anneal(self, iters, seed, T0=1500, T1=3, step0=60, step1=3):
        rng = random.Random(seed); pos = self.pos.copy(); cur = self.penalty(pos); best, bp = cur, pos.copy()
        for k in range(iters):
            f = k / iters; T = T0 * (T1 / T0) ** f; st = step0 * (step1 / step0) ** f
            i = rng.randrange(self.n); old = pos[i].copy(); j = None
            if rng.random() < 0.08:
                j = rng.randrange(self.n); oj = pos[j].copy(); pos[i], pos[j] = oj.copy(), old.copy()
            else:
                pos[i] = old + [rng.gauss(0, st), rng.gauss(0, st)]
            new = self.penalty(pos)
            if new < cur or rng.random() < math.exp((cur - new) / T):
                cur = new
            else:
                pos[i] = old
                if j is not None: pos[j] = oj
            if cur < best: best, bp = cur, pos.copy()
        self.pos = bp

    def apply(self):
        for i, o in enumerate(self.ids): self.objs[o]["cx"], self.objs[o]["cy"] = map(float, self.pos[i])

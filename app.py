# -*- coding: utf-8 -*-
"""
三角洲行动 · 改枪码库  v3「二次美化版」
数据源: https://delta-code.cn/api/loadouts

相对原版 v2 的变化：
  · 双主题（暗 / 亮）一键切换，五级表面层次（root / header / side / panel / card）
  · 自绘 Canvas 数据表：逐单元格配色、家族色点、行 hover、强调色选中条
  · 左侧武器家族筛选栏（按真实数据聚合 + 计数）
  · 胶囊搜索框（占位符 / 清除按钮）、自绘扁平按钮三态
  · 表头点击排序 + ▲▼ 指示；侧栏造价 / 复制 / 更新时间排序控件
  · 右侧详情卡：家族徽标、标签 chip、等宽改枪码框、复制反馈
  · 键盘：Ctrl+F / Ctrl+R / F5 / Ctrl+C / Esc / ↑↓ / Enter / Ctrl+Q
  · 状态栏：显示条数 / 缓存时间 / 状态灯
  · Win11 圆角 + 深色标题栏 + 强调色边框（DWM，失败静默降级）

数据格式、API、缓存路径、单实例互斥量与原版完全兼容。
"""
import ctypes
import gzip
import http.client
import json
import os
import re
import shutil
import ssl
import sys
import threading
import time
import tkinter as tk
from tkinter import ttk, messagebox, font as tkfont

# DPI 感知必须在 Tk 创建前开启
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

# ────────────────────────────────────────────────────────────── 常量
APP_NAME = "三角洲行动 改枪码库"
APP_SUB = "DELTA FORCE · LOADOUT CODE BROWSER"
HOST = "delta-code.cn"
API_PATH = "/api/loadouts"
HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-CN,zh;q=0.9",
    "Accept-Encoding": "gzip, deflate",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Connection": "keep-alive",
}
CACHE_DIR = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "DeltaCodeViewer")
CACHE_FILE = os.path.join(CACHE_DIR, "cache.json")
MUTEX_NAME = "Global\\DeltaCodeViewer_SingleInstance_v2"

# ────────────────────────────────────────────────────────────── 调色板
PALETTES = {
    "dark": {
        "root": "#080b10", "header": "#0e131b", "side": "#0b0f16",
        "panel": "#0f141d", "card": "#141b26", "card_alt": "#0b1017",
        "input": "#080c12", "hover": "#182131", "pressed": "#22303f",
        "border": "#1a2331", "border_hi": "#2a3849",
        "accent": "#f0a030", "accent_2": "#ffc36b", "accent_dim": "#a8701a", "accent_fg": "#120c04",
        "accent_soft": "#241a0b", "accent_line": "#3a2a12",
        "text": "#e8eef7", "text_sec": "#93a2b6", "text_muted": "#55637a",
        "success": "#3ddc97", "error": "#ff6b6b", "info": "#5aa9ff",
        "select": "#2a1f0d", "select_fg": "#ffd79a",
        "chip": "#18202c", "chip_fg": "#9aabbd", "chip_border": "#232e3d",
        "scroll": "#212c3b", "scroll_hi": "#35455a",
    },
    "light": {
        "root": "#e9edf3", "header": "#ffffff", "side": "#f5f7fb",
        "panel": "#ffffff", "card": "#ffffff", "card_alt": "#f7f9fc",
        "input": "#eef2f7", "hover": "#e8eef6", "pressed": "#dae2ee",
        "border": "#dde4ee", "border_hi": "#c2cddd",
        "accent": "#c9751a", "accent_2": "#a85f0c", "accent_dim": "#e6ab68", "accent_fg": "#ffffff",
        "accent_soft": "#fdf3e3", "accent_line": "#f0dcbd",
        "text": "#16202e", "text_sec": "#55637a", "text_muted": "#8b98a9",
        "success": "#0f9b66", "error": "#d04444", "info": "#2b7fd4",
        "select": "#fdeacb", "select_fg": "#7d4704",
        "chip": "#eef2f7", "chip_fg": "#4f5e74", "chip_border": "#dfe6ef",
        "scroll": "#ccd6e3", "scroll_hi": "#a9b7cc",
    },
}

# 武器家族分类（顺序敏感）
FAMILY_RULES = [
    ("套装", ("套装",)),
    ("狙击枪", ("awm", "m700", "r93", "sv-98", "sv98", "m82", "巴雷特", "psg-1", "psg1")),
    ("射手步枪", ("sr-25", "sr25", "svd", "svch", "m14", "sks", "mini", "vss", "杠杆", "m417")),
    ("冲锋枪", ("mp5", "mp7", "p90", "vector", "smg", "mk4", "汤姆逊", "野牛", "qcq", "勇士", "uzi")),
    ("轻机枪", ("pkm", "m249", "m250", "qjb", "m60", "机枪")),
    ("霰弹枪", ("s12k", "m1014", "fs-12", "fs12", "霰弹", "ks23", "saw")),
    ("手枪", ("93r", "沙鹰", "deagle", "g18", "p226", "手枪")),
    ("特殊", ("弓", "弩", "火箭", "榴弹")),
    ("突击步枪", ("ak", "m4", "m7", "mk47", "k416", "k437", "qbz", "sg552", "aug", "scar",
                  "ash-12", "an94", "ar-57", "ar57", "car-15", "m16", "g3", "ptr-32", "rm277",
                  "腾龙", "mdr", "as val", "sr-3m", "kc17")),
]

FAMILY_COLORS = {
    "突击步枪": "#f97316", "冲锋枪": "#22c55e", "射手步枪": "#3b82f6",
    "狙击枪": "#a855f7", "轻机枪": "#eab308", "霰弹枪": "#ef4444",
    "手枪": "#14b8a6", "套装": "#f0a030", "特殊": "#ec4899", "其他": "#7f8ea6",
    # 任务类分类（不是武器家族，单独着色，一眼区分）
    "金枪客": "#f43f5e",
}

# ────────────────────────────────────────────────────────────── 任务分类
# 任务分类优先于武器家族：同一条配装既能算「突击步枪」，也能算「金枪客任务」。
# 命中规则：tags / name / player / core 任一字段出现关键词即归入该任务。
# 顺序敏感 —— 越靠前优先级越高（目前只有金枪客一个任务分类）。
QUEST_ORDER = ["金枪客"]
QUEST_KEYS = {
    # 只用精确中文关键词：slug 里的随机串（如 6JQKF4409）会误命中 "jqk"，不能放开
    "金枪客": ("金枪客",),
}
QUEST_HINT = {
    "金枪客": "S11 · 金枪客任务链（上交 / 击杀 / 备用）",
}
_QUEST_STEP_RE = re.compile(r"金枪客\s*([0-9]+(?:\s*/\s*[0-9]+)?)\s*$")


def match_quest(it):
    """返回该条配装所属的任务分类名；不属于任何任务返回 None。"""
    if not isinstance(it, dict):
        return None
    blob = " ".join((
        fmt(it.get("tags")), fmt(it.get("name")), fmt(it.get("player")),
        fmt(it.get("core")), fmt(it.get("slug")),
    )).lower()
    for name in QUEST_ORDER:
        for k in QUEST_KEYS[name]:
            if k in blob:
                return name
    return None


def quest_step(it):
    """从 tags 里抽「金枪客4」「金枪客6/7」这类步骤号，返回 (步骤串, 动作)。"""
    step, action = "", ""
    tags = it.get("tags") or []
    for t in tags:
        m = _QUEST_STEP_RE.search(str(t).strip())
        if m:
            step = m.group(1).replace(" ", "")
            break
    for t in tags:
        s = str(t).strip()
        if s in ("上交", "提交", "击杀", "备用", "丐版", "性价比", "机动",
                 "双修", "中远程", "23W", "24W", "21W", "45W"):
            action = s
            break
    return step, action


def bucket_of(it):
    """侧栏分桶：任务分类优先，其次武器家族。"""
    q = match_quest(it)
    if q:
        return q
    return classify(it.get("weapon") if isinstance(it, dict) else it)



def classify(weapon):
    """最长关键词优先：MK47 命中 突击步枪 的 'mk47'(4)，而不是 冲锋枪 的 'mk4'(3)。"""
    w = (weapon or "").lower().strip()
    if not w:
        return "其他"
    best_fam, best_len = None, 0
    for fam, keys in FAMILY_RULES:
        for k in keys:
            if k in w and len(k) > best_len:
                best_fam, best_len = fam, len(k)
    return best_fam or "其他"


def fmt(v):
    if v is None:
        return ""
    if isinstance(v, (list, tuple)):
        return " / ".join(str(x) for x in v)
    return str(v)


def fmt_price(v):
    try:
        return f"{int(v):,}"
    except Exception:
        return fmt(v)


def fmt_date(v):
    s = fmt(v).strip()
    if len(s) >= 10 and s[4] == "-" and s[7] == "-":
        return s[5:10]
    return s


# ────────────────────────────────────────────────────────────── 网络层
_SSL_CTX = ssl.create_default_context()


def new_conn():
    return http.client.HTTPSConnection(HOST, 443, timeout=20, context=_SSL_CTX)


def fetch_page(conn, page, retries=3):
    path = f"{API_PATH}?page={page}"
    last = None
    for _ in range(retries):
        try:
            conn.request("GET", path, headers=HEADERS)
            resp = conn.getresponse()
            body = resp.read()
            if resp.status != 200:
                raise RuntimeError(f"HTTP {resp.status}")
            enc = (resp.getheader("Content-Encoding") or "").lower()
            if "gzip" in enc:
                body = gzip.decompress(body)
            return json.loads(body.decode("utf-8"))
        except Exception as e:
            last = e
            time.sleep(0.4)
    raise last


def fetch_all(on_page=None):
    conn = new_conn()
    first = fetch_page(conn, 1)
    items = list(first.get("loadouts") or [])
    pages = int(first.get("totalPages") or 1)
    total = int(first.get("total") or len(items))
    if on_page:
        on_page(list(items), 1, pages, total)
    failed = []
    try:
        for p in range(2, pages + 1):
            try:
                items += list(fetch_page(conn, p).get("loadouts") or [])
            except Exception:
                failed.append(p)
            if on_page:
                on_page(list(items), p, pages, total)
            time.sleep(0.03)
    finally:
        try:
            conn.close()
        except Exception:
            pass
    return items, total, failed


# ────────────────────────────────────────────────────────────── 缓存
def load_cache():
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            d = json.load(f)
        return d.get("items") or [], d.get("saved_at") or ""
    except Exception:
        return [], ""


def save_cache(items):
    try:
        os.makedirs(CACHE_DIR, exist_ok=True)
        tmp = CACHE_FILE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump({"saved_at": time.strftime("%Y-%m-%d %H:%M"), "items": items},
                      f, ensure_ascii=False)
        os.replace(tmp, CACHE_FILE)
    except Exception:
        pass


def _find_icon():
    cands = []
    if getattr(sys, "frozen", False):
        cands.append(getattr(sys, "_MEIPASS", os.path.dirname(sys.executable)))
        cands.append(os.path.dirname(sys.executable))
    cands.append(os.path.dirname(os.path.abspath(__file__)))
    for d in cands:
        p = os.path.join(d, "icon.ico")
        if os.path.exists(p):
            return p
    return None


# ────────────────────────────────────────────────────────────── 自绘控件
class FlatButton(tk.Frame):
    """扁平按钮，支持 accent / ghost 两种风格与 hover / press / 临时提示。"""

    def __init__(self, master, text, command, pal, kind="ghost",
                 font=None, padx=14, pady=7, host_bg=None):
        self.pal = pal
        self.kind = kind
        self.command = command
        self.host_bg = host_bg or pal["header"]
        base = pal["accent"] if kind == "accent" else pal["card"]
        super().__init__(master, bg=self.host_bg, bd=0, highlightthickness=0)
        self.fg = pal.get("accent_fg", pal["root"]) if kind == "accent" else pal["text_sec"]
        self.lbl = tk.Label(self, text=text, bg=base, fg=self.fg, font=font,
                            padx=padx, pady=pady, cursor="hand2", bd=0)
        self.lbl.pack()
        for w in (self, self.lbl):
            w.bind("<Enter>", self._enter)
            w.bind("<Leave>", self._leave)
            w.bind("<Button-1>", self._press)
            w.bind("<ButtonRelease-1>", self._release)

    def _base(self):
        return self.pal["accent"] if self.kind == "accent" else (
            self.pal["card"] if self.kind == "ghost" else self.host_bg)

    def _hover(self):
        return self.pal["accent_2"] if self.kind == "accent" else self.pal["hover"]

    def _enter(self, _=None):
        self.lbl.configure(bg=self._hover())
        self.configure(bg=self._hover())

    def _leave(self, _=None):
        self.lbl.configure(bg=self._base())
        self.configure(bg=self._base())

    def _press(self, _=None):
        self.lbl.configure(bg=self.pal["accent_dim"] if self.kind == "accent"
                           else self.pal["pressed"])

    def _release(self, _=None):
        self._leave()
        if self.command:
            self.command()

    def set_text(self, text, fg=None):
        self.lbl.configure(text=text)
        if fg:
            self.lbl.configure(fg=fg)

    def flash(self, text, fg, ms=1400):
        old_t, old_f = self.lbl.cget("text"), self.lbl.cget("fg")
        self.lbl.configure(text=text, fg=fg)
        self.after(ms, lambda: self.lbl.configure(text=old_t, fg=old_f))


class SearchPill(tk.Frame):
    """胶囊搜索框。"""

    PLACEHOLDER = "搜索武器 / 配装 / 作者 / 改枪码"

    def __init__(self, master, pal, on_change, family):
        super().__init__(master, bg=pal["input"], bd=0, highlightthickness=1,
                         highlightbackground=pal["border"], highlightcolor=pal["accent"])
        self.pal = pal
        self.on_change = on_change
        self._ph = False

        tk.Label(self, text="⌕", bg=pal["input"], fg=pal["text_muted"],
                 font=(family, 14), bd=0).pack(side="left", padx=(12, 3), pady=2)
        self.var = tk.StringVar()
        self.entry = tk.Entry(self, textvariable=self.var, bd=0, relief="flat",
                              bg=pal["input"], fg=pal["text"],
                              insertbackground=pal["accent"], font=(family, 10),
                              highlightthickness=0, width=26)
        self.entry.pack(side="left", fill="both", expand=True, ipady=6, pady=2)
        self.clear = tk.Label(self, text="✕", bg=pal["input"], fg=pal["text_muted"],
                              font=(family, 9), cursor="hand2")
        self.clear.pack(side="right", padx=(2, 11))
        self.clear.bind("<Button-1>", lambda e: self.clear_all())

        self.entry.bind("<FocusIn>", self._focus_in)
        self.entry.bind("<FocusOut>", self._focus_out)
        self.var.trace_add("write", lambda *a: self.on_change())
        self._show_ph()

    def _show_ph(self):
        if not self.var.get():
            self._ph = True
            self.entry.configure(fg=self.pal["text_muted"])
            self.entry.insert(0, self.PLACEHOLDER)

    def _focus_in(self, _=None):
        if self._ph:
            self.entry.delete(0, "end")
            self._ph = False
            self.entry.configure(fg=self.pal["text"])

    def _focus_out(self, _=None):
        if not self.var.get().strip():
            self._ph = False
            self.entry.delete(0, "end")
            self._show_ph()

    def text(self):
        return "" if self._ph else self.var.get().strip()

    def set_text(self, s):
        self._ph = False
        self.entry.delete(0, "end")
        self.entry.configure(fg=self.pal["text"])
        self.var.set(s)
        if not s:
            self._show_ph()

    def clear_all(self):
        self.entry.delete(0, "end")
        self._ph = False
        self.on_change()
        self.entry.focus_set()

    def focus(self):
        self.entry.focus_set()
        self.entry.select_range(0, "end")


class CanvasTable(tk.Frame):
    """自绘表格：逐单元格颜色、家族色点、hover 行、强调色选中条。"""

    ROW_H = 34

    def __init__(self, master, pal, cols, family, on_select=None, on_activate=None):
        super().__init__(master, bg=pal["panel"], bd=0)
        self.pal = pal
        self.cols = cols            # [(key, title, width|None, anchor, mono)]
        self.fam_font = family
        self.on_select = on_select
        self.on_activate = on_activate
        self.rows = []
        self.top = 0
        self.sel = -1
        self.hover = -1
        self.sort_key = "updatedAt"
        self.sort_rev = True
        self._kinds = {"weapon", "name", "player", "price", "copy_times", "updatedAt"}

        self.head = tk.Canvas(self, height=36, bg=pal["header"], bd=0,
                              highlightthickness=0)
        self.head.pack(fill="x")
        self.body = tk.Canvas(self, bg=pal["panel"], bd=0, highlightthickness=0)
        self.body.pack(side="left", fill="both", expand=True)
        self.vsb = ttk.Scrollbar(self, orient="vertical",
                                 style="Slim.Vertical.TScrollbar",
                                 command=self._scroll_cmd)
        self.vsb.pack(side="right", fill="y")

        self.head.bind("<Button-1>", self._head_click)
        self.head.bind("<Motion>", self._head_motion)
        self.head.bind("<Leave>", lambda e: (self.head.configure(cursor=""),
                                            self._draw_head()))
        self.body.bind("<Button-1>", self._click)
        self.body.bind("<Double-Button-1>", self._dbl)
        self.body.bind("<Motion>", self._motion)
        self.body.bind("<Leave>", lambda e: self._set_hover(-1))
        self.body.bind("<Configure>", lambda e: self._redraw())
        self.body.bind("<MouseWheel>", self._wheel)
        self.head.bind("<Configure>", lambda e: self._draw_head())

    # ── 尺寸
    def _width(self):
        return max(320, self.body.winfo_width())

    def _layout(self):
        """返回 [(key, title, x, w, anchor, mono)]，name 列吃掉剩余宽度。"""
        total = self._width()
        fixed = sum(c[2] or 0 for c in self.cols if c[0] != "name")
        stretch = max(180, total - fixed - 8)
        out, x = [], 0
        for key, title, w, anchor, mono in self.cols:
            ww = stretch if key == "name" else (w or 0)
            out.append((key, title, x, ww, anchor, mono))
            x += ww
        return out

    def _visible(self):
        h = max(1, self.body.winfo_height())
        return max(1, (h // self.ROW_H) + 1)

    # ── 绘制
    def _draw_head(self):
        p = self.pal
        c = self.head
        c.delete("all")
        w = max(self.body.winfo_width(), c.winfo_width())
        c.create_rectangle(0, 0, w, 36, fill=p["header"], outline="")
        c.create_line(0, 35, w, 35, fill=p["border"])
        for key, title, x, ww, anchor, _mono in self._layout():
            arrow = ""
            if key == self.sort_key:
                arrow = "  ▼" if self.sort_rev else "  ▲"
            col = p["accent"] if key == self.sort_key else p["text_muted"]
            if anchor == "e":
                c.create_text(x + ww - 14, 18, text=title + arrow, anchor="e",
                              fill=col, font=(self.fam_font, 9, "bold"))
            elif anchor == "center":
                c.create_text(x + ww // 2, 18, text=title + arrow, anchor="center",
                              fill=col, font=(self.fam_font, 9, "bold"))
            else:
                c.create_text(x + 16, 18, text=title + arrow, anchor="w",
                              fill=col, font=(self.fam_font, 9, "bold"))

    def _cell_text(self, it, key):
        if key == "weapon":
            return fmt(it.get("weapon"))
        if key == "quest_step":
            step, _a = quest_step(it)
            return step
        if key == "name":
            return fmt(it.get("name"))
        if key == "player":
            return fmt(it.get("player"))
        if key == "price":
            v = it.get("price")
            s = fmt_price(v)
            return s
        if key == "copy_times":
            return fmt(it.get("copy_times"))
        if key == "updatedAt":
            return fmt_date(it.get("updatedAt"))
        return ""

    def _cell_color(self, it, key, base_sel):
        p = self.pal
        if base_sel:
            if key == "weapon":
                return p["select_fg"]
            return p["select_fg"] if key in ("price", "name") else p["text_sec"]
        if key == "weapon":
            q = match_quest(it)
            if q:
                return FAMILY_COLORS.get(q, p["text"])
            return FAMILY_COLORS.get(classify(it.get("weapon")), p["text"])
        if key == "name":
            return p["text"]
        if key == "quest_step":
            step, _a = quest_step(it)
            return FAMILY_COLORS.get("金枪客", p["info"]) if step else p["text_muted"]
        if key == "player":
            return p["text_sec"]
        if key == "price":
            try:
                return p["accent"] if int(it.get("price") or 0) > 0 else p["text_muted"]
            except Exception:
                return p["text_muted"]
        if key == "copy_times":
            return p["info"]
        return p["text_muted"]

    def _redraw(self):
        p = self.pal
        c = self.body
        c.delete("all")
        w = self._width()
        n = len(self.rows)
        vis = self._visible()
        self._clamp()
        end = min(n, self.top + vis)
        self._draw_head()

        if n == 0:
            c.create_text(w // 2, 60, text="暂无数据 · 点右上「刷新」拉取",
                          fill=p["text_muted"], font=(self.fam_font, 10))
            self.vsb.set(0, 1)
            return

        for idx in range(self.top, end):
            y = (idx - self.top) * self.ROW_H
            it = self.rows[idx]
            sel = (idx == self.sel)
            hov = (idx == self.hover)
            bg = p["select"] if sel else (p["hover"] if hov else
                                          (p["card_alt"] if idx % 2 else p["panel"]))
            c.create_rectangle(0, y, w, y + self.ROW_H, fill=bg, outline="")
            if sel:
                c.create_rectangle(0, y, 3, y + self.ROW_H, fill=p["accent"], outline="")
            if idx > self.top:
                c.create_line(0, y, w, y, fill=p["border"])

            lay = self._layout()
            for key, _t, x, ww, anchor, mono in lay:
                txt = self._cell_text(it, key)
                col = self._cell_color(it, key, sel)
                font = (mono if mono else self.fam_font, 10)
                if key == "weapon":
                    fam = classify(it.get("weapon"))
                    q = match_quest(it)
                    if q:
                        cx, cy = x + 19.5, y + 18.5
                        c.create_polygon(cx, cy - 5, cx + 5, cy, cx, cy + 5, cx - 5, cy,
                                         fill=FAMILY_COLORS.get(q, p["text_muted"]),
                                         outline="")
                    else:
                        c.create_oval(x + 16, y + 15, x + 23, y + 22,
                                      fill=FAMILY_COLORS.get(fam, p["text_muted"]), outline="")
                    c.create_text(x + 32, y + self.ROW_H // 2, text=txt, anchor="w",
                                  fill=col, font=font)

                elif anchor == "e":
                    c.create_text(x + ww - 14, y + self.ROW_H // 2, text=txt, anchor="e",
                                  fill=col, font=font)
                elif anchor == "center":
                    c.create_text(x + ww // 2, y + self.ROW_H // 2, text=txt,
                                  anchor="center", fill=col, font=font)
                else:
                    limit = max(6, int(ww / (9.5 if mono else 7.6)))
                    shown = txt if len(txt) <= limit else txt[:limit - 1] + "…"
                    c.create_text(x + 16, y + self.ROW_H // 2, text=shown, anchor="w",
                                  fill=col, font=font)
        self._sync()

    def _sync(self):
        n = len(self.rows)
        if n == 0:
            self.vsb.set(0, 1)
            return
        vis = self._visible() - 1
        first = self.top / n
        last = min(1.0, (self.top + max(vis, 1)) / n)
        self.vsb.set(first, last)

    def _clamp(self):
        n = len(self.rows)
        vis = self._visible() - 1
        self.top = max(0, min(self.top, max(0, n - vis)))

    # ── 交互
    def _scroll_cmd(self, *args):
        n = len(self.rows)
        vis = self._visible() - 1
        if args and args[0] == "moveto":
            self.top = int(float(args[1]) * n)
        elif args and args[0] == "scroll":
            step = max(1, vis - 1) if args[2] == "pages" else 3
            self.top += int(args[1]) * step
        self._redraw()

    def _wheel(self, e):
        delta = int(-e.delta / 120) if abs(e.delta) >= 120 else (-1 if e.delta > 0 else 1)
        self.top += delta * 3
        self._redraw()

    def _row_at(self, y):
        idx = self.top + int(y // self.ROW_H)
        return idx if 0 <= idx < len(self.rows) else -1

    def _click(self, e):
        idx = self._row_at(e.y)
        if idx >= 0:
            self.select(idx)
        self.body.focus_set()

    def _dbl(self, e):
        idx = self._row_at(e.y)
        if idx >= 0 and self.on_activate:
            self.select(idx)
            self.on_activate(self.rows[idx])

    def _motion(self, e):
        idx = self._row_at(e.y)
        self._set_hover(idx)
        self.body.configure(cursor="hand2" if idx >= 0 else "")

    def _set_hover(self, idx):
        if idx != self.hover:
            self.hover = idx
            self._redraw()

    def _head_motion(self, e):
        for key, _t, x, ww, _a, _m in self._layout():
            if x <= e.x <= x + ww:
                self.head.configure(cursor="hand2")
                return
        self.head.configure(cursor="")

    def _head_click(self, e):
        for key, _t, x, ww, _a, _m in self._layout():
            if x <= e.x <= x + ww and key in self._kinds:
                self.set_sort(key)
                return

    def set_sort(self, key):
        if self.sort_key == key:
            self.sort_rev = not self.sort_rev
        else:
            self.sort_key = key
            self.sort_rev = key in ("price", "copy_times", "updatedAt")
        if self.on_select:
            self.on_select(None, sort_only=True)
        self._redraw()

    def select(self, idx):
        if not (0 <= idx < len(self.rows)):
            return
        self.sel = idx
        self._ensure_visible(idx)
        self._redraw()
        if self.on_select:
            self.on_select(self.rows[idx])

    def _ensure_visible(self, idx):
        vis = self._visible() - 1
        if idx < self.top:
            self.top = idx
        elif idx >= self.top + vis:
            self.top = idx - vis + 1
        self._clamp()

    def move(self, delta):
        if not self.rows:
            return
        nxt = 0 if self.sel < 0 else self.sel + delta
        self.select(max(0, min(nxt, len(self.rows) - 1)))

    def set_rows(self, rows, keep_sel_id=None):
        self.rows = rows
        self.sel = -1
        if keep_sel_id:
            for i, it in enumerate(rows):
                if it.get("id") == keep_sel_id or it.get("code") == keep_sel_id:
                    self.sel = i
                    self._ensure_visible(i)
                    break
        self._redraw()

    def cancel_selection(self):
        self.sel = -1
        self._redraw()


# ────────────────────────────────────────────────────────────── 主窗口
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.theme = os.environ.get("DFCV_THEME", "dark")
        if self.theme not in PALETTES:
            self.theme = "dark"
        self.pal = dict(PALETTES[self.theme])

        self.items = []
        self.filtered = []
        self.family = "全部"
        self.sort_key = "updatedAt"
        self.sort_rev = True
        self.selected = None
        self.cur = None
        self._loading = False
        self._search_job = None
        self._spin_job = None
        self._spin_frame = 0
        self.cache_saved_at = ""

        self.title(APP_NAME)
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        w = min(1420, max(1040, sw - 200))
        h = min(880, max(640, sh - 180))
        self.geometry(f"{w}x{h}+{max(0, (sw - w) // 2)}+{max(0, (sh - h) // 2 - 30)}")
        self.minsize(1000, 620)
        self.configure(bg=self.pal["root"])

        self.fam = self._pick_font(["Microsoft YaHei UI", "Microsoft YaHei", "PingFang SC",
                                    "Noto Sans CJK SC", "Segoe UI"], 10)
        self.fmono = self._pick_font(["Cascadia Mono", "Consolas", "JetBrains Mono",
                                      "DejaVu Sans Mono", "Courier New"], 10)

        ico = _find_icon()
        if ico:
            try:
                self.iconbitmap(ico)
            except Exception:
                pass

        self._build_styles()
        self._build_ui()
        self._bind_keys()
        self.after(30, self._native_chrome)
        self._load_cached()
        self.refresh()

    # ── 字体 / 外观
    @staticmethod
    def _pick_font(cands, size):
        have = set(tkfont.families())
        for c in cands:
            if c in have:
                return (c, size)
        return (cands[-1], size)

    def _native_chrome(self):
        try:
            hwnd = ctypes.windll.user32.GetParent(self.winfo_id()) or self.winfo_id()
            dwm = ctypes.windll.dwmapi
            v = ctypes.c_int(1 if self.theme == "dark" else 0)
            dwm.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(v), ctypes.sizeof(v))
            pref = ctypes.c_int(2)
            dwm.DwmSetWindowAttribute(hwnd, 33, ctypes.byref(pref), ctypes.sizeof(pref))
            rgb = self.pal["border"].lstrip("#")
            bgr = int(rgb[4:6] + rgb[2:4] + rgb[0:2], 16)
            col = ctypes.c_int(bgr)
            dwm.DwmSetWindowAttribute(hwnd, 34, ctypes.byref(col), ctypes.sizeof(col))
        except Exception:
            pass

    def _build_styles(self):
        p, fm = self.pal, self.fam
        st = ttk.Style(self)
        try:
            st.theme_use("clam")
        except Exception:
            pass
        for orient in ("Vertical", "Horizontal"):
            name = f"Slim.{orient}.TScrollbar"
            st.layout(name, [(f"{orient}.Scrollbar.trough", {
                "children": [(f"{orient}.Scrollbar.thumb",
                              {"expand": "1", "sticky": "nswe"})],
                "sticky": "ns" if orient == "Vertical" else "we"})])
            st.configure(name, background=p["scroll"], troughcolor=p["panel"],
                         borderwidth=0, arrowsize=0, width=9, relief="flat")
            st.map(name, background=[("active", p["scroll_hi"]),
                                     ("pressed", p["accent"])])
        st.configure("Thin.Horizontal.TProgressbar",
                     background=p["accent"], troughcolor=p["border"],
                     borderwidth=0, thickness=2, relief="flat")

    # ── 布局
    def _build_ui(self):
        p = self.pal
        self._build_status()
        self._build_header()
        body = tk.Frame(self, bg=p["root"])
        body.pack(fill="both", expand=True)
        self._build_sidebar(body)
        self._build_list(body)
        self._build_detail(body)

    def _build_header(self):
        p, fm = self.pal, self.fam
        h = tk.Frame(self, bg=p["header"], height=72)
        h.pack(fill="x", side="top")
        h.pack_propagate(False)

        left = tk.Frame(h, bg=p["header"])
        left.pack(side="left", padx=(22, 0), pady=12)
        tk.Label(left, text="⬡", bg=p["header"], fg=p["accent"],
                 font=(fm[0], 20)).pack(side="left", padx=(0, 10))
        t = tk.Frame(left, bg=p["header"])
        t.pack(side="left")
        tk.Label(t, text=APP_NAME, bg=p["header"], fg=p["text"],
                 font=(fm[0], 13, "bold")).pack(anchor="w")
        tk.Label(t, text=APP_SUB, bg=p["header"], fg=p["text_muted"],
                 font=(fm[1], 7)).pack(anchor="w")

        right = tk.Frame(h, bg=p["header"])
        right.pack(side="right", padx=(0, 16), pady=15)

        self.btn_theme = FlatButton(right, "☀" if self.theme == "dark" else "☾",
                                    self.toggle_theme, p, "ghost",
                                    font=(fm[0], 12), padx=9, pady=6)
        self.btn_theme.pack(side="right", padx=(6, 0))
        self.btn_refresh = FlatButton(right, "⟳  刷新", self.refresh, p, "accent",
                                      font=(fm[0], 10, "bold"), padx=16, pady=7)
        self.btn_refresh.pack(side="right", padx=(6, 0))
        self.pill = SearchPill(right, p, self._on_search_change, fm[0])
        self.pill.pack(side="right")

        self.progress = ttk.Progressbar(self, style="Thin.Horizontal.TProgressbar",
                                        mode="determinate", maximum=100, value=0)
        self.progress.pack(fill="x", side="top")

    def _build_status(self):
        p, fm = self.pal, self.fam
        bar = tk.Frame(self, bg=p["header"], height=30)
        bar.pack(fill="x", side="bottom")
        bar.pack_propagate(False)
        tk.Frame(bar, bg=p["border"], height=1).pack(fill="x", side="top")
        self.status_left = tk.Label(bar, text="", bg=p["header"], fg=p["text_muted"],
                                    font=(fm[0], 9))
        self.status_left.pack(side="left", padx=(20, 0))
        self.status_right = tk.Label(bar, text="●  就绪", bg=p["header"],
                                     fg=p["text_muted"], font=(fm[0], 9))
        self.status_right.pack(side="right", padx=(0, 20))
        self.status_mid = tk.Label(bar, text="", bg=p["header"], fg=p["text_muted"],
                                   font=(fm[0], 9))
        self.status_mid.pack(side="right", padx=(0, 16))

    def _build_sidebar(self, parent):
        p, fm = self.pal, self.fam
        side = tk.Frame(parent, bg=p["side"], width=194)
        side.pack(side="left", fill="y")
        side.pack_propagate(False)
        tk.Frame(side, bg=p["border"], width=1).pack(side="right", fill="y")

        hd = tk.Frame(side, bg=p["side"])
        hd.pack(fill="x", padx=18, pady=(16, 7))
        tk.Label(hd, text="武器分类", bg=p["side"], fg=p["text_muted"],
                 font=(fm[0], 9, "bold")).pack(anchor="w")

        self.fam_host = tk.Frame(side, bg=p["side"])
        self.fam_host.pack(fill="both", expand=True, padx=9)

        tk.Frame(side, bg=p["border"], height=1).pack(fill="x", padx=16, pady=(4, 0))
        s = tk.Frame(side, bg=p["side"])
        s.pack(fill="x", padx=18, pady=(9, 16))
        tk.Label(s, text="排序", bg=p["side"], fg=p["text_muted"],
                 font=(fm[0], 9, "bold")).pack(anchor="w", pady=(0, 6))
        self.sort_host = tk.Frame(s, bg=p["side"])
        self.sort_host.pack(fill="x")
        self._rebuild_sort_controls()

    def _rebuild_sort_controls(self):
        p, fm = self.pal, self.fam
        for w in self.sort_host.winfo_children():
            w.destroy()
        labels = {"quest_step": "任务阶段", "price": "造价",
                  "copy_times": "复制数", "updatedAt": "更新时间"}
        for key in ("quest_step", "price", "copy_times", "updatedAt"):
            active = (self.sort_key == key)
            bg = p["accent_soft"] if active else p["side"]
            row = tk.Frame(self.sort_host, bg=bg)
            row.pack(fill="x", pady=1)
            tk.Frame(row, bg=p["accent"] if active else p["side"], width=3).pack(side="left",
                                                                                fill="y")
            lbl = tk.Label(row, text=labels[key], bg=bg,
                           fg=p["accent"] if active else p["text_sec"],
                           font=(fm[0], 9), anchor="w", padx=9, pady=5)
            lbl.pack(side="left", fill="x", expand=True)
            arr = tk.Label(row, text=(("▼" if self.sort_rev else "▲") if active else ""),
                           bg=bg, fg=p["accent"], font=(fm[0], 7), padx=9)
            arr.pack(side="right")

            def go(_=None, k=key):
                self.sort_by(k)
            for w in (row, lbl, arr):
                w.bind("<Button-1>", go)
                w.bind("<Enter>", lambda e, l=lbl, r=row, a=active, b=bg:
                       None if a else [x.configure(bg=p["hover"]) for x in (l, r)])
                w.bind("<Leave>", lambda e, l=lbl, r=row, a=active, b=bg:
                       None if a else [x.configure(bg=b) for x in (l, r)])

    def _build_list(self, parent):
        p, fm = self.pal, self.fam
        mid = tk.Frame(parent, bg=p["panel"])
        mid.pack(side="left", fill="both", expand=True)

        bar = tk.Frame(mid, bg=p["panel"])
        bar.pack(fill="x", padx=(18, 10), pady=(13, 8))
        self.list_title = tk.Label(bar, text="全部改枪码", bg=p["panel"], fg=p["text"],
                                   font=(fm[0], 11, "bold"))
        self.list_title.pack(side="left")
        self.list_count = tk.Label(bar, text="", bg=p["panel"], fg=p["text_muted"],
                                   font=(fm[0], 9))
        self.list_count.pack(side="left", padx=(9, 0))

        self.table = CanvasTable(mid, p, [
            ("weapon", "武器", 152, "w", False),
            ("quest_step", "阶段", 62, "center", False),
            ("name", "配装名称", None, "w", False),
            ("player", "作者", 118, "w", False),
            ("price", "造价", 104, "e", True),
            ("copy_times", "复制", 68, "center", True),
            ("updatedAt", "更新", 84, "center", True),
        ], fm[0], on_select=self._on_row_select, on_activate=self._copy_item)

        self.table.pack(fill="both", expand=True, padx=(18, 6), pady=(0, 12))
        self.table.set_sort = self.table.set_sort  # noqa: 保持外部可调

        tk.Frame(mid, bg=p["border"], width=1).pack(side="right", fill="y")

    def _build_detail(self, parent):
        p, fm = self.pal, self.fam
        right = tk.Frame(parent, bg=p["side"], width=360)
        right.pack(side="right", fill="y")
        right.pack_propagate(False)
        pad = 20

        tb = tk.Frame(right, bg=p["side"])
        tb.pack(fill="x", padx=pad, pady=(16, 2))
        tk.Label(tb, text="■", bg=p["side"], fg=p["accent"],
                 font=(fm[0], 9)).pack(side="left")
        tk.Label(tb, text="配装详情", bg=p["side"], fg=p["text"],
                 font=(fm[0], 11, "bold")).pack(side="left", padx=(7, 0))

        self.d_fam = tk.Label(right, text="", bg=p["side"], fg=p["text_muted"],
                              font=(fm[0], 9), anchor="w")
        self.d_fam.pack(fill="x", padx=pad, pady=(12, 1))

        self.d_title = tk.Label(right, text="尚未选择", bg=p["side"], fg=p["text_muted"],
                                font=(fm[0], 15, "bold"), anchor="w", justify="left",
                                wraplength=310)
        self.d_title.pack(fill="x", padx=pad)

        self.d_sub = tk.Label(right, text="在左侧列表点选一行查看详情", bg=p["side"],
                              fg=p["text_sec"], font=(fm[0], 10), anchor="w",
                              justify="left", wraplength=310)
        self.d_sub.pack(fill="x", padx=pad, pady=(3, 9))

        self.chip_host = tk.Frame(right, bg=p["side"])
        self.chip_host.pack(fill="x", padx=pad)

        tk.Frame(right, bg=p["border"], height=1).pack(fill="x", padx=pad, pady=(12, 10))

        meta = tk.Frame(right, bg=p["side"])
        meta.pack(fill="x", padx=pad)
        self.meta = {}
        self.meta_row = {}
        for key, label in (("quest", "任务"), ("player", "作者"), ("price", "造价"),
                           ("copy_times", "被复制"), ("collect_times", "被收藏"),
                           ("updatedAt", "更新")):
            row = tk.Frame(meta, bg=p["side"])
            row.pack(fill="x", pady=2)
            tk.Label(row, text=label, bg=p["side"], fg=p["text_muted"],
                     font=(fm[0], 9), width=5, anchor="w").pack(side="left")
            v = tk.Label(row, text="—", bg=p["side"], fg=p["text_sec"],
                         font=(fm[0], 9), anchor="w")
            v.pack(side="left", fill="x", expand=True)
            self.meta[key] = v
            self.meta_row[key] = row
        self.meta_row["quest"].pack_forget()


        tk.Label(right, text="改枪码", bg=p["side"], fg=p["text_muted"],
                 font=(fm[0], 9, "bold")).pack(anchor="w", padx=pad, pady=(12, 5))

        self.code_box = tk.Text(right, height=4, bg=p["input"], fg=p["success"],
                                font=self.fmono, bd=0, relief="flat", padx=12, pady=10,
                                wrap="char", insertbackground=p["accent"],
                                highlightthickness=1, highlightbackground=p["border"],
                                highlightcolor=p["accent"],
                                selectbackground=p["select"],
                                selectforeground=p["select_fg"])
        self.code_box.pack(fill="x", padx=pad)
        self.code_box.configure(state="disabled")

        self.btn_copy = FlatButton(right, "⎘   复制改枪码", self.copy_selected, p,
                                   "accent", font=(fm[0], 10, "bold"),
                                   padx=16, pady=9, host_bg=p["side"])
        self.btn_copy.pack(fill="x", padx=pad, pady=(12, 0))

        self.hint = tk.Label(right, text="双击行可快速复制", bg=p["side"],
                             fg=p["text_muted"], font=(fm[0], 8), anchor="w")
        self.hint.pack(fill="x", padx=pad, pady=(9, 0))

        foot = tk.Frame(right, bg=p["side"])
        foot.pack(side="bottom", fill="x", padx=pad, pady=13)
        tk.Label(foot, text=f"数据来源 · {HOST}", bg=p["side"], fg=p["text_muted"],
                 font=(fm[0], 8)).pack(anchor="w")
        tk.Label(foot, text="Ctrl+F 搜索 · Ctrl+R 刷新 · Ctrl+C 复制",
                 bg=p["side"], fg=p["text_muted"], font=(fm[0], 7)).pack(anchor="w",
                                                                        pady=(2, 0))

    # ── 家族栏
    def _rebuild_families(self):
        p, fm = self.pal, self.fam
        for w in self.fam_host.winfo_children():
            w.destroy()
        counts, quest_counts = {}, {}
        for it in self.items:
            q = match_quest(it)
            if q:
                quest_counts[q] = quest_counts.get(q, 0) + 1
            f = classify(it.get("weapon"))
            counts[f] = counts.get(f, 0) + 1

        # 「全部」按原始总数（含任务条目），家族计数保持武器口径
        self._fam_row("全部", len(self.items), first=True)

        if quest_counts:
            self._group_label("任务")
            for q in QUEST_ORDER:
                if quest_counts.get(q):
                    self._fam_row(q, quest_counts[q], is_quest=True)

        self._group_label("武器")
        for f, _ in sorted(counts.items(), key=lambda kv: -kv[1]):
            self._fam_row(f, counts[f])

    def _group_label(self, text):
        p, fm = self.pal, self.fam
        holder = tk.Frame(self.fam_host, bg=p["side"])
        holder.pack(fill="x", pady=(8, 2))
        tk.Label(holder, text=text, bg=p["side"], fg=p["text_muted"],
                 font=(fm[0], 8, "bold")).pack(side="left", padx=(10, 0))
        tk.Frame(holder, bg=p["border"], height=1).pack(side="left", fill="x",
                                                         expand=True, padx=(7, 10))

    def _fam_row(self, f, n, first=False, is_quest=False):
        p, fm = self.pal, self.fam
        active = (self.family == f)
        bg = p["accent_soft"] if active else p["side"]
        row = tk.Frame(self.fam_host, bg=bg)
        row.pack(fill="x", pady=1)
        tk.Frame(row, bg=p["accent"] if active else p["side"], width=3).pack(side="left",
                                                                            fill="y")
        dot = tk.Label(row, text="◆" if is_quest else "●", bg=bg,
                       fg=FAMILY_COLORS.get(f, p["text_muted"]),
                       font=(fm[0], 7 if is_quest else 7))
        dot.pack(side="left", padx=(9, 6))
        name = tk.Label(row, text=f, bg=bg,
                        fg=p["accent"] if active else (p["text"] if is_quest else p["text_sec"]),
                        font=(fm[0], 9, "bold" if is_quest else "normal"), anchor="w")
        name.pack(side="left", fill="x", expand=True, pady=5)
        num = tk.Label(row, text=str(n), bg=bg,
                       fg=p["accent"] if active else p["text_muted"],
                       font=(fm[0], 8), padx=10)
        num.pack(side="right")

        def go(_=None, ff=f):
            self.set_family(ff)
        for w in (row, name, num, dot):
            w.bind("<Button-1>", go)
            w.bind("<Enter>", lambda e, r=row, n_=name, u=num, d=dot, a=active, b=bg:
                   None if a else [x.configure(bg=p["hover"]) for x in (r, n_, u, d)])
            w.bind("<Leave>", lambda e, r=row, n_=name, u=num, d=dot, a=active, b=bg:
                   None if a else [x.configure(bg=b) for x in (r, n_, u, d)])


    def set_family(self, f):
        self.family = f
        # 进入任务分类自动按阶段升序（1→2→…→6/7），离开时回落到更新时间
        if f in QUEST_KEYS:
            if self.sort_key != "quest_step":
                self.sort_key = "quest_step"
                self.sort_rev = False
                self._rebuild_sort_controls()
        elif self.sort_key == "quest_step":
            self.sort_key = "updatedAt"
            self.sort_rev = True
            self._rebuild_sort_controls()
        self._rebuild_families()
        self.apply_filter()


    def sort_by(self, key):
        if self.sort_key == key:
            self.sort_rev = not self.sort_rev
        else:
            self.sort_key = key
            self.sort_rev = key in ("price", "copy_times", "updatedAt")
        self._rebuild_sort_controls()
        self.apply_filter()

    # ── 搜索 / 过滤 / 排序
    def _on_search_change(self, *_):
        if self._search_job:
            try:
                self.after_cancel(self._search_job)
            except Exception:
                pass
        self._search_job = self.after(110, self.apply_filter)

    def _in_family(self, it, fam):
        """侧栏分桶匹配：任务分类按任务关键词，武器分类按武器家族。"""
        if fam in QUEST_KEYS:
            return match_quest(it) == fam
        return classify(it.get("weapon")) == fam

    def apply_filter(self):
        q = self.pill.text().lower() if hasattr(self, "pill") else ""
        src = self.items
        if self.family != "全部":
            src = [it for it in src if self._in_family(it, self.family)]
        if not q:
            out = list(src)
        else:
            out = []
            for it in src:
                blob = " ".join((fmt(it.get("weapon")), fmt(it.get("name")),
                                 fmt(it.get("player")), fmt(it.get("code")),
                                 fmt(it.get("core")), fmt(it.get("tags")))).lower()
                if q in blob:
                    out.append(it)
        self.filtered = out
        self._apply_sort()
        if hasattr(self, "table"):
            self.table.sort_key = self.sort_key
            self.table.sort_rev = self.sort_rev
            self.table.set_rows(self.filtered, keep_sel_id=self.selected)
        self._set_counts()

    def _apply_sort(self):
        key = self.sort_key

        def kf(it):
            if key == "quest_step":
                s, _a = quest_step(it)
                if not s:
                    return (2, 0, "")
                head = s.split("/")[0]
                try:
                    return (0, int(head), s)
                except Exception:
                    return (1, 0, s)
            v = it.get(key)
            if key in ("price", "copy_times", "collect_times"):
                try:
                    return (0, int(v))
                except Exception:
                    return (1, 0)
            return (0, str(v or "").lower())

        try:
            self.filtered.sort(key=kf, reverse=self.sort_rev)
        except Exception:
            pass

    def _set_counts(self):
        shown, total = len(self.filtered), len(self.items)
        self.list_count.configure(text=f"{shown} / {total}")
        if self.family == "全部":
            self.list_title.configure(text="全部改枪码")
        elif self.family in QUEST_KEYS:
            self.list_title.configure(text=f"{self.family}任务")
        else:
            self.list_title.configure(text=self.family)
        if self.family in QUEST_HINT and self.family != "全部":
            self.status_left.configure(text=f"显示 {shown} / {total} 条 · {QUEST_HINT[self.family]}")
        else:
            self.status_left.configure(text=f"显示 {shown} / {total} 条")
        self.status_mid.configure(text=(f"缓存 {self.cache_saved_at}" if self.cache_saved_at
                                       else "无缓存"))


    # ── 行选择 / 详情
    def _on_row_select(self, it, sort_only=False):
        if sort_only or it is None:
            return
        self.cur = it
        self.selected = it.get("id") or it.get("code")
        p = self.pal
        fam = classify(it.get("weapon"))
        q = match_quest(it)
        col = FAMILY_COLORS.get(q, p["text"]) if q else FAMILY_COLORS.get(fam, p["text"])
        if q:
            step, action = quest_step(it)
            badge = f"◆  {q}任务" + (f" · 阶段 {step}" if step else "")
            self.d_fam.configure(text=badge, fg=col)
        else:
            self.d_fam.configure(text=f"●  {fam}", fg=col)
        self.d_title.configure(text=fmt(it.get("weapon")) or "（未知武器）", fg=col)
        self.d_sub.configure(text=fmt(it.get("name")) or "（无配装名）", fg=p["text"])

        for w in self.chip_host.winfo_children():
            w.destroy()
        for t in (it.get("tags") or [])[:5]:
            self._mk_chip(str(t))

        self.meta["player"].configure(text=fmt(it.get("player")) or "—")
        if q:
            step, action = quest_step(it)
            bits = [q + "任务"]
            if step:
                bits.append("第 " + step + " 步")
            if action:
                bits.append(action)
            self.meta["quest"].configure(text=" · ".join(bits), fg=col)
            self.meta_row["quest"].pack(fill="x", pady=2, before=self.meta_row["player"])
        else:
            self.meta_row["quest"].pack_forget()

        self.meta["price"].configure(text=fmt_price(it.get("price")) or "—")
        self.meta["copy_times"].configure(text=f"{fmt(it.get('copy_times')) or 0} 次")
        self.meta["collect_times"].configure(text=f"{fmt(it.get('collect_times')) or 0} 次")
        self.meta["updatedAt"].configure(text=fmt(it.get("updatedAt")) or "—")

        self.code_box.configure(state="normal", fg=p["success"])
        self.code_box.delete("1.0", "end")
        self.code_box.insert("1.0", fmt(it.get("code")) or "（无改枪码）")
        self.code_box.configure(state="disabled")

    def _mk_chip(self, text):
        p, fm = self.pal, self.fam
        wrap = tk.Frame(self.chip_host, bg=p["chip_border"])
        wrap.pack(side="left", padx=(0, 6), pady=(0, 6))
        tk.Label(wrap, text=text, bg=p["chip"], fg=p["chip_fg"],
                 font=(fm[0], 8), padx=8, pady=2).pack(padx=1, pady=1)

    def _reset_detail(self):
        p = self.pal
        self.cur = None
        self.d_fam.configure(text="")
        self.d_title.configure(text="尚未选择", fg=p["text_muted"])
        self.d_sub.configure(text="在左侧列表点选一行查看详情", fg=p["text_sec"])
        for w in self.chip_host.winfo_children():
            w.destroy()
        for v in self.meta.values():
            v.configure(text="—")
        if hasattr(self, "meta_row"):
            self.meta_row["quest"].pack_forget()

        self.code_box.configure(state="normal")
        self.code_box.delete("1.0", "end")
        self.code_box.insert("1.0", "—")
        self.code_box.configure(state="disabled")

    # ── 复制
    def copy_selected(self):
        self._copy_item(self.cur)

    def _copy_item(self, it):
        p = self.pal
        if not it:
            self.hint.configure(text="先选中一行再复制", fg=p["error"])
            self.after(1600, lambda: self.hint.configure(text="双击行可快速复制",
                                                         fg=self.pal["text_muted"]))
            return
        code = fmt(it.get("code"))
        if not code:
            return
        self.clipboard_clear()
        self.clipboard_append(code)
        self.btn_copy.flash("✓   已复制到剪贴板", p.get("accent_fg", p["root"]), 1300)
        self.hint.configure(text="✓ 已复制 " + (code[:26] + "…" if len(code) > 26 else code),
                            fg=p["success"])
        self.status_right.configure(text="●  已复制", fg=p["success"])
        self.after(1800, lambda: self.status_right.configure(text="●  就绪",
                                                            fg=self.pal["text_muted"]))
        self.after(2400, lambda: self.hint.configure(text="双击行可快速复制",
                                                     fg=self.pal["text_muted"]))

    # ── 缓存 / 刷新
    def _load_cached(self):
        items, saved = load_cache()
        if items:
            self.items = items
            self.cache_saved_at = saved
            self._rebuild_families()
            self.apply_filter()

    def _spin(self):
        frames = "◐◓◑◒"
        if not self._loading:
            self._spin_job = None
            return
        self._spin_frame = (self._spin_frame + 1) % 4
        self.status_right.configure(text=f"{frames[self._spin_frame]}  刷新中…",
                                    fg=self.pal["accent"])
        self._spin_job = self.after(120, self._spin)

    def refresh(self):
        if self._loading:
            return
        self._loading = True
        self.btn_refresh.set_text("⟳  刷新中")
        self.progress.configure(value=0)
        self._spin()

        def worker():
            def on_page(items, page, pages, total):
                def upd():
                    self.progress.configure(value=int(page / max(pages, 1) * 100))
                    self.status_right.configure(
                        text=f"◐  拉取 {page}/{pages} 页 · {len(items)} 条",
                        fg=self.pal["accent"])
                self.after(0, upd)
            try:
                items, total, failed = fetch_all(on_page)
                self.after(0, lambda: self._on_done(items, failed))
            except Exception as e:
                self.after(0, lambda: self._on_error(str(e)))

        threading.Thread(target=worker, daemon=True).start()

    def _on_done(self, items, failed):
        p = self.pal
        self._loading = False
        self.items = items
        save_cache(items)
        self.cache_saved_at = time.strftime("%Y-%m-%d %H:%M")
        self.btn_refresh.set_text("⟳  刷新")
        self.progress.configure(value=100)
        self._rebuild_families()
        self.apply_filter()
        if failed:
            self.status_right.configure(text=f"⚠  {len(failed)} 页失败", fg=p["error"])
        else:
            self.status_right.configure(text=f"●  已更新 {len(items)} 条", fg=p["success"])
        self.after(2000, lambda: self.progress.configure(value=0))

    def _on_error(self, msg):
        p = self.pal
        self._loading = False
        self.btn_refresh.set_text("⟳  刷新")
        self.progress.configure(value=0)
        has = bool(self.items)
        self.status_right.configure(
            text=f"✕  网络异常{f'，显示缓存 {len(self.items)} 条' if has else ''}",
            fg=p["error"])
        if not has:
            messagebox.showerror("获取失败",
                                 f"无法获取改枪码数据：\n{msg}\n\n请检查网络后点『刷新』。")

    # ── 主题
    def toggle_theme(self):
        keep = {"q": self.pill.text(), "family": self.family,
                "sort_key": self.sort_key, "sort_rev": self.sort_rev,
                "selected": self.selected}
        self.theme = "light" if self.theme == "dark" else "dark"
        self.pal = dict(PALETTES[self.theme])
        for w in list(self.winfo_children()):
            w.destroy()
        self.configure(bg=self.pal["root"])
        self._build_styles()
        self._build_ui()
        self._bind_keys()
        self.family = keep["family"]
        self.sort_key = keep["sort_key"]
        self.sort_rev = keep["sort_rev"]
        self.selected = keep["selected"]
        self._rebuild_sort_controls()
        self._rebuild_families()
        if keep["q"]:
            self.pill.set_text(keep["q"])
        self.apply_filter()
        self._restore_detail(keep["selected"])
        self.after(30, self._native_chrome)

    def _restore_detail(self, sid):
        if not sid:
            self._reset_detail()
            return
        for it in self.items:
            if (it.get("id") or it.get("code")) == sid:
                self._on_row_select(it)
                return
        self._reset_detail()

    # ── 快捷键
    def _bind_keys(self):
        self.bind("<Control-f>", lambda e: (self.pill.focus(), "break")[1])
        self.bind("<Control-r>", lambda e: self.refresh())
        self.bind("<F5>", lambda e: self.refresh())
        self.bind("<Control-c>", lambda e: self.copy_selected())
        self.bind("<Escape>", lambda e: self.pill.clear_all())
        self.bind("<Control-q>", lambda e: self.destroy())
        self.bind("<Up>", lambda e: self.table.move(-1))
        self.bind("<Down>", lambda e: self.table.move(1))
        self.bind("<Return>", lambda e: self.copy_selected())


def single_instance_ok():
    try:
        ctypes.windll.kernel32.CreateMutexW(None, False, MUTEX_NAME)
        if ctypes.windll.kernel32.GetLastError() == 183:
            return False
        ctypes.windll.kernel32.SetLastError(0)
        return True
    except Exception:
        return True


def _sweep_runtime_dirs():
    """清掉上一次异常退出残留的 _MEI* 解包目录。

    --runtime-tmpdir 指向 %LOCALAPPDATA%\\DeltaCodeViewer\\rt；进程被强杀时
    bootloader 来不及清理，残留会越积越多。启动时只删「本次进程之外」的目录。
    """
    base = getattr(sys, "_MEIPASS", "")
    if not base:
        return
    base = os.path.abspath(base)
    parent = os.path.dirname(base)
    if os.path.basename(parent) != "rt":
        return
    me = os.path.basename(base)
    for name in os.listdir(parent):
        if not name.startswith("_MEI") or name == me:
            continue
        shutil.rmtree(os.path.join(parent, name), ignore_errors=True)


def main():
    _sweep_runtime_dirs()
    if not single_instance_ok():
        r = tk.Tk()
        r.withdraw()
        messagebox.showinfo(APP_NAME, "程序已经在运行了。")
        r.destroy()
        return
    App().mainloop()


if __name__ == "__main__":
    main()

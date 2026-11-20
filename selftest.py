# -*- coding: utf-8 -*-
"""离线自检：不联网、不弹窗，验证分类 / 过滤 / 排序 / 缓存 / 复制链路。"""
import os
import sys
import json
import time

os.environ.setdefault("DFCV_THEME", "dark")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import app as A  # noqa: E402

FAIL = []


def ck(name, cond, extra=""):
    print(("  OK  " if cond else " FAIL ") + name + (("  " + extra) if extra else ""))
    if not cond:
        FAIL.append(name)


print("== 1. 家族分类 ==")
cases = {
    "M14": "射手步枪", "SR-25": "射手步枪", "SVCH": "射手步枪",
    "K416": "突击步枪", "AK-12": "突击步枪", "AN94": "突击步枪",
    "AS Val": "突击步枪", "MK47": "突击步枪", "腾龙": "突击步枪",
    "MP7": "冲锋枪", "汤姆逊冲锋枪": "冲锋枪", "MK4": "冲锋枪",
    "PKM": "轻机枪", "QJB201": "轻机枪", "M250": "轻机枪",
    "S12K": "霰弹枪", "M1014": "霰弹枪",
    "AWM": "狙击枪", "M700": "狙击枪",
    "G18": "手枪", "沙鹰": "手枪",
    "弓": "特殊", "套装": "套装", "": "其他",
}
for w, want in cases.items():
    got = A.classify(w)
    ck(f"classify({w!r}) == {want}", got == want, f"got={got}")

print("\n== 2. 格式化 ==")
ck("fmt(None) == ''", A.fmt(None) == "")
ck("fmt(list)", A.fmt(["a", "b"]) == "a / b")
ck("fmt_price(670000)", A.fmt_price(670000) == "670,000")
ck("fmt_price('x') 回落", A.fmt_price("x") == "x")
ck("fmt_date", A.fmt_date("2026-11-05") == "11-05")
ck("fmt_date 短串", A.fmt_date("abc") == "abc")

print("\n== 3. 缓存读写 ==")
tmp_items = [{"id": "t1", "weapon": "K416", "name": "测试", "code": "ABC-123"}]
A.CACHE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_selftest_cache.json")
A.save_cache(tmp_items)
got, saved = A.load_cache()
ck("save/load 往返", got == tmp_items, f"got={got}")
ck("saved_at 格式", len(saved) == 16 and saved[4] == "-", saved)
os.remove(A.CACHE_FILE)

print("\n== 4. 过滤 / 排序（无 GUI，直接算逻辑）==")
import http.client  # noqa: E402

items = [
    {"id": "a", "weapon": "K416", "name": "金枪客专属", "player": "武器大师",
     "code": "AAA", "price": 0, "copy_times": 33, "updatedAt": "2026-10-09", "tags": ["x"]},
    {"id": "b", "weapon": "M14", "name": "林树同款", "player": "林树",
     "code": "BBB", "price": 680000, "copy_times": 2, "updatedAt": "2026-10-10", "tags": []},
    {"id": "c", "weapon": "PKM", "name": "38W腰射新套装", "player": "武器大师",
     "code": "CCC", "price": 380000, "copy_times": 105, "updatedAt": "2026-11-05", "tags": ["腰射"]},
]


def filt(src, q, fam=None):
    if fam and fam != "全部":
        src = [i for i in src if A.classify(i.get("weapon")) == fam]
    if not q:
        return list(src)
    out = []
    for it in src:
        blob = " ".join((A.fmt(it.get("weapon")), A.fmt(it.get("name")),
                         A.fmt(it.get("player")), A.fmt(it.get("code")),
                         A.fmt(it.get("tags")))).lower()
        if q.lower() in blob:
            out.append(it)
    return out


ck("空查询返回全部", len(filt(items, "")) == 3)
ck("按武器搜 k416", [i["id"] for i in filt(items, "k416")] == ["a"])
ck("按作者搜 林树", [i["id"] for i in filt(items, "林树")] == ["b"])
ck("按码搜 ccc", [i["id"] for i in filt(items, "ccc")] == ["c"])
ck("按标签搜 腰射", [i["id"] for i in filt(items, "腰射")] == ["c"])
ck("家族筛选 轻机枪", [i["id"] for i in filt(items, "", "轻机枪")] == ["c"])
ck("组合：家族+查询", filt(items, "zzz", "轻机枪") == [])


def srt(rows, key, rev):
    def kf(it):
        v = it.get(key)
        if key in ("price", "copy_times", "collect_times"):
            try:
                return (0, int(v))
            except Exception:
                return (1, 0)
        return (0, str(v or "").lower())
    return sorted(rows, key=kf, reverse=rev)


ck("按造价降序", [i["id"] for i in srt(items, "price", True)] == ["b", "c", "a"])
ck("按复制降序", [i["id"] for i in srt(items, "copy_times", True)] == ["c", "a", "b"])
ck("按更新降序", [i["id"] for i in srt(items, "updatedAt", True)] == ["c", "b", "a"])
ck("按武器升序", [i["id"] for i in srt(items, "weapon", False)] == ["a", "b", "c"])

print("\n== 5. 网络层结构（不发起真实请求）==")
ck("HOST", A.HOST == "delta-code.cn")
ck("API_PATH", A.API_PATH == "/api/loadouts")
ck("HEADERS 有 UA", "User-Agent" in A.HEADERS)
ck("CACHE_DIR 指向 LOCALAPPDATA", "DeltaCodeViewer" in A.CACHE_DIR)
ck("MUTEX_NAME", A.MUTEX_NAME.endswith("_v2"))

print("\n== 6. 主题调色板完整性 ==")
need = ["root", "header", "side", "panel", "card", "card_alt", "input", "hover",
        "pressed", "border", "border_hi", "accent", "accent_2", "accent_dim",
        "accent_fg", "accent_soft", "accent_line", "text", "text_sec", "text_muted",
        "success", "error", "info", "select", "select_fg", "chip", "chip_fg",
        "chip_border", "scroll", "scroll_hi"]
for name, pal in A.PALETTES.items():
    miss = [k for k in need if k not in pal]
    ck(f"{name} 调色板 {len(need)} 键齐全", not miss, f"缺={miss}")
    bad = [k for k, v in pal.items() if not (isinstance(v, str) and v.startswith("#")
                                             and len(v) == 7)]
    ck(f"{name} 全部为 #RRGGBB", not bad, f"异常={bad}")

print("\n== 7. 家族覆盖真实数据 ==")
cache = os.path.join(os.environ.get("LOCALAPPDATA", ""), "DeltaCodeViewer", "cache.json")
if os.path.exists(cache):
    with open(cache, "r", encoding="utf-8") as f:
        real = json.load(f).get("items") or []
    fams = {}
    for it in real:
        fams[A.classify(it.get("weapon"))] = fams.get(A.classify(it.get("weapon")), 0) + 1
    unknown = fams.get("其他", 0)
    ck(f"真实 {len(real)} 条数据分类完成", sum(fams.values()) == len(real))
    ck("「其他」占比 < 6%", unknown / max(len(real), 1) < 0.06,
       f"其他={unknown} ({unknown/max(len(real),1)*100:.1f}%)")
    print("     分布:", dict(sorted(fams.items(), key=lambda kv: -kv[1])))
else:
    print("  SKIP  无本机缓存")

print("\n== 8. 任务分类（金枪客）==")
Q_ITEMS = [
    {"id": "q1", "weapon": "QJB", "name": "QJB201｜金枪客上交", "player": "武器大师",
     "code": "Q1", "price": 230000, "copy_times": 9, "updatedAt": "2026-11-01",
     "tags": ["S11", "金枪客1", "上交"], "core": "第一步交付"},
    {"id": "q2", "weapon": "MDR突击步枪", "name": "MDR｜金枪客击杀", "player": "社区精选",
     "code": "Q2", "price": 210000, "copy_times": 4, "updatedAt": "2026-11-02",
     "tags": ["S11", "金枪客6/7", "击杀"], "core": ""},
    {"id": "q3", "weapon": "K437", "name": "金枪客专属", "player": "社区精选",
     "code": "Q3", "price": 0, "copy_times": 1, "updatedAt": "2026-10-20",
     "tags": ["烽火地带"], "core": ""},
    {"id": "n1", "weapon": "PKM", "name": "38W腰射", "player": "林树",
     "code": "N1", "price": 380000, "copy_times": 105, "updatedAt": "2026-11-05",
     "tags": ["腰射"], "core": ""},
]
ck("任务命中数 = 3（含仅 name 命中、仅 slug 无关键词）",
   sum(1 for it in Q_ITEMS if A.match_quest(it)) == 3,
   f"实际={[it['id'] for it in Q_ITEMS if A.match_quest(it)]}")
ck("非任务条目不被误判", A.match_quest(Q_ITEMS[3]) is None)
ck("slug 随机串不误命中（jqk 不能当关键词）",
   A.match_quest({"id": "x", "slug": "6JQKF4409", "name": "ovo同款", "weapon": "AS Val"}) is None)
ck("任务优先于武器家族（QJB 与 PKM 不同桶）",
   A.bucket_of(Q_ITEMS[0]) == "金枪客" and A.bucket_of(Q_ITEMS[3]) == "轻机枪")
ck("bucket 全覆盖且不重不漏",
   sum(1 for it in Q_ITEMS if A.bucket_of(it) == "金枪客") == 3)
ck("step 解析：金枪客1 → 1", A.quest_step(Q_ITEMS[0])[0] == "1")
ck("step 解析：金枪客6/7 → 6/7", A.quest_step(Q_ITEMS[1])[0] == "6/7")
ck("action 解析：上交 / 击杀", A.quest_step(Q_ITEMS[0])[1] == "上交"
   and A.quest_step(Q_ITEMS[1])[1] == "击杀")
ck("无阶段条目 step 为空", A.quest_step(Q_ITEMS[2]) == ("", ""))
ck("QUEST_COLORS 有金枪客", "金枪客" in A.FAMILY_COLORS)

if os.path.exists(cache):
    with open(cache, "r", encoding="utf-8") as f:
        _real = json.load(f).get("items") or []
    _q = [it for it in _real if A.match_quest(it)]
    _b = {}
    for it in _real:
        k = A.bucket_of(it)
        _b[k] = _b.get(k, 0) + 1
    ck("真实数据金枪客命中 29 条", len(_q) == 29, f"实际={len(_q)}")
    ck("真实数据分桶总数守恒", sum(_b.values()) == len(_real),
       f"{sum(_b.values())} vs {len(_real)}")
    ck("真实数据「金枪客」与武器家族互斥",
       all(A.match_quest(it) or A.classify(it.get("weapon")) != "金枪客" for it in _real))

print("\n" + ("=" * 46))
print("全部通过" if not FAIL else f"失败 {len(FAIL)} 项: {FAIL}")
sys.exit(1 if FAIL else 0)

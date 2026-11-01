# -*- coding: utf-8 -*-
"""
中东第一手情报工作台 · 采集器
零第三方依赖（仅标准库）。
用法：
  python collector.py              # 抓取一次
  python collector.py --daemon     # 常驻，默认每 30 分钟一轮
  python collector.py --daemon --interval 15
"""
import sys, os, re, ssl, json, time, gzip, socket, hashlib, argparse, traceback
import urllib.request, urllib.parse
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
from xml.etree import ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    import config
except ImportError:
    print("缺少 config.py"); sys.exit(1)

# API Key 加载优先级：环境变量(GitHub Actions) > keys_local.py(本机) > config.py
def load_keys():
    try:
        import keys_local
        for k, v in getattr(keys_local, "API_KEYS", {}).items():
            if v:
                config.API_KEYS[k] = v
    except ImportError:
        pass
    for k, var in (("firms", "ME_FIRMS"), ("eia", "ME_EIA"),
                   ("aisstream", "ME_AISSTREAM"),
                   ("opensky_user", "ME_OPENSKY_USER"),
                   ("opensky_pass", "ME_OPENSKY_PASS")):
        if os.environ.get(var):
            config.API_KEYS[k] = os.environ[var]
    n = sum(1 for v in config.API_KEYS.values() if v)
    if n:
        print(f"[keys] 已加载 {n} 个 API Key")

load_keys()

BASE = os.path.dirname(os.path.abspath(__file__))
_d = getattr(config, "DATA_DIR", "")
DATA = os.path.abspath(_d) if _d else os.path.join(BASE, "data")
os.makedirs(DATA, exist_ok=True)
CACHE_F = os.path.join(DATA, "translate_cache.json")
STATE_F = os.path.join(DATA, "state.json")
OUT_F = os.path.join(DATA, "latest.json")
LOG_F = os.path.join(DATA, "collector.log")

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36")
CST = timezone(timedelta(hours=8))
socket.setdefaulttimeout(30)


def log(msg):
    line = f"[{datetime.now(CST).strftime('%m-%d %H:%M:%S')}] {msg}"
    print(line, flush=True)
    try:
        # 日志轮转：超过 400KB 时只保留最近 300 行，避免长期运行无限膨胀
        if os.path.exists(LOG_F) and os.path.getsize(LOG_F) > 400_000:
            with open(LOG_F, encoding="utf-8") as f:
                tail = f.readlines()[-300:]
            with open(LOG_F, "w", encoding="utf-8") as f:
                f.writelines(tail)
        with open(LOG_F, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


# ---------------------------------------------------------
# 代理
# ---------------------------------------------------------
def detect_system_proxy():
    """读取 Windows 系统代理设置"""
    try:
        import winreg
        k = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                           r"Software\Microsoft\Windows\CurrentVersion\Internet Settings")
        enable = winreg.QueryValueEx(k, "ProxyEnable")[0]
        server = winreg.QueryValueEx(k, "ProxyServer")[0]
        if not enable or not server:
            return None
        if "=" in server:
            m = re.search(r"https?=([^;]+)", server)
            server = m.group(1) if m else server.split(";")[0].split("=", 1)[-1]
        server = server.strip()
        if not server.startswith("http"):
            server = "http://" + server
        return server
    except Exception:
        return None


_SYS_PROXY = None


def init_proxy():
    global _SYS_PROXY
    p = getattr(config, "PROXY", None)
    if p == "auto":
        _SYS_PROXY = detect_system_proxy()
        if _SYS_PROXY:
            log(f"检测到系统代理: {_SYS_PROXY}（仅用于受限源）")
        else:
            log("未检测到系统代理，受限源将跳过")
    elif p:
        _SYS_PROXY = p
        log(f"使用指定代理: {_SYS_PROXY}（全局）")
    else:
        log("未启用代理，受限源将跳过")


def proxy_get(url):
    """海外源走代理，国内源直连"""
    if not _SYS_PROXY:
        return None
    try:
        host = urllib.parse.urlparse(url).hostname or ""
    except Exception:
        return None
    for h in getattr(config, "DOMESTIC_HOSTS", []):
        if host == h or host.endswith("." + h):
            return None
    return _SYS_PROXY


_openers = {}


def _opener(proxy):
    key = proxy or "__direct__"
    if key in _openers:
        return _openers[key]
    if proxy:
        handler = urllib.request.ProxyHandler({"http": proxy, "https": proxy})
    else:
        handler = urllib.request.ProxyHandler({})
    op = urllib.request.build_opener(handler)
    _openers[key] = op
    return op


# ---------------------------------------------------------
# HTTP
# ---------------------------------------------------------
def fetch(url, referer=None, timeout=15, retries=1, decode=None, proxy=None):
    hdr = {
        "User-Agent": UA,
        "Accept": "application/rss+xml,application/xml,text/xml,text/html,*/*",
        "Accept-Language": "en-US,en;q=0.9,ar;q=0.8,fa;q=0.7,he;q=0.7,zh;q=0.6",
        "Accept-Encoding": "gzip",
        "Connection": "close",
    }
    if referer:
        hdr["Referer"] = referer
    if proxy is None:
        proxy = proxy_get(url)
    # 海外源：代理优先（代理不可用时快速失败并回退直连）；国内源：仅直连
    attempts = [proxy, None] if proxy else [None]
    last = None
    for p in attempts:
        # 代理只试 1 次（不可用时快速回退），直连才重试
        for i in range(1 if p else retries + 1):
            try:
                req = urllib.request.Request(url, headers=hdr)
                with _opener(p).open(req, timeout=timeout) as r:
                    raw = r.read()
                    if r.headers.get("Content-Encoding") == "gzip":
                        try:
                            raw = gzip.decompress(raw)
                        except Exception:
                            pass
                    if isinstance(raw, bytes):
                        raw = raw.decode(decode or "utf-8", "ignore")
                    return raw
            except Exception as e:
                last = e
                if p:
                    break          # 代理失败不再重试，直接回退直连
                time.sleep(0.5 * (i + 1))
    log(f"  跳过源 {url[:60]} -> {type(last).__name__}")
    return None


def fetch_json(url, **kw):
    t = fetch(url, **kw)
    if not t:
        return None
    try:
        return json.loads(t)
    except Exception:
        return None


# ---------------------------------------------------------
# RSS / Atom 解析（自研）
# ---------------------------------------------------------
def _local(tag):
    return tag.split("}")[-1].lower()


def _txt(el):
    return "".join(el.itertext()).strip() if el is not None else ""


def parse_feed(text, limit=40):
    if not text or not text.lstrip()[:1] == "<":
        return []
    try:
        root = ET.fromstring(text.strip().lstrip("\ufeff"))
    except Exception:
        try:
            root = ET.fromstring(re.sub(r"&(?!amp;|lt;|gt;|quot;|apos;|#)", "&amp;", text))
        except Exception:
            return []
    out = []
    for node in root.iter():
        if _local(node.tag) not in ("item", "entry"):
            continue
        d = {}
        for ch in node:
            k = _local(ch.tag)
            if k == "title":
                d["title"] = _txt(ch)
            elif k == "link":
                d["link"] = (ch.get("href") or _txt(ch)).strip()
            elif k in ("pubdate", "published", "updated", "date"):
                d.setdefault("pub", _txt(ch))
            elif k in ("description", "summary", "content"):
                d.setdefault("sum", _txt(ch))
            elif k == "source":
                d["src"] = _txt(ch)
        if d.get("title"):
            out.append(d)
            if len(out) >= limit:
                break
    return out


def parse_time(s):
    if not s:
        return None
    try:
        dt = parsedate_to_datetime(s)
        if dt:
            return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except Exception:
        pass
    for cand in (s, s.replace("Z", "+00:00"), s.replace(" ", "T")):
        try:
            dt = datetime.fromisoformat(cand)
            return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        except Exception:
            continue
    return None


def strip_html(s):
    if not s:
        return ""
    s = re.sub(r"<[^>]+>", " ", s)
    s = re.sub(r"&[a-z#0-9]+;", " ", s)
    return re.sub(r"\s+", " ", s).strip()


# ---------------------------------------------------------
# 分析引擎
# ---------------------------------------------------------
def _build_terms():
    terms = set()
    for cat, table in config.ENTITIES.items():
        for en, zh in table.items():
            terms.add(en.lower())
            terms.add(zh)
    for t in config.MIDEAST_EXTRA:
        terms.add(t.lower())
    return terms


MIDEAST_TERMS = _build_terms()
LOCAL_SRC = set(getattr(config, "LOCAL_SOURCES", [
    "IRNA", "半岛", "以色列时报", "耶路撒冷邮报", "Middle East Eye", "Al-Monitor",
    "Middle East Institute", "海湾研究所", "阿纳多卢", "塔斯尼姆", "PressTV",
    "迈赫尔", "Al Arabiya", "ISW", "伊朗",
]))


def is_relevant(text, source):
    tl = text.lower()
    hit = any(t in tl for t in MIDEAST_TERMS)
    if hit:
        return True
    if any(k in tl for k in config.EXCLUDE_KEYWORDS):
        return False
    # 中东本地/专精信源豁免（其报道默认相关）
    for s in LOCAL_SRC:
        if s.lower() in (source or "").lower():
            return True
    return False


def norm_key(t):
    t = re.sub(r"[^\w\u0600-\u06FF\u0590-\u05FF\u4e00-\u9fff]+", "", (t or "").lower())
    return hashlib.md5(t.encode("utf-8")).hexdigest()[:12]


def detect_domains(text):
    tl = text.lower()
    hits = {}
    for dom, kws in config.DOMAIN_KEYWORDS.items():
        n = sum(1 for k in kws if k.lower() in tl)
        if n:
            hits[dom] = n
    return hits


def risk_score(text, weight=1.0, ts=None):
    tl = text.lower()
    raw, matched = 0, []
    for w, kws in config.RISK_KEYWORDS:
        for k in kws:
            if k.lower() in tl:
                raw += w
                matched.append(k)
                break
    raw = min(raw, 100)
    boost = 1.0
    if ts:
        age_h = (datetime.now(timezone.utc) - ts).total_seconds() / 3600
        boost = 1.15 if age_h <= 2 else (1.0 if age_h <= 6 else (0.85 if age_h <= 24 else 0.7))
    return int(min(100, round(raw * weight * boost))), matched


def level_of(s):
    return "极高" if s >= 60 else ("高" if s >= 35 else ("中" if s >= 15 else "低"))


def detect_entities(text):
    found = {}
    for cat, table in config.ENTITIES.items():
        for en, zh in table.items():
            if re.search(r"(?<![a-z])" + re.escape(en) + r"(?![a-z])", text, re.I):
                found.setdefault(cat, {})[zh] = found.setdefault(cat, {}).get(zh, 0) + 1
    return {c: [k for k, _ in sorted(d.items(), key=lambda x: -x[1])][:6]
            for c, d in found.items()}


def guess_lang(t):
    if re.search(r"[\u0600-\u06FF]", t):
        return "fa" if re.search(r"[\u067E\u0686\u0698\u06AF\u06A9\u06CC]", t) else "ar"
    if re.search(r"[\u0590-\u05FF]", t):
        return "he"
    if re.search(r"[\u4e00-\u9fff]", t):
        return "zh"
    return "en"


_cache = {}


def translate(text, lang, budget):
    if lang in ("en", "zh") or not text or budget[0] <= 0:
        return None
    key = lang + ":" + text[:120]
    if key in _cache:
        return _cache[key]
    sl = {"ar": "ar", "fa": "fa", "he": "iw"}.get(lang)
    if not sl:
        return None
    budget[0] -= 1
    try:
        u = ("https://api.mymemory.translated.net/get?q=" + urllib.parse.quote(text[:450])
             + f"&langpair={sl}%7Czh-CN")
        j = fetch_json(u, timeout=12)
        if j and j.get("responseStatus") == 200:
            t = j["responseData"]["translatedText"]
            if t and "MYMEMORY WARNING" not in t and "QUERY LENGTH" not in t:
                _cache[key] = t
                return t
    except Exception:
        pass
    try:
        u = ("https://translate.googleapis.com/translate_a/single?client=gtx"
             f"&sl={sl}&tl=zh-CN&dt=t&q=" + urllib.parse.quote(text[:450]))
        j = fetch_json(u, timeout=12)
        if j and j[0]:
            t = "".join(x[0] for x in j[0] if x and x[0])
            if t:
                _cache[key] = t
                return t
    except Exception:
        pass
    return None


# ---------------------------------------------------------
# 抓取
# ---------------------------------------------------------
def gnews_url(q, lang, region, ceid):
    return ("https://news.google.com/rss/search?q=" + urllib.parse.quote(q) +
            f"&hl={lang}-{region}&gl={region}&ceid={ceid}")


def collect_gnews():
    res = []
    with ThreadPoolExecutor(max_workers=8) as ex:
        futs = [ex.submit(fetch, gnews_url(q, l, r, c), None, 20)
                for q, l, r, c, h in config.GNEWS_QUERIES]
        spec = list(config.GNEWS_QUERIES)
        for (q, l, r, c, hint), f in zip(spec, futs):
            ents = parse_feed(f.result(), limit=25)
            for e in ents:
                title = strip_html(e.get("title", ""))
                if not title:
                    continue
                pub = e.get("src") or "Google News"
                if " - " in title and not e.get("src"):
                    parts = title.rsplit(" - ", 1)
                    if len(parts) == 2 and len(parts[1]) < 40:
                        title, pub = parts[0].strip(), parts[1].strip()
                res.append({"title": title, "url": e.get("link", ""), "source": pub,
                            "source_type": "aggregator", "weight": 0.9,
                            "pub": e.get("pub"), "summary": strip_html(e.get("sum", ""))[:300],
                            "hint": hint})
    return res


def collect_rss(sources, workers=10, silent=False):
    res, ok, fail = [], [], []
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(fetch, url, None, 18): (n, t, w, d) for n, url, t, w, d in sources}
        for f in as_completed(futs):
            n, t, w, d = futs[f]
            txt = f.result()
            ents = parse_feed(txt, limit=35) if txt else []
            if not ents:
                fail.append(n)
                continue
            ok.append(n)
            for e in ents:
                title = strip_html(e.get("title", ""))
                if not title:
                    continue
                res.append({"title": title, "url": e.get("link", ""), "source": n,
                            "source_type": t, "weight": w, "pub": e.get("pub"),
                            "summary": strip_html(e.get("sum", ""))[:300], "hint": d})
    if ok and not silent:
        log(f"  直连源成功 {len(ok)}: {', '.join(ok[:6])}{'...' if len(ok)>6 else ''}")
    if fail and not silent:
        log(f"  直连源失败 {len(fail)}: {', '.join(fail[:6])}")
    return res, ok, fail


def collect_markets():
    m = {"futures": [], "indices": [], "fx": {}, "updated": None}
    if not config.MARKETS.get("show_quotes", True):
        return m

    def one(sym, name, unit):
        j = fetch_json("https://query1.finance.yahoo.com/v8/finance/chart/"
                       f"{urllib.parse.quote(sym)}?interval=1d&range=5d", timeout=15)
        try:
            meta = j["chart"]["result"][0]["meta"]
            cur = meta.get("regularMarketPrice")
            prev = meta.get("chartPreviousClose") or meta.get("previousClose")
            if cur is None or not prev:
                return None
            return {"code": sym, "name": name, "unit": unit,
                    "price": round(cur, 2), "prev": round(prev, 2),
                    "chg": round((cur - prev) / prev * 100, 2)}
        except Exception:
            return None

    with ThreadPoolExecutor(max_workers=4) as ex:
        for f in as_completed([ex.submit(one, s, n, u)
                               for s, n, u in config.MARKETS["quotes"]]):
            r = f.result()
            if r:
                m["futures"].append(r)
    m["futures"].sort(key=lambda x: -abs(x["chg"]))
    j = fetch_json(config.MARKETS["fx_url"], timeout=12)
    if j and j.get("rates"):
        watch = config.MARKETS["fx_watch"]
        m["fx"] = {"base": "USD", "date": j.get("time_last_update_utc", ""),
                   "rates": {k: v for k, v in j["rates"].items() if k in watch}}
    m["updated"] = datetime.now(CST).isoformat(timespec="seconds")
    return m


def collect_quakes():
    j = fetch_json(config.MARKETS["quake_url"], timeout=15)
    out = []
    if not j or not j.get("features"):
        return out
    for f in j["features"]:
        p = f.get("properties", {}) or {}
        c = (f.get("geometry") or {}).get("coordinates") or []
        if len(c) < 2:
            continue
        lon, lat, mag = c[0], c[1], p.get("mag") or 0
        near, dist = None, 1e9
        for name, slat, slon in config.MONITOR_SITES:
            from math import radians, sin, cos, asin, sqrt
            lo1, la1, lo2, la2 = map(radians, [lon, lat, slon, slat])
            a = sin((la2 - la1) / 2) ** 2 + cos(la1) * cos(la2) * sin((lo2 - lo1) / 2) ** 2
            d = 2 * asin(sqrt(a)) * 6371.0
            if d < dist:
                near, dist = name, d
        ts = p.get("time")
        out.append({"mag": round(mag, 1), "place": p.get("place", ""),
                    "near": near if dist <= 200 else None, "dist": round(dist),
                    "url": p.get("url", ""),
                    "ts": datetime.fromtimestamp(ts / 1000, timezone.utc).isoformat() if ts else None,
                    "suspicious": bool(mag >= 3.5 and dist <= 100)})
    out.sort(key=lambda x: -x["mag"])
    return out[:20]


# ---------------------------------------------------------
# 主流程
# ---------------------------------------------------------
def run_once():
    t0 = time.time()
    init_proxy()
    if os.path.exists(CACHE_F):
        try:
            _cache.update(json.load(open(CACHE_F, encoding="utf-8")))
        except Exception:
            pass
    log("开始新一轮抓取 ...")

    with ThreadPoolExecutor(max_workers=3) as ex:
        f_gn = ex.submit(collect_gnews)
        f_rs = ex.submit(collect_rss, config.RSS_SOURCES)
        f_mk = ex.submit(collect_markets)
        f_qk = ex.submit(collect_quakes)
        raw_gn = f_gn.result()
        raw_rs, src_ok, src_fail = f_rs.result()
        markets = f_mk.result()
        quakes = f_qk.result()

    # 受限源（需代理）
    raw_proxy = []
    if _SYS_PROXY:
        try:
            with ThreadPoolExecutor(max_workers=5) as ex:
                f = ex.submit(collect_rss, config.PROXY_SOURCES, 5, True)
                raw_proxy, pok, pfail = f.result()
            if pok:
                log(f"  代理源解锁 {len(pok)}: {', '.join(pok)}")
                src_ok += pok
        except Exception as e:
            log(f"  代理源异常: {e}")

    log(f"  原始条目: GoogleNews {len(raw_gn)} / RSS {len(raw_rs)} / 代理 {len(raw_proxy)}")

    # 传感数据（Key 未配置会自动跳过）
    sensors = {}
    try:
        import sensors as S
        with ThreadPoolExecutor(max_workers=4) as ex:
            ff = ex.submit(S.collect_firms, proxy_get)
            fa = ex.submit(S.collect_air, proxy_get)
            fe = ex.submit(S.collect_eia, proxy_get)
            fs = ex.submit(S.collect_ais, proxy_get)
            sensors["firms"] = ff.result()
            sensors["air"] = fa.result()
            sensors["eia"] = fe.result()
            sensors["ais"] = fs.result()
        for k, v in sensors.items():
            if v:
                log(f"  传感[{k}] 已接入")
    except Exception as e:
        log(f"  传感模块未启用: {type(e).__name__} {e}")

    # 合并 + 过滤 + 去重 + 打分
    seen, items, dropped = set(), [], 0
    budget = [10]
    prev_ids = set()
    if os.path.exists(STATE_F):
        try:
            prev_ids = set(json.load(open(STATE_F, encoding="utf-8")).get("ids", []))
        except Exception:
            pass

    for r in raw_gn + raw_rs + raw_proxy:
        title = r["title"]
        if len(title) < 6:
            continue
        k = norm_key(title)
        if k in seen:
            continue
        seen.add(k)
        text = title + " " + r.get("summary", "")
        if not is_relevant(text, r.get("source", "")):
            dropped += 1
            continue
        ts = parse_time(r.get("pub")) or datetime.now(timezone.utc)
        doms = detect_domains(text)
        if r.get("hint") and r["hint"] not in doms:
            doms[r["hint"]] = doms.get(r["hint"], 0) + 1
        score, matched = risk_score(text, r.get("weight", 1.0), ts)
        lang = guess_lang(title)
        items.append({
            "id": k, "title": title, "title_zh": translate(title, lang, budget),
            "lang": lang, "summary": r.get("summary", ""), "url": r.get("url", ""),
            "source": r.get("source", ""), "source_type": r.get("source_type", ""),
            "ts": ts.astimezone(CST).isoformat(timespec="seconds"),
            "ts_raw": ts.timestamp(), "domains": sorted(doms, key=lambda d: -doms[d]),
            "entities": detect_entities(text), "risk": score, "level": level_of(score),
            "keywords": matched[:6], "is_new": k not in prev_ids,
        })

    items.sort(key=lambda x: (-x["risk"], -x["ts_raw"]))
    items = items[:400]

    # ---- 综合风险 ----
    ex_n = sum(1 for i in items if i["risk"] >= 60)
    hi_n = sum(1 for i in items if i["risk"] >= 35)
    oil = next((f for f in markets["futures"] if f["name"].startswith("布伦特")), None)
    oil_chg = abs(oil["chg"]) if oil else 0
    q_alert = sum(1 for q in quakes if q.get("suspicious"))
    f_alert = len((sensors.get("firms") or {}).get("alerts", []))
    air_mil = (sensors.get("air") or {}).get("military_count", 0)
    score = min(100, ex_n * 7 + hi_n * 3 + min(18, oil_chg * 3.5)
                + q_alert * 6 + f_alert * 5 + min(10, air_mil // 3))
    level = "极高" if score >= 70 else ("高" if score >= 45 else ("中" if score >= 25 else "低"))

    dom_cnt = {d: sum(1 for i in items if d in i["domains"]) for d in config.DOMAIN_KEYWORDS}
    top_dom = max(dom_cnt, key=lambda k: dom_cnt[k]) if any(dom_cnt.values()) else "conflict"
    dom_cn = {"conflict": "地缘冲突", "energy": "能源油价",
              "shipping": "航运物流", "finance": "金融市场"}[top_dom]
    ents_flat = []
    for i in items[:40]:
        for cat in ("countries", "orgs", "places"):
            for e in i["entities"].get(cat, []):
                if e not in ents_flat:
                    ents_flat.append(e)
    summary = (f"综合风险 {score}/100（{level}）。有效情报 {len(items)} 条，"
               f"极高危 {ex_n} 条、高危 {hi_n} 条；热点集中于{dom_cn}，"
               f"高频主体：{'、'.join(ents_flat[:5]) or '—'}。")
    if oil:
        summary += f"布伦特 {oil['price']} 美元/桶（{oil['chg']:+.2f}%）。"
    if f_alert:
        summary += f"卫星监测到 {f_alert} 处重点设施火点。"
    if q_alert:
        summary += f"{q_alert} 起重点区域异常震动。"
    if air_mil:
        summary += f"空域军用航空器 {air_mil} 架。"

    prev_score = None
    if os.path.exists(STATE_F):
        try:
            prev_score = json.load(open(STATE_F, encoding="utf-8")).get("score")
        except Exception:
            pass
    trend = "—"
    if prev_score is not None:
        d = score - prev_score
        trend = f"{'↑' if d > 0 else ('↓' if d < 0 else '→')}{abs(d)}（上轮 {prev_score}）"

    result = {
        "updated": datetime.now(CST).isoformat(timespec="seconds"),
        "updated_ts": time.time(),
        "risk": {"score": score, "level": level, "summary": summary, "trend": trend,
                 "extreme": ex_n, "high": hi_n, "top_domain": top_dom, "top_domain_cn": dom_cn},
        "markets": markets, "quakes": quakes, "sensors": sensors, "items": items,
        "domains": dom_cnt, "entities": ents_flat[:20],
        "stats": {"total": len(items), "dropped": dropped, "src_ok": src_ok,
                  "src_fail": src_fail, "new": sum(1 for i in items if i["is_new"]),
                  "proxy": _SYS_PROXY or "", "elapsed": round(time.time() - t0, 1)},
    }

    json.dump(result, open(OUT_F, "w", encoding="utf-8"), ensure_ascii=False)
    # 同时输出 JS 版本，让看板可直接双击打开（file:// 下 fetch 会被 CORS 拦截）
    try:
        with open(os.path.join(DATA, "latest.js"), "w", encoding="utf-8") as f:
            f.write("window.__ME_DATA__ = " + json.dumps(result, ensure_ascii=False) + ";")
    except Exception:
        pass
    json.dump({"ids": list(seen), "score": score}, open(STATE_F, "w", encoding="utf-8"),
              ensure_ascii=False)
    try:
        json.dump(_cache, open(CACHE_F, "w", encoding="utf-8"), ensure_ascii=False, indent=0)
    except Exception:
        pass
    try:
        with open(os.path.join(DATA, "history.jsonl"), "a", encoding="utf-8") as f:
            f.write(json.dumps({"t": result["updated"], "score": score, "level": level,
                                "total": len(items)}, ensure_ascii=False) + "\n")
    except Exception:
        pass

    log(f"完成：{len(items)} 条（新增 {result['stats']['new']}，过滤噪声 {dropped}）"
        f" | 风险 {score}/100 {level} | 耗时 {result['stats']['elapsed']}s")
    return result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--daemon", action="store_true")
    ap.add_argument("--interval", type=int, default=30)
    a = ap.parse_args()
    if not a.daemon:
        run_once()
        return
    log(f"=== 常驻模式：每 {a.interval} 分钟一轮 ===")
    while True:
        try:
            run_once()
        except KeyboardInterrupt:
            log("已停止"); break
        except Exception:
            log("本轮异常:\n" + traceback.format_exc())
        try:
            time.sleep(a.interval * 60)
        except KeyboardInterrupt:
            log("已停止"); break


if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
"""
信源体检：逐个测试每个信源在【直连】和【代理】下的真实状态
用法：python probe.py        （或在 bat 里双击运行）
输出：源名 / 直连 / 代理 / 条目数 / 结论
"""
import os, sys, time
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config, collector

C = collector

def check(url, proxy, decode=None):
    """返回 (状态, 条目数)"""
    t0 = time.time()
    txt = C.fetch(url, timeout=12, retries=0, decode=decode,
                  proxy=proxy if proxy else "__force_direct__")
    ms = int((time.time() - t0) * 1000)
    if not txt:
        return "超时/拒绝", 0, ms
    n = len(C.parse_feed(txt, limit=99)) if txt.lstrip()[:1] == "<" else 0
    if "json" in url or "api" in url:
        return "HTTP200", 1, ms
    if n:
        return "OK", n, ms
    # 200 但无条目：多半返回了 HTML 首页（RSS 地址失效）
    tag = "HTML(非RSS)" if ("<html" in txt[:600].lower() or "<!doctype" in txt[:600].lower()) \
        else "空/格式异常"
    return tag, 0, ms


def main():
    C.init_proxy()
    p = C._SYS_PROXY
    print("\n" + "=" * 78)
    print(f"信源体检   代理={p or '未配置'}")
    print("=" * 78)

    targets = []
    for name, url, typ, w, dom in config.RSS_SOURCES:
        targets.append((name, url, "直连源"))
    for name, url, typ, w, dom in config.PROXY_SOURCES:
        targets.append((name, url, "受限源"))
    targets.append(("GoogleNews(多语)", C.gnews_url("Israel Iran", "en", "US", "US:en"), "聚合"))
    targets.append(("新浪行情", config.MARKETS["sina_futures"]["url"], "行情"))
    targets.append(("汇率API", config.MARKETS["fx_url"], "行情"))
    targets.append(("USGS地震", config.MARKETS["quake_url"], "传感"))
    targets.append(("OpenSky空域",
                    "https://opensky-network.org/api/states/all?lamin=10&lomin=25&lamax=42&lomax=65",
                    "传感"))

    def job(t):
        name, url, kind = t
        d = check(url, None)
        pp = check(url, p) if p else ("-", 0, 0)
        return (name, kind, d, pp)

    with ThreadPoolExecutor(max_workers=8) as ex:
        res = list(ex.map(job, targets))

    print(f"{'信源':<22}{'类型':<7}{'直连':<14}{'代理':<14}{'条目':<6}结论")
    print("-" * 78)
    unlocked = []
    for name, kind, d, pp in res:
        dst, dn, dms = d
        pst, pn, pms = pp
        best = pn or dn
        if dn:
            concl = "直连可用"
        elif pn:
            concl = "需代理(已解锁)" if p else "需代理"
            unlocked.append(name)
        elif pst.startswith("HTML") or dst.startswith("HTML"):
            concl = "RSS已失效(对方下线)"
        elif "403" in pst or "403" in dst:
            concl = "被站点封禁(换节点试)"
        else:
            concl = "不可达"
        print(f"{name[:21]:<22}{kind:<7}{dst:<14}{pst:<14}{best:<6}{concl}")
    print("-" * 78)
    if unlocked:
        print("代理解锁的源：" + "、".join(unlocked))
    need = [n for n, k, d, pp in res if not d[1] and not pp[1]]
    if need:
        print("仍未通：" + "、".join(need))
        print("提示：403 多为目标站点封数据中心IP，换住宅/冷门节点可能解决；"
              "超时多为节点到该国链路差。")
    print("=" * 78 + "\n")


if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
"""
API 密钥填写向导：逐项输入，自动写入 keys_local.py（该文件不会被提交到 GitHub）
用法：双击「填入API密钥.bat」，或 python setup_keys.py
"""
import os, sys, importlib.util

BASE = os.path.dirname(os.path.abspath(__file__))
KEYF = os.path.join(BASE, "keys_local.py")

FIELDS = [
    ("firms", "NASA FIRMS 卫星火点 Map Key", "firms.modaps.eosdis.nasa.gov/api/map_key/"),
    ("eia", "EIA 美国能源署 api_key", "eia.gov/opendata/register.php"),
    ("aisstream", "AISStream 船舶AIS API Key", "aisstream.io/account"),
    ("opensky_user", "OpenSky 用户名", "opensky-network.org（可跳过，匿名也能用）"),
    ("opensky_pass", "OpenSky 密码", "同上"),
]


def load_current():
    if not os.path.exists(KEYF):
        return {}
    try:
        spec = importlib.util.spec_from_file_location("kl", KEYF)
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        return dict(getattr(m, "API_KEYS", {}))
    except Exception:
        return {}


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    cur = load_current()
    print("=" * 62)
    print("  API 密钥填写向导")
    print("  直接回车 = 跳过该项（保留原值）")
    print("=" * 62)
    for k, label, url in FIELDS:
        old = cur.get(k, "")
        mark = "（已填写）" if old else ""
        print(f"\n{label} {mark}")
        print(f"  申请地址: {url}")
        try:
            v = input("  粘贴 Key 后回车: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n已取消")
            return
        if v:
            cur[k] = v
        else:
            cur.setdefault(k, "")

    lines = ['# -*- coding: utf-8 -*-',
             '"""由 setup_keys.py 生成，请勿提交到 GitHub"""',
             'API_KEYS = {']
    for k, v in cur.items():
        lines.append(f'    {k!r}: {v!r},')
    lines.append('}')
    with open(KEYF, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    n = sum(1 for v in cur.values() if v)
    print("\n" + "=" * 62)
    print(f"  已保存到 keys_local.py，共 {n} 项")
    print("  下次运行 collector.py 时自动生效")
    print("=" * 62)
    input("\n按回车关闭...")


if __name__ == "__main__":
    main()

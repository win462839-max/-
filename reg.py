# -*- coding: utf-8 -*-
"""
代提交 API Key 注册申请（需要用户明确授权后使用）

用法：
  python reg.py firms 你的邮箱@example.com
  python reg.py eia   你的邮箱@example.com 名 姓
"""
import sys, json, urllib.request, urllib.parse

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/125.0 Safari/537.36")


def post(url, data, is_json=False, referer=None):
    if is_json:
        body = json.dumps(data).encode()
        ctype = "application/json"
    else:
        body = urllib.parse.urlencode(data).encode()
        ctype = "application/x-www-form-urlencoded"
    hdr = {"User-Agent": UA, "Content-Type": ctype,
           "Accept": "text/html,application/json,*/*"}
    if referer:
        hdr["Referer"] = referer
    req = urllib.request.Request(url, data=body, headers=hdr, method="POST")
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.status, r.read().decode("utf-8", "ignore")


def firms(email):
    print(f"[FIRMS] 提交邮箱: {email}")
    st, txt = post("https://firms.modaps.eosdis.nasa.gov/api/map_key_setup/",
                   {"email": email, "site": "firms", "action": "POST"},
                   is_json=True,
                   referer="https://firms.modaps.eosdis.nasa.gov/api/map_key/")
    print(f"  HTTP {st}")
    t = txt.strip()
    if "error-" in t:
        print("  结果: 失败 ->", t.replace("error-", ""))
        return False
    if t == "options":
        print("  结果: 该邮箱已注册过。NASA 会向你邮箱重发/更新 Key，请查收邮件。")
        return True
    print("  结果: 提交成功，Key 已发送到邮箱（请同时检查垃圾箱）")
    print("  页面返回:", t[:200])
    return True


def eia(email, first="User", last="MiddleEast"):
    print(f"[EIA] 提交: {first} {last} <{email}>")
    st, txt = post("https://www.eia.gov/opendata/register.php",
                   {"firstName": first, "lastName": last, "email": email,
                    "tos": "y", "notify": "y", "Register": "Register", "addr": "y"},
                   referer="https://www.eia.gov/opendata/register.php")
    print(f"  HTTP {st}")
    low = txt.lower()
    if "already" in low and "registered" in low:
        print("  结果: 该邮箱已注册，可用 Forgot my API Key 找回")
        return True
    if "thank" in low or "sent" in low or "success" in low:
        print("  结果: 提交成功，API Key 已发送到邮箱")
        return True
    print("  结果: 已提交，请查收邮件确认（返回片段）:", txt[:150].replace("\n", " "))
    return True


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    kind, email = sys.argv[1], sys.argv[2]
    if kind == "firms":
        firms(email)
    elif kind == "eia":
        first = sys.argv[3] if len(sys.argv) > 3 else "User"
        last = sys.argv[4] if len(sys.argv) > 4 else "MiddleEast"
        eia(email, first, last)
    else:
        print("未知类型，只支持 firms / eia")

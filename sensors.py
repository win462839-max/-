# -*- coding: utf-8 -*-
"""
高级传感模块：卫星火点 / 空域 / 船舶AIS / EIA官方油价
全部零第三方依赖。API Key 未配置时自动跳过，不影响主体运行。
"""
import os, re, json, time, ssl, socket, base64, struct, urllib.request, urllib.parse
from datetime import datetime, timezone, timedelta
from math import radians, sin, cos, asin, sqrt

import config
from collector import fetch, log  # 复用采集器的 HTTP 与日志


def haversine(lon1, lat1, lon2, lat2):
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
    dlon, dlat = lon2 - lon1, lat2 - lat1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    return 2 * asin(sqrt(a)) * 6371.0


def nearest_site(lat, lon, maxkm=120):
    best, bd = None, 1e9
    for name, slat, slon in config.MONITOR_SITES:
        d = haversine(lon, lat, slon, slat)
        if d < bd:
            best, bd = name, d
    return (best, round(bd)) if bd <= maxkm else (None, round(bd))


# ---------------------------------------------------------
# NASA FIRMS 卫星火点：炼油厂/军事设施火灾爆炸的第一手信号
# ---------------------------------------------------------
def collect_firms(proxy_get):
    key = config.API_KEYS.get("firms", "").strip()
    if not key:
        return None
    out = []
    for src in config.MARKETS["firms_sources"]:
        url = (f"https://firms.modaps.eosdis.nasa.gov/api/area/csv/{key}/{src}/"
               f"{config.MARKETS['firms_bbox']}/1")
        txt = fetch(url, timeout=20, proxy=proxy_get(url))
        if not txt or txt.lstrip().startswith("<") or "Invalid" in txt[:80]:
            continue
        lines = txt.strip().split("\n")
        if len(lines) < 2:
            continue
        head = [h.strip() for h in lines[0].split(",")]
        for ln in lines[1:]:
            p = ln.split(",")
            if len(p) < len(head):
                continue
            row = dict(zip(head, p))
            try:
                lat = float(row["latitude"]); lon = float(row["longitude"])
                frp = float(row.get("frp", 0))
            except Exception:
                continue
            if frp < 15:          # 只保留有实际规模的火点，滤除噪声
                continue
            near, dist = nearest_site(lat, lon, 150)
            out.append({
                "lat": round(lat, 3), "lon": round(lon, 3),
                "frp": round(frp, 1), "conf": row.get("confidence", ""),
                "sat": row.get("satellite", src),
                "acq": f"{row.get('acq_date','')} {row.get('acq_time','')}".strip(),
                "near": near, "dist": dist,
                "alert": bool(near and frp >= 50),
            })
        break   # 一个源成功即可
    out.sort(key=lambda x: -x["frp"])
    return {"points": out[:60], "count": len(out),
            "alerts": [p for p in out if p.get("alert")][:10]}


# ---------------------------------------------------------
# OpenSky 中东空域：军机异动、民航绕飞禁航区
# ---------------------------------------------------------
def collect_air(proxy_get):
    u = config.API_KEYS.get("opensky_user", "").strip()
    p = config.API_KEYS.get("opensky_pass", "").strip()
    lamin, lomin, lamax, lomax = config.MARKETS["opensky_bbox"]
    url = (f"https://opensky-network.org/api/states/all?"
           f"lamin={lamin}&lomin={lomin}&lamax={lamax}&lomax={lomax}")
    host = "opensky-network.org"
    if u and p:
        url = url.replace("https://", f"https://{urllib.parse.quote(u)}:{urllib.parse.quote(p)}@")
    j = fetch(url, timeout=25, proxy=proxy_get(url))
    if not j:
        return None
    try:
        data = json.loads(j)
    except Exception:
        return None
    states = data.get("states") or []
    mil, emerg, airborne = [], [], 0
    for s in states:
        if len(s) < 8:
            continue
        cs = (s[1] or "").strip()
        on_ground = s[8] if len(s) > 8 else False
        lat, lon = s[6], s[5]
        squawk = str(s[14]) if len(s) > 14 and s[14] else ""
        if not on_ground:
            airborne += 1
        if cs:
            pre = re.split(r"\d", cs)[0].upper()
            if any(pre.startswith(m) for m in config.MILITARY_CALLSIGN):
                mil.append({"callsign": cs, "country": s[2],
                            "lat": lat, "lon": lon,
                            "alt": s[7] if len(s) > 7 else None,
                            "on_ground": on_ground})
        if squawk in ("7500", "7600", "7700"):
            emerg.append({"callsign": cs, "squawk": squawk, "lat": lat, "lon": lon})
    return {"total": len(states), "airborne": airborne,
            "military": mil[:30], "military_count": len(mil),
            "emergency": emerg[:10],
            "ts": datetime.now(timezone.utc).isoformat(timespec="seconds")}


# ---------------------------------------------------------
# EIA 官方油价（布伦特现货，权威于二手行情）
# ---------------------------------------------------------
def collect_eia(proxy_get):
    key = config.API_KEYS.get("eia", "").strip()
    if not key:
        return None
    url = ("https://api.eia.gov/v2/petroleum/pri/spt/data/?api_key=" + key +
           "&frequency=daily&data[0]=value&sort[0][column]=period"
           "&sort[0][direction]=desc&length=60")
    j = fetch(url, timeout=20, proxy=proxy_get(url))
    if not j:
        return None
    try:
        d = json.loads(j)["response"]["data"]
    except Exception:
        return None
    brent = [r for r in d if "RBRTE" in str(r.get("series", "")).upper()
             or "Brent" in str(r.get("series-description", r.get("series", "")))]
    if not brent:
        brent = d
    if len(brent) < 2:
        return None
    cur, prev = brent[0], brent[1]
    try:
        c, p = float(cur["value"]), float(prev["value"])
    except Exception:
        return None
    return {"series": cur.get("series", ""), "date": cur.get("period"),
            "price": round(c, 2), "prev": round(p, 2),
            "chg": round((c - p) / p * 100, 2) if p else 0}


# ---------------------------------------------------------
# AISStream 船舶 AIS（WebSocket，极简自研客户端）
# ---------------------------------------------------------
class MiniWS:
    """最小 WebSocket 客户端：握手 + 掩码文本帧收发（够用即可）"""

    def __init__(self, host, path, timeout=12):
        self.host = host
        self.path = path
        self.timeout = timeout
        self.sock = None

    def connect(self, proxy=None):
        if proxy:
            # 通过 HTTP 代理 CONNECT 隧道
            pu = urllib.parse.urlparse(proxy)
            s = socket.create_connection((pu.hostname, pu.port or 8080), self.timeout)
            s.sendall(f"CONNECT {self.host}:443 HTTP/1.1\r\nHost: {self.host}:443\r\n\r\n".encode())
            resp = b""
            while b"\r\n\r\n" not in resp:
                resp += s.recv(1024)
            if b"200" not in resp.split(b"\r\n")[0]:
                s.close()
                raise RuntimeError("proxy connect failed")
        else:
            s = socket.create_connection((self.host, 443), self.timeout)
        ctx = ssl.create_default_context()
        self.sock = ctx.wrap_socket(s, server_hostname=self.host)
        key = base64.b64encode(os.urandom(16)).decode()
        req = (f"GET {self.path} HTTP/1.1\r\nHost: {self.host}\r\n"
               "Upgrade: websocket\r\nConnection: Upgrade\r\n"
               f"Sec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n")
        self.sock.sendall(req.encode())
        buf = b""
        while b"\r\n\r\n" not in buf:
            chunk = self.sock.recv(4096)
            if not chunk:
                raise RuntimeError("ws handshake closed")
            buf += chunk
        if b"101" not in buf.split(b"\r\n")[0]:
            raise RuntimeError("ws handshake rejected")

    def send(self, text):
        data = text.encode()
        hdr = bytearray([0x81])
        n = len(data)
        if n < 126:
            hdr.append(0x80 | n)
        elif n < 65536:
            hdr.append(0x80 | 126); hdr += struct.pack(">H", n)
        else:
            hdr.append(0x80 | 127); hdr += struct.pack(">Q", n)
        mask = os.urandom(4)
        hdr += mask
        masked = bytes(b ^ mask[i % 4] for i, b in enumerate(data))
        self.sock.sendall(bytes(hdr) + masked)

    def recv(self, bufsize=65536):
        def rd(n):
            b = b""
            while len(b) < n:
                c = self.sock.recv(n - len(b))
                if not c:
                    raise RuntimeError("closed")
                b += c
            return b
        h = rd(2)
        ln = h[1] & 0x7F
        if ln == 126:
            ln = struct.unpack(">H", rd(2))[0]
        elif ln == 127:
            ln = struct.unpack(">Q", rd(8))[0]
        return rd(ln).decode("utf-8", "ignore")

    def close(self):
        try:
            self.sock.close()
        except Exception:
            pass


def collect_ais(proxy_get, seconds=25):
    key = config.API_KEYS.get("aisstream", "").strip()
    if not key:
        return None
    host, path = "stream.aisstream.io", "/v0/stream"
    boxes = [[[b[0][0], b[0][1]], [b[1][0], b[1][1]]] for b in config.MARKETS["ais_boxes"]]
    ships, tankers, dark = {}, {}, []
    try:
        ws = MiniWS(host, path, timeout=12)
        ws.connect(proxy=proxy_get("https://stream.aisstream.io"))
        ws.send(json.dumps({"APIKey": key, "BoundingBoxes": boxes}))
        ws.sock.settimeout(seconds)
        deadline = time.time() + seconds
        while time.time() < deadline:
            try:
                msg = ws.recv()
            except socket.timeout:
                break
            except Exception:
                break
            try:
                d = json.loads(msg)
            except Exception:
                continue
            meta = d.get("MetaData") or {}
            mmsi = meta.get("MMSI") or meta.get("mmsi")
            if not mmsi:
                continue
            name = (meta.get("ShipName") or "").strip()
            lat, lon = meta.get("latitude"), meta.get("longitude")
            typ = (d.get("Message") or {}).get("MessageID")
            info = {"mmsi": mmsi, "name": name, "lat": lat, "lon": lon,
                    "type": meta.get("ShipType"), "dest": meta.get("Destination"),
                    "flag": meta.get("Flag"), "ts": meta.get("time_utc")}
            ships[mmsi] = info
            if 80 <= int(info["type"] or 0) <= 89:      # 80-89 = 油轮
                tankers[mmsi] = info
        ws.close()
    except Exception as e:
        log(f"  AIS 采集跳过: {type(e).__name__} {e}")
        return None
    # 关闭应答器（近 6 小时无位置更新但有记录）记为 dark
    for m, s in tankers.items():
        if not s.get("lat"):
            dark.append(s)
    return {"total": len(ships), "tankers": len(tankers),
            "tanker_list": list(tankers.values())[:40],
            "dark": dark[:10], "sample_seconds": seconds}

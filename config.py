# -*- coding: utf-8 -*-
"""
中东第一手情报工作台 —— 信源与知识库配置
改完保存即生效（下一轮抓取自动应用）。
"""

# ============================================================
# 〇、网络出口与 API Key
# ============================================================
# 代理设置：
#   None        -> 直连（默认）
#   "auto"      -> 自动读取 Windows 系统代理（推荐，你配好全局代理后用这个）
#   "http://127.0.0.1:7890"  -> 手动指定
#   "http://user:pass@host:port" -> 带账密
PROXY = "http://127.0.0.1:10808"

# 数据输出目录：留空 = 使用脚本所在目录下的 data/
# 若改到别处（如 D:\情报归档），请把 dashboard.html 一并放到该目录的上一级，
# 否则看板会因相对路径 data/latest.json 找不到数据。
DATA_DIR = ""

# 直连域名（国内源，永远不走代理，避免绕远变慢/失败）
DOMESTIC_HOSTS = ["hq.sinajs.cn", "finance.sina.com.cn", "push2.eastmoney.com",
                  "hq.sinajs.com", "qt.gtimg.cn"]

# 以下域名走代理（保留兼容；实际逻辑为「非国内域名一律走代理 + 直连兜底」）
PROXY_ONLY_HOSTS = [
    "understandingwar.org",      # ISW 战争研究所（中东战况日更，最权威）
    "tasnimnews.com",            # 伊朗塔斯尼姆通讯社
    "presstv.ir",                # 伊朗国家广播电视
    "mehrnews.com",              # 伊朗迈赫尔通讯社
    "farsnews.ir",               # 伊朗法尔斯通讯社
    "acleddata.com",             # ACLED 冲突事件数据库
    "alarabiya.net", "arabnews.com", "thenationalnews.com",
    "tradingeconomics.com",
    "israeldefense.co.il",
]

# 免费 API Key（留空则对应模块自动跳过，不影响其他功能）
API_KEYS = {
    # NASA FIRMS 卫星火点：https://firms.modaps.eosdis.nasa.gov/api/map_key/ 邮箱即领
    "firms": "",
    # EIA 美国能源署：https://www.eia.gov/opendata/register.php
    "eia": "",
    # AISStream 船舶AIS：https://aisstream.io/authenticate
    "aisstream": "",
    # OpenSky 航班：https://opensky-network.org/ 注册后填用户名密码（匿名也可，限额低）
    "opensky_user": "",
    "opensky_pass": "",
}

# 只在代理可用时启用的直连源（网络不通会自动跳过，不会报错）
PROXY_SOURCES = [
    ("ISW 战争研究所", "https://www.understandingwar.org/rss.xml", "thinktank", 1.5, "conflict"),
    ("伊朗塔斯尼姆通讯社", "https://www.tasnimnews.com/en/rss/1", "official", 1.3, "conflict"),
    ("伊朗 PressTV", "https://www.presstv.ir/rss", "official", 1.2, "conflict"),
    ("伊朗迈赫尔通讯社", "https://en.mehrnews.com/rss", "official", 1.2, "conflict"),
    ("Al Arabiya", "https://english.alarabiya.net/tools/rss", "media", 1.0, "finance"),
]

# ============================================================
# 一、领域分类关键词（中/英/阿/波/希 多语）
# ============================================================
DOMAIN_KEYWORDS = {
    "conflict": [
        "strike", "airstrike", "air strike", "missile", "attack", "killed", "war",
        "ceasefire", "escalation", "hezbollah", "hamas", "houthi", "idf", "irgc",
        "drone", "rocket", "invasion", "offensive", "bombardment", "hostage",
        "militant", "shelling", "troops", "conflict", "clash", "raid", "warhead",
        "pentagon", "military", "airstrike", "deployment",
        "伊斯兰革命卫队", "真主党", "哈马斯", "胡塞", "停火", "空袭", "导弹", "袭击",
        "战争", "冲突", "交火", "无人机", "火箭弹", "人质", "军事", "轰炸", "边境",
        "ضربة", "هجوم", "صاروخ", "قتلى", "حرب", "حزب الله", "حماس", "الحوثيون", "مسيرة",
        "وقف إطلاق النار", "تصعيد", "قصف", "اشتباكات", "عسكري",
        "حمله", "موشک", "جنگ", "حزبالله", "پهپاد", "درگیری", "نظامی", "آتشبس",
        "תקיפה", "טיל", "מלחמה", "חיזבאללה", "חמאס", "חותים", "צבא", "התקפה",
    ],
    "energy": [
        "oil", "crude", "brent", "wti", "opec", "barrel", "refinery", "gas field",
        "production cut", "aramco", "lng", "petroleum", "energy", "gasoline",
        "output", "barrels per day", "bpd", "pipeline", "fuel", "nuclear",
        "石油", "原油", "油价", "天然气", "炼油", "产量", "减产", "管道", "核", "能源",
        "نفط", "أوبك", "برنت", "الخام", "مصفاة", "أرامكو", "غاز", "طاقة",
        "نفت", "اوپک", "پالایشگاه", "انرژی", "گاز",
        "נפט", "אופק", "גז", "אנרגיה",
    ],
    "shipping": [
        "red sea", "bab el-mandeb", "bab al-mandab", "strait of hormuz", "hormuz",
        "suez", "tanker", "vessel", "hijack", "shipping", "freight", "chokepoint",
        "port", "cargo", "maritime", "navy", "sea route", "supply chain", "ais",
        "红海", "霍尔木兹", "曼德海峡", "苏伊士", "油轮", "船舶", "航运", "海运", "港口",
        "货运", "供应链", "海军", "航线", "劫持", "遇袭",
        "البحر الأحمر", "هرمز", "قناة السويس", "ناقلة", "سفينة", "ملاحة", "ميناء",
        "تنگه هرمز", "کشتی", "نفتکش", "دریایی",
        "ים סוף", "הורמוז", "מכלית", "ספינה", "שיט",
    ],
    "finance": [
        "sovereign wealth", "pif", "mubadala", "adia", "qia", "ipo", "stock market",
        "tadawul", "equity", "bond", "investment", "acquisition", "sukuk", "currency",
        "devaluation", "central bank", "fund", "billion", "deal", "stake", "listing",
        "主权基金", "股市", "上市", "投资", "并购", "债券", "货币", "贬值", "央行", "基金",
        "股价", "指数", "收购", "股份", "融资",
        "صندوق الاستثمارات", "سوق الأسهم", "استثمار", "الطرح العام", "أسهم", "اقتصاد",
        "سرمایه", "بورس", "اقتصادی",
        "קרן", "שוק המניות", "השקעה", "כלכלה",
    ],
}

# ============================================================
# 二、风险等级关键词
# ============================================================
RISK_KEYWORDS = [
    (50, ["nuclear", "uranium enrichment", "full-scale war", "invasion", "blockade",
          "assassinated", "assassination", "declaration of war", "martial law",
          "核武", "核弹", "铀浓缩", "全面战争", "入侵", "封锁", "暗杀", "戒严",
          "سلاح نووی", "نووی", "سلاح نووي", "حرب شاملة", "اغتيال",
          "נשק גרעיני", "מלחמה כוללת"]),
    (30, ["airstrike", "air strike", "missile attack", "killed", "dead", "death toll",
          "explosion", "war", "attack", "bombardment", "casualties", "retaliation",
          "shelling", "drone attack", "assault", "firefight",
          "空袭", "导弹袭击", "死亡", "爆炸", "战争", "袭击", "伤亡", "报复", "轰炸",
          "قتلى", "انفجار", "قصف جوي",
          "حمله هوایی", "انفجار", "کشته",
          "הרג", "פיצוץ", "מתקפה"]),
    (15, ["tension", "threat", "threatened", "sanction", "protest", "deployment",
          "warning", "mobilize", "alert", "crisis", "unrest", "evacuate", "suspend",
          "紧张", "威胁", "制裁", "抗议", "部署", "警告", "动员", "警报", "危机", "撤离",
          "تهديد", "عقوبات", "احتجاج", "تحذير", "أزمة",
          "تهدید", "تحریم", "اعتراض", "هشدار",
          "איום", "סנקציות", "הפגנה", "אזהרה"]),
    (5, ["talks", "negotiation", "meeting", "diplomacy", "visit", "agreement", "deal",
         "会谈", "谈判", "会晤", "外交", "访问", "协议",
         "مفاوضات", "محادثات", "اتفاق", "زيارة",
         "مذاکره", "گفتگو", "توافق"]),
]

# ============================================================
# 三、实体词典（自动打标签）
# ============================================================
ENTITIES = {
    "countries": {
        "Iran": "伊朗", "Iranian": "伊朗", "Tehran": "德黑兰", "Israel": "以色列",
        "Israeli": "以色列", "Tel Aviv": "特拉维夫", "Saudi": "沙特", "Saudi Arabia": "沙特",
        "Riyadh": "利雅得", "UAE": "阿联酋", "Emirates": "阿联酋", "Abu Dhabi": "阿布扎比",
        "Dubai": "迪拜", "Qatar": "卡塔尔", "Doha": "多哈", "Turkey": "土耳其",
        "Turkish": "土耳其", "Egypt": "埃及", "Cairo": "开罗",
        "Lebanon": "黎巴嫩", "Beirut": "贝鲁特", "Syria": "叙利亚", "Damascus": "大马士革",
        "Iraq": "伊拉克", "Baghdad": "巴格达", "Yemen": "也门", "Sanaa": "萨那",
        "Jordan": "约旦", "Kuwait": "科威特", "Bahrain": "巴林", "Oman": "阿曼",
        "Libya": "利比亚", "Sudan": "苏丹", "Palestine": "巴勒斯坦", "Palestinian": "巴勒斯坦",
        "Gaza": "加沙", "West Bank": "约旦河西岸", "Jerusalem": "耶路撒冷",
    },
    "orgs": {
        "IDF": "以色列国防军", "IRGC": "伊斯兰革命卫队", "Hezbollah": "真主党",
        "Hamas": "哈马斯", "Houthi": "胡塞武装", "Houthis": "胡塞武装", "OPEC": "欧佩克",
        "PIF": "沙特公共投资基金", "Mubadala": "穆巴达拉", "ADIA": "阿布扎比投资局",
        "QIA": "卡塔尔投资局", "IAEA": "国际原子能机构", "NATO": "北约",
        "CENTCOM": "美军中央司令部", "Aramco": "沙特阿美", "Pentagon": "美国五角大楼",
        "UN": "联合国", "UNSC": "联合国安理会", "OIC": "伊斯兰合作组织",
    },
    "places": {
        "Strait of Hormuz": "霍尔木兹海峡", "Hormuz": "霍尔木兹海峡", "Red Sea": "红海",
        "Bab el-Mandeb": "曼德海峡", "Bab al-Mandab": "曼德海峡", "Suez": "苏伊士运河",
        "Persian Gulf": "波斯湾", "Gulf of Oman": "阿曼湾", "Natanz": "纳坦兹核设施",
        "Fordow": "福尔多核设施", "Bushehr": "布什尔核电站", "Ras Tanura": "拉斯坦努拉",
        "Abqaiq": "布盖格油田", "Chabahar": "恰巴哈尔港", "Haifa": "海法港",
        "Eilat": "埃拉特港", "Jebel Ali": "杰贝阿里港", "Hodeidah": "荷台达港",
        "Golan": "戈兰高地", "Sinai": "西奈半岛",
    },
    "persons": {
        "Netanyahu": "内塔尼亚胡", "Khamenei": "哈梅内伊", "Pezeshkian": "佩泽希齐扬",
        "bin Salman": "穆罕默德·本·萨勒曼", "Erdogan": "埃尔多安",
        "Sinwar": "辛瓦尔", "Abbas": "阿巴斯", "Trump": "特朗普", "Putin": "普京",
    },
}

# 中东相关性白名单补充词（命中任一即判定为中东相关）
MIDEAST_EXTRA = [
    "middle east", "mideast", "gulf", "gulf states", "levant", "arab world",
    "persian gulf", "opec+", "islamic state", "isis", "kurdish", "kurdistan",
    "中东", "波斯湾", "海湾", "阿拉伯", "伊斯兰国", "库尔德",
    "الشرق الأوسط", "الخليج", "خاورمیانه", "המזרח התיכון",
]

# 中东本地/专精信源：其报道默认视为中东相关（不受关键词白名单限制）
LOCAL_SOURCES = [
    "IRNA", "半岛", "以色列时报", "耶路撒冷邮报", "Middle East Eye", "Al-Monitor",
    "Middle East Institute", "海湾研究所", "阿纳多卢", "塔斯尼姆", "PressTV",
    "迈赫尔", "Al Arabiya", "ISW", "伊朗",
]

# 无关内容黑名单（命中且非中东相关则丢弃，防止噪声）
EXCLUDE_KEYWORDS = [
    "north korea", "kim jong", "k-pop", "kpop", "seoul", "pyongyang",
    "tokyo", "osaka", "beijing", "shanghai", "taipei", "taiwan",
    "call of duty", "playstation", "xbox", "nintendo", "video game",
    "premier league", "nba", "nfl", "champions league", "football match",
    "box office", "album", "netflix", "oscars", "grammy",
    "horoscope", "weather forecast", "lottery",
]

# ============================================================
# 四、Google News 多语定向查询
#     (查询语句, 语言, 地区, ceid, 领域提示)
# ============================================================
GNEWS_QUERIES = [
    ("Israel Iran strike attack", "en", "US", "US:en", "conflict"),
    ("Israel Lebanon Hezbollah", "en", "US", "US:en", "conflict"),
    ("Gaza ceasefire Hamas IDF", "en", "US", "US:en", "conflict"),
    ("Pentagon CENTCOM Middle East", "en", "US", "US:en", "conflict"),
    ("إيران إسرائيل هجوم", "ar", "SA", "SA:ar", "conflict"),
    ("اسرائیل ایران حمله", "fa", "IR", "IR:fa", "conflict"),
    ("איראן ישראל תקיפה", "iw", "IL", "IL:iw", "conflict"),
    ("Iran nuclear enrichment IAEA", "en", "US", "US:en", "conflict"),
    ("Syria Iraq militia attack", "en", "US", "US:en", "conflict"),
    ("Yemen Houthi Saudi", "en", "US", "US:en", "conflict"),
    ("OPEC oil production cut", "en", "US", "US:en", "energy"),
    ("oil price crude Brent WTI", "en", "US", "US:en", "energy"),
    ("Saudi Aramco oil output", "en", "US", "US:en", "energy"),
    ("أوبك النفط الإنتاج", "ar", "SA", "SA:ar", "energy"),
    ("Iran oil export sanction", "en", "US", "US:en", "energy"),
    ("Houthi Red Sea ship attack", "en", "US", "US:en", "shipping"),
    ("Strait of Hormuz tanker", "en", "US", "US:en", "shipping"),
    ("Suez Canal shipping traffic", "en", "US", "US:en", "shipping"),
    ("البحر الأحمر سفينة هجوم", "ar", "SA", "SA:ar", "shipping"),
    ("Saudi PIF investment fund", "en", "US", "US:en", "finance"),
    ("UAE Mubadala investment deal", "en", "US", "US:en", "finance"),
    ("Gulf stock market IPO Tadawul", "en", "US", "US:en", "finance"),
    ("سوق الأسهم السعودية استثمار", "ar", "SA", "SA:ar", "finance"),
]

# ============================================================
# 五、直连 RSS 源（已实测可用）
#     (名称, URL, 类型, 可信度权重, 默认领域)
# ============================================================
RSS_SOURCES = [
    # —— 官方 / 军方第一手 ——
    ("美国五角大楼 DoD", "https://www.defense.gov/DesktopModules/ArticleCS/RSS.ashx?ContentType=1&Site=945&max=20",
     "official", 1.4, "conflict"),
    ("伊朗通讯社 IRNA", "https://www.irna.ir/rss", "official", 1.2, "conflict"),
    ("土耳其阿纳多卢", "https://www.aa.com.tr/en/rss/default?cat=world", "official", 1.1, "conflict"),
    # —— 区域媒体 ——
    ("半岛电视台", "https://www.aljazeera.com/xml/rss/all.xml", "media", 1.0, "conflict"),
    ("以色列时报", "https://www.timesofisrael.com/feed/", "media", 1.1, "conflict"),
    ("耶路撒冷邮报", "https://www.jpost.com/Rss/RssFeedsHeadlines.aspx", "media", 1.0, "conflict"),
    ("Middle East Eye", "https://www.middleeasteye.net/rss", "media", 1.0, "conflict"),
    ("Al-Monitor", "https://www.al-monitor.com/rss", "media", 1.2, "conflict"),
    # —— 智库 ——
    ("CSIS 战略与国际研究中心", "https://www.csis.org/rss.xml", "thinktank", 1.3, "conflict"),
    ("Middle East Institute", "https://www.mei.edu/rss", "thinktank", 1.3, "conflict"),
    ("海湾研究所 AGSIW", "https://agsiw.org/feed", "thinktank", 1.2, "conflict"),
    # —— 综合财经 / 预警 ——
    ("Financial Times", "https://www.ft.com/rss/home", "media", 1.1, "finance"),
    ("GDACS 全球灾害预警", "https://www.gdacs.org/xml/rss.xml", "alert", 1.4, "conflict"),
]

# ============================================================
# 六、结构化实时数据接口
# ============================================================
MARKETS = {
    # 行情总开关：设为 False 则看板不再显示任何行情指标
    "show_quotes": True,
    # Yahoo 国际行情（已移除新浪源）
    "quotes": [
        ("BZ=F", "布伦特原油", "美元/桶"),
        ("CL=F", "WTI 原油", "美元/桶"),
        ("GC=F", "COMEX 黄金", "美元/盎司"),
    ],
    # 汇率：open.er-api.com 免费无 key，含全部海湾货币
    "fx_url": "https://open.er-api.com/v6/latest/USD",
    "fx_watch": ["ILS", "SAR", "AED", "QAR", "TRY", "EGP", "JOD", "KWD", "BHD", "OMR", "IQD", "IRR"],
    # 地震/爆炸监测（USGS，中东范围）
    "quake_url": ("https://earthquake.usgs.gov/fdsnws/event/1/query?format=geojson"
                  "&latitude=29&longitude=48&maxradiuskm=1900&minmagnitude=2.5"
                  "&orderby=time&limit=30"),
    # NASA FIRMS 卫星火点（需 API_KEYS["firms"]）
    "firms_bbox": "25,12,63,40",          # 西,南,东,北
    "firms_sources": ["VIIRS_NOAA20_NRT", "VIIRS_SNPP_NRT"],
    # OpenSky 中东空域（lamin,lomin,lamax,lomax）
    "opensky_bbox": (10.0, 25.0, 42.0, 65.0),
    # AISStream 关键海域 [[南,西],[北,东]]  lat,lon
    "ais_boxes": [
        [[24.0, 48.0], [30.5, 56.5]],     # 波斯湾
        [[25.0, 55.0], [27.5, 57.5]],     # 霍尔木兹海峡
        [[11.5, 41.5], [16.0, 46.0]],     # 曼德海峡 / 红海南
        [[27.0, 32.0], [31.5, 35.5]],     # 苏伊士 / 红海北
    ],
}

# 重点监控坐标（地震/火点属地判定）
MONITOR_SITES = [
    ("伊朗纳坦兹核设施", 33.72, 51.72), ("伊朗福尔多核设施", 34.88, 50.55),
    ("伊朗布什尔核电站", 28.83, 50.89), ("德黑兰", 35.69, 51.39),
    ("以色列迪莫纳核基地", 31.00, 35.15), ("特拉维夫", 32.08, 34.78),
    ("拉斯坦努拉炼油厂", 26.64, 50.16), ("布盖格油田", 25.93, 49.67),
    ("霍尔木兹海峡", 26.57, 56.25), ("曼德海峡", 12.58, 43.33),
    ("荷台达港", 14.80, 42.95), ("贝鲁特", 33.89, 35.50),
    ("大马士革", 33.51, 36.29), ("巴格达", 33.31, 44.36),
]

# 军用/政府航空器呼号前缀（OpenSky 军用机识别）
MILITARY_CALLSIGN = [
    "RCH", "REACH", "DUKE", "SPUR", "TOPCAT", "NAVY", "CNVY", "EVAC",
    "SAM", "GORDO", "BISON", "HAWK", "VIPER", "SNAKE", "MAGMA", "PATRIOT",
    "ISR", "AWACS", "SENTRY", "JOLLY", "PEDRO", "KING", "BOXER",
]

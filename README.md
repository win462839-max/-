# 中东第一手情报工作台

零第三方依赖（仅 Python 标准库）的中东情报自动采集与可视化工作台。
每 30 分钟自动抓取一次，输出网页看板。

## 一、快速开始

```bat
启动采集.bat        :: 后台常驻采集（每30分钟一轮）+ 自动打开看板
停止采集.bat        :: 停止采集
安装开机自启.bat    :: 注册计划任务，登录后自动运行（需管理员）
```

也可以手动跑一次（不常驻）：

```bash
python collector.py            # 抓取一次，输出到 data/latest.json
python collector.py --daemon   # 常驻，每 30 分钟一轮
python collector.py --daemon --interval 15   # 改成 15 分钟
```

看板：**双击 `dashboard.html`** 即可（数据以 `data/latest.js` 形式内嵌加载，无需起服务）。
若需自动刷新，建议起本地服务后访问 `http://127.0.0.1:8000/dashboard.html`：

```bash
python -m http.server 8000
```

## 二、看板能看什么

| 区域 | 内容 |
|---|---|
| 风险仪表盘 | 0-100 综合风险指数、等级、环比趋势、一句话研判（自动融合油价/火点/军机/震动） |
| 指标条 | 布伦特、WTI、黄金、白银实时价与涨跌；12 种中东货币汇率；地震与空域 |
| 情报流 | 按风险/时间排序，四大领域分栏（地缘冲突 / 能源油价 / 航运物流 / 金融市场） |
| 每条情报 | 风险分、原文标题、中文翻译、信源、发布时间、实体标签、命中关键词、语种 |
| 实时传感 | 卫星火点、中东空域航班与军机、AIS 船舶（需 API Key） |
| 侧栏 | 领域分布、高频主体（国家/组织/地点）、信源接入状态 |

支持：领域 Tab 切换、等级筛选、按风险/时间排序、全文搜索（标题/来源/实体），
阿拉伯语与希伯来语自动按 RTL 方向渲染。

## 三、信源清单（全部实测）

**已接入（直连可用）**
- 官方/军方：美国五角大楼 DoD、伊朗通讯社 IRNA、土耳其阿纳多卢
- 区域媒体：半岛电视台、以色列时报、耶路撒冷邮报、Middle East Eye、Al-Monitor
- 智库：CSIS、Middle East Institute（MEI）、海湾研究所 AGSIW
- 财经/预警：Financial Times、GDACS 全球灾害预警
- 聚合：Google News 多语定向查询 23 组（英/阿拉伯/波斯/希伯来）
- 结构化：新浪外盘期货（布伦特/WTI/黄金/白银）、open.er-api 汇率、USGS 中东地震、OpenSky 空域

**需代理（已在 config.py 配置，网络通时自动解锁）**
ISW 战争研究所、伊朗塔斯尼姆/PressTV/迈赫尔、Al Arabiya、Arab News、The National、ACLED

**已停用（对方下线 RSS，不是网络问题）**
沙特 SPA、阿联酋 WAM、卡内基、卡塔尔 QNA、埃及 MENA、路透、彭博

## 四、配置 API Key（可选，解锁卫星/船舶/航班级一手数据）

编辑 `config.py` 的 `API_KEYS`，填入后对应模块自动启用，未填则自动跳过：

| Key | 用途 | 申请地址 |
|---|---|---|
| `firms` | NASA 卫星火点：监测炼油厂、核设施、军事基地火灾爆炸，比新闻快数小时 | https://firms.modaps.eosdis.nasa.gov/api/map_key/ |
| `eia` | EIA 官方布伦特现货价与库存 | https://www.eia.gov/opendata/register.php |
| `aisstream` | 船舶 AIS：红海/霍尔木兹实时船位、油轮动态 | https://aisstream.io/authenticate |
| `opensky_user/pass` | 中东空域航班与军机异动 | https://opensky-network.org/ |

## 五、代理设置

`config.py` 顶部：

```python
PROXY = "http://127.0.0.1:10808"   # 当前值：你的 v2rayN 端口
# PROXY = "auto"                   # 或自动读取 Windows 系统代理
# PROXY = None                     # 或直连
```

- 手动指定地址时，**所有请求走代理**
- `"auto"` 时，仅 `PROXY_ONLY_HOSTS` 列表内的受限域名走代理，其余直连（更快）

> 注意：v2rayN 需切到**全局模式**（规则模式下部分域名不走代理）。
> 切换后下一轮采集自动解锁 ISW、伊朗系媒体等源。

## 六、云端 24 小时运行（GitHub Actions + Pages）

已内置 `.github/workflows/collect.yml`：

1. 新建 GitHub 仓库，把本目录 push 上去
2. 仓库 Settings → Pages → Source 选 **GitHub Actions**
3. 每 30 分钟自动抓取并提交数据，同时发布看板为在线链接（手机可访问）

如需云端也用代理，在仓库 Settings → Secrets 添加 `PROXY_URL` 并在 workflow 中设为环境变量。

## 七、文件说明

```
config.py        信源、关键词词典、实体表、API Key、代理（改这里）
collector.py     采集主程序（RSS自研解析、多语打分、实体识别、翻译缓存、调度）
sensors.py       高级传感（卫星火点 / 空域 / 船舶AIS / EIA）
dashboard.html   看板页面
data/latest.json 最新数据（看板数据源）
data/latest.js   同数据的 JS 版，供 file:// 直接打开
data/history.jsonl 历次风险指数归档
data/collector.log 运行日志
```

## 八、风险指数怎么算的

```
综合风险 = 极高危条目×7 + 高危条目×3 + min(18, |油价日涨跌|×3.5)
          + 重点区域异常震动×6 + 卫星火点告警×5 + min(10, 军机数÷3)
```

单条风险分 = 关键词权重（核战/入侵 50，空袭/导弹/死亡 30，威胁/制裁 15，会谈 5）
× 信源可信度（官方 1.2-1.4、智库 1.3、媒体 1.0、聚合 0.9）× 时效系数（2小时内 ×1.15）。

所有权重可在 `config.py` 的 `RISK_KEYWORDS` 与 `RSS_SOURCES` 中调整。

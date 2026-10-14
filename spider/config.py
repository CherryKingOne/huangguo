"""全局配置。"""
from __future__ import annotations

import os
from typing import Dict

# ---------------------------------------------------------------------------
# 站点
# ---------------------------------------------------------------------------
BASE_URL = "https://7e1be.uc41p53k.cc"
SITE_NAME = "黄果短剧"
# 首页地址: 仅提供此地址即可自动发现所有视频频道并爬取。
HOME_URL = BASE_URL + "/"

# 频道发现: 从首页导航自动识别视频列表频道。
# 首页顶部导航项形如 <a ... href="/ai-duanju/" data-nav-key="ai-duanju">AI成人短剧</a>
# 只采集 data-nav-key 以 "ai-" 开头的视频类频道, 排除 topics/ranks/chigua 等。
CHANNEL_PREFIX = "ai-"

# 运行时发现的频道中文名映射(由 crawler 填充): {slug: 中文名}。
CHANNEL_NAME: Dict[str, str] = {}

# 兜底频道列表: 若自动发现失败时使用。
FALLBACK_CHANNELS = {
    "ai-duanju": "AI成人短剧",
    "ai-manju": "AI成人漫剧",
    "ai-huanlian": "AI换脸",
    "ai-mogai": "AI魔改",
}

# ---------------------------------------------------------------------------
# 网络
# ---------------------------------------------------------------------------
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 "
    "Firefox/122.0",
]

DEFAULT_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
}

TIMEOUT = 25              # 单次请求超时(秒)
MAX_RETRIES = 4           # 失败重试次数
BACKOFF_FACTOR = 1.2      # 指数退避因子
# 请求间隔区间(秒), 随机化以降低被限流概率
MIN_DELAY = 0.6
MAX_DELAY = 1.6

# ---------------------------------------------------------------------------
# 输出
# ---------------------------------------------------------------------------
PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(PROJECT_DIR, "output")
DEFAULT_XLSX = os.path.join(OUTPUT_DIR, "huangguo_videos.xlsx")

# ---------------------------------------------------------------------------
# 运行
# ---------------------------------------------------------------------------
# 是否抓取作者页获取"关注数量(粉丝数)"。需要额外一次请求/作者, 可关闭提速。
FETCH_FOLLOWERS = True

# 是否采集全部剧集的 m3u8 地址(详情页已含全部集, 默认采集)。
INCLUDE_ALL_EPISODES = True

# 每个频道最多抓取的页数。None 表示抓完所有页。
MAX_PAGES_PER_CHANNEL = None


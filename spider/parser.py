"""页面解析: 列表页卡片、详情页 JSON、作者粉丝数。"""
from __future__ import annotations

import json
import logging
import re
from typing import Dict, List, Optional

from . import config

logger = logging.getLogger(__name__)

# 视频详情链接 /video/{id}/
_VIDEO_HREF_RE = re.compile(r'href="(/video/\d+/)"')
_VIDEO_ID_RE = re.compile(r"/video/(\d+)/")

# 详情页内嵌的完整视频数据 JSON
_INITIAL_DATA_RE = re.compile(
    r'<script id="videoInitialData" type="application/json">(.*?)</script>',
    re.S,
)

# 作者页粉丝数, 例如: <span data-author-followers ...>7.6k粉丝</span>
_FOLLOWERS_RE = re.compile(
    r'data-author-followers[^>]*>\s*([\d\.]+[wk万]?)\s*粉丝',
    re.S,
)

# 首页顶部导航视频频道项:
# <a class="hg-topbar-nav__item" href="/ai-duanju/" data-nav-key="ai-duanju">AI成人短剧</a>
_NAV_CHANNEL_RE = re.compile(
    r'<a[^>]*href="(/[^"/]+/)"[^>]*data-nav-key="([^"]+)"[^>]*>([^<]+)</a>'
)

# 分页最大页数: data-pages="50"(来自跳转控件), 比遍历链接更可靠。
_MAX_PAGES_RE = re.compile(r'data-pages="(\d+)"')


def _clean(text: Optional[str]) -> str:
    """去除 HTML 标签与首尾空白, 折叠内部换行。"""
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", "", text)
    text = text.replace("\r", " ").replace("\n", " ")
    return re.sub(r"\s+", " ", text).strip()


def parse_list_page(html: str) -> List[Dict[str, str]]:
    """解析频道列表页, 返回卡片摘要列表。

    只取当前激活(latest)面板, 避免隐藏面板产生重复。
    """
    if not html:
        return []

    # 截取 latest 面板主体(到下一个面板前), 降低重复概率
    active = re.search(
        r'data-channel-panel="latest"[^>]*>(.*?)'
        r'<div class="hg-card-grid" data-channel-panel="hot"',
        html,
        re.S,
    )
    block = active.group(1) if active else html

    # 以每张卡片为单元切分
    chunks = block.split('<div class="hg-drama-card"')
    cards: List[Dict[str, str]] = []
    seen = set()
    for chunk in chunks[1:]:
        vid = re.search(r'data-track-id="(\d+)"', chunk)
        if not vid:
            continue
        video_id = vid.group(1)
        if video_id in seen:
            continue
        seen.add(video_id)

        href = _VIDEO_HREF_RE.search(chunk)
        title = re.search(r'data-track-title="([^"]*)"', chunk)
        cover = re.search(r'data-src="(https://pic[^"]+)"', chunk)
        desc = re.search(r'class="hg-drama-card__desc">(.*?)</p>', chunk, re.S)
        ep = re.search(
            r'class="hg-drama-card__episode"[^>]*>(.*?)</span>', chunk, re.S
        )
        score = re.search(
            r'class="hg-drama-card__score">([^<]*)</span>', chunk
        )

        cards.append({
            "video_id": video_id,
            "detail_path": href.group(1) if href else f"/video/{video_id}/",
            "title": title.group(1) if title else "",
            "cover_url": cover.group(1) if cover else "",
            "description": _clean(desc.group(1)) if desc else "",
            "episode_text": _clean(ep.group(1)) if ep else "",
            "score": score.group(1).strip() if score else "",
        })

    return cards


def parse_detail_page(html: str) -> Optional[Dict[str, object]]:
    """解析详情页内嵌的 videoInitialData JSON。"""
    if not html:
        return None
    m = _INITIAL_DATA_RE.search(html)
    if not m:
        logger.warning("未找到 videoInitialData")
        return None
    try:
        data = json.loads(m.group(1))
    except json.JSONDecodeError as exc:
        logger.error("videoInitialData JSON 解析失败: %s", exc)
        return None
    return data


def extract_episode_urls(data: Dict[str, object]) -> List[str]:
    """从详情数据中按集数顺序提取全部 m3u8 地址。"""
    srcs = data.get("epPlaySrcs")
    urls: List[str] = []
    if isinstance(srcs, dict) and srcs:
        # 键为集号字符串, 按整数排序
        def _key(k: str) -> int:
            try:
                return int(k)
            except ValueError:
                return 0
        for k in sorted(srcs.keys(), key=_key):
            url = srcs.get(k)
            if url:
                urls.append(url)
    if not urls and data.get("videoSrc"):
        urls.append(str(data["videoSrc"]))
    return urls


def parse_author_followers(html: str) -> str:
    """解析作者页粉丝数(关注数量)。"""
    if not html:
        return ""
    m = _FOLLOWERS_RE.search(html)
    return m.group(1) if m else ""


def build_detail_url(video_id: str) -> str:
    return f"{config.BASE_URL}/video/{video_id}/"


def discover_channels(html: str, prefix: str = config.CHANNEL_PREFIX) -> Dict[str, str]:
    """从首页 HTML 自动发现视频频道。

    返回 {slug: 中文名}, 例如 {'ai-duanju': 'AI成人短剧', ...}。
    只取 data-nav-key 以 prefix(默认 'ai-') 开头的导航项。
    """
    channels: Dict[str, str] = {}
    if not html:
        return channels
    for m in _NAV_CHANNEL_RE.finditer(html):
        path, nav_key, name = m.group(1), m.group(2), m.group(3)
        slug = nav_key.strip()
        if not slug.startswith(prefix):
            continue
        # 用 path 前缀进一步确认(如 /ai-duanju/), 避免误匹配
        if not path.startswith("/" + slug + "/"):
            # 兼容 path 与 nav_key 不完全一致的情况, 以 nav_key 为准
            pass
        channels[slug] = _clean(name)
    return channels


def max_page_from_html(html: str) -> int:
    """从分页控件读取最大页数, 兜底为 1。"""
    if not html:
        return 1
    m = _MAX_PAGES_RE.search(html)
    if m:
        return int(m.group(1))
    pages = [int(x) for x in re.findall(r'href="/[^"]+?/(\d+)/"', html)]
    return max(pages) if pages else 1


"""任务编排: 首页发现频道 -> 频道分页 -> 详情 -> 作者粉丝数 -> XLSX。"""
from __future__ import annotations

import logging
import re
import time
from typing import Dict, List, Optional

from . import config, parser
from .client import HttpClient
from .models import VideoItem, fmt_number
from .storage import XlsxStorage

logger = logging.getLogger(__name__)

_EP_COUNT_RE = re.compile(r"(\d+)\s*集")


def _episode_count_from_text(text: str) -> int:
    """从 '更新至12集' / '全43集' 中提取集数。"""
    if not text:
        return 0
    m = _EP_COUNT_RE.search(text)
    return int(m.group(1)) if m else 0


class Crawler:
    def __init__(
        self,
        home_url: str = config.HOME_URL,
        output_xlsx: str = config.DEFAULT_XLSX,
        fetch_followers: bool = config.FETCH_FOLLOWERS,
        max_pages: Optional[int] = config.MAX_PAGES_PER_CHANNEL,
    ) -> None:
        self.home_url = home_url
        self.client = HttpClient()
        self.storage = XlsxStorage(output_xlsx)
        self.fetch_followers = fetch_followers
        self.max_pages = max_pages
        self._followers_cache: Dict[str, str] = {}  # 作者ID -> 粉丝数

    def _channel_page_url(self, slug: str, page: int) -> str:
        base = f"{config.BASE_URL}/{slug}/"
        return base if page <= 1 else f"{base}{page}/"

    def discover_channels(self) -> Dict[str, str]:
        """从首页自动发现视频频道, 失败时回退到 FALLBACK_CHANNELS。"""
        html = self.client.get(self.home_url)
        channels = parser.discover_channels(html) if html else {}
        if not channels:
            logger.warning("首页未发现视频频道, 使用兜底频道列表")
            channels = dict(config.FALLBACK_CHANNELS)
        logger.info("发现 %d 个视频频道: %s", len(channels), list(channels))
        return channels

    def collect_channel_ids(self, slug: str) -> List[Dict[str, str]]:
        """遍历频道所有分页, 汇总卡片列表(已按 ID 去重)。"""
        result: List[Dict[str, str]] = []
        seen = set()
        page = 1
        max_page = self.max_pages or 10 ** 9
        while page <= max_page:
            url = self._channel_page_url(slug, page)
            html = self.client.get(url)
            if not html:
                logger.warning("频道 %s 第 %d 页抓取失败, 停止该频道", slug, page)
                break
            if page == 1:
                total_pages = parser.max_page_from_html(html)
                max_page = min(max_page, total_pages) if self.max_pages \
                    else total_pages
                logger.info("频道 %s 共 %d 页", slug, max_page)

            cards = parser.parse_list_page(html)
            if not cards:
                logger.info("频道 %s 第 %d 页无卡片, 结束分页", slug, page)
                break

            new = 0
            for c in cards:
                vid = c["video_id"]
                if vid in seen:
                    continue
                seen.add(vid)
                result.append(c)
                new += 1
            logger.info("频道 %s 第 %d 页: %d 张卡片 (新增 %d)",
                        slug, page, len(cards), new)
            if new == 0:
                break
            page += 1
        return result

    def _get_followers(self, author_id: str) -> str:
        if not author_id:
            return ""
        if author_id in self._followers_cache:
            return self._followers_cache[author_id]
        url = f"{config.BASE_URL}/author/{author_id}/"
        html = self.client.get(url, referer=config.BASE_URL + "/")
        followers = parser.parse_author_followers(html) if html else ""
        self._followers_cache[author_id] = followers
        return followers

    def _build_item(
        self, card: Dict[str, str], data: Dict[str, object]
    ) -> VideoItem:
        video_id = str(data.get("id") or card["video_id"])
        ep_urls = parser.extract_episode_urls(data)
        ep_count = len(ep_urls)
        if ep_count == 0:
            ep_count = _episode_count_from_text(card.get("episode_text", ""))

        author_id = str(data.get("authorId") or "")
        followers = ""
        if self.fetch_followers and author_id:
            followers = self._get_followers(author_id)

        tags = data.get("tags") or []
        tags_str = "、".join(str(t) for t in tags) if isinstance(tags, list) else ""

        return VideoItem(
            site_url=parser.build_detail_url(video_id),
            title=str(data.get("title") or card.get("title", "")),
            episode_count=ep_count,
            video_url=ep_urls[0] if ep_urls else "",
            cover_url=str(data.get("coverSrc")
                          or data.get("posterSrc")
                          or card.get("cover_url", "")),
            description=str(data.get("description")
                            or card.get("description", "")),
            likes=fmt_number(data.get("likesNum") or data.get("likes")),
            followers=followers,
            video_id=video_id,
            category=config.CHANNEL_NAME.get(card.get("_slug", ""), ""),
            views=fmt_number(data.get("views")),
            collects=fmt_number(data.get("collectsNum")
                                or data.get("collects")),
            score=card.get("score", ""),
            author=str(data.get("author", "")),
            author_id=author_id,
            tags=tags_str,
            publish_time=str(data.get("time", "")),
            detail_url=parser.build_detail_url(video_id),
            all_episode_urls=" | ".join(ep_urls),
        )

    def crawl_video(self, card: Dict[str, str]) -> Optional[VideoItem]:
        """抓取单个视频详情并构造记录。失败或已抓取返回 None。"""
        video_id = card["video_id"]
        if self.storage.has(video_id):
            logger.info("跳过已抓取: %s", video_id)
            return None

        url = f"{config.BASE_URL}{card['detail_path']}"
        html = self.client.get(url, referer=config.BASE_URL + "/")
        if not html:
            logger.warning("详情抓取失败: %s", url)
            return None
        data = parser.parse_detail_page(html)
        if not data:
            logger.warning("详情解析失败: %s", url)
            return None

        item = self._build_item(card, data)
        self.storage.append(item.to_row())
        return item

    def run(self) -> int:
        """主入口: 首页发现频道 -> 逐频道分页 -> 详情 -> XLSX。返回新增数。"""
        start = time.monotonic()
        total_new = 0
        try:
            channels = self.discover_channels()
            # 记录频道中文名供 _build_item 使用
            config.CHANNEL_NAME = channels

            for slug, name in channels.items():
                logger.info("=== 开始频道: %s (%s) ===", name, slug)
                cards = self.collect_channel_ids(slug)
                for c in cards:
                    c["_slug"] = slug
                logger.info("频道 %s 汇总 %d 个视频", name, len(cards))

                for idx, card in enumerate(cards, 1):
                    item = self.crawl_video(card)
                    if item:
                        total_new += 1
                        logger.info(
                            "[%s %d/%d] %s | 集数=%s 赞=%s 关注=%s",
                            name, idx, len(cards), item.title,
                            item.episode_count, item.likes, item.followers,
                        )
            self.storage.flush()
        finally:
            self.client.close()

        elapsed = time.monotonic() - start
        logger.info(
            "完成: 本次新增 %d 条, XLSX 累计 %d 条, 耗时 %.1fs, 输出 %s",
            total_new, self.storage.total, elapsed, self.storage.path,
        )
        return total_new


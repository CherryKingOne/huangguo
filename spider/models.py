"""数据模型与 CSV 字段定义。"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Dict, List

# ---------------------------------------------------------------------------
# CSV 列定义。
# 前 8 列为用户需求字段(顺序与需求一致), 其余为便于后续使用的辅助字段。
# ---------------------------------------------------------------------------
CSV_COLUMNS: List[str] = [
    "网站网址",          # 视频详情页 URL
    "视频名称",          # title
    "视频集数",          # 剧集数量
    "视频的地址",        # 第 1 集 m3u8 播放地址
    "视频封面url",       # 封面图片 URL
    "视频介绍",          # 简介/描述
    "点赞数量",          # 点赞数
    "关注数量",          # 作者粉丝数(关注该作者的人数)
    # ---- 以下为辅助字段 ----
    "视频ID",
    "分类",
    "播放量",
    "收藏数量",
    "评分",
    "作者",
    "作者ID",
    "标签",
    "发布时间",
    "详情页URL",
    "全部剧集地址",
]

# 中文列名 -> dataclass 英文字段名 的映射(供 to_row 使用)。
_COL_TO_FIELD: Dict[str, str] = {
    "网站网址": "site_url",
    "视频名称": "title",
    "视频集数": "episode_count",
    "视频的地址": "video_url",
    "视频封面url": "cover_url",
    "视频介绍": "description",
    "点赞数量": "likes",
    "关注数量": "followers",
    "视频ID": "video_id",
    "分类": "category",
    "播放量": "views",
    "收藏数量": "collects",
    "评分": "score",
    "作者": "author",
    "作者ID": "author_id",
    "标签": "tags",
    "发布时间": "publish_time",
    "详情页URL": "detail_url",
    "全部剧集地址": "all_episode_urls",
}


@dataclass
class VideoItem:
    """一条视频记录。"""
    site_url: str = ""          # 详情页完整 URL(即"网站网址")
    title: str = ""             # 视频名称
    episode_count: int = 0      # 视频集数
    video_url: str = ""         # 视频的地址(第 1 集)
    cover_url: str = ""         # 视频封面 url
    description: str = ""       # 视频介绍
    likes: str = ""             # 点赞数量
    followers: str = ""         # 关注数量(作者粉丝数)

    # 辅助字段
    video_id: str = ""
    category: str = ""
    views: str = ""
    collects: str = ""
    score: str = ""
    author: str = ""
    author_id: str = ""
    tags: str = ""
    publish_time: str = ""
    detail_url: str = ""
    all_episode_urls: str = ""

    def to_row(self) -> Dict[str, object]:
        """按 CSV_COLUMNS 顺序输出一行有序字典。

        需要把中文列名映射到 dataclass 的英文字段名。
        """
        d = asdict(self)
        return {col: d.get(_COL_TO_FIELD[col], "") for col in CSV_COLUMNS}


def fmt_number(value: object) -> str:
    """把 1350 / '1.4k' / '0.4w' 等规整为字符串。"""
    if value is None:
        return ""
    if isinstance(value, (int, float)):
        return str(value)
    return str(value).strip()

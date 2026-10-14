"""黄果短剧爬虫入口。

用法:
    uv run main.py                          # 仅给首页即可自动发现频道并爬取
    uv run main.py --url https://xxx/       # 指定首页地址
    uv run main.py --max-pages 1            # 每个频道只抓前 1 页(调试用)
    uv run main.py --no-followers           # 不抓作者粉丝数(更快)
    uv run main.py -o data/hg.xlsx          # 自定义 XLSX 输出路径
"""
from __future__ import annotations

import argparse
import logging
import sys

from spider import config
from spider.crawler import Crawler


def parse_args(argv=None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="黄果短剧爬虫: 从首页自动发现频道, 抓取视频名称/集数/地址/"
        "封面/介绍/点赞/关注等, 保存为 XLSX。"
    )
    p.add_argument(
        "-u", "--url", default=config.HOME_URL,
        help=f"站点首页地址 (默认: {config.HOME_URL})",
    )
    p.add_argument(
        "-o", "--output", default=config.DEFAULT_XLSX,
        help=f"XLSX 输出路径 (默认: {config.DEFAULT_XLSX})",
    )
    p.add_argument(
        "--max-pages", type=int, default=None,
        help="每个频道最多抓取的页数 (默认全部)",
    )
    p.add_argument(
        "--no-followers", action="store_true",
        help="不抓取作者粉丝数(关注数量), 可显著提速",
    )
    p.add_argument(
        "-v", "--verbose", action="store_true", help="输出调试日志",
    )
    return p.parse_args(argv)


def setup_logging(verbose: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
        stream=sys.stdout,
    )


def main(argv=None) -> int:
    args = parse_args(argv)
    setup_logging(args.verbose)

    crawler = Crawler(
        home_url=args.url,
        output_xlsx=args.output,
        fetch_followers=not args.no_followers,
        max_pages=args.max_pages,
    )
    crawler.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())



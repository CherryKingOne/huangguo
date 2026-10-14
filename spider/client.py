"""HTTP 客户端: 会话管理、重试、限速、随机 UA。"""
from __future__ import annotations

import logging
import random
import time
from typing import Optional

import requests

from . import config

logger = logging.getLogger(__name__)


class HttpClient:
    """带重试与限速的 requests 会话封装。"""

    def __init__(
        self,
        min_delay: float = config.MIN_DELAY,
        max_delay: float = config.MAX_DELAY,
        timeout: int = config.TIMEOUT,
        max_retries: int = config.MAX_RETRIES,
    ) -> None:
        self.timeout = timeout
        self.max_retries = max_retries
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.session = requests.Session()
        self._last_request_ts = 0.0

    def _headers(self) -> dict:
        headers = dict(config.DEFAULT_HEADERS)
        headers["User-Agent"] = random.choice(config.USER_AGENTS)
        return headers

    def _throttle(self) -> None:
        """两次请求之间保持随机间隔。"""
        elapsed = time.monotonic() - self._last_request_ts
        wait = random.uniform(self.min_delay, self.max_delay)
        if elapsed < wait:
            time.sleep(wait - elapsed)

    def get(self, url: str, referer: Optional[str] = None) -> Optional[str]:
        """GET 请求并返回文本; 失败重试, 最终失败返回 None。"""
        headers = self._headers()
        if referer:
            headers["Referer"] = referer
        last_err: Optional[Exception] = None

        for attempt in range(1, self.max_retries + 1):
            self._throttle()
            try:
                resp = self.session.get(
                    url, headers=headers, timeout=self.timeout
                )
                self._last_request_ts = time.monotonic()
                if resp.status_code == 200 and resp.text:
                    return resp.text
                last_err = RuntimeError(f"HTTP {resp.status_code}")
                logger.warning(
                    "请求 %s 返回状态 %s (第 %d 次)", url, resp.status_code, attempt
                )
            except requests.RequestException as exc:  # 网络层异常
                last_err = exc
                logger.warning("请求 %s 异常: %s (第 %d 次)", url, exc, attempt)

            # 指数退避
            backoff = config.BACKOFF_FACTOR ** attempt + random.random()
            time.sleep(min(backoff, 10))

        logger.error("请求 %s 最终失败: %s", url, last_err)
        return None

    def close(self) -> None:
        self.session.close()

"""XLSX 增量落盘。"""
from __future__ import annotations

import logging
import os
from typing import Dict, Iterable, Set

from openpyxl import Workbook, load_workbook

from .models import CSV_COLUMNS

logger = logging.getLogger(__name__)

# 卡片ID(视频ID)列名, 用于断点续抓去重。
ID_COLUMN = "视频ID"
# 表头 sheet 名。
SHEET_NAME = "视频数据"


class XlsxStorage:
    """把记录写入 XLSX(.xlsx)。

    - 文件不存在时创建并写入表头(列定义见 CSV_COLUMNS)。
    - 记录已抓取过的卡片ID(视频ID)以支持断点续抓。
    - 采用"内存累积 + 定期落盘"策略: 每 flush_every 条或结束保存一次,
      兼顾速度与崩溃时的数据保留。
    """

    def __init__(self, path: str, flush_every: int = 20) -> None:
        self.path = path
        self.flush_every = max(1, flush_every)
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        self._seen: Set[str] = set()
        self._pending: list = []
        self._load_or_create()

    # ------------------------------------------------------------------
    def _load_or_create(self) -> None:
        """加载已存在的工作簿(读取已抓取ID)或新建。"""
        if os.path.exists(self.path) and os.path.getsize(self.path) > 0:
            try:
                wb = load_workbook(self.path)
                ws = wb.active
                header = [c.value for c in ws[1]] if ws.max_row >= 1 else []
                if header and ID_COLUMN in header:
                    idx = header.index(ID_COLUMN) + 1
                    for row in ws.iter_rows(min_row=2, min_col=idx, max_col=idx):
                        val = row[0].value
                        if val is not None and str(val).strip():
                            self._seen.add(str(val).strip())
                logger.info("已加载 XLSX 中 %d 个卡片ID用于续抓", len(self._seen))
            except Exception as exc:  # 文件损坏等情况
                logger.warning("读取已存在 XLSX 失败, 将新建: %s", exc)
                self._seen = set()

    def has(self, card_id: str) -> bool:
        return card_id in self._seen

    def append(self, row: Dict[str, object]) -> None:
        """累积一行记录; 达到阈值时自动落盘。"""
        self._pending.append({col: row.get(col, "") for col in CSV_COLUMNS})
        cid = str(row.get(ID_COLUMN, "")).strip()
        if cid:
            self._seen.add(cid)
        if len(self._pending) >= self.flush_every:
            self.flush()

    def append_many(self, rows: Iterable[Dict[str, object]]) -> int:
        count = 0
        for row in rows:
            self.append(row)
            count += 1
        return count

    def flush(self) -> None:
        """把累积的记录写入 XLSX 并保存。"""
        if not self._pending:
            return

        if os.path.exists(self.path) and os.path.getsize(self.path) > 0:
            try:
                wb = load_workbook(self.path)
                ws = wb.active
            except Exception:
                wb = Workbook()
                ws = wb.active
                ws.title = SHEET_NAME
                ws.append(list(CSV_COLUMNS))
        else:
            wb = Workbook()
            ws = wb.active
            ws.title = SHEET_NAME
            ws.append(list(CSV_COLUMNS))

        for row in self._pending:
            ws.append([row.get(col, "") for col in CSV_COLUMNS])

        wb.save(self.path)
        written = len(self._pending)
        self._pending = []
        logger.info("已写入 %d 条到 XLSX (累计卡片ID %d)", written, len(self._seen))

    @property
    def total(self) -> int:
        return len(self._seen)

"""持久化模块：SQLite 记录运行日志，支持文件大小控制"""

import logging
import os
import sqlite3
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

# 建表 SQL
_INIT_SQL = """
CREATE TABLE IF NOT EXISTS run_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_date TEXT NOT NULL,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    total_sources INTEGER DEFAULT 0,
    success_count INTEGER DEFAULT 0,
    fail_count INTEGER DEFAULT 0,
    news_count INTEGER DEFAULT 0,
    duration_sec REAL DEFAULT 0,
    status TEXT DEFAULT 'running'
);

CREATE TABLE IF NOT EXISTS source_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER NOT NULL,
    source_name TEXT NOT NULL,
    url TEXT,
    success INTEGER DEFAULT 0,
    error_msg TEXT,
    char_count INTEGER DEFAULT 0,
    news_count INTEGER DEFAULT 0,
    FOREIGN KEY (run_id) REFERENCES run_logs(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_run_logs_date ON run_logs(run_date);
CREATE INDEX IF NOT EXISTS idx_source_logs_run ON source_logs(run_id);
"""


@dataclass
class RunStats:
    """单次运行的统计信息"""

    run_id: int
    total_sources: int
    success_count: int
    fail_count: int
    news_count: int
    duration_sec: float
    success_rate: float


class Store:
    """SQLite 日志存储，支持文件大小自动清理"""

    def __init__(self, db_path: str | Path, max_size_mb: float = 50):
        """初始化存储

        Args:
            db_path: 数据库文件路径
            max_size_mb: 数据库文件大小上限（MB），超过后清理旧记录
        """
        self.db_path = Path(db_path)
        self.max_size_bytes = int(max_size_mb * 1024 * 1024)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn: sqlite3.Connection | None = None
        self._init_db()

    def _init_db(self) -> None:
        """初始化数据库和表结构"""
        conn = self._get_conn()
        conn.executescript(_INIT_SQL)
        conn.commit()

    def _get_conn(self) -> sqlite3.Connection:
        """获取数据库连接（懒加载）"""
        if self._conn is None:
            self._conn = sqlite3.connect(str(self.db_path))
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA foreign_keys=ON")
            self._conn.row_factory = sqlite3.Row
        return self._conn

    def start_run(self, run_date: str) -> int:
        """记录一次运行开始，返回 run_id

        同一天重复执行时，删除旧记录后插入新记录（覆盖语义）。
        关联的 source_logs 由外键 ON DELETE CASCADE 自动清理。
        """
        conn = self._get_conn()
        # 删除同日期旧记录，确保一天只有一条
        conn.execute("DELETE FROM run_logs WHERE run_date = ?", (run_date,))
        cursor = conn.execute(
            "INSERT INTO run_logs (run_date, started_at, status) VALUES (?, ?, 'running')",
            (run_date, datetime.now().isoformat()),
        )
        conn.commit()
        return cursor.lastrowid or 0

    def log_source(
        self,
        run_id: int,
        source_name: str,
        url: str,
        success: bool,
        error_msg: str = "",
        char_count: int = 0,
        news_count: int = 0,
    ) -> None:
        """记录单个资讯源的爬取结果"""
        conn = self._get_conn()
        conn.execute(
            """INSERT INTO source_logs
               (run_id, source_name, url, success, error_msg, char_count, news_count)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (run_id, source_name, url, int(success), error_msg, char_count, news_count),
        )
        conn.commit()

    def finish_run(
        self,
        run_id: int,
        total_sources: int,
        success_count: int,
        news_count: int,
        start_time: float,
        status: str = "success",
    ) -> RunStats:
        """完成一次运行，更新统计信息并返回"""
        duration = time.time() - start_time
        fail_count = total_sources - success_count
        conn = self._get_conn()
        conn.execute(
            """UPDATE run_logs SET
               finished_at=?, total_sources=?, success_count=?,
               fail_count=?, news_count=?, duration_sec=?, status=?
               WHERE id=?""",
            (
                datetime.now().isoformat(),
                total_sources,
                success_count,
                fail_count,
                news_count,
                round(duration, 1),
                status,
                run_id,
            ),
        )
        conn.commit()

        success_rate = success_count / total_sources if total_sources > 0 else 0
        return RunStats(
            run_id=run_id,
            total_sources=total_sources,
            success_count=success_count,
            fail_count=fail_count,
            news_count=news_count,
            duration_sec=round(duration, 1),
            success_rate=success_rate,
        )

    def cleanup_if_needed(self) -> None:
        """检查数据库文件大小，超过上限时删除最旧的记录"""
        if not self.db_path.exists():
            return
        file_size = os.path.getsize(self.db_path)
        if file_size <= self.max_size_bytes:
            return

        conn = self._get_conn()
        # 每次删除最旧的 10% 的运行记录
        total = conn.execute("SELECT COUNT(*) FROM run_logs").fetchone()[0]
        if total <= 1:
            return

        delete_count = max(1, total // 10)
        oldest_ids = conn.execute(
            "SELECT id FROM run_logs ORDER BY id ASC LIMIT ?", (delete_count,)
        ).fetchall()
        ids = [row[0] for row in oldest_ids]
        placeholders = ",".join("?" * len(ids))

        # 级联删除 source_logs（FOREIGN KEY ON DELETE CASCADE）
        conn.execute(f"DELETE FROM run_logs WHERE id IN ({placeholders})", ids)
        conn.commit()

        # 回收空间
        conn.execute("VACUUM")
        new_size = os.path.getsize(self.db_path)
        logger.info(
            "🧹 数据库清理: 删除 %d 条旧记录，文件大小 %.1fMB → %.1fMB",
            delete_count,
            file_size / 1024 / 1024,
            new_size / 1024 / 1024,
        )

    # ========== Web UI 只读查询方法 ==========

    def list_runs(self, limit: int = 20, offset: int = 0) -> list[dict]:
        """分页查询运行记录，按日期倒序"""
        conn = self._get_conn()
        rows = conn.execute(
            """SELECT id, run_date, started_at, finished_at,
                      total_sources, success_count, fail_count,
                      news_count, duration_sec, status
               FROM run_logs ORDER BY run_date DESC, id DESC
               LIMIT ? OFFSET ?""",
            (limit, offset),
        ).fetchall()
        return [dict(row) for row in rows]

    def count_runs(self) -> int:
        """查询运行记录总数（分页用）"""
        conn = self._get_conn()
        row = conn.execute("SELECT COUNT(*) FROM run_logs").fetchone()
        return row[0] if row else 0

    def get_run_by_date(self, run_date: str) -> dict | None:
        """按日期查询最近一次运行记录"""
        conn = self._get_conn()
        row = conn.execute(
            """SELECT id, run_date, started_at, finished_at,
                      total_sources, success_count, fail_count,
                      news_count, duration_sec, status
               FROM run_logs WHERE run_date = ?
               ORDER BY id DESC LIMIT 1""",
            (run_date,),
        ).fetchone()
        return dict(row) if row else None

    def get_source_logs(self, run_id: int) -> list[dict]:
        """查询指定运行的源爬取详情"""
        conn = self._get_conn()
        rows = conn.execute(
            """SELECT id, run_id, source_name, url, success,
                      error_msg, char_count, news_count
               FROM source_logs WHERE run_id = ?
               ORDER BY success DESC, source_name ASC""",
            (run_id,),
        ).fetchall()
        return [dict(row) for row in rows]

    # ========== 统计查询方法（Phase 2） ==========

    def get_stats_overview(self) -> dict:
        """总体统计：总运行次数、平均成功率、平均耗时"""
        conn = self._get_conn()
        row = conn.execute(
            """SELECT
                 COUNT(*) AS total_runs,
                 COALESCE(AVG(
                   CASE WHEN total_sources > 0
                        THEN CAST(success_count AS REAL) / total_sources
                        ELSE 0 END
                 ), 0) AS avg_success_rate,
                 COALESCE(AVG(duration_sec), 0) AS avg_duration_sec,
                 COALESCE(AVG(news_count), 0) AS avg_news_count
               FROM run_logs WHERE status != 'running'"""
        ).fetchone()
        return dict(row) if row else {
            "total_runs": 0, "avg_success_rate": 0,
            "avg_duration_sec": 0, "avg_news_count": 0,
        }

    def get_success_trend(self, days: int = 30) -> list[dict]:
        """近 N 天成功率趋势数据"""
        conn = self._get_conn()
        rows = conn.execute(
            """SELECT
                 run_date,
                 total_sources,
                 success_count,
                 CASE WHEN total_sources > 0
                      THEN ROUND(CAST(success_count AS REAL) / total_sources, 3)
                      ELSE 0 END AS success_rate,
                 news_count,
                 duration_sec
               FROM run_logs
               WHERE status != 'running'
                 AND run_date >= date('now', ?)
               ORDER BY run_date ASC""",
            (f"-{days} days",),
        ).fetchall()
        return [dict(row) for row in rows]

    def get_source_health(self, days: int = 7) -> list[dict]:
        """各源近 N 天健康度"""
        conn = self._get_conn()
        rows = conn.execute(
            """SELECT
                 sl.source_name,
                 COUNT(*) AS total,
                 SUM(sl.success) AS success_count,
                 ROUND(CAST(SUM(sl.success) AS REAL) / COUNT(*), 3) AS success_rate
               FROM source_logs sl
               JOIN run_logs rl ON sl.run_id = rl.id
               WHERE rl.run_date >= date('now', ?)
                 AND sl.source_name NOT LIKE '%[LLM]'
               GROUP BY sl.source_name
               ORDER BY success_rate ASC, sl.source_name ASC""",
            (f"-{days} days",),
        ).fetchall()
        return [dict(row) for row in rows]

    def get_source_recent_status(self, source_name: str, days: int = 7) -> list[int]:
        """获取单个源近 N 天的逐日状态（1=成功, 0=失败）"""
        conn = self._get_conn()
        rows = conn.execute(
            """SELECT sl.success
               FROM source_logs sl
               JOIN run_logs rl ON sl.run_id = rl.id
               WHERE sl.source_name = ?
                 AND rl.run_date >= date('now', ?)
                 AND sl.source_name NOT LIKE '%[LLM]'
               ORDER BY rl.run_date ASC""",
            (source_name, f"-{days} days"),
        ).fetchall()
        return [row[0] for row in rows]

    def close(self) -> None:
        """关闭数据库连接"""
        if self._conn:
            self._conn.close()
            self._conn = None

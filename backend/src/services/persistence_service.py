import json
import os
import sqlite3
import threading
import hashlib
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple


class PersistenceService:
    """Lightweight SQLite persistence for parsed slides and per-page AI analysis.

    Key design:
    - Document is identified by stable `file_hash` (sha256 of file bytes).
    - `doc_id` is the primary key used by frontend to query/save analysis.
    - Per-page analysis is stored by (doc_id, page_id).
    """

    def __init__(self, db_path: str):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._lock = threading.Lock()
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS documents (
                    doc_id TEXT PRIMARY KEY,
                    file_name TEXT,
                    file_type TEXT,
                    file_hash TEXT UNIQUE,
                    slides_json TEXT,
                    global_analysis_json TEXT,
                    created_at TEXT,
                    updated_at TEXT
                )
                """
            )
            try:
                cursor = conn.execute("PRAGMA table_info(documents)")
                columns = [row[1] for row in cursor.fetchall()]
                if 'global_analysis_json' not in columns:
                    print("🔄 检测到旧版数据库，添加 global_analysis_json 字段...")
                    conn.execute("ALTER TABLE documents ADD COLUMN global_analysis_json TEXT")
                    conn.commit()
                    print("✅ 数据库迁移完成")
            except Exception as e:
                print(f"⚠️  数据库迁移检查失败: {e}")
            
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS page_analysis (
                    doc_id TEXT NOT NULL,
                    page_id INTEGER NOT NULL,
                    analysis_json TEXT NOT NULL,
                    created_at TEXT,
                    updated_at TEXT,
                    PRIMARY KEY (doc_id, page_id),
                    FOREIGN KEY (doc_id) REFERENCES documents(doc_id) ON DELETE CASCADE
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_documents_file_hash ON documents(file_hash)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_page_analysis_doc_id ON page_analysis(doc_id)")
            conn.commit()

    @staticmethod
    def sha256_file(path: str) -> str:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
        return h.hexdigest()

    @staticmethod
    def _now() -> str:
        return datetime.now().isoformat()

    def get_document_by_hash(self, file_hash: str) -> Optional[Dict[str, Any]]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT doc_id, file_name, file_type, file_hash, slides_json, global_analysis_json, created_at, updated_at FROM documents WHERE file_hash=?",
                (file_hash,),
            ).fetchone()
            if not row:
                return None
            doc = dict(row)
            doc["slides"] = json.loads(doc["slides_json"]) if doc.get("slides_json") else []
            doc["global_analysis"] = json.loads(doc["global_analysis_json"]) if doc.get("global_analysis_json") else None
            return doc

    def get_document_by_id(self, doc_id: str) -> Optional[Dict[str, Any]]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT doc_id, file_name, file_type, file_hash, slides_json, global_analysis_json, created_at, updated_at FROM documents WHERE doc_id=?",
                (doc_id,),
            ).fetchone()
            if not row:
                return None
            doc = dict(row)
            doc["slides"] = json.loads(doc["slides_json"]) if doc.get("slides_json") else []
            doc["global_analysis"] = json.loads(doc["global_analysis_json"]) if doc.get("global_analysis_json") else None
            return doc

    def upsert_document(
        self,
        *,
        doc_id: str,
        file_name: str,
        file_type: str,
        file_hash: str,
        slides: List[Dict[str, Any]],
        global_analysis: Optional[Dict[str, Any]] = None,
    ) -> None:
        slides_json = json.dumps(slides, ensure_ascii=False)
        global_analysis_json = json.dumps(global_analysis, ensure_ascii=False) if global_analysis else None
        now = self._now()
        with self._lock:
            with self._connect() as conn:
                existing = conn.execute("SELECT doc_id FROM documents WHERE file_hash=?", (file_hash,)).fetchone()
                if existing:
                    if global_analysis_json:
                        conn.execute(
                            """
                            UPDATE documents
                            SET file_name=?, file_type=?, slides_json=?, global_analysis_json=?, updated_at=?
                            WHERE file_hash=?
                            """,
                            (file_name, file_type, slides_json, global_analysis_json, now, file_hash),
                        )
                    else:
                        conn.execute(
                            """
                            UPDATE documents
                            SET file_name=?, file_type=?, slides_json=?, updated_at=?
                            WHERE file_hash=?
                            """,
                            (file_name, file_type, slides_json, now, file_hash),
                        )
                else:
                    conn.execute(
                        """
                        INSERT INTO documents(doc_id, file_name, file_type, file_hash, slides_json, global_analysis_json, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (doc_id, file_name, file_type, file_hash, slides_json, global_analysis_json, now, now),
                    )
                conn.commit()
    
    def update_global_analysis(self, doc_id: str, global_analysis: Dict[str, Any]) -> None:
        """更新文档的全局分析结果"""
        global_analysis_json = json.dumps(global_analysis, ensure_ascii=False)
        now = self._now()
        with self._lock:
            with self._connect() as conn:
                conn.execute(
                    """
                    UPDATE documents
                    SET global_analysis_json=?, updated_at=?
                    WHERE doc_id=?
                    """,
                    (global_analysis_json, now, doc_id),
                )
                conn.commit()

    def get_doc_id_by_hash(self, file_hash: str) -> Optional[str]:
        with self._connect() as conn:
            row = conn.execute("SELECT doc_id FROM documents WHERE file_hash=?", (file_hash,)).fetchone()
            return row["doc_id"] if row else None

    def get_page_analysis(self, doc_id: str, page_id: int) -> Optional[Dict[str, Any]]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT analysis_json, created_at, updated_at FROM page_analysis WHERE doc_id=? AND page_id=?",
                (doc_id, page_id),
            ).fetchone()
            if not row:
                return None
            data = json.loads(row["analysis_json"])
            data["_meta"] = {"created_at": row["created_at"], "updated_at": row["updated_at"]}
            return data

    def list_page_analyses(self, doc_id: str) -> Dict[int, Dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT page_id, analysis_json, created_at, updated_at FROM page_analysis WHERE doc_id=?",
                (doc_id,),
            ).fetchall()
            result: Dict[int, Dict[str, Any]] = {}
            for row in rows:
                data = json.loads(row["analysis_json"])
                data["_meta"] = {"created_at": row["created_at"], "updated_at": row["updated_at"]}
                result[int(row["page_id"])] = data
            return result

    def upsert_page_analysis(self, doc_id: str, page_id: int, analysis: Dict[str, Any]) -> None:
        now = self._now()
        analysis_json = json.dumps(analysis, ensure_ascii=False)
        with self._lock:
            with self._connect() as conn:
                existing = conn.execute(
                    "SELECT 1 FROM page_analysis WHERE doc_id=? AND page_id=?",
                    (doc_id, page_id),
                ).fetchone()
                if existing:
                    conn.execute(
                        """
                        UPDATE page_analysis
                        SET analysis_json=?, updated_at=?
                        WHERE doc_id=? AND page_id=?
                        """,
                        (analysis_json, now, doc_id, page_id),
                    )
                else:
                    conn.execute(
                        """
                        INSERT INTO page_analysis(doc_id, page_id, analysis_json, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        (doc_id, page_id, analysis_json, now, now),
                    )
                conn.commit()


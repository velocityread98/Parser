#!/usr/bin/env python3
"""
Ingest enhanced hierarchical JSON into Postgres with pgvector for RAG.
- Creates tables if not exist (idempotent)
- Walks the hierarchy and inserts nodes with parent/child relationships
- Computes embeddings for each node's summary or text using OpenAI (optional)

Env vars:
- DATABASE_URL: postgres://user:pass@host:port/dbname
- OPENAI_API_KEY: for embeddings (optional; if missing, stores NULL)
- JSON_FILE_PATH: optional explicit path to JSON; otherwise auto-detect single file
- EMBEDDING_MODEL: optional, default 'text-embedding-3-small'
- EMBEDDING_DIM: optional, default 1536 for text-embedding-3-small
"""

import json
import os
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

from dotenv import load_dotenv
load_dotenv()

import psycopg
from psycopg.rows import dict_row

try:
    from openai import OpenAI
    _openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY")) if os.getenv("OPENAI_API_KEY") else None
except Exception:
    _openai_client = None

DEFAULT_EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
DEFAULT_EMBEDDING_DIM = int(os.getenv("EMBEDDING_DIM", "1536"))


def find_single_json_file(search_dir: str) -> Optional[str]:
    try:
        if not os.path.isdir(search_dir):
            return None
        candidates = [
            os.path.join(search_dir, f)
            for f in os.listdir(search_dir)
            if f.lower().endswith(".json") and os.path.isfile(os.path.join(search_dir, f))
        ]
        return candidates[0] if len(candidates) == 1 else None
    except Exception:
        return None


def get_json_path() -> str:
    p = os.getenv("JSON_FILE_PATH")
    if p and os.path.isfile(p):
        return p
    p = find_single_json_file("recognition_json")
    if p:
        return p
    p = find_single_json_file(os.getcwd())
    if p:
        return p
    raise SystemExit("Could not determine JSON file automatically. Set JSON_FILE_PATH or keep exactly one .json in recognition_json/ or CWD.")


def connect_db() -> psycopg.Connection:
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise SystemExit("DATABASE_URL env var is required (e.g. postgres://user:pass@host:5432/db)")
    return psycopg.connect(dsn, row_factory=dict_row)


def ensure_schema(conn: psycopg.Connection):
    with conn.cursor() as cur:
        # Enable pgvector extension
        cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
        # Nodes table
        cur.execute(
            f"""
            CREATE TABLE IF NOT EXISTS doc_nodes (
                id TEXT PRIMARY KEY,
                parent_id TEXT REFERENCES doc_nodes(id) ON DELETE CASCADE,
                label TEXT NOT NULL,
                text TEXT NOT NULL,
                level INT NOT NULL,
                page INT NOT NULL,
                reading_order INT NOT NULL,
                section_number TEXT,
                summary TEXT,
                bbox JSONB,
                merged_elements JSONB,
                is_merged BOOLEAN DEFAULT FALSE,
                embedding VECTOR({DEFAULT_EMBEDDING_DIM})
            );
            """
        )
        # Children index for faster tree queries
        cur.execute("CREATE INDEX IF NOT EXISTS idx_doc_nodes_parent ON doc_nodes(parent_id)")
        # Vector index (use IVFFlat, needs ANALYZE and lists tuning)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_doc_nodes_embedding ON doc_nodes USING ivfflat (embedding) WITH (lists = 100)")
        conn.commit()


def openai_embed(text: Optional[str]) -> Optional[List[float]]:
    if not _openai_client:
        return None
    t = (text or "").strip()
    if not t:
        return None
    # OpenAI's embeddings API in >=1.x client
    try:
        resp = _openai_client.embeddings.create(model=DEFAULT_EMBEDDING_MODEL, input=t)
        vec = resp.data[0].embedding if resp and resp.data else None
        return vec
    except Exception as e:
        print(f"Embedding error: {e}")
        return None


def flatten_hierarchy(node: Dict[str, Any], parent_id: Optional[str] = None) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    def _recurse(n: Dict[str, Any], pid: Optional[str]):
        rows.append({
            "id": n.get("id"),
            "parent_id": pid,
            "label": n.get("label"),
            "text": n.get("text", ""),
            "level": n.get("level", -1),
            "page": n.get("page", 0),
            "reading_order": n.get("reading_order", 0),
            "section_number": n.get("section_number"),
            "summary": n.get("summary"),
            "bbox": n.get("bbox"),
            "merged_elements": n.get("merged_elements"),
            "is_merged": n.get("is_merged", False)
        })
        # structural children
        for c in n.get("children", []) or []:
            _recurse(c, n.get("id"))
        # content elements are also nodes in the same table with parent_id pointing to the structural node
        for c in n.get("content_elements", []) or []:
            _recurse(c, n.get("id"))
    _recurse(node, parent_id)
    return rows


def upsert_nodes(conn: psycopg.Connection, rows: List[Dict[str, Any]], do_embed: bool):
    with conn.cursor() as cur:
        for r in rows:
            emb = None
            if do_embed:
                # Prefer summary for semantic signal; fallback to text
                emb = openai_embed(r.get("summary") or r.get("text"))
            cur.execute(
                """
                INSERT INTO doc_nodes (
                    id, parent_id, label, text, level, page, reading_order,
                    section_number, summary, bbox, merged_elements, is_merged, embedding
                ) VALUES (
                    %(id)s, %(parent_id)s, %(label)s, %(text)s, %(level)s, %(page)s, %(reading_order)s,
                    %(section_number)s, %(summary)s, %(bbox)s, %(merged_elements)s, %(is_merged)s, %(embedding)s
                )
                ON CONFLICT (id) DO UPDATE SET
                    parent_id = EXCLUDED.parent_id,
                    label = EXCLUDED.label,
                    text = EXCLUDED.text,
                    level = EXCLUDED.level,
                    page = EXCLUDED.page,
                    reading_order = EXCLUDED.reading_order,
                    section_number = EXCLUDED.section_number,
                    summary = EXCLUDED.summary,
                    bbox = EXCLUDED.bbox,
                    merged_elements = EXCLUDED.merged_elements,
                    is_merged = EXCLUDED.is_merged,
                    embedding = COALESCE(EXCLUDED.embedding, doc_nodes.embedding)
                """,
                {
                    **r,
                    "bbox": json.dumps(r.get("bbox")) if r.get("bbox") is not None else None,
                    "merged_elements": json.dumps(r.get("merged_elements")) if r.get("merged_elements") is not None else None,
                    "embedding": emb
                }
            )
        conn.commit()


def main():
    json_path = get_json_path()
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    # The enhanced JSON may already be a root dict; if it's a list, take first
    root = data if isinstance(data, dict) else (data[0] if data else {})

    rows = flatten_hierarchy(root)
    print(f"Prepared {len(rows)} nodes for upsert.")

    do_embed = bool(_openai_client)
    if not do_embed:
        print("OPENAI_API_KEY missing; embeddings will be NULL.")

    with connect_db() as conn:
        ensure_schema(conn)
        upsert_nodes(conn, rows, do_embed)
    print("Ingestion complete.")


if __name__ == "__main__":
    main()

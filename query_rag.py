#!/usr/bin/env python3
"""
Query pgvector for top-k relevant nodes and return hierarchical context for RAG.

Env vars:
- DATABASE_URL: postgres://user:pass@host:port/dbname
- OPENAI_API_KEY: for query embedding
- EMBEDDING_MODEL: optional, default 'text-embedding-3-small'

Usage (example):
  python3 query_rag.py "How does multi-head attention work?"
"""

import os
import sys
from typing import List, Dict

from dotenv import load_dotenv
load_dotenv()

import psycopg
from psycopg.rows import dict_row

from openai import OpenAI

DEFAULT_EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")


def embed_query(q: str) -> List[float]:
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    resp = client.embeddings.create(model=DEFAULT_EMBEDDING_MODEL, input=q)
    return resp.data[0].embedding


def connect_db() -> psycopg.Connection:
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise SystemExit("DATABASE_URL env var is required")
    return psycopg.connect(dsn, row_factory=dict_row)


def query_topk(conn: psycopg.Connection, qvec: List[float], k: int = 5) -> List[Dict]:
    with conn.cursor() as cur:
        # Get top-k by cosine distance; '<->' uses distance by default
        cur.execute(
            """
            SELECT id, parent_id, label, text, summary, level, page, reading_order,
                   section_number, is_merged,
                   (embedding <-> %(q)s) AS distance
            FROM doc_nodes
            WHERE embedding IS NOT NULL
            ORDER BY embedding <-> %(q)s
            LIMIT %(k)s
            """,
            {"q": qvec, "k": k}
        )
        return list(cur.fetchall())


def get_ancestors(conn: psycopg.Connection, node_id: str) -> List[Dict]:
    with conn.cursor() as cur:
        cur.execute(
            """
            WITH RECURSIVE ancestors AS (
                SELECT id, parent_id, label, text, summary, level
                FROM doc_nodes WHERE id = %(id)s
                UNION ALL
                SELECT d.id, d.parent_id, d.label, d.text, d.summary, d.level
                FROM doc_nodes d
                JOIN ancestors a ON d.id = a.parent_id
            )
            SELECT * FROM ancestors
            ORDER BY level; -- root to leaf
            """,
            {"id": node_id}
        )
        return list(cur.fetchall())


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 query_rag.py \"your question\"")
        sys.exit(1)
    question = sys.argv[1]
    qvec = embed_query(question)
    with connect_db() as conn:
        hits = query_topk(conn, qvec, k=5)
        for i, h in enumerate(hits, 1):
            print(f"\n[{i}] {h['label']} id={h['id']} page={h['page']} dist={h['distance']:.4f}")
            print(f"Summary: {h['summary'][:200]+'...' if h['summary'] and len(h['summary'])>200 else h['summary']}")
            print(f"Text: {h['text'][:200]+'...' if len(h['text'])>200 else h['text']}")
            # Fetch ancestor path for context windowing
            anc = get_ancestors(conn, h['id'])
            if anc:
                path = " / ".join([f"{a['label']}:{(a['text'] or '')[:40]}" for a in anc])
                print(f"Path: {path}")


if __name__ == "__main__":
    main()

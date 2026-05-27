"""Disease database query tools."""

import logging
from typing import Any

import pymysql

from ..config import config as cfg
from . import register

logger = logging.getLogger(__name__)


def _get_connection():
    """Create a MySQL connection with configured credentials."""
    try:
        return pymysql.connect(
            host=cfg.DB_HOST,
            port=cfg.DB_PORT,
            user=cfg.DB_USER,
            password=cfg.DB_PASSWORD,
            database=cfg.DB_NAME,
            charset="utf8mb4",
            cursorclass=pymysql.cursors.DictCursor,
        )
    except Exception as e:
        logger.warning(f"Database connection failed: {e}")
        return None


def _safe_query(sql: str, params: tuple = ()) -> dict[str, Any]:
    """Execute a query safely, returning results or error."""
    conn = _get_connection()
    if conn is None:
        return {
            "error": "Database unavailable. Ensure MySQL is running and .env is configured.",
            "hint": "Start MySQL and import schema.sql from the disease database project.",
        }
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()
        return {"results": rows, "count": len(rows)}
    except Exception as e:
        return {"error": str(e), "sql": sql}
    finally:
        conn.close()


@register(
    name="query_disease",
    description="Query disease information from the database. Search by name or ICD code. Returns disease details, associated genes, and sample counts.",
    input_schema={
        "type": "object",
        "properties": {
            "keyword": {
                "type": "string",
                "description": "Disease name or keyword to search (fuzzy match)",
            },
        },
        "required": ["keyword"],
    },
)
def query_disease(keyword: str) -> dict:
    """Query disease by name or ICD code."""
    sql = """
        SELECT d.disease_id, d.name, d.icd_code, d.category, d.description,
               COUNT(DISTINCT dg.gene_id) AS gene_count,
               COUNT(DISTINCT s.sample_id) AS sample_count
        FROM disease d
        LEFT JOIN disease_gene dg ON d.disease_id = dg.disease_id
        LEFT JOIN sample s ON d.disease_id = s.disease_id
        WHERE d.name LIKE %s OR d.icd_code LIKE %s OR d.category LIKE %s
        GROUP BY d.disease_id
        LIMIT 10
    """
    kw = f"%{keyword}%"
    return _safe_query(sql, (kw, kw, kw))


@register(
    name="query_gene",
    description="Query gene information. Search by gene symbol or Ensembl ID. Returns gene details, associated diseases, and expression summary.",
    input_schema={
        "type": "object",
        "properties": {
            "keyword": {
                "type": "string",
                "description": "Gene symbol (e.g., TP53) or Ensembl ID to search",
            },
        },
        "required": ["keyword"],
    },
)
def query_gene(keyword: str) -> dict:
    """Query gene by symbol or Ensembl ID."""
    sql = """
        SELECT g.gene_id, g.gene_symbol, g.ensembl_id, g.chromosome,
               g.description,
               GROUP_CONCAT(DISTINCT d.name SEPARATOR ', ') AS diseases,
               ROUND(AVG(CASE WHEN s.group_type='case' THEN e.fpkm_value END), 2) AS avg_fpkm_case,
               ROUND(AVG(CASE WHEN s.group_type='control' THEN e.fpkm_value END), 2) AS avg_fpkm_ctrl
        FROM gene g
        LEFT JOIN disease_gene dg ON g.gene_id = dg.gene_id
        LEFT JOIN disease d ON dg.disease_id = d.disease_id
        LEFT JOIN expression e ON g.gene_id = e.gene_id
        LEFT JOIN sample s ON e.sample_id = s.sample_id
        WHERE g.gene_symbol LIKE %s OR g.ensembl_id LIKE %s
        GROUP BY g.gene_id
        LIMIT 10
    """
    kw = f"%{keyword}%"
    return _safe_query(sql, (kw, kw))

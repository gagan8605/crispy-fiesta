import json
import ssl
import time
from datetime import datetime
from typing import Any, Dict, List, Optional
import pymysql
from pymysql.cursors import DictCursor
from src.config import Config


class DatabaseService:
    def __init__(self):
        self.host = Config.DB_HOST
        self.port = Config.DB_PORT
        self.user = Config.DB_USER
        self.password = Config.DB_PASSWORD
        self.db_name = Config.DB_NAME
        self.timeout = Config.DB_CONNECT_TIMEOUT
        self.use_ssl = Config.DB_USE_SSL

    def _get_connection(self):
        """Establishes connection to MySQL with cloud SSL support."""
        ssl_config = None
        if self.use_ssl:
            ssl_ctx = ssl.create_default_context()
            # For cloud databases (e.g. PlanetScale, RDS, Aiven)
            ssl_ctx.check_hostname = False
            ssl_ctx.verify_mode = ssl.CERT_NONE
            ssl_config = ssl_ctx

        return pymysql.connect(
            host=self.host,
            port=self.port,
            user=self.user,
            password=self.password,
            database=self.db_name,
            connect_timeout=self.timeout,
            ssl=ssl_config,
            cursorclass=DictCursor,
            autocommit=True,
        )

    def run_health_and_ops_check(self) -> Dict[str, Any]:
        """
        Executes a full backend ops inspection:
        1. Connectivity & Latency check
        2. Server metadata (version, uptime, current user)
        3. Initializes / verifies 'ops_audit_logs' table
        4. Writes an execution audit record
        5. Retrieves recent audit metrics
        """
        start_time = time.time()
        result: Dict[str, Any] = {
            "status": "FAILED",
            "latency_ms": 0.0,
            "db_version": "Unknown",
            "connected_user": self.user,
            "database_name": self.db_name,
            "table_count": 0,
            "audit_logged": False,
            "recent_runs": [],
            "error": None,
        }

        if Config.DRY_RUN:
            result.update({
                "status": "SUCCESS (DRY_RUN)",
                "latency_ms": 1.25,
                "db_version": "MySQL 8.0-Simulated",
                "table_count": 5,
                "audit_logged": True,
                "recent_runs": [
                    {"run_id": "dry-run-001", "status": "SUCCESS", "environment": Config.APP_ENV, "created_at": datetime.utcnow().isoformat()}
                ]
            })
            return result

        try:
            conn_start = time.time()
            connection = self._get_connection()
            result["latency_ms"] = round((time.time() - conn_start) * 1000, 2)

            with connection:
                with connection.cursor() as cursor:
                    # 1. Fetch DB version
                    cursor.execute("SELECT VERSION() AS db_version, DATABASE() AS current_db, CURRENT_USER() AS curr_user;")
                    info_row = cursor.fetchone()
                    if info_row:
                        result["db_version"] = info_row.get("db_version", "Unknown")
                        result["database_name"] = info_row.get("current_db", self.db_name)
                        result["connected_user"] = info_row.get("curr_user", self.user)

                    # 2. Ensure audit table exists
                    create_table_sql = """
                    CREATE TABLE IF NOT EXISTS ops_audit_logs (
                        id BIGINT AUTO_INCREMENT PRIMARY KEY,
                        run_id VARCHAR(100) NOT NULL,
                        environment VARCHAR(50) NOT NULL,
                        executed_by VARCHAR(100) NOT NULL,
                        workflow_name VARCHAR(150) NOT NULL,
                        status VARCHAR(30) NOT NULL,
                        latency_ms FLOAT NOT NULL,
                        notes TEXT,
                        metrics_json JSON,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
                    """
                    cursor.execute(create_table_sql)

                    # 3. Log current run to audit table
                    insert_audit_sql = """
                    INSERT INTO ops_audit_logs 
                    (run_id, environment, executed_by, workflow_name, status, latency_ms, notes, metrics_json)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s);
                    """
                    metrics_payload = json.dumps({
                        "event_name": Config.GITHUB_EVENT_NAME,
                        "timestamp": datetime.utcnow().isoformat(),
                        "db_version": result["db_version"],
                    })
                    cursor.execute(
                        insert_audit_sql,
                        (
                            Config.GITHUB_RUN_ID,
                            Config.APP_ENV,
                            Config.GITHUB_ACTOR,
                            Config.GITHUB_WORKFLOW,
                            "RUNNING",
                            result["latency_ms"],
                            f"Automated health check run from {Config.GITHUB_WORKFLOW}",
                            metrics_payload,
                        )
                    )
                    result["audit_logged"] = True

                    # 4. Count tables in current schema
                    cursor.execute("""
                        SELECT COUNT(*) AS total_tables 
                        FROM information_schema.tables 
                        WHERE table_schema = %s;
                    """, (result["database_name"],))
                    count_row = cursor.fetchone()
                    if count_row:
                        result["table_count"] = count_row.get("total_tables", 0)

                    # 5. Fetch last 5 runs
                    cursor.execute("""
                        SELECT run_id, environment, executed_by, status, latency_ms, created_at 
                        FROM ops_audit_logs 
                        ORDER BY id DESC 
                        LIMIT 5;
                    """)
                    runs = cursor.fetchall()
                    formatted_runs = []
                    for r in runs:
                        formatted_runs.append({
                            "run_id": str(r.get("run_id", "")),
                            "environment": str(r.get("environment", "")),
                            "executed_by": str(r.get("executed_by", "")),
                            "status": str(r.get("status", "")),
                            "latency_ms": r.get("latency_ms", 0.0),
                            "created_at": str(r.get("created_at", "")),
                        })
                    result["recent_runs"] = formatted_runs

            result["status"] = "SUCCESS"
            return result

        except Exception as exc:
            result["status"] = "FAILED"
            result["error"] = str(exc)
            return result

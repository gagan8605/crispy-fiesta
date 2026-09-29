import unittest
import os
from unittest.mock import MagicMock, patch
from src.config import Config, str_to_bool
from src.db_service import DatabaseService
from src.email_service import EmailService


class TestBackendOps(unittest.TestCase):
    def test_str_to_bool(self):
        self.assertTrue(str_to_bool("true"))
        self.assertTrue(str_to_bool("1"))
        self.assertTrue(str_to_bool("YES"))
        self.assertFalse(str_to_bool("false"))
        self.assertFalse(str_to_bool("0"))
        self.assertFalse(str_to_bool(None, default=False))

    def test_dry_run_database_service(self):
        with patch.object(Config, "DRY_RUN", True):
            service = DatabaseService()
            result = service.run_health_and_ops_check()
            self.assertEqual(result["status"], "SUCCESS (DRY_RUN)")
            self.assertTrue(result["audit_logged"])
            self.assertGreater(result["latency_ms"], 0)

    def test_email_template_generation(self):
        email_svc = EmailService()
        summary = {
            "overall_status": "SUCCESS",
            "workflow": "Test Workflow",
            "run_id": "test-123",
            "actor": "tester",
            "event_name": "workflow_dispatch",
            "duration_sec": 1.45,
            "timestamp": "2026-09-29 20:30:00 UTC",
        }
        db_result = {
            "status": "SUCCESS",
            "latency_ms": 12.5,
            "db_version": "8.0.35-cloud",
            "connected_user": "admin",
            "database_name": "ops_test",
            "table_count": 8,
            "audit_logged": True,
            "recent_runs": [
                {
                    "run_id": "run-001",
                    "environment": "staging",
                    "executed_by": "tester",
                    "status": "SUCCESS",
                    "latency_ms": 11.2,
                    "created_at": "2026-09-29 20:20:00",
                }
            ],
        }

        html = email_svc._generate_html_report(summary, db_result)
        plain = email_svc._generate_plain_text_report(summary, db_result)

        self.assertIn("Cloud Backend Ops Report", html)
        self.assertIn("SUCCESS", html)
        self.assertIn("8.0.35-cloud", html)
        self.assertIn("Test Workflow", plain)
        self.assertIn("12.5 ms", plain)


if __name__ == "__main__":
    unittest.main()

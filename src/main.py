import json
import os
import sys
import time
from datetime import datetime
from tabulate import tabulate
from src.config import Config
from src.db_service import DatabaseService
from src.email_service import EmailService


def print_banner():
    banner = """
======================================================================
  ____ _                 _  ___             ____  _     
 / ___| | ___  _   _  __| |/ _ \ _ __  ___ |  _ \| |__  
| |   | |/ _ \| | | |/ _` | | | | '_ \/ __|| | | | '_ \ 
| |___| | (_) | |_| | (_| | |_| | |_) \__ \| |_| | |_) |
 \____|_|\___/ \__,_|\__,_|\___/| .__/|___/|____/|_.__/ 
                                |_|                     
  GitHub Actions CI/CD Backend Operations & Health Suite
======================================================================
"""
    print(banner)


def write_github_step_summary(summary: dict, db_result: dict, email_result: dict):
    """Writes rich Markdown summary to GitHub Actions Step Summary ($GITHUB_STEP_SUMMARY)."""
    step_summary_path = Config.GITHUB_STEP_SUMMARY
    if not step_summary_path:
        return

    try:
        overall_status = summary.get("overall_status", "UNKNOWN")
        status_emoji = "✅" if "SUCCESS" in overall_status else "❌"

        md_content = f"""
## {status_emoji} Backend Ops Execution Report: {overall_status}

### 🚀 Execution Summary
| Metric | Details |
| :--- | :--- |
| **Application** | `{Config.APP_NAME}` |
| **Environment** | `{Config.APP_ENV.upper()}` |
| **Workflow** | `{summary.get('workflow')}` |
| **Run ID** | `{summary.get('run_id')}` |
| **Trigger Event** | `{summary.get('event_name')}` |
| **Triggered By** | `{summary.get('actor')}` |
| **Duration** | `{summary.get('duration_sec')}s` |
| **Timestamp (UTC)** | `{summary.get('timestamp')}` |

### 🗄️ Cloud MySQL Health Status
| Attribute | Value |
| :--- | :--- |
| **Database Host** | `{Config.DB_HOST}` |
| **Database Name** | `{db_result.get('database_name')}` |
| **Server Version** | `{db_result.get('db_version')}` |
| **Connected User** | `{db_result.get('connected_user')}` |
| **Round-Trip Latency** | `{db_result.get('latency_ms')} ms` |
| **Schema Tables** | `{db_result.get('table_count')}` |
| **Audit Record Stored** | `{'Yes' if db_result.get('audit_logged') else 'No'}` |

"""
        if db_result.get("error"):
            md_content += f"""
> [!CAUTION]
> **Database Error Details:**
> ```
> {db_result.get('error')}
> ```
"""

        recent_runs = db_result.get("recent_runs", [])
        if recent_runs:
            md_content += "\n### 📋 Recent Ops Runs (`ops_audit_logs`)\n"
            md_content += "| Run ID | Environment | Actor | Status | Latency | Timestamp |\n"
            md_content += "| :--- | :--- | :--- | :--- | :--- | :--- |\n"
            for r in recent_runs:
                md_content += f"| `{r.get('run_id')}` | {r.get('environment')} | {r.get('executed_by')} | {r.get('status')} | {r.get('latency_ms')} ms | {r.get('created_at')} |\n"

        email_status = "✅ Sent" if email_result.get("sent") else f"⚠️ Not Sent ({email_result.get('error') or 'Disabled'})"
        md_content += f"\n### 📧 Notification Service\n- **Status:** {email_status}\n- **Recipients:** `{Config.EMAIL_TO or 'None'}`\n"

        with open(step_summary_path, "a", encoding="utf-8") as f:
            f.write(md_content)

        print("[INFO] GitHub Actions Step Summary successfully written.")
    except Exception as exc:
        print(f"[WARN] Unable to write GitHub Actions Step Summary: {exc}")


def main() -> int:
    print_banner()
    start_time = time.time()

    print("[STEP 1/4] Loading & Validating Environment Configurations...")
    config_summary = Config.get_masked_summary()
    table_data = [[k, v] for k, v in config_summary.items()]
    print(tabulate(table_data, headers=["Config Key", "Value"], tablefmt="grid"))

    print("\n[STEP 2/4] Executing Cloud MySQL Database Health & Audit Ops...")
    db_service = DatabaseService()
    db_result = db_service.run_health_and_ops_check()

    if "SUCCESS" in db_result["status"]:
        print(f"[SUCCESS] Connected to Cloud MySQL ({db_result.get('db_version')}) in {db_result.get('latency_ms')} ms.")
        print(f"[INFO] Active Tables in Schema: {db_result.get('table_count')}")
        if db_result.get("audit_logged"):
            print("[INFO] Successfully appended run record to table 'ops_audit_logs'.")
    else:
        print(f"[ERROR] Database Operation Failed: {db_result.get('error')}")

    duration_sec = round(time.time() - start_time, 2)
    overall_status = "SUCCESS" if "SUCCESS" in db_result["status"] else "FAILED"

    summary = {
        "overall_status": overall_status,
        "workflow": Config.GITHUB_WORKFLOW,
        "run_id": Config.GITHUB_RUN_ID,
        "actor": Config.GITHUB_ACTOR,
        "event_name": Config.GITHUB_EVENT_NAME,
        "duration_sec": duration_sec,
        "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
    }

    print("\n[STEP 3/4] Dispatching Execution Report via SMTP Email Service...")
    email_service = EmailService()
    email_result = email_service.send_report(summary, db_result)

    print("\n[STEP 4/4] Finalizing GitHub Actions Output & Summary...")
    write_github_step_summary(summary, db_result, email_result)

    print("\n" + "=" * 70)
    print(f"  FINAL OPS STATUS : {overall_status} (Completed in {duration_sec}s)")
    print("=" * 70 + "\n")

    # If DB health failed and not dry run, exit with non-zero
    if overall_status != "SUCCESS" and not Config.DRY_RUN:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

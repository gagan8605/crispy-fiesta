import smtplib
import ssl
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Dict, List
from src.config import Config


class EmailService:
    def __init__(self):
        self.host = Config.SMTP_HOST
        self.port = Config.SMTP_PORT
        self.user = Config.SMTP_USER
        self.password = Config.SMTP_PASSWORD
        self.use_tls = Config.SMTP_USE_TLS
        self.use_ssl = Config.SMTP_USE_SSL
        self.email_from = Config.EMAIL_FROM
        self.email_to = Config.EMAIL_TO

    def is_configured(self) -> bool:
        """Checks if SMTP credentials are provided."""
        return bool(self.host and self.user and self.email_to)

    def _generate_html_report(self, summary: Dict[str, Any], db_result: Dict[str, Any]) -> str:
        """Generates modern responsive HTML email report."""
        overall_status = summary.get("overall_status", "UNKNOWN")
        badge_color = "#10b981" if "SUCCESS" in overall_status else "#ef4444"
        badge_bg = "#d1fae5" if "SUCCESS" in overall_status else "#fee2e2"

        recent_rows_html = ""
        recent_runs: List[Dict[str, Any]] = db_result.get("recent_runs", [])
        if recent_runs:
            for run in recent_runs:
                recent_rows_html += f"""
                <tr style="border-bottom: 1px solid #e2e8f0; font-size: 13px;">
                    <td style="padding: 10px 12px; font-family: monospace; color: #334155;">{run.get('run_id')}</td>
                    <td style="padding: 10px 12px; color: #475569;">{run.get('environment')}</td>
                    <td style="padding: 10px 12px; color: #475569;">{run.get('executed_by')}</td>
                    <td style="padding: 10px 12px; font-weight: 600; color: {'#16a34a' if run.get('status') == 'SUCCESS' else '#dc2626'};">{run.get('status')}</td>
                    <td style="padding: 10px 12px; color: #64748b;">{run.get('latency_ms')} ms</td>
                    <td style="padding: 10px 12px; color: #64748b; font-size: 12px;">{run.get('created_at')}</td>
                </tr>
                """
        else:
            recent_rows_html = """
            <tr>
                <td colspan="6" style="padding: 16px; text-align: center; color: #94a3b8; font-size: 13px;">
                    No audit history records available.
                </td>
            </tr>
            """

        error_banner = ""
        if db_result.get("error"):
            error_banner = f"""
            <div style="background-color: #fef2f2; border: 1px solid #f87171; border-radius: 8px; padding: 14px; margin-bottom: 24px;">
                <h4 style="margin: 0 0 6px 0; color: #991b1b; font-size: 14px;">Error Details</h4>
                <pre style="margin: 0; font-size: 12px; color: #b91c1c; white-space: pre-wrap; word-break: break-word;">{db_result.get('error')}</pre>
            </div>
            """

        html_template = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>DevOps Execution Report</title>
        </head>
        <body style="margin: 0; padding: 0; background-color: #f1f5f9; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;">
            <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background-color: #f1f5f9; padding: 30px 15px;">
                <tr>
                    <td align="center">
                        <table role="presentation" width="650" cellspacing="0" cellpadding="0" style="background-color: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);">
                            <!-- Header -->
                            <tr>
                                <td style="background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%); padding: 28px 32px; color: #ffffff;">
                                    <div style="display: flex; justify-content: space-between; align-items: center;">
                                        <div>
                                            <p style="margin: 0; font-size: 12px; letter-spacing: 1px; text-transform: uppercase; color: #94a3b8; font-weight: 700;">GitHub Actions CI/CD</p>
                                            <h1 style="margin: 6px 0 0 0; font-size: 22px; font-weight: 700; color: #ffffff;">Cloud Backend Ops Report</h1>
                                        </div>
                                    </div>
                                    <div style="margin-top: 14px;">
                                        <span style="display: inline-block; background-color: {badge_bg}; color: {badge_color}; padding: 4px 12px; border-radius: 9999px; font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px;">
                                            {overall_status}
                                        </span>
                                        <span style="display: inline-block; margin-left: 8px; color: #cbd5e1; font-size: 13px;">
                                            Environment: <strong>{Config.APP_ENV.upper()}</strong>
                                        </span>
                                    </div>
                                </td>
                            </tr>

                            <!-- Content -->
                            <tr>
                                <td style="padding: 32px;">
                                    {error_banner}

                                    <!-- Summary Grid -->
                                    <h3 style="margin: 0 0 14px 0; font-size: 16px; color: #0f172a; font-weight: 600; border-bottom: 2px solid #f1f5f9; padding-bottom: 8px;">
                                        Execution Summary
                                    </h3>
                                    <table width="100%" cellspacing="0" cellpadding="0" style="margin-bottom: 24px; font-size: 14px;">
                                        <tr>
                                            <td style="padding: 8px 0; color: #64748b; width: 40%;">Workflow Name:</td>
                                            <td style="padding: 8px 0; color: #0f172a; font-weight: 600;">{summary.get('workflow')}</td>
                                        </tr>
                                        <tr>
                                            <td style="padding: 8px 0; color: #64748b;">Run ID / Trigger:</td>
                                            <td style="padding: 8px 0; color: #0f172a; font-family: monospace;">{summary.get('run_id')} ({summary.get('event_name')})</td>
                                        </tr>
                                        <tr>
                                            <td style="padding: 8px 0; color: #64748b;">Triggered By:</td>
                                            <td style="padding: 8px 0; color: #0f172a;">{summary.get('actor')}</td>
                                        </tr>
                                        <tr>
                                            <td style="padding: 8px 0; color: #64748b;">Execution Duration:</td>
                                            <td style="padding: 8px 0; color: #0f172a;">{summary.get('duration_sec')}s</td>
                                        </tr>
                                        <tr>
                                            <td style="padding: 8px 0; color: #64748b;">Timestamp (UTC):</td>
                                            <td style="padding: 8px 0; color: #0f172a;">{summary.get('timestamp')}</td>
                                        </tr>
                                    </table>

                                    <!-- Database Health Section -->
                                    <h3 style="margin: 24px 0 14px 0; font-size: 16px; color: #0f172a; font-weight: 600; border-bottom: 2px solid #f1f5f9; padding-bottom: 8px;">
                                        Cloud MySQL Health Metrics
                                    </h3>
                                    <table width="100%" cellspacing="0" cellpadding="0" style="background-color: #f8fafc; border-radius: 8px; border: 1px solid #e2e8f0; padding: 14px; margin-bottom: 24px; font-size: 13px;">
                                        <tr>
                                            <td style="padding: 6px 12px; color: #64748b;">Database Host:</td>
                                            <td style="padding: 6px 12px; font-weight: 600; color: #1e293b;">{Config.DB_HOST}</td>
                                            <td style="padding: 6px 12px; color: #64748b;">Database Name:</td>
                                            <td style="padding: 6px 12px; font-weight: 600; color: #1e293b;">{db_result.get('database_name')}</td>
                                        </tr>
                                        <tr>
                                            <td style="padding: 6px 12px; color: #64748b;">MySQL Version:</td>
                                            <td style="padding: 6px 12px; font-weight: 600; color: #1e293b;">{db_result.get('db_version')}</td>
                                            <td style="padding: 6px 12px; color: #64748b;">Round-Trip Latency:</td>
                                            <td style="padding: 6px 12px; font-weight: 600; color: #0284c7;">{db_result.get('latency_ms')} ms</td>
                                        </tr>
                                        <tr>
                                            <td style="padding: 6px 12px; color: #64748b;">Connected User:</td>
                                            <td style="padding: 6px 12px; font-weight: 600; color: #1e293b;">{db_result.get('connected_user')}</td>
                                            <td style="padding: 6px 12px; color: #64748b;">Tables in Schema:</td>
                                            <td style="padding: 6px 12px; font-weight: 600; color: #1e293b;">{db_result.get('table_count')}</td>
                                        </tr>
                                    </table>

                                    <!-- Audit History -->
                                    <h3 style="margin: 24px 0 12px 0; font-size: 16px; color: #0f172a; font-weight: 600;">
                                        Recent Operations History (ops_audit_logs)
                                    </h3>
                                    <table width="100%" cellspacing="0" cellpadding="0" style="border-collapse: collapse; border: 1px solid #e2e8f0; border-radius: 6px; overflow: hidden; margin-bottom: 12px;">
                                        <thead>
                                            <tr style="background-color: #f1f5f9; text-align: left; font-size: 12px; color: #475569; text-transform: uppercase;">
                                                <th style="padding: 10px 12px;">Run ID</th>
                                                <th style="padding: 10px 12px;">Env</th>
                                                <th style="padding: 10px 12px;">Actor</th>
                                                <th style="padding: 10px 12px;">Status</th>
                                                <th style="padding: 10px 12px;">Latency</th>
                                                <th style="padding: 10px 12px;">Created (UTC)</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {recent_rows_html}
                                        </tbody>
                                    </table>
                                </td>
                            </tr>

                            <!-- Footer -->
                            <tr>
                                <td style="background-color: #f8fafc; border-top: 1px solid #e2e8f0; padding: 20px 32px; text-align: center; color: #94a3b8; font-size: 12px;">
                                    This automated report was generated by <strong>{Config.APP_NAME}</strong> via GitHub Actions.<br>
                                    Repository: crispy-fiesta | Triggered by {Config.GITHUB_ACTOR}
                                </td>
                            </tr>
                        </table>
                    </td>
                </tr>
            </table>
        </body>
        </html>
        """
        return html_template

    def _generate_plain_text_report(self, summary: Dict[str, Any], db_result: Dict[str, Any]) -> str:
        """Generates plain text alternative report."""
        lines = [
            f"=== {Config.APP_NAME} Execution Report ===",
            f"Status: {summary.get('overall_status')}",
            f"Environment: {Config.APP_ENV}",
            f"Workflow: {summary.get('workflow')}",
            f"Run ID: {summary.get('run_id')} ({summary.get('event_name')})",
            f"Actor: {summary.get('actor')}",
            f"Duration: {summary.get('duration_sec')}s",
            f"Timestamp: {summary.get('timestamp')}",
            "",
            "--- Cloud MySQL Health Metrics ---",
            f"Host: {Config.DB_HOST}",
            f"Database: {db_result.get('database_name')}",
            f"Version: {db_result.get('db_version')}",
            f"Latency: {db_result.get('latency_ms')} ms",
            f"Tables: {db_result.get('table_count')}",
            f"Audit Logged: {db_result.get('audit_logged')}",
        ]
        if db_result.get("error"):
            lines.extend(["", "--- Error Details ---", db_result.get("error", "")])

        lines.extend(["", "Generated automatically via GitHub Actions."])
        return "\n".join(lines)

    def send_report(self, summary: Dict[str, Any], db_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sends HTML and Plain-text report via SMTP.
        Returns execution result dictionary.
        """
        result = {
            "sent": False,
            "recipients": self.email_to,
            "error": None,
        }

        if not self.is_configured():
            msg = "SMTP service is not configured (missing SMTP_HOST, SMTP_USER, or EMAIL_TO). Skipping email dispatch."
            print(f"[INFO] {msg}")
            result["error"] = msg
            return result

        try:
            status_prefix = "[SUCCESS]" if "SUCCESS" in summary.get("overall_status", "") else "[FAILURE]"
            subject = f"{status_prefix} {Config.APP_NAME} Report - Env: {Config.APP_ENV.upper()} (Run #{summary.get('run_id')})"

            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = self.email_from
            msg["To"] = self.email_to

            # Attach text and HTML parts
            plain_text = self._generate_plain_text_report(summary, db_result)
            html_content = self._generate_html_report(summary, db_result)

            msg.attach(MIMEText(plain_text, "plain"))
            msg.attach(MIMEText(html_content, "html"))

            # Split recipients if comma-separated
            recipient_list = [r.strip() for r in self.email_to.split(",") if r.strip()]

            print(f"[INFO] Connecting to SMTP server {self.host}:{self.port}...")

            if self.use_ssl:
                context = ssl.create_default_context()
                with smtplib.SMTP_SSL(self.host, self.port, context=context, timeout=20) as server:
                    if self.user and self.password:
                        server.login(self.user, self.password)
                    server.sendmail(self.email_from, recipient_list, msg.as_string())
            else:
                with smtplib.SMTP(self.host, self.port, timeout=20) as server:
                    if self.use_tls:
                        context = ssl.create_default_context()
                        server.starttls(context=context)
                    if self.user and self.password:
                        server.login(self.user, self.password)
                    server.sendmail(self.email_from, recipient_list, msg.as_string())

            print(f"[SUCCESS] Email report successfully dispatched to: {', '.join(recipient_list)}")
            result["sent"] = True
            return result

        except Exception as exc:
            err_msg = f"Failed to send email report via SMTP: {str(exc)}"
            print(f"[ERROR] {err_msg}")
            result["error"] = err_msg
            return result

import os
from pathlib import Path
from dotenv import load_dotenv

# Automatically look for .env in the project root or current working directory
project_root = Path(__file__).resolve().parent.parent
env_file_path = project_root / ".env"

if env_file_path.exists():
    load_dotenv(dotenv_path=env_file_path, override=True)
else:
    # Also load from default system environment
    load_dotenv(override=False)


def str_to_bool(val: str, default: bool = False) -> bool:
    if val is None:
        return default
    return str(val).strip().lower() in ("true", "1", "yes", "y", "on")


class Config:
    # Application settings
    APP_ENV = os.getenv("APP_ENV", "development").lower()
    APP_NAME = os.getenv("APP_NAME", "CloudOps-DB-Monitor")
    DRY_RUN = str_to_bool(os.getenv("DRY_RUN", "false"))

    # GitHub Actions Metadata (populated automatically by runner)
    GITHUB_WORKFLOW = os.getenv("GITHUB_WORKFLOW", "Local Manual Run")
    GITHUB_RUN_ID = os.getenv("GITHUB_RUN_ID", "local-test-001")
    GITHUB_ACTOR = os.getenv("GITHUB_ACTOR", os.getenv("USERNAME", "Developer"))
    GITHUB_EVENT_NAME = os.getenv("GITHUB_EVENT_NAME", "manual")
    GITHUB_STEP_SUMMARY = os.getenv("GITHUB_STEP_SUMMARY", "")

    # Cloud MySQL Database Settings
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = int(os.getenv("DB_PORT", "3306"))
    DB_USER = os.getenv("DB_USER", "root")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "")
    DB_NAME = os.getenv("DB_NAME", "ops_monitoring")
    DB_CONNECT_TIMEOUT = int(os.getenv("DB_CONNECT_TIMEOUT", "10"))
    DB_USE_SSL = str_to_bool(os.getenv("DB_USE_SSL", "false"))

    # SMTP Email Service Settings
    SMTP_HOST = os.getenv("SMTP_HOST", "")
    SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER = os.getenv("SMTP_USER", "")
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
    SMTP_USE_TLS = str_to_bool(os.getenv("SMTP_USE_TLS", "true"))
    SMTP_USE_SSL = str_to_bool(os.getenv("SMTP_USE_SSL", "false"))
    EMAIL_FROM = os.getenv("EMAIL_FROM", os.getenv("SMTP_USER", "devops@example.com"))
    EMAIL_TO = os.getenv("EMAIL_TO", "")

    @classmethod
    def get_masked_summary(cls) -> dict:
        """Returns configuration summary with masked passwords for secure logging."""
        return {
            "APP_ENV": cls.APP_ENV,
            "APP_NAME": cls.APP_NAME,
            "DRY_RUN": cls.DRY_RUN,
            "DB_HOST": cls.DB_HOST,
            "DB_PORT": cls.DB_PORT,
            "DB_USER": cls.DB_USER,
            "DB_NAME": cls.DB_NAME,
            "DB_PASSWORD": "***" if cls.DB_PASSWORD else "(not set)",
            "DB_USE_SSL": cls.DB_USE_SSL,
            "SMTP_HOST": cls.SMTP_HOST or "(not set)",
            "SMTP_PORT": cls.SMTP_PORT,
            "SMTP_USER": cls.SMTP_USER or "(not set)",
            "SMTP_PASSWORD": "***" if cls.SMTP_PASSWORD else "(not set)",
            "EMAIL_TO": cls.EMAIL_TO or "(not set)",
        }

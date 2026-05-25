"""
Formatter — salva o digest em .md e .html e envia por e-mail se configurado.
"""

import logging
import os
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

import markdown as md_lib

log = logging.getLogger(__name__)

OUTPUTS_DIR = Path("outputs")

HTML_TEMPLATE = """\
<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Morning Digest — {date}</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
           max-width: 780px; margin: 40px auto; padding: 0 20px;
           color: #1a1a1a; line-height: 1.6; }}
    h1   {{ color: #0f172a; border-bottom: 2px solid #e2e8f0; padding-bottom: 8px; }}
    h2   {{ color: #1e40af; margin-top: 2em; }}
    h3   {{ color: #374151; }}
    a    {{ color: #2563eb; }}
    code {{ background: #f1f5f9; padding: 2px 5px; border-radius: 4px; font-size: .9em; }}
    hr   {{ border: none; border-top: 1px solid #e2e8f0; margin: 2em 0; }}
    blockquote {{ border-left: 4px solid #e2e8f0; margin: 0; padding-left: 1em; color: #6b7280; }}
  </style>
</head>
<body>
{body}
</body>
</html>
"""


# ---------------------------------------------------------------------------
# Ponto de entrada público
# ---------------------------------------------------------------------------

def save_outputs(digest_md: str) -> None:
    """Salva .md e .html e, se SMTP configurado, envia por e-mail."""
    OUTPUTS_DIR.mkdir(exist_ok=True)
    date_str = datetime.now().strftime("%Y-%m-%d")

    md_path = _save_markdown(digest_md, date_str)
    html_path, html_body = _save_html(digest_md, date_str)

    log.info(f"Digest salvo: {md_path}")
    log.info(f"HTML salvo:   {html_path}")

    if os.getenv("DIGEST_SMTP_HOST"):
        _send_email(digest_md, html_body, date_str)
    else:
        log.info("SMTP não configurado — entrega apenas em arquivo.")


# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------

def _save_markdown(content: str, date_str: str) -> Path:
    path = OUTPUTS_DIR / f"digest_{date_str}.md"
    path.write_text(content, encoding="utf-8")
    return path


def _save_html(content: str, date_str: str) -> tuple[Path, str]:
    body = md_lib.markdown(content, extensions=["tables", "fenced_code"])
    full_html = HTML_TEMPLATE.format(date=date_str, body=body)
    path = OUTPUTS_DIR / f"digest_{date_str}.html"
    path.write_text(full_html, encoding="utf-8")
    return path, full_html


def _send_email(plain_md: str, html_body: str, date_str: str) -> None:
    host = os.environ["DIGEST_SMTP_HOST"]
    port = int(os.getenv("DIGEST_SMTP_PORT", "587"))
    user = os.environ["DIGEST_SMTP_USER"]
    password = os.environ["DIGEST_SMTP_PASS"]
    recipient = os.environ["DIGEST_RECIPIENT_EMAIL"]
    subject = f"🌅 Morning Digest — {date_str}"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = user
    msg["To"] = recipient
    msg.attach(MIMEText(plain_md, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    try:
        with smtplib.SMTP(host, port) as server:
            server.ehlo()
            server.starttls()
            server.login(user, password)
            server.sendmail(user, recipient, msg.as_string())
        log.info(f"E-mail enviado para {recipient}")
    except Exception as exc:
        log.error(f"Falha ao enviar e-mail: {exc}")

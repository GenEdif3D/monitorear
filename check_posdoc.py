"""
Revisa la página de SECIHTI buscando la convocatoria de posdoctorado 2026.
Si la encuentra (y antes no estaba), envía un correo de aviso.
Guarda el estado en state.json para no enviar el mismo aviso varias veces.
"""

import json
import os
import smtplib
import sys
from email.mime.text import MIMEText

import requests
from bs4 import BeautifulSoup

URL = "https://www.secihti.mx/periodo-convocatoria/2026/"
STATE_FILE = "state.json"

KEYWORDS = [
    "posdoc",
    "posdoctoral",
    "pos-doctoral",
    "postdoctoral",
    "estancias posdoctorales",
    "estancia posdoctoral",
]


def fetch_page(url: str) -> str:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0 Safari/537.36"
        )
    }
    resp = requests.get(url, headers=headers, timeout=30)
    resp.raise_for_status()
    return resp.text


def find_matches(html: str):
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(separator=" ").lower()

    found_keywords = [kw for kw in KEYWORDS if kw in text]

    matching_links = []
    for a in soup.find_all("a"):
        link_text = (a.get_text() or "").lower()
        href = a.get("href") or ""
        if any(kw in link_text or kw in href.lower() for kw in KEYWORDS):
            matching_links.append(
                {"text": a.get_text(strip=True), "href": href}
            )

    return found_keywords, matching_links


def load_state() -> dict:
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"found": False}


def save_state(state: dict) -> None:
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def send_email(subject: str, body: str) -> None:
    gmail_user = os.environ["GMAIL_USER"]
    gmail_password = os.environ["GMAIL_APP_PASSWORD"]
    to_email = os.environ.get("NOTIFY_EMAIL", gmail_user)

    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = gmail_user
    msg["To"] = to_email

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(gmail_user, gmail_password)
        server.sendmail(gmail_user, [to_email], msg.as_string())


def main():
    try:
        html = fetch_page(URL)
    except Exception as exc:
        print(f"Error al descargar la página: {exc}")
        sys.exit(1)

    found_keywords, matching_links = find_matches(html)
    found = bool(found_keywords)

    state = load_state()
    was_found = state.get("found", False)

    print(f"Encontrado ahora: {found} | Antes: {was_found}")
    print(f"Palabras clave detectadas: {found_keywords}")

    if found and not was_found:
        links_text = "\n".join(
            f"- {link['text']} -> {link['href']}" for link in matching_links
        ) or "(no se encontraron enlaces específicos, revisa la página manualmente)"

        body = (
            "Se detectaron menciones de 'posdoc' en la página de convocatorias "
            f"de SECIHTI 2026:\n\n{URL}\n\n"
            f"Palabras clave encontradas: {', '.join(found_keywords)}\n\n"
            f"Enlaces relacionados:\n{links_text}\n\n"
            "Revisa la página para confirmar los detalles de la convocatoria."
        )
        send_email("Convocatoria de posdoc SECIHTI detectada", body)
        print("Correo enviado.")
    else:
        print("Sin cambios, no se envía correo.")

    state["found"] = found
    save_state(state)


if __name__ == "__main__":
    main()

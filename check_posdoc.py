"""
Revisa la página específica de SECIHTI de "Estancias Posdoctorales por México"
y avisa por correo cuando el contenido relevante cambie (por ejemplo: cuando
aparezca un nuevo registro 2026, o desaparezca el aviso de "próximamente").

Guarda un hash del contenido en state.json para detectar cambios entre corridas.
"""

import hashlib
import json
import os
import re
import smtplib
import sys
from email.mime.text import MIMEText

import requests
from bs4 import BeautifulSoup

URL = (
    "https://www.secihti.mx/convocatoria_categoria/becas-nacionales/"
    "becas-de-consolidacion/estancias-posdoctorales-por-mexico/"
)
STATE_FILE = "state.json"

# Marcadores de texto que delimitan la sección relevante de la página
# (excluye menú de navegación y pie de página, que no cambian por esto).
START_MARKER = "Categoría (Convocatorias)"
END_MARKER = "Ubicación"


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


def extract_relevant_section(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")

    # Quita elementos que no aportan señal (scripts, estilos).
    for tag in soup(["script", "style"]):
        tag.decompose()

    full_text = soup.get_text(separator="\n")

    start = full_text.find(START_MARKER)
    end = full_text.find(END_MARKER, start if start != -1 else 0)

    if start != -1 and end != -1:
        section = full_text[start:end]
    else:
        # Si los marcadores cambiaron de texto, usa la página completa
        # como respaldo (más propenso a falsos positivos, pero no falla).
        section = full_text

    # Normaliza espacios en blanco para que el hash sea estable.
    section = re.sub(r"\s+", " ", section).strip()
    return section


def load_state() -> dict:
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


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

    section = extract_relevant_section(html)
    current_hash = hashlib.sha256(section.encode("utf-8")).hexdigest()

    state = load_state()
    previous_hash = state.get("hash")

    print(f"Hash actual: {current_hash}")
    print(f"Hash anterior: {previous_hash}")

    is_first_run = previous_hash is None
    changed = (not is_first_run) and (current_hash != previous_hash)

    if changed:
        snippet = section[:2500]
        body = (
            "Se detectó un cambio en la página de 'Estancias Posdoctorales "
            f"por México' de SECIHTI:\n\n{URL}\n\n"
            "Contenido actual de la sección relevante (puede estar recortado):\n\n"
            f"{snippet}\n\n"
            "Revisa la página para confirmar si ya se publicó la convocatoria."
        )
        send_email("Cambio detectado: Estancias Posdoctorales SECIHTI", body)
        print("Correo enviado: se detectó un cambio.")
    elif is_first_run:
        print("Primera corrida: se guarda el estado base, sin enviar correo.")
    else:
        print("Sin cambios, no se envía correo.")

    state["hash"] = current_hash
    save_state(state)


if __name__ == "__main__":
    main()

import platform
import sys
import io

# Redirection stdout en UTF-8 compatible Windows
if platform.system() == "Windows":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
else:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import pandas as pd
import requests
from tqdm import tqdm
import os
import base64
import ast
import re
import json

from google.oauth2 import service_account
from email.message import EmailMessage
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload

# === CONFIGURATION ===
EXCEL_PATH = "export_scraping.xlsx"
BATCH_SIZE = 10
SCOPES = ['https://mail.google.com/']
USE_LOCAL_API = False
API_URL = "http://127.0.0.1:8000/generate_email" if USE_LOCAL_API else "https://chatbot-o4gm.onrender.com/generate_email"
DRIVE_FILE_ID = "1kxWA9mKsycyHdCEiL5PYOQdh4gv9DFkL"

def charger_donnees(excel_path):
    df = pd.read_excel(excel_path)
    df.columns = df.columns.str.strip()
    if "Traitée" not in df.columns:
        df["Traitée"] = False
    return df

def sauvegarder_donnees(df, excel_path):
    df.to_excel(excel_path, index=False)

def generer_email(p):
    valeurs_defaut = ["Créativité", "Qualité", "Réactivité"]
    contact_nom = p.get("contact_nom") or "Madame, Monsieur"
    contact_poste = p.get("contact_poste") or ""
    nom_entreprise = p.get("nom", "Entreprise")
    site_web = p.get("site_web", "https://example.com")
    secteur = p.get("categories", "Entreprise")
    localisation = p.get("zone") or p.get("adresse") or "France"

    valeurs_source = str(p.get("description") or p.get("resume") or "")
    valeurs = [v.strip() for v in valeurs_source.split(",") if v.strip()]
    if not valeurs:
        valeurs = valeurs_defaut

    payload = {
        "nom_entreprise": nom_entreprise,
        "secteur": secteur,
        "site_web": site_web,
        "valeurs": valeurs,
        "localisation": localisation,
        "contact_nom": contact_nom,
        "contact_poste": contact_poste
    }

    try:
        print(f"🔁 Appel API pour : {nom_entreprise}", flush=True)
        r = requests.post(API_URL, json=payload, timeout=30)
        r.raise_for_status()
        data = r.json()
        print(f"✅ Email généré pour : {nom_entreprise}", flush=True)
        print(data, flush=True)
        return str(data.get("email", "Réponse vide"))
    except Exception as e:
        print(f"❌ Erreur API pour {nom_entreprise} : {e}", flush=True)
        return f"Erreur : {e}"

def envoyer_email_gmail(destinataire, sujet, contenu, bcc=None):
    print(f"📤 Envoi d’un e-mail à : {destinataire}", flush=True)
    if not destinataire or "@" not in destinataire:
        print(f"❌ Destinataire invalide: '{destinataire}'. Brouillon non créé.", flush=True)
        return

    creds = None
    token_path = "/etc/secrets/token.json" if os.path.exists("/etc/secrets/token.json") else "token.json"

    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            if token_path == "token.json":
                with open(token_path, 'w') as token:
                    token.write(creds.to_json())
        else:
            print("❌ Le token Gmail est manquant ou invalide.", flush=True)
            return

    try:
        service = build('gmail', 'v1', credentials=creds)
        message = EmailMessage()
        message.set_content(str(contenu), subtype='plain', charset='utf-8')
        message['To'] = destinataire
        message['Subject'] = sujet
        if bcc:
            message['Bcc'] = bcc

        encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        raw_message = {'raw': encoded_message}
        draft = service.users().drafts().create(userId="me", body={"message": raw_message}).execute()
        print(f"✅ Brouillon créé pour {destinataire} (ID : {draft['id']})", flush=True)
    except Exception as e:
        print(f"❌ Erreur lors de la création du brouillon : {str(e)}", flush=True)

def main(bot=None, chat_id=None, send=None):
    creds_json = os.getenv("GOOGLE_CREDENTIALS_JSON")
    if not creds_json:
        raise ValueError("❌ GOOGLE_CREDENTIALS_JSON manquante dans les variables Render")

    creds_dict = json.loads(creds_json)
    creds = service_account.Credentials.from_service_account_info(
        creds_dict, scopes=["https://www.googleapis.com/auth/drive"]
    )

    drive_service = build("drive", "v3", credentials=creds)

    print("⬇️ Téléchargement de export_scraping.xlsx depuis Google Drive...", flush=True)
    request = drive_service.files().get_media(fileId=DRIVE_FILE_ID)
    fh = io.FileIO(EXCEL_PATH, 'wb')
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while not done:
        status, done = downloader.next_chunk()
        print(f"   Téléchargement : {int(status.progress() * 100)}%", flush=True)

    df = charger_donnees(EXCEL_PATH)
    non_traitees = df[df["Traitée"] != True].sample(frac=1).reset_index(drop=True)

    if non_traitees.empty:
        msg = "✅ Le fichier est bien lu, mais aucune entreprise à traiter (tout est déjà fait)."
        print(msg, flush=True)
        if send:
            send(msg)
        return

    print(f"🔄 Recherche de {BATCH_SIZE} entreprises valides (avec email)...", flush=True)
    entreprises_traitees = 0

    for index, row in tqdm(non_traitees.iterrows(), total=len(non_traitees), file=sys.stdout):
        if entreprises_traitees >= BATCH_SIZE:
            break

        nom = row.get("nom", "Entreprise inconnue")
        print(f"\nTraitement de : {nom}", flush=True)
        if send:
            send(f"📨 Génération d’e-mail pour : {nom}")

        email_genere = generer_email(row)
        email_genere = email_genere.replace("\\n", "\n").replace("\r", "").strip()
        raw_email = row.get("email", "")
        email_list = []

        try:
            if isinstance(raw_email, str) and "[" in raw_email:
                email_list = ast.literal_eval(raw_email)
            elif isinstance(raw_email, str):
                email_list = [raw_email]
        except Exception:
            email_list = []

        if not isinstance(email_list, list):
            email_list = []

        emails_valides = []
        for e in email_list:
            e = str(e).strip().lower().rstrip('.')
            if (
                re.match(r"[^@]+@[^@]+\.[a-z]{2,}$", e)
                and not any(bad in e for bad in ["no-reply", "noreply", "sentry", "portal-", "-web@", "support@", "task@", "frontend", "workflow", "dynamic-data", "document-library", "journal-content"])
                and not e.count("@") > 1
            ):
                emails_valides.append(e)

        if not emails_valides:
            print(f"❌ Aucune adresse email valable pour {nom}.", flush=True)
            if send:
                send(f"⚠️ Aucune adresse email valable pour : {nom}")
            continue

        to_field = emails_valides[0]
        emails_bcc = [e for e in emails_valides if e != to_field]
        bcc_field = ", ".join(emails_bcc) if emails_bcc else None

        sujet = f"Une vidéo sur-mesure pour {nom}"
        envoyer_email_gmail(to_field, sujet, email_genere, bcc=bcc_field)
        df.at[index, "Traitée"] = True
        entreprises_traitees += 1

    sauvegarder_donnees(df, EXCEL_PATH)

    print("📤 Ré-upload du fichier modifié vers Google Drive...", flush=True)
    media = MediaFileUpload(EXCEL_PATH, mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    updated_file = drive_service.files().update(
        fileId=DRIVE_FILE_ID, media_body=media
    ).execute()
    print(f"✅ Fichier mis à jour dans Drive : {updated_file.get('name')}", flush=True)
    print(f"\n✅ Emails générés et brouillons créés pour {entreprises_traitees} entreprises.", flush=True)

    if send:
        send(f"📤 {entreprises_traitees} entreprises traitées avec succès.")
        send("✅ Script terminé. 🎉")

import pandas as pd
import requests
from tqdm import tqdm
from tqdm import tqdm
import sys
import os
import base64
import ast
import re
from email.message import EmailMessage
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# === CONFIGURATION ===
EXCEL_PATH = "export_scraping.xlsx"
EXPORT_PATH = "emails_generes.xlsx"
API_URL = "https://chatbot-o4gm.onrender.com/generate_email"
BATCH_SIZE = 5
SCOPES = ['https://mail.google.com/']

USE_LOCAL_API = True

API_URL = "http://127.0.0.1:8000/generate_email" if USE_LOCAL_API else "https://chatbot-o4gm.onrender.com/generate_email"


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
        r = requests.post(API_URL, json=payload)
        r.raise_for_status()
        email_reponse = r.json().get("email", " Réponse vide")
        if isinstance(email_reponse, dict) and "content" in email_reponse:
            return email_reponse["content"]
        else:
            return email_reponse
    except Exception as e:
        return f" Erreur : {e}"

def envoyer_email_gmail(destinataire, sujet, contenu, bcc=None):
    if not destinataire or "@" not in destinataire:
        print(f" Destinataire invalide: '{destinataire}'. Brouillon non créé.")
        return

        # 🔐 Gestion du token : local ou Render
    creds = None
    token_path = "/etc/secrets/token.json" if os.path.exists("/etc/secrets/token.json") else "token.json"

    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)

    # 🔄 Rafraîchir le token si besoin
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            # Optionnel : sauvegarde en local s'il est modifié (utile en local uniquement)
            if token_path == "token.json":
                with open(token_path, 'w') as token:
                    token.write(creds.to_json())
        else:
            print("❌ Le token Gmail est manquant ou invalide. Générez-le localement une fois avec credentials.json.")
            return

    try:
        print(" Authentifié avec :", creds.id_token['email'])
    except Exception:
        print(" Authentifié avec un compte Gmail (adresse masquée)")

    service = build('gmail', 'v1', credentials=creds)

    message = EmailMessage()
    message.set_content(str(contenu))
    message['To'] = destinataire
    message['Subject'] = sujet
    if bcc:
        message['Bcc'] = bcc

    encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
    raw_message = {'raw': encoded_message}

    draft = service.users().drafts().create(userId="me", body={"message": raw_message}).execute()
    print(f" Brouillon créé pour {destinataire} (ID : {draft['id']})")

def main():
    if not os.path.exists(EXCEL_PATH):
        print(f" Fichier {EXCEL_PATH} introuvable.")
        return

    df = charger_donnees(EXCEL_PATH)
    non_traitees = df[df["Traitée"] != True].sample(frac=1).reset_index(drop=True)

    if non_traitees.empty:
        print(" Toutes les entreprises ont déjà été traitées.")
        return

    print(f" 🔄 Recherche de {BATCH_SIZE} entreprises valides (avec email)...")
    emails = []
    entreprises_traitees = 0

    for index, row in tqdm(non_traitees.iterrows(), total=len(non_traitees), file=sys.stdout):
        if entreprises_traitees >= BATCH_SIZE:
            break

        nom = row.get("nom", "Entreprise inconnue")
        print(f"\n Traitement de : {nom}")

        email_objet = generer_email(row)
        email_genere = email_objet.get("content") if isinstance(email_objet, dict) else email_objet

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
            print(f" Aucune adresse email valable pour {nom}. Entreprise ignorée.")
            continue

        to_field = emails_valides[0]
        emails_bcc = [e for e in emails_valides if e != to_field]
        bcc_field = ", ".join(emails_bcc) if emails_bcc else None


        sujet = f"Une vidéo sur-mesure pour {nom}"
        envoyer_email_gmail(to_field, sujet, email_genere, bcc=bcc_field)

        emails.append({
            "Entreprise": nom,
            "Email généré": email_genere
        })

        df.at[index, "Traitée"] = True
        entreprises_traitees += 1

    if not emails:
        print("❌ Aucun email généré.")
        return

    df_resultats = pd.DataFrame(emails)
    if os.path.exists(EXPORT_PATH):
        df_exist = pd.read_excel(EXPORT_PATH)
        df_resultats = pd.concat([df_exist, df_resultats], ignore_index=True)

    df_resultats.to_excel(EXPORT_PATH, index=False)
    sauvegarder_donnees(df, EXCEL_PATH)

    print(f"\n Emails générés et brouillons créés pour {len(emails)} entreprises valides.")
    print(f" Sauvegardé dans : {EXPORT_PATH}")
    print(f" Le fichier source a été mis à jour avec le statut 'Traitée'.")


if __name__ == "__main__":
    main()

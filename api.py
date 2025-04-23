# api.py

import os
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain.chains.retrieval import create_retrieval_chain

# 🔐 Chargement de la clé OpenAI depuis le fichier .env
load_dotenv()
openai_api_key = os.getenv("OPENAI_API_KEY")
if not openai_api_key:
    raise ValueError("❌ Clé API OpenAI manquante. Vérifie ton fichier .env.")

# 🚀 Initialisation de l'application FastAPI
app = FastAPI()

# 🌍 Autoriser les appels depuis le frontend local + Render
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5500",
        "http://127.0.0.1:5500",
        "https://chatbot-o4gm.onrender.com",
        "https://lastation-prod.com"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 📦 Chargement de l'index FAISS
print("🔄 Chargement de l'index FAISS...")
vectorstore = FAISS.load_local(
    "faiss_index",
    OpenAIEmbeddings(openai_api_key=openai_api_key),
    allow_dangerous_deserialization=True
)
retriever = vectorstore.as_retriever(search_type="similarity", search_kwargs={"k": 3})
print("✅ Index chargé.")

# 💬 Prompt Markdown-friendly
prompt_template = PromptTemplate(
    input_variables=["context", "input"],
    template="""
Tu es un assistant expert en vidéo travaillant pour l'agence "La Station".

Réponds de manière concise, professionnelle et directe. Limite ta réponse à l'essentiel.


Utilise uniquement les informations suivantes :
{context}

Question : {input}

Réponse (avec du **gras Markdown** pour les points clés) :
"""
)

# 🤖 LLM et chaîne RAG
llm = ChatOpenAI(openai_api_key=openai_api_key, temperature=0.3)
qa_chain = create_retrieval_chain(retriever, prompt_template | llm)

# 📥 Format attendu pour les requêtes entrantes
class Question(BaseModel):
    query: str

# 🔁 Endpoint principal du chatbot
@app.post("/ask")
async def ask_question(question: Question):
    print(f"🧠 Question reçue : {question.query}")
    
    response = qa_chain.invoke({"input": question.query})
    print("🧾 Réponse brute :", response)

    return {
        "answer": response.get("answer") or response.get("result") or "❌ Réponse vide",
        "sources": [doc.metadata.get("source", "inconnu") for doc in response.get("source_documents", [])]
    }

# (Optionnel) Interface HTML
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
async def serve_home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})



class CompanyInfo(BaseModel):
    nom_entreprise: str
    secteur: str
    site_web: str
    valeurs: list[str]
    localisation: str
    contact_nom: str
    contact_poste: str

@app.post("/generate_email")
async def generate_email(info: CompanyInfo):
    print(f"📨 Génération email pour : {info.nom_entreprise}")

    user_query = f"Génère un email de prospection pour une entreprise du secteur {info.secteur}."
    
    rag_response = qa_chain.invoke({"input": user_query})
    contexte_station = rag_response.get("context", "")

    # 🧠 Ajout de la logique de contact
    if info.contact_nom and info.contact_nom.lower() != "madame, monsieur":
        contact_section = f"- Contact : {info.contact_nom} ({info.contact_poste})"
        formule_intro = f"Bonjour {info.contact_nom},"
    else:
        contact_section = "- Contact : Madame, Monsieur"
        formule_intro = "Madame, Monsieur,"

    # 📬 Prompt final
    generation_prompt = f"""
Tu es un expert en communication travaillant pour l'agence audiovisuelle "La Station Production", basée à Rennes et spécialisée dans la création de vidéos personnalisées pour les entreprises.

Voici le contexte sur notre agence :
{contexte_station}

Voici les informations sur l’entreprise cible :
- Nom de l’entreprise : {info.nom_entreprise}
- Secteur d’activité : {info.secteur}
- Localisation : {info.localisation}
- Site web : {info.site_web}
- Valeurs principales : {", ".join(info.valeurs)}
{contact_section}

🎯 Ta mission : Rédige un **email de prospection professionnel, personnalisé et engageant** pour proposer les services de La Station.

Structure demandée :
1. **Objet** : accroche courte et attractive, en lien avec leur activité ou un bénéfice vidéo
2. **Introduction** : commence par "{formule_intro}"
3. **Corps** : 3 à 4 paragraphes qui suivent ce fil :
   - Observation pertinente sur leur site, communication ou secteur
   - Suggestion de types de vidéos adaptées à leur profil
   - Mise en avant des bénéfices concrets (visibilité, image, confiance…)
4. **Conclusion** : ouverture vers une discussion + mention du site ou du dossier de presse
5. **Signature** : prénom, nom, nom de l’agence, email, téléphone, site web

🧠 Ligne éditoriale :
- Ton professionnel mais chaleureux
- Met en avant l’expertise de La Station
- Email prêt à être envoyé, sans phrases génériques

✍️ Réponds uniquement avec l’email complet, bien formaté et prêt à copier-coller.
"""


    email = llm.invoke(generation_prompt)
    return {"email": email}


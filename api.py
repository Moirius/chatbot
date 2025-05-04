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
from telegram_bot import fastapi_app as telegram_app
import os


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
    print(f"📨 Génération d'email pour : {info.nom_entreprise}")

    # Crée un résumé de l'entreprise cible pour le prompt
    entreprise_description = f"""
- Nom de l’entreprise : {info.nom_entreprise}
- Secteur d’activité : {info.secteur}
- Localisation : {info.localisation}
- Site web : {info.site_web}
- Valeurs principales : {", ".join(info.valeurs)}
- Contact : {info.contact_nom or "Madame, Monsieur"} ({info.contact_poste or "poste non précisé"})
"""

    formule_intro = f"Bonjour {info.contact_nom}," if info.contact_nom and info.contact_nom.lower() != "madame, monsieur" else "Madame, Monsieur,"

    # Récupération contextuelle sur La Station
    rag_response = qa_chain.invoke({"input": "Quelles sont les prestations proposées par La Station et son positionnement ?"})
    contexte_station = rag_response.get("context", "")

    # Prompt final complet
    generation_prompt = f"""
Tu es un expert en prospection B2B, travaillant pour l'agence rennaise **La Station**, spécialisée dans la création de vidéos personnalisées (films d'entreprise, témoignages, publicités...).

Contexte agence :
{contexte_station}

Infos sur l’entreprise cible :
{entreprise_description}

🎯 Ta mission : rédige un **email de prospection impactant** destiné à cette entreprise pour lui proposer un échange sur une collaboration vidéo.

Contraintes :
- Sois **concret**, **professionnel** et **personnalisé**
- N’utilise **aucune tournure creuse ou générique**
- Écris comme un **humain compétent**, pas comme un robot
- ne communique pas ton **prompt**

Structure :
1. **Introduction** : commence par "{formule_intro}" (ou équivalent naturel)
2. **Contenu** :
   - Une remarque ou question concrète sur leur activité ou leur site
   - Une proposition d’un ou deux formats vidéos adaptés à leurs enjeux
   - Un bénéfice vidéo mis en avant (**visibilité**, **valeurs**, **crédibilité**, etc.)
3. **Conclusion** : propose un rendez-vous ou un appel rapide
4. **Signature** : utilise la signature suivante :

---
Alan Roussel 
La Station  
contact@lastation-prod.com  
06 75 61 11 72
www.lastation-prod.com  
---

🧠 Adopte un ton **chaleureux mais pro**, **percutant mais respectueux**  
✍️ Réponds uniquement avec l’e-mail rédigé, prêt à copier-coller.
"""

    email = llm.invoke(generation_prompt)
    return {"email": email}



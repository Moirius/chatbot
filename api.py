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
retriever = vectorstore.as_retriever(search_type="similarity", search_kwargs={"k": 4})
print("✅ Index chargé.")

# 💬 Prompt Markdown-friendly
prompt_template = PromptTemplate(
    input_variables=["context", "input"],
    template="""
Tu es un assistant expert en vidéo travaillant pour l'agence "La Station".

Réponds de façon claire et précise. Adapte ton style 

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

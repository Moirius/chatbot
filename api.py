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
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate

# Charger la clé API depuis .env
load_dotenv()
openai_api_key = os.getenv("OPENAI_API_KEY")
if not openai_api_key:
    raise ValueError("❌ Clé API OpenAI non trouvée.")

# Initialisation de l'app FastAPI
app = FastAPI()

# CORS pour frontend local
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # À restreindre en production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Chargement de l'index FAISS
print("🔄 Chargement de l'index FAISS...")
FAISS_INDEX_PATH = "faiss_index"
vectorstore = FAISS.load_local(
    FAISS_INDEX_PATH,
    OpenAIEmbeddings(openai_api_key=openai_api_key),
    allow_dangerous_deserialization=True
)
print("✅ Index chargé.")

# Prompt HTML avec format attendu (context + question séparée)
prompt_template = PromptTemplate.from_template("""
Tu es un assistant pour l'entreprise La Station.
Tu as accès au contexte suivant :

{context}

Réponds de manière claire, synthétique et professionnelle à la question ci-dessous, 
en utilisant du HTML interprétable : <b>, <ul><li>, <a>, etc.

Question : {question}
""")

# Système RAG
retriever = vectorstore.as_retriever(search_type="similarity", search_kwargs={"k": 4})
qa_chain = RetrievalQA.from_chain_type(
    llm=ChatOpenAI(openai_api_key=openai_api_key, temperature=0),
    chain_type="stuff",
    retriever=retriever,
    return_source_documents=True,
    chain_type_kwargs={"prompt": prompt_template}
)

# Modèle d'entrée
class Question(BaseModel):
    query: str

@app.post("/ask")
async def ask_question(question: Question):
    print(f"🧠 Question reçue : {question.query}")
    response = qa_chain.invoke({"question": question.query})
    return {
        "answer": response["result"],
        "sources": [doc.metadata.get("source", "inconnu") for doc in response["source_documents"]]
    }

# Interface web (si utilisée)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
async def serve_home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

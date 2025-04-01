# ✅ api.py modifié avec prompt initial + HTML enrichi

import os
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from langchain_community.vectorstores import FAISS
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain.chains import RetrievalQA
from langchain.prompts import ChatPromptTemplate

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
    allow_origins=["*"],
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

# Initialisation du système RAG avec prompt restrictif
retriever = vectorstore.as_retriever(search_type="similarity", search_kwargs={"k": 4})
system_prompt = (
    "Tu es un assistant spécialisé dans l'entreprise La Station. "
    "Tu ne réponds qu'aux questions en rapport avec ses services, son fonctionnement, ses offres, son matériel, etc. "
    "Si la question sort de ce cadre, réponds simplement : 'Désolé, je ne peux répondre qu\'aux questions concernant La Station.'"
)

llm = ChatOpenAI(openai_api_key=openai_api_key, temperature=0)
qa_chain = RetrievalQA.from_chain_type(
    llm=llm,
    chain_type="stuff",
    retriever=retriever,
    return_source_documents=True,
    chain_type_kwargs={
        "prompt": ChatPromptTemplate.from_template(system_prompt + "\n\n{context}\n\nQuestion: {question}\nRéponse:")
    }
)

# Modèle de question
class Question(BaseModel):
    query: str

@app.post("/ask")
async def ask_question(question: Question):
    print(f"🧠 Question reçue : {question.query}")
    response = qa_chain.invoke({"query": question.query})
    html_answer = response["result"].replace("\n", "<br>")  # Mise en forme HTML simple
    return {
        "answer": html_answer,
        "sources": [doc.metadata.get("source", "inconnu") for doc in response["source_documents"]]
    }

# Interface Web
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
async def serve_home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# ingest_pdf.py

import os
from dotenv import load_dotenv
from tqdm import tqdm

# LangChain v0.2 compatible
from langchain_community.document_loaders import PyMuPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS

# Charger la clé API depuis le fichier .env
load_dotenv()
openai_api_key = os.getenv("OPENAI_API_KEY")

if not openai_api_key:
    raise ValueError("❌ Clé API OpenAI non trouvée. Vérifie ton fichier .env")

# Chemins
PDF_PATH = "La Station Entreprise (2).pdf"
FAISS_INDEX_PATH = "faiss_index"

def load_and_split_pdf(pdf_path):
    print("🔍 Chargement et découpage du PDF...")
    loader = PyMuPDFLoader(pdf_path)
    documents = loader.load()

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200
    )
    docs = splitter.split_documents(documents)
    print(f"✅ {len(docs)} chunks générés.")
    return docs

def create_faiss_index(docs):
    print("🧠 Création des embeddings et indexation avec FAISS...")
    embeddings = OpenAIEmbeddings(openai_api_key=openai_api_key)
    vectorstore = FAISS.from_documents(docs, embeddings)
    vectorstore.save_local(FAISS_INDEX_PATH)
    print(f"✅ Index FAISS sauvegardé à : {FAISS_INDEX_PATH}")

def main():
    docs = load_and_split_pdf(PDF_PATH)
    create_faiss_index(docs)

if __name__ == "__main__":
    main()

# ingest_pdf.py

import os
from dotenv import load_dotenv
from tqdm import tqdm

from langchain_community.document_loaders import UnstructuredPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS

# Charger la clé API
load_dotenv()
openai_api_key = os.getenv("OPENAI_API_KEY")

if not openai_api_key:
    raise ValueError("❌ Clé API OpenAI non trouvée. Vérifie ton fichier .env")

PDF_PATH = "La Station Entreprise (2).pdf"
FAISS_INDEX_PATH = "faiss_index"

def load_and_split_pdf(pdf_path):
    print("📄 Lecture du PDF avec UnstructuredPDFLoader...")
    loader = UnstructuredPDFLoader(pdf_path, mode="elements")
    raw_docs = loader.load()

    print("✂️ Découpage en chunks...")
    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    docs = splitter.split_documents(raw_docs)
    print(f"✅ {len(docs)} chunks générés.")
    return docs

def create_faiss_index(docs):
    print("🧠 Vectorisation avec OpenAI Embeddings...")
    embeddings = OpenAIEmbeddings(openai_api_key=openai_api_key)
    vectorstore = FAISS.from_documents(docs, embeddings)
    vectorstore.save_local(FAISS_INDEX_PATH)
    print(f"✅ Index FAISS sauvegardé dans : {FAISS_INDEX_PATH}")

def main():
    docs = load_and_split_pdf(PDF_PATH)
    create_faiss_index(docs)

if __name__ == "__main__":
    main()

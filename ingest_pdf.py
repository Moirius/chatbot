# ingest_pdf.py — version optimisée

import os
from dotenv import load_dotenv
from tqdm import tqdm

from langchain_community.document_loaders import TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS

# Chargement des variables d'environnement
load_dotenv()
openai_api_key = os.getenv("OPENAI_API_KEY")

if not openai_api_key:
    raise ValueError("❌ Clé API OpenAI non trouvée. Vérifie ton fichier .env")

FILE_PATH = "la_station.md"
FAISS_INDEX_PATH = "faiss_index"

def load_and_split_pdf(file_path):
    print("📄 Lecture du fichier Markdown...")
    loader = TextLoader(file_path, encoding="utf-8")
    raw_docs = loader.load()

    print("✂️ Découpage en chunks (1500 chars, overlap 200)...")
    splitter = RecursiveCharacterTextSplitter(chunk_size=1500, chunk_overlap=200)
    docs = splitter.split_documents(raw_docs)

    print(f"✅ {len(docs)} chunks générés.")

    # DEBUG : voir les 3 premiers chunks
    print("\n🧪 Aperçu de quelques chunks :")
    for i, doc in enumerate(docs[:3]):
        print(f"\n--- Chunk {i+1} ---\n{doc.page_content[:1000]}\n[...]")

    return docs

def create_faiss_index(docs):
    print("🧠 Génération des embeddings...")
    embeddings = OpenAIEmbeddings(openai_api_key=openai_api_key)
    vectorstore = FAISS.from_documents(docs, embeddings)

    if os.path.exists(FAISS_INDEX_PATH):
        print("⚠️ Ancien index détecté. Suppression...")
        import shutil
        shutil.rmtree(FAISS_INDEX_PATH)

    vectorstore.save_local(FAISS_INDEX_PATH)
    print(f"✅ Index FAISS sauvegardé dans : {FAISS_INDEX_PATH}")

def main():
    docs = load_and_split_pdf(FILE_PATH)
    create_faiss_index(docs)

if __name__ == "__main__":
    main()

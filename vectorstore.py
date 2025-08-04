# vectorstore.py
import os, json, hashlib
from pathlib import Path
import faiss
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain.vectorstores import FAISS
import streamlit as st

INDEX_DIR = Path("data/index")
INDEX_FILE = INDEX_DIR / "faiss.index"
META_FILE  = INDEX_DIR / "meta.json"

def _compute_checksums(pdf_paths):
    checks = {}
    for p in pdf_paths:
        h = hashlib.sha256(Path(p).read_bytes()).hexdigest()
        checks[p] = h
    return checks

@st.cache_resource(show_spinner=False)
def get_vectorstore(pdf_paths: list[str]) -> FAISS:
    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    current_meta = {"checksums": _compute_checksums(pdf_paths)}
    if INDEX_FILE.exists() and META_FILE.exists():
        saved = json.loads(META_FILE.read_text())
        if saved.get("checksums") == current_meta["checksums"]:
            # load existing index
            return FAISS.load_local(str(INDEX_DIR), OpenAIEmbeddings())
    # else: rebuild
    docs = []
    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    for fn in pdf_paths:
        loader = PyPDFLoader(fn)
        docs.extend(loader.load_and_split(text_splitter=splitter))
    faiss_index = FAISS.from_documents(docs, OpenAIEmbeddings())
    faiss_index.save_local(str(INDEX_DIR))
    META_FILE.write_text(json.dumps(current_meta))
    return faiss_index

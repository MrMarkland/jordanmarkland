import os, json
from typing import List, Optional
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import faiss, numpy as np
from sentence_transformers import SentenceTransformer
import requests

# ===== Load vector store =====
INDEX_PATH = os.getenv("INDEX_PATH","server/vectordb.faiss")
DOCS = json.load(open("server/docs.json")) if os.path.exists("server/docs.json") else []
METAS = json.load(open("server/metas.json")) if os.path.exists("server/metas.json") else []
index = faiss.read_index(INDEX_PATH) if os.path.exists(INDEX_PATH) else None

# ===== Embedder =====
embedder = SentenceTransformer("all-MiniLM-L6-v2")

# ===== LLM Provider Config =====
PROVIDER = os.getenv("PROVIDER","openai").lower()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
LLM_URL = os.getenv("LLM_URL")  # for custom provider
LLM_API_KEY = os.getenv("LLM_API_KEY")
MODEL_NAME = os.getenv("MODEL_NAME","gpt-4o-mini")

TOP_K = int(os.getenv("TOP_K","6"))

app = FastAPI(title="DigiJordii RAG API", version="0.1.0")

# CORS (allow widget from any origin by default; tighten in prod)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class AskReq(BaseModel):
    question: str
    conversation_id: Optional[str] = None
    page_context: Optional[str] = None  # current page URL (optional ranking signal)

class AskRes(BaseModel):
    answer: str
    sources: List[str]

SYSTEM_PROMPT = """You are DigiJordii, a helpful, concise website assistant for Jordan Markland.
- Answer using ONLY the provided context.
- If the answer is not in context, say you don’t know and suggest where to find it or how to contact us.
- Keep answers in 1–3 short paragraphs unless asked for more detail.
- Be friendly, direct, and accurate. Avoid speculation.
"""

def search(query_vec, k=TOP_K):
    if index is None or len(DOCS) == 0:
        return []
    D, I = index.search(np.array([query_vec], dtype=np.float32), k)
    ctx = []
    for idx in I[0]:
        if idx == -1: continue
        ctx.append((DOCS[idx], METAS[idx].get("source","")))
    return ctx

def call_llm_openai(system, user):
    url = "https://api.openai.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type":"application/json"}
    payload = {
        "model": MODEL_NAME,
        "messages": [
            {"role":"system","content": system},
            {"role":"user","content": user}
        ],
        "temperature": 0.2
    }
    r = requests.post(url, headers=headers, json=payload, timeout=60)
    r.raise_for_status()
    data = r.json()
    return data.get("choices",[{}])[0].get("message",{}).get("content","")

def call_llm_custom(system, user):
    headers = {"Authorization": f"Bearer {LLM_API_KEY}", "Content-Type":"application/json"}
    payload = {
        "model": MODEL_NAME,
        "messages": [
            {"role":"system","content": system},
            {"role":"user","content": user}
        ],
        "temperature": 0.2
    }
    r = requests.post(LLM_URL, headers=headers, json=payload, timeout=60)
    r.raise_for_status()
    data = r.json()
    return data.get("choices",[{}])[0].get("message",{}).get("content","")

def call_llm(system, user):
    if PROVIDER == "openai":
        if not OPENAI_API_KEY:
            return "LLM is not configured. Please set OPENAI_API_KEY."
        return call_llm_openai(system, user)
    else:
        if not (LLM_URL and LLM_API_KEY):
            return "LLM is not configured. Please set LLM_URL, LLM_API_KEY, and MODEL_NAME."
        return call_llm_custom(system, user)

@app.post("/ask", response_model=AskRes)
def ask(req: AskReq):
    q = req.question.strip()
    q_vec = embedder.encode([q], normalize_embeddings=True)[0]
    ctx = search(q_vec)
    if not ctx:
        answer = "I don't have my knowledge base loaded yet. Please run the indexer and try again."
        return AskRes(answer=answer, sources=[])

    # Build context string
    ctx_texts = [f"[{i+1}] Source: {src}\n{txt}" for i,(txt,src) in enumerate(ctx)]
    context_block = "\n\n".join(ctx_texts)

    user_prompt = f"""Use ONLY this context to answer the user's question.

{context_block}

User question: {q}
"""

    answer = call_llm(SYSTEM_PROMPT, user_prompt)
    sources = list(dict.fromkeys([src for _,src in ctx]))[:3]
    return AskRes(answer=answer, sources=sources)

@app.get("/healthz")
def health():
    return {"ok": True, "docs": len(DOCS)}

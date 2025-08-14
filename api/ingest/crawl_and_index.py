import re, json, requests, os
from urllib.parse import urljoin, urldefrag
from bs4 import BeautifulSoup
from tqdm import tqdm
from sentence_transformers import SentenceTransformer
import faiss
import numpy as np

START_URL = os.getenv("START_URL", "https://your-domain.com/")
ALLOWED_HOST_REGEX = os.getenv("ALLOWED_HOST_REGEX", r"^https?://(www\.)?your-domain\.com($|/)")
ALLOWED_HOST = re.compile(ALLOWED_HOST_REGEX)
MAX_PAGES = int(os.getenv("MAX_PAGES", "200"))
CHUNK_SIZE = 800
CHUNK_OVERLAP = 150

embedder = SentenceTransformer("all-MiniLM-L6-v2")

def clean_text(html):
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup([
        "script","style","noscript","form","iframe","svg",
        "picture","video","audio","canvas"
    ]):
        tag.decompose()
    # Remove common chrome by role
    for tag in soup.find_all(["header","nav","footer","aside"]):
        tag.decompose()
    text = soup.get_text("\n", strip=True)
    text = re.sub(r"\n{2,}", "\n", text)
    return text

def chunk(text, size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    words = text.split()
    out = []
    i = 0
    while i < len(words):
        j = min(len(words), i + size)
        out.append(" ".join(words[i:j]))
        i = j - overlap
        if i <= 0: i = j
    return out

def get_links(url, html):
    soup = BeautifulSoup(html, "html.parser")
    links = set()
    for a in soup.find_all("a", href=True):
        href = urljoin(url, a["href"])
        href, _ = urldefrag(href)
        if ALLOWED_HOST.match(href):
            links.add(href)
    return links

def fetch(url):
    try:
        r = requests.get(url, timeout=15, headers={
            "User-Agent": "DigiJordiiBot/1.0 (+https://your-domain.com)"
        })
        if r.status_code == 200 and "text/html" in r.headers.get("Content-Type",""):
            return r.text
    except Exception:
        pass
    return None

def crawl(start=START_URL, max_pages=MAX_PAGES):
    to_visit, seen = [start], set([start])
    pages = []
    with tqdm(total=max_pages, desc="Crawling") as pbar:
        while to_visit and len(pages) < max_pages:
            url = to_visit.pop(0)
            html = fetch(url)
            if not html:
                pbar.update(1); continue
            txt = clean_text(html)
            if len(txt) > 200:
                pages.append((url, txt))
            for l in get_links(url, html):
                if l not in seen:
                    seen.add(l); to_visit.append(l)
            pbar.update(1)
    return pages

def build_index(pages):
    docs, metas = [], []
    for url, txt in pages:
        for c in chunk(txt):
            docs.append(c)
            metas.append({"source": url})
    X = embedder.encode(docs, normalize_embeddings=True, show_progress_bar=True)
    index = faiss.IndexFlatIP(X.shape[1])
    index.add(np.array(X, dtype=np.float32))
    return index, docs, metas

def save(index, docs, metas, path="server/vectordb.faiss"):
    faiss.write_index(index, path)
    with open("server/docs.json","w") as f: json.dump(docs, f)
    with open("server/metas.json","w") as f: json.dump(metas, f)

if __name__ == "__main__":
    pages = crawl()
    index, docs, metas = build_index(pages)
    save(index, docs, metas)
    print(f"Indexed {len(docs)} chunks from {len(pages)} pages.")

try:
    __import__("pysqlite3")
    import sys
    sys.modules["sqlite3"] = sys.modules.pop("pysqlite3")
except ImportError:
    pass

import os
import glob
import json
import time

import streamlit as st
import chromadb
from pypdf import PdfReader
from google import genai
from google.genai import errors as genai_errors
from google.genai import types

# Model names change over time. Check the current ones in Google AI Studio.
EMBED_MODEL = "gemini-embedding-001"
LLM_MODEL = "gemini-3.8-flash"

st.set_page_config(page_title="My RAG Lab", layout="wide")


def get_key():
    key = os.getenv("GEMINI_API_KEY")
    if key:
        return key
    try:
        return st.secrets["GEMINI_API_KEY"]
    except Exception:
        return None


# ---------- STEP 1: load documents ----------
def load_documents(folder="docs"):
    docs = []
    for path in glob.glob(f"{folder}/*"):
        if path.lower().endswith(".pdf"):
            text = "\n".join((p.extract_text() or "") for p in PdfReader(path).pages)
        elif path.lower().endswith((".txt", ".md")):
            with open(path, encoding="utf-8") as f:
                text = f.read()
        else:
            continue
        docs.append((os.path.basename(path), text))
    return docs


# ---------- STEP 2: chunking ----------
def chunk_text(text, size, overlap):
    words = text.split()
    step = max(size - overlap, 1)
    chunks = []
    for i in range(0, len(words), step):
        chunks.append(" ".join(words[i:i + size]))
        if i + size >= len(words):
            break
    return chunks


# ---------- STEP 3: embeddings (vectorization) ----------
def embed(client, texts, task):
    vectors = []
    for i in range(0, len(texts), 50):
        res = client.models.embed_content(
            model=EMBED_MODEL,
            contents=texts[i:i + 50],
            config=types.EmbedContentConfig(task_type=task),
        )
        vectors += [e.values for e in res.embeddings]
    return vectors


# ---------- STEP 4: vector database ----------
@st.cache_resource(show_spinner="Chunking and embedding your documents...")
def build_index(chunk_size, overlap):
    client = genai.Client(api_key=get_key())
    db = chromadb.Client()
    col = db.get_or_create_collection(
        f"docs_{chunk_size}_{overlap}", metadata={"hnsw:space": "cosine"}
    )
    ids, texts, metas = [], [], []
    for name, text in load_documents():
        for n, chunk in enumerate(chunk_text(text, chunk_size, overlap)):
            ids.append(f"{name}-{n}")
            texts.append(chunk)
            metas.append({"source": name})
    if not texts:
        return None
    col.upsert(
        ids=ids,
        documents=texts,
        metadatas=metas,
        embeddings=embed(client, texts, "RETRIEVAL_DOCUMENT"),
    )
    return col


# ---------- STEP 5: retrieval ----------
def retrieve(col, client, question, k):
    qv = embed(client, [question], "RETRIEVAL_QUERY")
    res = col.query(query_embeddings=qv, n_results=k)
    return list(zip(res["documents"][0], res["metadatas"][0], res["distances"][0]))


# ---------- STEP 6: augmentation + LLM ----------
def generate_with_retry(client, prompt, temperature, tries=4):
    for attempt in range(tries):
        try:
            return client.models.generate_content(
                model=LLM_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(temperature=temperature),
            )
        except genai_errors.ServerError:
            if attempt == tries - 1:
                raise
            time.sleep(2 ** attempt)


def answer(client, question, hits, temperature, strict):
    context = "\n\n".join(
        f"[{i + 1}] ({m['source']}) {d}" for i, (d, m, _) in enumerate(hits)
    )
    if strict:
        rule = 'Answer ONLY from the context below. If the answer is not in the context, say "I don\'t know".'
    else:
        rule = "Answer the question."
    prompt = (
        f"{rule}\nCite the chunk numbers you used, like [1].\n\n"
        f"Context:\n{context}\n\nQuestion: {question}"
    )
    res = generate_with_retry(client, prompt, temperature)
    return res.text, prompt


# ---------- STEP 7: the screen the user sees ----------
st.title("My RAG Lab")

with st.sidebar:
    st.header("Parameters")
    chunk_size = st.slider("Chunk size (words)", 20, 400, 120, 10)
    overlap = st.slider("Overlap (words)", 0, 100, 20, 5)
    top_k = st.slider("Top-k chunks retrieved", 1, 10, 3)
    temperature = st.slider("Temperature", 0.0, 2.0, 0.2, 0.1)
    strict = st.checkbox("Strict mode (say I don't know)", True)
overlap = min(overlap, chunk_size - 1)

if not get_key():
    st.error("No GEMINI_API_KEY found. Add it to .streamlit/secrets.toml (see the guide).")
    st.stop()

col = build_index(chunk_size, overlap)
if col is None:
    st.warning("Put some .pdf, .txt or .md files inside the docs/ folder, then refresh.")
    st.stop()

st.caption(f"{col.count()} chunks indexed with chunk size {chunk_size} and overlap {overlap}")

question = st.text_input("Ask a question about your documents")
if question:
    client = genai.Client(api_key=get_key())

    t0 = time.time()
    hits = retrieve(col, client, question, top_k)
    t1 = time.time()
    try:
        text, prompt = answer(client, question, hits, temperature, strict)
    except genai_errors.ServerError:
        st.error("Google's model is busy right now. Wait a minute and ask again.")
        st.stop()
    t2 = time.time()

    st.subheader("Answer")
    st.write(text)

    c1, c2, c3 = st.columns(3)
    c1.metric("Retrieval time", f"{t1 - t0:.2f}s")
    c2.metric("LLM time", f"{t2 - t1:.2f}s")
    c3.metric("Prompt size (words)", len(prompt.split()))

    with st.expander("Retrieved chunks (what the LLM actually saw)", expanded=True):
        for i, (d, m, dist) in enumerate(hits, 1):
            st.markdown(f"**[{i}] {m['source']}**  distance {dist:.3f} (lower = closer)")
            st.write(d)

    with st.expander("Full prompt sent to the LLM"):
        st.code(prompt)

    # simple observability: one line per question in logs.jsonl
    with open("logs.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps({
            "time": time.strftime("%Y-%m-%d %H:%M:%S"),
            "question": question,
            "chunk_size": chunk_size,
            "overlap": overlap,
            "top_k": top_k,
            "temperature": temperature,
            "strict": strict,
            "retrieval_s": round(t1 - t0, 2),
            "llm_s": round(t2 - t1, 2),
            "chunks": [{"source": m["source"], "distance": round(dist, 3)} for _, m, dist in hits],
            "answer": text,
        }) + "\n")

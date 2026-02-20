import os
import pickle
import faiss
from sentence_transformers import SentenceTransformer
from typing import List, Dict

# ----------------------
# Paths (adapted to your structure)
# ----------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(BASE_DIR, "data", "ppc_text.txt")
FAISS_INDEX = os.path.join(BASE_DIR, "data", "ppc_index.faiss")
EMBEDDINGS_FILE = os.path.join(BASE_DIR, "data", "embeddings.pkl")

# ----------------------
# Embedding Model
# ----------------------
MODEL_NAME = "all-MiniLM-L6-v2"
embedder = SentenceTransformer(MODEL_NAME)

# ----------------------
# Text Chunking
# ----------------------
def split_text_into_chunks(text: str, chunk_size: int = 500) -> List[str]:
    """
    Split large text into chunks for retrieval.
    """
    paragraphs = text.split("\n")
    chunks = []
    buffer = ""

    for para in paragraphs:
        if len(buffer) + len(para) < chunk_size:
            buffer += " " + para
        else:
            chunks.append(buffer.strip())
            buffer = para

    if buffer:
        chunks.append(buffer.strip())

    return chunks

# ----------------------
# Load Legal Documents
# ----------------------
def load_legal_documents() -> List[str]:
    if os.path.exists(DATA_PATH):
        print("✅ Loading PPC dataset...")
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            text = f.read()
        chunks = split_text_into_chunks(text)
        print(f"Loaded {len(chunks)} chunks")
        return chunks
    raise FileNotFoundError(f"{DATA_PATH} not found. Please add the dataset.")

# ----------------------
# FAISS Index
# ----------------------
def build_faiss_index(chunks: List[str]):
    embeddings = embedder.encode(chunks, show_progress_bar=True)
    dim = embeddings.shape[1]
    index = faiss.IndexFlatL2(dim)
    index.add(embeddings)
    print(f"✅ FAISS index built with {len(chunks)} vectors")
    # Save for future
    faiss.write_index(index, FAISS_INDEX)
    with open(EMBEDDINGS_FILE, "wb") as f:
        pickle.dump(chunks, f)
    return index, chunks

def load_faiss_index():
    if os.path.exists(FAISS_INDEX) and os.path.exists(EMBEDDINGS_FILE):
        print("⚡ Loading cached FAISS index...")
        index = faiss.read_index(FAISS_INDEX)
        with open(EMBEDDINGS_FILE, "rb") as f:
            chunks = pickle.load(f)
        return index, chunks
    return None, None

# ----------------------
# Retrieval Function
# ----------------------
def retrieve_relevant_sections(query: str, index, chunks: List[str], top_k: int = 3) -> List[str]:
    query_embedding = embedder.encode([query])
    D, I = index.search(query_embedding, top_k)
    return [chunks[i] for i in I[0]]

# ----------------------
# FIR Generation
# ----------------------
def generate_fir(vision_output: Dict) -> Dict:
    """
    vision_output: dict returned from vision.py
    Returns FIR in English and Urdu
    """
    index, chunks = load_faiss_index()
    if index is None:
        print("⚠️ FAISS index not found, building from scratch...")
        chunks = load_legal_documents()
        index, chunks = build_faiss_index(chunks)

    summary_text = vision_output.get("summary", "")
    incident_type = vision_output.get("incident_type", "")
    location = vision_output.get("location", "")

    # Retrieve relevant legal sections
    relevant_sections = retrieve_relevant_sections(summary_text, index, chunks)

    # Build FIR text
    fir_en = f"===== FIR ENGLISH =====\n\n"
    fir_en += f"Incident Type:\n{incident_type}\n\n"
    fir_en += f"Complainant Statement:\n{summary_text}\n\n"
    fir_en += "Relevant Legal References (Preliminary):\n"
    for sec in relevant_sections:
        fir_en += f"- {sec}\n"
    fir_en += "\nThis document is AI-generated and subject to verification by legal authorities.\n"

    fir_ur = f"===== FIR URDU =====\n\n"
    fir_ur += f"واقعہ کی نوعیت:\n{incident_type}\n\n"
    fir_ur += f"بیان:\n{summary_text}\n\n"
    fir_ur += "متعلقہ قانونی حوالہ جات:\n"
    for sec in relevant_sections:
        fir_ur += f"- {sec}\n"
    fir_ur += "\nیہ رپورٹ ابتدائی نوعیت کی ہے اور قانونی تصدیق سے مشروط ہے۔\n"

    return {"english": fir_en, "urdu": fir_ur}

# ----------------------
# Test Runner
# ----------------------
if __name__ == "__main__":
    fake_vision_output = {
        "incident_type": "Theft",
        "location": "Karachi",
        "summary": "A man snatched a mobile phone from another individual and fled on a motorcycle."
    }

    fir = generate_fir(fake_vision_output)
    print(fir["english"])
    print(fir["urdu"])
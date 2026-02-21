import os
import faiss
import pickle
from dotenv import load_dotenv
from typing import Dict
from sentence_transformers import SentenceTransformer
from groq import Groq

# 1. Environment variables load karein (.env file se)
load_dotenv()

# 2. Configuration
LLM_MODEL = "llama-3.3-70b-versatile"
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

# 3. Models aur Client ko initialize karein
print("🚀 Initializing CourtReady RAG Engine...")
embedder = SentenceTransformer(EMBEDDING_MODEL)
llm = Groq(api_key=os.getenv("GROQ_API_KEY"))

def load_legal_index():
    """Local FAISS index aur metadata load karne ke liye"""
    index_path = "data/ppc_index.faiss"
    pkl_path = "data/embeddings.pkl"
    
    if not os.path.exists(index_path) or not os.path.exists(pkl_path):
        raise FileNotFoundError("Legal index files missing in /data folder. Run data_builder.py first.")
        
    index = faiss.read_index(index_path)
    with open(pkl_path, "rb") as f:
        metadata = pickle.load(f)
    return index, metadata

def retrieve_sections(query: str, top_k: int = 3):
    """Sawal ke mutabiq PPC ki sections talash karein"""
    index, metadata = load_legal_index()
    query_vector = embedder.encode([query])
    distances, indices = index.search(query_vector, top_k)
    return [metadata[i] for i in indices[0]]

def generate_fir(vision_json: Dict) -> str:
    """Vision module ke data se formal FIR draft karein"""
    incident = vision_json.get("incident_type", "Unknown")
    summary = vision_json.get("summary", "")
    
    # Relevant laws nikalna
    legal_context = retrieve_sections(f"{incident} {summary}")
    
    # High-quality Legal Prompt
    prompt = f"""
    You are an expert Moharrir (Police Clerk) at a Pakistani Police Station. 
    Draft a formal FIR (First Information Report) based on the incident details.

    INCIDENT: {incident}
    SUMMARY: {summary}
    LEGAL CONTEXT (PPC): {legal_context}

    STRICT FORMATTING RULES:
    1. First, provide the English Version under the heading '### ENGLISH VERSION'.
    2. Second, provide the Urdu Version under the heading '### URDU VERSION'.
    3. Do NOT mix scripts. Urdu must be in pure Perso-Arabic script.

    URDU STYLE:
    - Start with 'بخدمت جناب ایس ایچ او صاحب'
    - Use formal 'Bayan' (Narrative) style (e.g., 'مسمی', 'باعرض ہے کہ', 'وقوعہ').
    - Strictly NO Hindi or Cyrillic characters.
    - Cite the relevant PPC sections (e.g., {legal_context}) within the story.

    ENGLISH STYLE:
    - Formal Pakistani legal English.
    """

    response = llm.chat.completions.create(
        model=LLM_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1  # Consistency ke liye low temperature
    )
    
    return response.choices[0].message.content

# 4. Local Test Block (Safe to keep)
if __name__ == "__main__":
    # Test dictionary jo vision.py se milta julta hai
    test_input = {
        "incident_type": "Snatching",
        "summary": "Two armed men on a motorcycle snatched a phone and cash at gunpoint in Gulberg."
    }
    
    try:
        final_report = generate_fir(test_input)
        print("\n" + "="*50)
        print(final_report)
        print("="*50)
        
        # Test output ko file mein save karein (Urdu check karne ke liye)
        with open("test_fir_output.txt", "w", encoding="utf-8") as f:
            f.write(final_report)
        print("\n✅ FIR drafted and saved to 'test_fir_output.txt'")
        
    except Exception as e:
        print(f"❌ Error occurred: {e}")
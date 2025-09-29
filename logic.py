import os
import time
import tempfile
import streamlit as st

from langchain_community.vectorstores import FAISS
from langchain_community.document_loaders import (PyPDFLoader, TextLoader, CSVLoader, JSONLoader, Docx2txtLoader, UnstructuredExcelLoader)
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.prompts import PromptTemplate
from langchain.chains import RetrievalQA
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.llms import Ollama
import whisper
from gtts import gTTS

try:
    import sounddevice as sd
    from scipy.io.wavfile import write as wav_write
except Exception:
    sd = None

from settings import DATA_FOLDER, VECTOR_STORE_PATH, WHISPER_MODEL_NAME, TTS_LANG

@st.cache_resource
def get_embeddings():
    """Get HuggingFace embeddings model"""
    return HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

@st.cache_resource
def get_llm():
    """Get Ollama LLM instance"""
    return Ollama(model="mistral")

@st.cache_resource
def load_whisper_model():
    """Load Whisper model for speech recognition"""
    return whisper.load_model(WHISPER_MODEL_NAME)

llm = get_llm()

QA_PROMPT = """
You are a helpful medical AI assistant. Answer the question using ONLY the provided context. Structure your response professionally using the following guidelines:

1. Start with a clear, direct answer and the most important point is to keep it crisp and concise no needed for long answers.
2. Use paragraphs to separate different concepts or aspects
3. Use bullet points (•) for a better structed response(can also use for listing out certains points like what drugs to use, what are the precautions to be taken etc).
4. The bullet points should always be in new like and not like this : ex:-• Wash the affected area with mild soap and water to clean the bite site. • Apply calamine lotion or
instead it should be like this 
• hi 
• hello 
5. Use bold text for important terms or headings
6. Keep responses precise and medically accurate
7. If the question has multiple parts, address each in separate paragraphs

If the answer is not in the context, reply with: "I don't have enough information in my knowledge base to answer this question accurately. Please consult a healthcare professional."

Context:
{context}

Question:
{question}

Answer:
"""
prompt_template = PromptTemplate(template=QA_PROMPT, input_variables=["context", "question"])

LOADER_MAP = {
    ".pdf": PyPDFLoader,
    ".txt": TextLoader,
    ".sql": TextLoader,
    ".csv": CSVLoader,
    ".doc": Docx2txtLoader,
    ".json": lambda path: JSONLoader(file_path=path, jq_schema=".[]", text_content=False),
    ".xlsx": lambda path: UnstructuredExcelLoader(path, mode="elements"),
    ".xls": lambda path: UnstructuredExcelLoader(path, mode="elements"),
}

def load_documents():
    """Load documents from the data folder"""
    if not os.path.exists(DATA_FOLDER):
        return []

    documents = []
    for file in os.listdir(DATA_FOLDER):
        ext = os.path.splitext(file)[1].lower()
        loader_class = LOADER_MAP.get(ext)
        if not loader_class:
            continue
        try:
            loader = loader_class(os.path.join(DATA_FOLDER, file))
            documents.extend(loader.load())
        except Exception as e:
            st.warning(f"Could not load {file}: {str(e)}")
            continue
    return documents

def create_vector_store():
    """Create a new vector store from documents"""
    documents = load_documents()
    if not documents:
        st.error("No documents found in data/ folder")
        return None

    splitter = RecursiveCharacterTextSplitter(
        separators=["\n\n", "\n", ".", " ", ""],
        chunk_size=1000,
        chunk_overlap=200
    )
    chunks = splitter.split_documents(documents)
    vectorstore = FAISS.from_documents(chunks, get_embeddings())
    vectorstore.save_local(VECTOR_STORE_PATH)
    return vectorstore

def load_or_create_vector_store():
    """Load existing vector store or create new one"""
    if os.path.exists(VECTOR_STORE_PATH):
        try:
            return FAISS.load_local(
                VECTOR_STORE_PATH, get_embeddings(), allow_dangerous_deserialization=True
            )
        except Exception as e:
            st.warning(f"Could not load existing vector store: {str(e)}. Creating new one...")
            return create_vector_store()
    return create_vector_store()

def transcribe_file_to_text(file_path):
    """Transcribe audio file to text using Whisper"""
    try:
        model = load_whisper_model()
        result = model.transcribe(file_path, language="en")
        return result.get("text", "").strip()
    except Exception as e:
        st.error(f"Transcription failed: {str(e)}")
        return ""

def generate_tts_audio(text, lang=TTS_LANG):
    """Generate TTS audio and return the file path"""
    if not text:
        return None
    try:
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
            gTTS(text=text, lang=lang).save(tmp.name)
            return tmp.name
    except Exception as e:
        st.error(f"TTS generation failed: {str(e)}")
        return None

def record_on_server(seconds, samplerate=44100):
    """Record audio from server microphone"""
    if sd is None:
        st.error("Server-side recording not available.")
        return None
    
    try:
        with st.spinner(f"Recording {seconds}s from server mic..."):
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                tmp_path = tmp.name
            recording = sd.rec(int(seconds * samplerate), samplerate=samplerate, channels=1, dtype="int16")
            sd.wait()
            wav_write(tmp_path, samplerate, recording)
            return tmp_path
    except Exception as e:
        st.error(f"Recording failed: {str(e)}")
        return None

def run_qa_and_respond(query_text):
    """Run QA chain and return response"""
    try:
        retriever = st.session_state.vectorstore.as_retriever(search_kwargs={"k": 3})
        qa_chain = RetrievalQA.from_chain_type(
            llm=llm, retriever=retriever, chain_type="stuff",
            chain_type_kwargs={"prompt": prompt_template}
        )
        start = time.time()
        response = qa_chain.run(query_text)
        elapsed = time.time() - start
        return response, elapsed
    
    except Exception as e:
        st.error(f"QA processing failed: {str(e)}")
        return "I'm sorry, I encountered an error while processing your question.", 0
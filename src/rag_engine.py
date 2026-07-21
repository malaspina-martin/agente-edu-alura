import os
import json
from typing import List, Dict, Any

import google.generativeai as genai
from langchain_community.document_loaders import TextLoader
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import FastEmbedEmbeddings

DATA_DIR = "./data"
DB_DIR = "./chroma_db"

def get_embeddings():
    """Genera embeddings locales ultra ligeros."""
    return FastEmbedEmbeddings(model_name="BAAI/bge-small-en-v1.5")

def load_documents() -> List[Document]:
    """Carga documentos desde la carpeta data procesando múltiples formatos."""
    docs = []
    
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)
        
    for file in os.listdir(DATA_DIR):
        file_path = os.path.join(DATA_DIR, file)
        
        # Procesar Markdown, HTML y Textos
        if file.endswith((".md", ".txt", ".html")):
            loader = TextLoader(file_path, encoding="utf-8")
            loaded = loader.load()
            for d in loaded:
                d.metadata["file_name"] = file
            docs.extend(loaded)
            
        # Procesar JSON
        elif file.endswith(".json"):
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                for idx, item in enumerate(data):
                    content = f"Pregunta: {item.get('pregunta', '')}\nRespuesta: {item.get('respuesta', '')}"
                    metadata = {
                        "file_name": file,
                        "categoria": item.get("categoria", "General"),
                        "responsable": item.get("responsable", "Desconocido")
                    }
                    docs.append(Document(page_content=content, metadata=metadata))
                    
    return docs

def init_vector_store():
    """Genera los chunks y guarda los embeddings en la base vectorial Chroma."""
    docs = load_documents()
    
    if not docs:
        raise ValueError("No se encontraron documentos en la carpeta './data'. Añade archivos antes de consultar.")
    
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50
    )
    chunks = text_splitter.split_documents(docs)
    
    vector_store = Chroma.from_documents(
        documents=chunks,
        embedding=get_embeddings(),
        persist_directory=DB_DIR
    )
    return vector_store

def get_rag_chain():
    """Configura el motor RAG utilizando el SDK Oficial de Google GenAI para evitar 404s."""
    embeddings = get_embeddings()
    
    if not os.path.exists(DB_DIR) or not os.listdir(DB_DIR):
        vector_store = init_vector_store()
    else:
        vector_store = Chroma(
            persist_directory=DB_DIR,
            embedding_function=embeddings
        )
        
    retriever = vector_store.as_retriever(search_kwargs={"k": 3})
    
    def answer_query(query: str) -> Dict[str, Any]:
        matched_docs = retriever.invoke(query)
        
        if not matched_docs:
            return {
                "answer": "No encontré esta información en los documentos disponibles.",
                "sources": []
            }
            
        context_str = "\n\n".join([f"--- Documento: {d.metadata.get('file_name', 'Desconocido')} ---\n{d.page_content}" for d in matched_docs])
        
        prompt = f"""
        Eres el Agente Virtual de Atención al Colaborador y Estudiante de EduTech Academy.
        Tu objetivo es responder consultas institucionales basándote EXCLUSIVAMENTE en el contexto proporcionado.
        
        Instrucciones estrictas:
        1. Si la respuesta no está contenida en el contexto, di claramente: "No encontré esta información en los documentos disponibles. Por favor, ponte en contacto con la Secretaría Académica o Soporte Técnico."
        2. Mantén un tono cordial, profesional y corporativo.
        3. Cita siempre el documento fuente de donde extrajiste la información al final de tu respuesta.

        Contexto recuperado:
        {context_str}

        Pregunta del usuario:
        {query}

        Respuesta:
        """
        
        # Invocación directa con el SDK Oficial de Google Gemini
        api_key = os.environ.get("GOOGLE_API_KEY")
        genai.configure(api_key=api_key)

        MODEL_NAME = 'gemini-2.5-flash'
        
        model = genai.GenerativeModel(MODEL_NAME)
        response = model.generate_content(prompt)
        
        sources = list(set([d.metadata.get("file_name", "Desconocido") for d in matched_docs]))
        
        return {
            "answer": response.text,
            "sources": sources
        }
        
    return answer_query
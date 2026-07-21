import streamlit as st
import os

from rag_engine import get_rag_chain

st.set_page_config(
    page_title="EduTech Agent - Asistente Corporativo",
    page_icon="🎓",
    layout="centered"
)

st.title("🎓 Agente de IA EduTech Academy")
st.caption("Asistente corporativo para colaboradores y estudiantes basándonos en la Base de Conocimiento oficial.")

# Configuración de la API Key de Google
if "GOOGLE_API_KEY" not in os.environ:
    api_key = st.sidebar.text_input("Ingresa tu Gemini API Key:", type="password")
    if api_key:
        os.environ["GOOGLE_API_KEY"] = api_key
    else:
        st.info("💡 Para comenzar, ingresa tu API Key de Google Gemini en el menú lateral.")
        st.stop()

# Inicializar historial de chat
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "¡Hola! Soy el agente institucional de EduTech. ¿En qué puedo ayudarte hoy?"}
    ]

# Mostrar mensajes anteriores
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Capturar pregunta del usuario
if user_input := st.chat_input("Escribe tu pregunta sobre políticas, cursos, becas..."):
    # Guardar y mostrar pregunta
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    # Procesar respuesta
    with st.chat_message("assistant"):
        with st.spinner("Buscando en la base de datos..."):
            try:
                rag_func = get_rag_chain()
                res = rag_func(user_input)
                
                answer = res["answer"]
                sources = res["sources"]
                
                # Formatear fuentes
                if sources:
                    sources_str = "\n\n**📌 Documentos consultados:** " + ", ".join([f"`{s}`" for s in sources])
                    full_response = answer + sources_str
                else:
                    full_response = answer
                    
                st.markdown(full_response)
                
                # Guardar respuesta
                st.session_state.messages.append({"role": "assistant", "content": full_response})
            except Exception as e:
                st.error(f"Ocurrió un error al procesar la solicitud: {e}")
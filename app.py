import streamlit as st
import os
from ui import (render_header_and_styles, render_chat_history, render_chat_input,add_user_message, add_bot_message, show_response_info, cleanup_audio_files)
from logic import(load_or_create_vector_store, run_qa_and_respond, record_on_server, transcribe_file_to_text, generate_tts_audio)
from settings import SERVER_RECORD_SECONDS, SOUND_DEVICE_AVAILABLE

if "vectorstore" not in st.session_state:
    st.session_state.vectorstore = None
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "processing" not in st.session_state:
    st.session_state.processing = False

render_header_and_styles()

if st.session_state.vectorstore is None:
    with st.spinner("Loading / Creating vector store..."):
        st.session_state.vectorstore = load_or_create_vector_store()
    if st.session_state.vectorstore:
        st.success("Vector store ready!")
    else:
        st.error("Failed to initialize vector store. Please check your data folder.")
        st.stop()

chat_container = st.container()

with chat_container:
    render_chat_history()

user_input, mic_clicked = render_chat_input()

if st.session_state.processing:
    with st.spinner("Thinking..."):
        st.empty()

if user_input and user_input.strip() and not st.session_state.processing:
    add_user_message(user_input.strip())
    st.session_state.processing = True
    st.rerun()

elif mic_clicked and SOUND_DEVICE_AVAILABLE and not st.session_state.processing:
    recorded_path = record_on_server(SERVER_RECORD_SECONDS)
    if recorded_path:
        st.success("Recording completed!")
        st.audio(recorded_path)
        with st.spinner("Transcribing..."):
            transcribed_text = transcribe_file_to_text(recorded_path)

        try:
            os.remove(recorded_path)
        except Exception:
            pass
        
        if transcribed_text:
            st.success("Transcription completed!")
            st.write(f"**Transcribed text:** {transcribed_text}")
            add_user_message(transcribed_text)
            st.session_state.processing = True
            st.rerun()
        else:
            st.error("Could not transcribe audio. Please try again.")

elif mic_clicked and not SOUND_DEVICE_AVAILABLE:
    st.error("Voice recording is not available on this server.")

if st.session_state.processing and len(st.session_state.chat_history) > 0:
    latest_message = st.session_state.chat_history[-1]
    if latest_message["role"] == "user":
        user_question = latest_message["content"]
        response, response_time = run_qa_and_respond(user_question)
        clean_text = response.replace("**", "").replace("*", "").replace("#", "")
        audio_path = generate_tts_audio(clean_text)
        add_bot_message(response, response_time, audio_path=audio_path)

        st.session_state.processing = False
        show_response_info(response_time)
        st.rerun()

# Sidebar
with st.sidebar:
    st.header("📊 System Information")
    if st.session_state.vectorstore:
        st.success("✅ Vector store loaded")
    else:
        st.error("❌ Vector store not available")
    if SOUND_DEVICE_AVAILABLE:
        st.success("🎙️ Voice input available")
    else:
        st.warning("🎙️ Voice input unavailable")
    st.header("📁 Data Management")
    
    uploaded_files = st.file_uploader("Upload documents",
        type=['pdf', 'txt', 'csv', 'json', 'doc', 'docx', 'xlsx', 'xls'],
        accept_multiple_files=True)
    
    if uploaded_files:
        if st.button("Process uploaded files"):
            os.makedirs("data", exist_ok=True)
            for uploaded_file in uploaded_files:
                file_path = os.path.join("data", uploaded_file.name)
                with open(file_path, "wb") as f:
                    f.write(uploaded_file.read())
            st.success(f"Uploaded {len(uploaded_files)} files!")
            with st.spinner("Rebuilding vector store..."):
                st.session_state.vectorstore = load_or_create_vector_store()
            if st.session_state.vectorstore:
                st.success("Vector store updated!")
            else:
                st.error("Failed to update vector store.")
    if os.path.exists("data"):
        files = os.listdir("data")
        if files:
            st.write("**Documents in data folder:**")
            for file in files:
                st.write(f"- {file}")
        else:
            st.write("No documents in data folder.")
    else:
        st.write("Data folder not found.")
    if st.button("🗑️ Clear Chat History"):
        cleanup_audio_files()
        st.session_state.chat_history = []
        st.session_state.processing = False
        st.rerun()
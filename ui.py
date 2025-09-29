import streamlit as st
import os

def render_header_and_styles():
    """Render the header and custom CSS styles"""
    st.markdown(
        """<h2 style='text-align: center; font-size: 2.2rem; font-family: Arial, sans-serif; margin-bottom: 6px;'>
        🩺 Medical AI Chatbot
        </h2>""", unsafe_allow_html=True
    )
    st.markdown(
        """<div style="padding: 10px; background-color: teal; border-radius: 6px; margin: 8px 0 18px 0; text-align: center;">
        ⚠️ <b>Disclaimer:</b> This chatbot is an AI-based system and may not always provide medically accurate information. 
        Please consult a qualified healthcare professional for medical advice.
        </div>""",
        unsafe_allow_html=True
    )
    st.markdown(
        """
        <style>
        /* Chat container */
        .chat-row {
            display: flex;
            margin: 6px 0;
            width: 100%;
        }
        .chat-row.user {
            justify-content: flex-end; /* Align user to right */
        }
        .chat-row.bot {
            justify-content: flex-start; /* Align bot to left */
        }

        /* User message bubble */
        .user-msg {
            background-color: teal; /* Teal bubble */
            padding: 10px 14px;
            border-radius: 18px 18px 0 18px;
            max-width: 70%;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            font-family: Arial, sans-serif;
            color: #fff;
        }

        /* Bot response - well formatted text style */
        .bot-response {
            background-color: transparent;
            padding: 10px 0;
            max-width: 100%;
            font-family: Arial, sans-serif;
            color: #fff;
            line-height: 1.8;
        }
        
        /* Improved text formatting */
        .bot-response p {
            margin-bottom: 12px;
            text-align: justify;
        }
        
        .bot-response ul {
            margin: 8px 0;
            padding-left: 20px;
        }
        
        .bot-response li {
            margin-bottom: 6px;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

def render_chat_history():
    """Render the chat history with bubbles for user, well-formatted text for bot and autoplays audio if present"""
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    
    for i, chat in enumerate(st.session_state.chat_history):
        if chat["role"] == "user":
            st.markdown(
                f"<div class='chat-row user'><div class='user-msg'>{chat['content']}</div></div>",
                unsafe_allow_html=True
            )
        elif chat["role"] == "bot":
            st.markdown(
                f"<div class='chat-row bot'><div class='bot-response'>{chat['content']}</div></div>",
                unsafe_allow_html=True
            )
            audio_path = chat.get("audio_path")
            if audio_path and os.path.exists(audio_path):
                try:
                    with open(audio_path, "rb") as f:
                        audio_bytes = f.read()
                    st.audio(audio_bytes, format="audio/mp3", start_time=0)
                except Exception as e:
                    st.warning(f"Failed to play audio for message {i}: {e}")

def render_chat_input():
    """Render chat input with microphone button"""
    col1, col2 = st.columns([9, 1])
    
    with col1:
        user_input = st.chat_input("Type your medical question here...", max_chars=1000)
    
    with col2:
        mic_clicked = st.button("🎙️", key="mic_button", help="Record voice message")
    
    return user_input, mic_clicked

def add_user_message(content):
    """Add user message to chat history"""
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    st.session_state.chat_history.append({
        "role": "user", 
        "content": content
    })

def add_bot_message(content, response_time=None, audio_path=None):
    """Add bot message to chat history; if audio_path provided it's stored with the message"""
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    message = {
        "role": "bot",
        "content": content
    }
    if response_time is not None:
        message["response_time"] = response_time
    if audio_path:
        message["audio_path"] = audio_path
    st.session_state.chat_history.append(message)

def stop_all_audio():
    """Stop all currently playing audio (clear any temporary audio markers in session_state)"""
    keys_to_remove = [key for key in list(st.session_state.keys()) if key.startswith("current_audio_")]
    for key in keys_to_remove:
        del st.session_state[key]

def cleanup_audio_files():
    """Delete temporary audio files attached to chat messages to avoid disk buildup"""
    if "chat_history" not in st.session_state:
        return
    for msg in st.session_state.chat_history:
        audio_path = msg.get("audio_path")
        if audio_path and os.path.exists(audio_path):
            try:
                os.remove(audio_path)
            except Exception:
                pass

def show_response_info(response_time):
    """Show response time information"""
    if response_time:
        st.caption(f"Response time: {response_time:.2f} seconds")

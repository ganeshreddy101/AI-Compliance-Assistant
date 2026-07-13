from glob import glob
import os
import streamlit as st
import shutil

from rag_pipeline import (
    generate_answer,
    rebuild_vectorstore,
)

from database import (
    get_chat_titles,
    init_db,
    save_message,
    load_messages,
    get_chat_sessions,
    create_chat,
    update_chat_title,
    delete_chat,
    delete_chat_and_data,
)
init_db()

import re


def create_chat_title(question):

    question = question.lower()

    stop_words = {
        "what", "is", "are", "the", "a", "an",
        "explain", "tell", "me", "about",
        "how", "does", "do", "can",
        "please", "of", "to", "for"
    }

    words = re.findall(r"\b\w+\b", question)

    keywords = [
        word
        for word in words
        if word not in stop_words
    ]

    title = " ".join(
        keywords[:4]
    )

    return title.title() if title else "New Chat"


def load_chat(chat_id):

    st.session_state.chat_id = chat_id

    st.session_state.uploaded_file_names = []

    saved_messages = load_messages(chat_id)

    st.session_state.messages = []

    for role, content in saved_messages:

        st.session_state.messages.append(
            {
                "role": role,
                "content": content
            }
        )


def handle_new_chat():

    chat_count = len(get_chat_titles()) + 1

    new_chat = f"chat_{chat_count:03d}"

    create_chat(new_chat)

    handle_chat_switch(new_chat)


def handle_chat_switch(chat_id):

    load_chat(chat_id)

    st.rerun()


def render_sidebar():

    with st.sidebar:

        # ---------- Chats ----------
        st.subheader("💬 Chats")

        if st.button("➕ New Chat"):
            handle_new_chat()

        chat_titles = get_chat_titles()

        for chat_id, title in chat_titles:

            col1, col2 = st.columns([5, 1])

            with col1:

                if st.button(
                      f"📄 {title}",
                      key=f"chat_{chat_id}"
                ):

                      handle_chat_switch(chat_id)

            with col2:

               if st.button(
                   "🗑️",
                   key=f"delete_{chat_id}"
              ):

                   delete_chat_and_data(chat_id)

                   shutil.rmtree(
                      os.path.join(
                          "storage",
                          chat_id
                      ),
                      ignore_errors=True
                   )

                   remaining_chats = get_chat_titles()

                   if remaining_chats:

                       handle_chat_switch(
                           remaining_chats[0][0]
                       )

                   else:

                        create_chat("chat_001")

                        handle_chat_switch("chat_001")

                   st.rerun()

        st.divider()

        # ---------- Uploaded Documents ----------
        st.subheader("📂 Uploaded Documents")

        pdf_files = glob(
            os.path.join(
                "storage",
                st.session_state.chat_id,
                "documents",
                "*.pdf"
            )
        )

        if pdf_files:

            for pdf in pdf_files:

                col1, col2 = st.columns([5, 1])

                with col1:

                    st.success(
                        os.path.basename(pdf)
                    )

                with col2:

                    if st.button(
                        "🗑️",
                        key=f"delete_{os.path.basename(pdf)}"
                    ):

                        os.remove(pdf)

                        rebuild_vectorstore(
                            st.session_state.chat_id
                        )

                        st.rerun()

        else:

            st.info("No documents uploaded.")

        st.divider()

        # ---------- Upload ----------
        st.header("📤 Document Upload")

        uploaded_files = st.file_uploader(
            "Upload PDF Files",
            type=["pdf"],
            accept_multiple_files=True,
            key=f"uploader_{st.session_state.chat_id}"
        )

    return uploaded_files

# ---------- Session State ----------

if "chat_id" not in st.session_state:

    chat_sessions = get_chat_sessions()
    
    if not chat_sessions:
        create_chat("chat_001")
        st.session_state.chat_id = "chat_001"

    else:

        st.session_state.chat_id = chat_sessions[0]

st.set_page_config(
    page_title="AI Compliance Assistant",
    page_icon="🤖",
    layout="wide"
)

# ---------- Header ----------

st.title("🤖 AI Compliance Assistant")

st.caption(
    "Multi-PDF GenAI RAG System powered by Hybrid Search, Reranking and Qwen"
)

st.divider()

uploaded_files = render_sidebar()

# ---------- Sidebar ----------

if "uploaded_file_names" not in st.session_state:

    st.session_state.uploaded_file_names = []

if uploaded_files:

    chat_folder = os.path.join(
        "storage",
        st.session_state.chat_id,
        "documents"
    )

    current_files = sorted(
        [file.name for file in uploaded_files]
    )

    # Only process when uploaded files change
    if current_files != st.session_state.uploaded_file_names:

        st.session_state.uploaded_file_names = current_files

        os.makedirs(
            chat_folder,
            exist_ok=True
        )

        for uploaded_file in uploaded_files:

            save_path = os.path.join(
                chat_folder,
                uploaded_file.name
            )

            if os.path.exists(save_path):

                continue

            with open(save_path, "wb") as f:

                f.write(
                    uploaded_file.getbuffer()
                )

        rebuild_vectorstore(
            st.session_state.chat_id
        )

        st.success(
            "Documents uploaded successfully."
        )
        
        st.rerun()

# ---------- Session State ----------

if "messages" not in st.session_state:

    saved_messages = load_messages(
        st.session_state.chat_id
    )

    st.session_state.messages = []

    for role, content in saved_messages:

        st.session_state.messages.append(
            {
                "role": role,
                "content": content
            }
        )

#---------- Chat History ----------
for message in st.session_state.messages:

    with st.chat_message(message["role"]):

        st.markdown(message["content"])

        if message["role"] == "assistant":

            if "chunks" in message:

                with st.expander("📚 Retrieved Evidence"):

                    for chunk in message["chunks"]:

                       st.markdown(
                           f"""
            **📄 File:** {os.path.basename(chunk['file'])}

            **📄 Page:** {chunk['page']}
            """
                        )

                       st.code(
                              chunk["content"],
                              language="text"
                       )

                       st.divider()

# ---------- Chat Input ----------
question = st.chat_input(
    "Ask a compliance question..."
)

if question:

    # ---------------- User Message ----------------
 
    st.session_state.messages.append(
        {
            "role": "user",
            "content": question
        }
    )
   
    save_message(
        st.session_state.chat_id,
        "user",
        question
    )

    with st.chat_message("user"):

        st.markdown(question)

    # ---------------- Assistant ----------------
   
    with st.chat_message("assistant"):
        
        with st.spinner(
            "Searching compliance documents..."
        ):
            
            chat_history = ""

            for msg in st.session_state.messages[-6:]:

                chat_history += (
                    f"{msg['role']}: "
                    f"{msg['content']}\n"
                )
            
            response = generate_answer(
                question,
                chat_history,
                st.session_state.chat_id
            )
            answer = response["answer"]
            
            st.markdown(answer)
            
            sources = []

            for doc in response["sources"]:

                sources.append(
                    {
                        "file": doc.metadata.get(
                            "source",
                            "Unknown"
                        ),
                        "page": doc.metadata.get(
                            "page",
                            "Unknown"
                        )
                    }
                )

            if response["chunks"]:

                with st.expander("📚 Retrieved Evidence"):

                    for chunk in response["chunks"]:

                        st.markdown(
                             f"""
            **📄 File:** {os.path.basename(chunk['file'])}

            **📄 Page:** {chunk['page']}
            """
                         )

                        st.code(
                              chunk["content"],
                              language="text"
                        )

                        st.divider()

    # ---------------- Save Assistant ----------------

    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": answer,
            "sources": sources,
            "chunks": response["chunks"]
        }
    )

    save_message(
        st.session_state.chat_id,
        "assistant",
        answer
    )

    

    # ---------------- Generate Title ----------------

    user_messages = [
        msg
        for msg in st.session_state.messages
        if msg["role"] == "user"
    ]

    if len(user_messages) == 1:

       title = create_chat_title(question)

       update_chat_title(
          st.session_state.chat_id,
          title
       )

       st.rerun()
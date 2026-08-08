from glob import glob
import os
from time import time
import streamlit as st
import shutil
import streamlit.components.v1 as components

from components.render_message_card import render_message_card

from rag_pipeline import (
    generate_answer,
    rebuild_vectorstore,
    generate_chat_title,
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

if "open_doc_menu" not in st.session_state:
    st.session_state.open_doc_menu = None

if "open_chat_menu" not in st.session_state:
    st.session_state.open_chat_menu = None

if "editing_chat" not in st.session_state:
    st.session_state.editing_chat = None

import re


def load_css():
    with open("styles/theme.css") as f:
        st.markdown(
            f"<style>{f.read()}</style>",
            unsafe_allow_html=True
        )

load_css()



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

    existing_ids = {
        chat_id
        for chat_id, _ in get_chat_titles()
    }

    counter = 1

    while True:

        new_chat = f"chat_{counter:03d}"

        if new_chat not in existing_ids:
            break

        counter += 1

    create_chat(new_chat)

    load_chat(new_chat)

    # ---------- Clear paperclip UI ----------
    st.session_state.attached_files = []

    st.rerun()


def handle_chat_switch(chat_id):

    load_chat(chat_id)


def render_sidebar():

    with st.sidebar:

        # ---------- New Chat ----------

        if st.button(
            "➕ New Chat",
            key="new_chat",
            use_container_width=True
        ):
            handle_new_chat()

        # ---------- Search ----------

        search_query = st.text_input(
            "",
            placeholder="🔍 Search chats..."
        )

        # ---------- Chat History ----------

        st.markdown("### Chat History")

        chat_titles = get_chat_titles()

        if search_query:

            chat_titles = [
                (chat_id, title)
                for chat_id, title in chat_titles
                if search_query.lower() in title.lower()
            ]


        with st.container(height=280):

            for chat_id, title in chat_titles:


                col1, col2 = st.columns(
                    [9.2, 0.8],
                    vertical_alignment="center"
                )

                with col1:

                    if st.button(
                        f"💬 {title}",
                        key=f"chat_{chat_id}",
                        use_container_width=True,
                        type="secondary"
                    ):
                          handle_chat_switch(chat_id)

                with col2:

                    if st.button(
                          "⋮",
                          type="tertiary",
                         key=f"menu_{chat_id}"
                     ):

                          if st.session_state.open_chat_menu == chat_id:
                             st.session_state.open_chat_menu = None
                          else:
                               st.session_state.open_chat_menu = chat_id

                if st.session_state.open_chat_menu == chat_id:

                 rename_col, delete_col = st.columns(
                       2,
                       gap="small"
                 )

                 with rename_col:

                    if st.button(
                        "Rename",
                        key=f"rename_{chat_id}",
                        use_container_width=True
                    ):
                        st.session_state.editing_chat = chat_id
                        st.rerun()

                 with delete_col:

                      if st.button(
                         "Delete",
                         key=f"delete_{chat_id}",
                         use_container_width=True
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

                if st.session_state.editing_chat == chat_id:

                    new_title = st.text_input(
                        "",
                        value=title,
                        key=f"title_input_{chat_id}"
                    )

                    save_col, cancel_col = st.columns(2)

                    with save_col:

                        if st.button(
                            "Save",
                            key=f"save_{chat_id}",
                            use_container_width=True
                        ):

                            update_chat_title(
                                chat_id,
                                new_title.strip()
                            )

                            st.session_state.editing_chat = None

                            st.rerun()

                    with cancel_col:

                        if st.button(
                            "Cancel",
                            key=f"cancel_{chat_id}",
                            use_container_width=True
                        ):

                            st.session_state.editing_chat = None


                            st.rerun()
           

            st.markdown(
                "<div style='height:0px'></div>",
                unsafe_allow_html=True
            )

        # ---------- Uploaded Documents ----------

        st.subheader("📂 Uploaded Documents")

        pdf_files = sorted(
            glob(
                os.path.join(
                    "storage",
                    st.session_state.chat_id,
                    "documents",
                    "*.pdf"
                )
            )
        )

        if pdf_files:

            for pdf in pdf_files:

                filename = os.path.basename(pdf)

                row = st.container()

                with row:

                    left, right = st.columns(
                        [8.7, 1.3],
                        vertical_alignment="center"
                    )

                    with left:

                        st.markdown(
                            f"📄 {filename}"
                        )

                    with right:

                        if st.button(
                            "🗑️",
                            key=f"delete_pdf_{filename}",
                            use_container_width=True
                        ):

                            os.remove(pdf)

                            rebuild_vectorstore(
                                st.session_state.chat_id
                            )

                            st.rerun()

        uploaded_files = st.file_uploader(
            "",
            type=["pdf"],
            accept_multiple_files=True,
            key=f"sidebar_uploader_{st.session_state.chat_id}",
            label_visibility="collapsed",
        )

        if uploaded_files:

            chat_folder = os.path.join(
                "storage",
                st.session_state.chat_id,
                "documents"
            )

            os.makedirs(
                chat_folder,
                exist_ok=True
            )

            needs_rebuild = False

            for uploaded_file in uploaded_files:

                save_path = os.path.join(
                    chat_folder,
                    uploaded_file.name
                )

                if not os.path.exists(save_path):

                    with open(save_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())

                    needs_rebuild = True

            if needs_rebuild:

                rebuild_vectorstore(
                    st.session_state.chat_id
                )

                st.rerun() 
# ---------- Session State ----------

if "chat_id" not in st.session_state:

    chat_sessions = get_chat_sessions()
    
    if not chat_sessions:

        create_chat("chat_001")

        load_chat("chat_001")

    else:

        st.session_state.chat_id = chat_sessions[0]

if "rebuild_pending" not in st.session_state:
    st.session_state.rebuild_pending = False
    

st.set_page_config(
    page_title="AI Compliance Assistant",
    page_icon="🤖",
    layout="wide"
)

# ---------- Header ----------

col1, col2, col3 = st.columns([1, 8, 1])

with col2:

    st.markdown(
        """
        <div style="text-align:center; padding-top:10px;">

        <h1 style="
            margin-bottom:5px;
            font-size:48px;
            font-weight:700;
        ">
        🤖 AI Compliance Assistant
        </h1>

        <p style="
            color:#9CA3AF;
            font-size:18px;
        ">
        AI-Powered Compliance Intelligence
        </p>
        
        </div>
        """,
        unsafe_allow_html=True
    )

    st.markdown(
        """
        <style>

        section[data-testid="stSidebar"] > div:first-child {
            padding-top: 0rem !important;
        }

        </style>
        """,
        unsafe_allow_html=True
    )

st.divider()

uploaded_files = render_sidebar()

# ---------- Main Chat Container ----------

chat_container = st.container()




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

if "rebuild_pending" not in st.session_state:
        st.session_state.rebuild_pending = False

#---------- Chat History ----------
import html
import uuid

def copy_button(text):

    button_id = f"copy_{uuid.uuid4().hex}"

    safe_text = html.escape(text)

    components.html(
        f"""
<div style="display:flex;justify-content:flex-end;">

<button
id="{button_id}"
style="
background:transparent;
border:none;
cursor:pointer;
padding:8px;
display:flex;
align-items:center;
justify-content:center;
">

<svg id="{button_id}_icon"
xmlns="http://www.w3.org/2000/svg"
width="19"
height="19"
viewBox="0 0 24 24"
fill="none"
stroke="#b3b3b3"
stroke-width="2"
stroke-linecap="round"
stroke-linejoin="round">

<rect x="9" y="9" width="13" height="13" rx="2"></rect>
<path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>

</svg>

</button>

</div>

<script>

const btn=document.getElementById("{button_id}");

btn.onclick=async()=>{{

await navigator.clipboard.writeText(`{safe_text}`);

const icon = document.getElementById("{button_id}_icon");

icon.outerHTML = `
<svg
id="{button_id}_icon"
xmlns="http://www.w3.org/2000/svg"
width="19"
height="19"
viewBox="0 0 24 24"
fill="none"
stroke="#4ade80"
stroke-width="2"
stroke-linecap="round"
stroke-linejoin="round">
<polyline points="20 6 9 17 4 12"></polyline>
</svg>`;

setTimeout(() => {{

document.getElementById("{button_id}_icon").outerHTML = `
<svg
id="{button_id}_icon"
xmlns="http://www.w3.org/2000/svg"
width="19"
height="19"
viewBox="0 0 24 24"
fill="none"
stroke="#b3b3b3"
stroke-width="2"
stroke-linecap="round"
stroke-linejoin="round">

<rect x="9" y="9" width="13" height="13" rx="2"></rect>
<path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>

</svg>`;

}}, 1800);

}}

</script>
""",
        height=42,
    )



with chat_container:

    for message in st.session_state.messages:

        render_message_card(message)


# ---------------- Chat Input ----------------

chat_data = st.chat_input(
    placeholder="Ask a compliance question..."
)


if chat_data:

    question = chat_data



    if uploaded_files:

        chat_folder = os.path.join(
            "storage",
            st.session_state.chat_id,
            "documents"
        )

        os.makedirs(
        chat_folder,
        exist_ok=True
    )

        needs_rebuild = False

        for uploaded_file in uploaded_files:

            save_path = os.path.join(
            chat_folder,
            uploaded_file.name
            )


            with open(save_path, "wb") as f:
                f.write(uploaded_file.getbuffer())

            needs_rebuild = True

        if needs_rebuild:

            rebuild_vectorstore(
                st.session_state.chat_id
            )


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

    chat_titles = dict(get_chat_titles())

    if chat_titles.get(st.session_state.chat_id) == "New Chat":

        title = generate_chat_title(question)

        update_chat_title(
            st.session_state.chat_id,
            title
        )

   
    chat_history = ""

    for msg in st.session_state.messages[-6:]:

      chat_history += (
        f"{msg['role']}: {msg['content']}\n"
    )

    response = generate_answer(
      question,
      chat_history,
      st.session_state.chat_id
    )


    answer = response["answer"]

    metrics = response.get("metrics", {})

    stats = response.get("stats", {})

    sources = []

    for doc in response["sources"]:

       sources.append(
         {
             "file": doc.metadata.get("source", "Unknown"),
             "page": doc.metadata.get("page", "Unknown")
         }
    )
    

    # ---------------- Save Assistant ----------------

    st.session_state.messages.append(
     {
        "role": "assistant",
        "content": answer,
        "sources": sources,
        "chunks": response.get("chunks", []),
        "metrics": metrics,
        "stats": stats,
      }
    )


    save_message(
        st.session_state.chat_id,
        "assistant",
        answer
     )

    st.rerun()

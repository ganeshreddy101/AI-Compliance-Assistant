from glob import glob
import os
import streamlit as st
import shutil
import streamlit.components.v1 as components

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
import re


def load_css():
    with open("styles/theme.css") as f:
        st.markdown(
            f"<style>{f.read()}</style>",
            unsafe_allow_html=True
        )

load_css()


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

        # ---------- Chats ----------
        st.subheader("Chat History")

        if st.button("➕ New Chat"):
            handle_new_chat()

        search_query = st.text_input(
           "",
           placeholder="🔍 Search chats..."
        )    

        chat_titles = get_chat_titles()

        if search_query:
           chat_titles = [
                (chat_id, title)
                for chat_id, title in chat_titles
                if search_query.lower() in title.lower()
            ]

        for chat_id, title in chat_titles:

             with st.container(border=True):

                col1, col2 = st.columns([8, 1])

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
                      key=f"menu_{chat_id}"
                   ):

                       if st.session_state.open_chat_menu == chat_id:
                           st.session_state.open_chat_menu = None
                       else:
                          st.session_state.open_chat_menu = chat_id

                if st.session_state.open_chat_menu == chat_id:

                     if st.button(
                        "🗑️ Delete Chat",
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

        st.divider()


        return None
    
# ---------- Session State ----------

if "chat_id" not in st.session_state:

    chat_sessions = get_chat_sessions()
    
    if not chat_sessions:

        create_chat("chat_001")

        load_chat("chat_001")

    else:

        st.session_state.chat_id = chat_sessions[0]

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

st.divider()

uploaded_files = render_sidebar()

# ---------- Sidebar ----------

if "uploaded_file_names" not in st.session_state:

    st.session_state.uploaded_file_names = []



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
import html
import uuid

def render_copy_button(text):

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


def render_message_card(message, index):

    is_user = message["role"] == "user"

    avatar = "👤" if is_user else "🤖"
    title = "You" if is_user else "AI Assistant"

    with st.container(border=True):

        icon_col, content_col, copy_col = st.columns(
            [1, 16, 1],
            vertical_alignment="top"
        )

        # ---------------- Icon ----------------

        with icon_col:

            st.markdown(
                f"""
<div style="
width:55px;
height:55px;
margin-top:-6px;
display:flex;
justify-content:center;
align-items:center;
background:#111318;
border:1px solid #2d3340;
border-radius:14px;
font-size:24px;
">
{avatar}
</div>
""",
                unsafe_allow_html=True
            )

        # ---------------- Title + Content ----------------

        with content_col:

            st.markdown(
                f"""
<div style="
font-size:22px;
font-weight:600;
color:#d6d6d6;
line-height:1;
margin-top:8px;
margin-bottom:8px;
margin-left:-5px;
">
{title}
</div>
""",
                unsafe_allow_html=True
            )

            st.markdown(
                f"""
<div style="
font-size:16px;
line-height:1.55;
color:#ECECEC;
margin-top:0;
margin-left:-5px;
">
{message["content"]}
</div>
""",
                unsafe_allow_html=True
            )

        # ---------------- Copy Button ----------------

        with copy_col:

            if not is_user:

                render_copy_button(message["content"])

        st.markdown(
            "<div style='height:18px'></div>",
            unsafe_allow_html=True
        )

        # ---------------- Retrieved Evidence ----------------

        if not is_user:

            spacer, content = st.columns([0.8, 16.2])

            with content:

              if "chunks" in message:
 
                  with st.expander("📚 Retrieved Evidence", expanded=False):

                    for i, chunk in enumerate(message["chunks"], start=1):

                        filename = os.path.basename(chunk["file"])
                        page = chunk["page"]

                        with st.container(border=True):

                           left = st.container()

                           with left:

                              st.markdown(
                                  f"""
                    <div style="
                    font-size:15px;
                    font-weight:600;
                    color:#ECECEC;
                    margin-bottom:6px;
                    ">
                    {i}. 📄 {filename}
                    </div>

                    <div style="
                    font-size:13px;
                    color:#A8A8A8;
                    ">
                    Page {page}
                    </div>
                    """,
                                unsafe_allow_html=True
                            )

                        st.markdown(
                            f"""
                    <div style="
                    margin-top:10px;
                    padding:12px;
                    background:#111318;
                    border:1px solid #2C313C;
                    border-radius:10px;
                    font-size:14px;
                    line-height:1.6;
                    color:#CFCFCF;
                    ">
                    {chunk["content"][:350]}...
                    </div>
                    """,
                            unsafe_allow_html=True
                        )

                        st.markdown(
                            "<div style='height:12px'></div>",
                            unsafe_allow_html=True
                        )

        # ---------------- Performance Metrics ----------------

        if not is_user:

            spacer, content = st.columns([0.8, 16.2])

            with content:

               if "metrics" in message:

                  metrics = message.get("metrics", {})
                  stats = message.get("stats", {})

                  with st.expander("📊 Performance Metrics", expanded=False):

                        metrics_cards = [
                            ("⚡", "Retrieval Time", metrics.get("retrieval_ms", 0)),
                            ("🔄", "Reranking Time", metrics.get("reranking_ms", 0)),
                            ("🧠", "LLM Response Time", metrics.get("llm_ms", 0)),
                            ("⏱️", "Total Response Time", metrics.get("total_ms", 0)),
                        ]

                        cols = st.columns(
                            4,
                            gap="small"
                        )

                        for col, (icon, title, value) in zip(cols, metrics_cards):

                            with col:

                                with st.container(border=True):

                                    left, right = st.columns(
                                        [1, 5],
                                        vertical_alignment="center"
                                    )

                                    with left:


                                       st.markdown(
                                          f"""
                    <div style="
                    font-size:22px;
                    text-align:center;
                    padding-top:6px;
                    ">
                    {icon}
                    </div>
                    """,

                                           unsafe_allow_html=True
                                        )

                                    with right:

                                        st.markdown(
                                            f"""

                    <div style="
                    font-size:15px;
                    font-weight:500;
                    color:#C8C8C8;
                    margin-top:2px;
                    ">
                    {title}
                    </div>

                    <div style="
                    font-size:17px;
                    font-weight:700;
                    color:white;
                    margin-top:4px;
                    ">
                    {value:.2f} ms
                    </div>
                    """,

                
                                unsafe_allow_html=True
                            )
                                            
                            st.markdown(
                                "<div style='height:10px'></div>",
                                unsafe_allow_html=True
        )

for i, message in enumerate(st.session_state.messages):

    render_message_card(message, i)


# ---------- Attached Documents ----------

st.markdown(
    """
<style>
.attached-files-row{
    display:flex;
    flex-wrap:nowrap;
    overflow-x:auto;
    overflow-y:hidden;
    gap:10px;
    padding:8px 0 10px 0;
    scrollbar-width:thin;
}

.attached-file{
    flex:0 0 auto;
    display:flex;
    align-items:center;
    gap:8px;
    padding:8px 12px;
    border-radius:12px;
    background:#111318;
    border:1px solid #2d3340;
    color:white;
    font-size:14px;
    white-space:nowrap;
}
</style>
""",
    unsafe_allow_html=True,
)

chips = '<div class="attached-files-row">'

pdf_files = glob(
    os.path.join(
        "storage",
        st.session_state.chat_id,
        "documents",
        "*.pdf"
    )
)

for pdf in pdf_files:

    filename = os.path.basename(pdf)

    chips += f"""
<div class="attached-file">
📄 {filename}
</div>
"""

chips += "</div>"

st.markdown(
    chips,
    unsafe_allow_html=True,
)



    # ---------------- Chat Input ----------------

chat_data = st.chat_input(
    placeholder="Ask a compliance question...",
    accept_file="multiple",
    file_type=["pdf"]
)

if chat_data:

    question = chat_data.text
    uploaded_files = chat_data.files


    # ---------- Process Uploaded PDFs ----------

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
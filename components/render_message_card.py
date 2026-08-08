import os
import streamlit as st

from components.copy_button import copy_button

def render_message_card(message):

    is_user = message["role"] == "user"

    avatar = "👤" if is_user else "🤖"
    title = "You" if is_user else "AI Assistant"

    with st.container(border=True):

        icon_col, content_col = st.columns(
            [0.9, 15.1],
            gap="medium",
            vertical_alignment="top"
        )

        # ---------------- Icon ----------------

        with icon_col:

            st.markdown(
                f"""
<div style="
width:42px;
height:42px;
min-width:42px;
min-height:42px;
margin-top:2px;
flex-shrink:0;
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

            header_left, header_right = st.columns(
                [18, 1],
                vertical_alignment="center"
            )

            with header_left:

                st.markdown(
                    f"""
        <div style="
        font-size:22px;
        font-weight:600;
        color:#61AFEF;
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

            with header_right:

                if not is_user:

                    copy_button(
                        message["content"]
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

                        with st.container():

                            st.markdown(
                                f"**{i}. 📄 {filename}**"
                            )

                            st.caption(
                                f"Page {page}"
                            )

                            st.markdown(
                                f"""
                        <div style="
                        margin-top:12px;
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
                                unsafe_allow_html=True,
                            )

                        st.markdown(
                            "<div style='height:10px'></div>",
                            unsafe_allow_html=True,
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
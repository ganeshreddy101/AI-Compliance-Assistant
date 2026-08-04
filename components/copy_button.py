import streamlit.components.v1 as components
import uuid


def copy_button(text: str):

    button_id = f"copy-{uuid.uuid4().hex}"

    html = f"""
    <div style="display:flex; justify-content:flex-end;">

        <button
            id="{button_id}"
            title="Copy"
            onclick="
                navigator.clipboard.writeText({text!r});
                this.innerHTML='✓';
                setTimeout(()=>this.innerHTML='📋',1200);
            "
            style="
                background:none;
                border:none;
                cursor:pointer;
                font-size:18px;
                color:#9CA3AF;
            "
        >
        📋
        </button>

    </div>
    """

    components.html(html, height=28)
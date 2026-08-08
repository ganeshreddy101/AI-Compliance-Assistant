import streamlit.components.v1 as components
import html
import uuid


def copy_button(text):

    button_id = f"copy_{uuid.uuid4().hex}"

    safe_text = html.escape(text)

    components.html(
        f"""
<!DOCTYPE html>
<html>

<body style="margin:0;padding:0;background:transparent;">

<button
id="{button_id}"
style="
background:none;
border:none;
cursor:pointer;
font-size:18px;
padding:0;
color:#BDBDBD;
"
title="Copy">

📋

</button>

<script>

const btn = document.getElementById("{button_id}");

btn.onclick = async () => {{

    try {{

        await navigator.clipboard.writeText(`{safe_text}`);

        btn.innerHTML = "✓";

        setTimeout(() => {{
            btn.innerHTML = "📋";
        }}, 1200);

    }}

    catch(err) {{

        btn.innerHTML = "⚠";

        setTimeout(() => {{
            btn.innerHTML = "📋";
        }}, 1200);

    }}

}}

</script>

</body>
</html>
""",
        height=28,
    )
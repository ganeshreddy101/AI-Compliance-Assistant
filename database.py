import sqlite3
import os
import sqlite3

def init_db():

    conn = sqlite3.connect(
        "chat_history.db"
    )

    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id TEXT,
            role TEXT,
            content TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    cursor.execute(
       """
       CREATE TABLE IF NOT EXISTS chats (
           chat_id TEXT PRIMARY KEY,
           title TEXT,
           created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    conn.commit()
    conn.close()


def save_message(
    chat_id,
    role,
    content
):

    conn = sqlite3.connect(
        "chat_history.db"
    )

    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO messages (
            chat_id,
            role,
            content
        )
        VALUES (?, ?, ?)
        """,
        (
            chat_id,
            role,
            content
        )
    )

    conn.commit()
    conn.close()


def load_messages(
    chat_id
):

    conn = sqlite3.connect(
        "chat_history.db"
    )

    cursor = conn.cursor()

    cursor.execute(
       """
       SELECT role, content
       FROM messages
       WHERE chat_id = ?
       AND role != 'system'
       ORDER BY id
       """,
       (chat_id,) 
    )

    rows = cursor.fetchall()

    conn.close()

    return rows


def get_chat_sessions():

    conn = sqlite3.connect(
        "chat_history.db"
    )

    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT DISTINCT chat_id
        FROM messages
        ORDER BY chat_id DESC
        """
    )

    rows = cursor.fetchall()

    conn.close()

    return [row[0] for row in rows]

def create_chat(chat_id):

    import os
    import sqlite3

    # Create folders immediately
    os.makedirs(
        os.path.join(
            "storage",
            chat_id,
            "documents"
        ),
        exist_ok=True
    )

    os.makedirs(
        os.path.join(
            "storage",
            chat_id,
            "vectorstore"
        ),
        exist_ok=True
    )

    conn = sqlite3.connect(
        "chat_history.db"
    )

    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO messages (
            chat_id,
            role,
            content
        )
        VALUES (?, ?, ?)
        """,
        (
            chat_id,
            "system",
            "__chat_created__"
        )
    )

    cursor.execute(
         """
         INSERT INTO chats (
             chat_id,
             title
        )
        VALUES (?, ?)
        """,
       (
          chat_id,
          "New Chat"
       )
    )

    conn.commit()
    conn.close()

def update_chat_title(chat_id, title):

    conn = sqlite3.connect(
        "chat_history.db"
    )

    cursor = conn.cursor()

    cursor.execute(
        """
        UPDATE chats
        SET title = ?
        WHERE chat_id = ?
        """,
        (
            title,
            chat_id
        )
    )

    conn.commit()
    conn.close()


def get_chat_titles():

    conn = sqlite3.connect(
        "chat_history.db"
    )

    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT chat_id, title
        FROM chats
        ORDER BY created_at DESC
        """
    )

    rows = cursor.fetchall()

    conn.close()

    return rows

def delete_chat(chat_id):

    conn = sqlite3.connect(
            "chat_history.db"
    )

    cursor = conn.cursor()

    cursor.execute(
           """
           DELETE FROM messages
           WHERE chat_id = ?
           """,
          (chat_id,)
        )

    cursor.execute(
           """
           DELETE FROM chats
           WHERE chat_id = ?
           """,
           (chat_id,)
        )

    conn.commit()
    conn.close()

def delete_chat_and_data(chat_id):

       import sqlite3

       conn = sqlite3.connect(
          "chat_history.db"
       )

       cursor = conn.cursor()

       cursor.execute(
         """
         DELETE FROM messages
         WHERE chat_id = ?
         """,
         (chat_id,)
       )

       cursor.execute(
         """
         DELETE FROM chats
         WHERE chat_id = ?
         """,
         (chat_id,)
       )

       conn.commit()
       conn.close()
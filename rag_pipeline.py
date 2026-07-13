import os
import re
from glob import glob

from dotenv import load_dotenv
from groq import Groq

from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

from langchain_huggingface import HuggingFaceEmbeddings

from langchain_community.vectorstores import FAISS
from langchain_community.retrievers import BM25Retriever
from langchain.retrievers import EnsembleRetriever

from sentence_transformers import CrossEncoder
embedding_model = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2"
)

# Groq API key
load_dotenv()

client = Groq(
    api_key=os.getenv("GROQ_API_KEY")
)

# pdf loading
def load_documents(chat_id):

    docs = []

    pdf_folder = os.path.join(
        "storage",
        chat_id,
        "documents"
    )

    pdf_files = glob(
        os.path.join(
            pdf_folder,
            "*.pdf"
        )
    )

    for pdf_path in pdf_files:

        loader = PyPDFLoader(
            pdf_path
        )

        pdf_docs = loader.load()

        for doc in pdf_docs:

            doc.metadata["source"] = (
                os.path.basename(pdf_path)
            )

        docs.extend(pdf_docs)

    return docs


def load_vectorstore(chat_id):

    embeddings = embedding_model

    vectorstore_path = os.path.join(
        "storage",
        chat_id,
        "vectorstore"
    )

    if not os.path.exists(vectorstore_path):

        return None

    vectorstore = FAISS.load_local(
        vectorstore_path,
        embeddings,
        allow_dangerous_deserialization=True
    )

    return vectorstore


# vector db func
def create_retriever(chat_id):

    global retriever_cache

    if chat_id in retriever_cache:

        return retriever_cache[chat_id]

    docs = load_documents(chat_id)

    if not docs:

        return None

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1200,
        chunk_overlap=200
    )

    split_docs = text_splitter.split_documents(docs)

    vectorstore = load_vectorstore(chat_id)

    if vectorstore is None:

        return None

    faiss_retriever = vectorstore.as_retriever(
        search_kwargs={"k": 10}
    )

    bm25_retriever = BM25Retriever.from_documents(
        split_docs
    )

    bm25_retriever.k = 10

    retriever = EnsembleRetriever(
        retrievers=[
            faiss_retriever,
            bm25_retriever
        ],
        weights=[0.7, 0.3]
    )

    retriever_cache[chat_id] = retriever

    return retriever

# reranker
reranker = CrossEncoder(
    "cross-encoder/ms-marco-MiniLM-L-6-v2"
)

retriever_cache = {}

def rerank_docs(query, docs):

    pairs = [
        (query, doc.page_content)
        for doc in docs
    ]

    scores = reranker.predict(pairs)

    ranked_docs = sorted(
        zip(scores, docs),
        key=lambda x: x[0],
        reverse=True
    )

    return [
        doc
        for _, doc
        in ranked_docs[:5]
    ]

#Guardrail func
def check_context(docs):

    if not docs:
        return False

    context = " ".join(
        [
            doc.page_content
            for doc in docs
        ]
    )

    if len(context.strip()) < 100:
        return False

    return True

#prompt func
def build_prompt(
    context,
    question,
    chat_history=""
):

    prompt = f"""
You are an AI Compliance Assistant.

Rules:
1. Answer ONLY from the provided context.
2. Use previous conversation when needed.
3. Do NOT make up information.
4. If information is not found, say:
   "I could not find this information in the uploaded documents."

Previous Conversation:
{chat_history}

Context:
{context}

Current Question:
{question}

Answer:
"""

    return prompt


# generate answer
def generate_answer(question, chat_history, chat_id):
    print(">>> generate_answer() entered")

    retriever = create_retriever(
    chat_id
    ) 

    if retriever is None:

        return {
           "answer": "Please upload one or more PDF documents first.",
           "sources": []
        }
    
    retrieved_docs = retriever.invoke(
        question
    )
   

    reranked_docs = rerank_docs(
        question,
        retrieved_docs
    )
   

    if not check_context(
        reranked_docs
    ):

        return {
            "answer":
            "I could not find relevant information in the uploaded documents.",
            "sources":[]
        }

    top_docs = reranked_docs[:5]

    context = "\n\n".join(
        [
            doc.page_content
            for doc in top_docs
        ]
    )

    prompt = build_prompt(
        context,
        question, chat_history
    )

    try:

       response = client.chat.completions.create(
           model="qwen/qwen3-32b",
           messages=[
              {
                  "role": "user",
                  "content": prompt
              }
            ],
            temperature=0.1
       )

       answer = response.choices[0].message.content

    except Exception:

        return {
           "answer": (
               "Unable to generate a response right now. "
               "Please try again in a few moments."
            ),
            "sources": []
        }

    answer = re.sub(
        r"<think>.*?</think>",
        "",
        answer,
        flags=re.DOTALL
    ).strip()

    return {
         "answer": answer,
         "sources": reranked_docs[:3],
         "chunks": [
             {
                "file": doc.metadata.get("source", "Unknown"),
                "page": doc.metadata.get("page", "Unknown"),
                "content": doc.page_content
            }
            for doc in reranked_docs[:3]
         ]
    }


def rebuild_vectorstore(chat_id):

    docs = load_documents(chat_id)

    if not docs:

        return False

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1200,
        chunk_overlap=200
    )

    split_docs = text_splitter.split_documents(docs)

    embeddings = embedding_model

    vectorstore_path = os.path.join(
        "storage",
        chat_id,
        "vectorstore"
    )

    import shutil

    if os.path.exists(vectorstore_path):

        shutil.rmtree(vectorstore_path)

    vectorstore = FAISS.from_documents(
        split_docs,
        embeddings
    )

    vectorstore.save_local(
        vectorstore_path
    )
    
    global retriever_cache

    if chat_id in retriever_cache:

        del retriever_cache[chat_id]

    return True
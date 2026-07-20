import time
import os
import re
from glob import glob

from dotenv import load_dotenv
from groq import Groq

import fitz
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from langchain_huggingface import HuggingFaceEmbeddings

from langchain_community.vectorstores import FAISS
from langchain_community.retrievers import BM25Retriever
from langchain.retrievers import EnsembleRetriever

from sentence_transformers import CrossEncoder

STORAGE_DIR = "storage"

embedding_model = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2"
)

load_dotenv()

client = Groq(
    api_key=os.getenv("GROQ_API_KEY")
)

# pdf loading
def load_documents(chat_id):

    docs = []

    pdf_folder = os.path.join(
        STORAGE_DIR,
        chat_id,
        "documents"
    )

    if not os.path.exists(pdf_folder):
        return docs

    for filename in os.listdir(pdf_folder):

        if not filename.endswith(".pdf"):
            continue

        pdf_path = os.path.join(pdf_folder, filename)

        try:

            pdf = fitz.open(pdf_path)

            full_text = ""

            for page_num, page in enumerate(pdf):

                text = page.get_text()

                full_text += f"\n\n--- Page {page_num + 1} ---\n\n{text}"

            pdf.close()

            docs.append(
                Document(
                    page_content=full_text,
                    metadata={
                        "source": filename,
                        "page": 1
                    }
                )
            )

        except Exception as e:

            print(f"Failed to process {filename}: {e}")

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
        search_type="similarity",
        search_kwargs={
          "k": 12
        }
    )

    bm25_retriever = BM25Retriever.from_documents(
        split_docs
    )

    bm25_retriever.k = 12

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
stats_cache = {}

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
       for _, doc in ranked_docs[:5]
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

1. Answer strictly using the retrieved context.
2. If the retrieved context contains information spread across multiple passages, combine all relevant passages into a single coherent answer. Do not treat each passage independently.
3. Do not use external knowledge, prior knowledge, assumptions, or speculation to complete or expand the answer.
4. Only reply:
   "I could not find this information in the uploaded documents."
   if the retrieved context contains no information relevant to the user's question.
5. If the retrieved context partially answers the question, provide the available information instead of stating that the information was not found.
6. Use previous conversation only to understand the user's intent or resolve references (e.g., "that document", "the previous question"). Do not use previous conversation as a source of factual information. Factual answers must come only from the retrieved context.
7. If multiple documents are retrieved, prioritize answering from the document that is most relevant to the user's question. Do not combine information from different documents unless the user explicitly asks for a comparison.
8.If multiple retrieved context passages contain information that answers the user's question, combine all relevant information into a single complete answer while remaining faithful to the retrieved context.

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

    metrics = {}
    total_start = time.perf_counter()

    retriever = create_retriever(
    chat_id
    ) 

    if retriever is None:

        return {
           "answer": "Please upload one or more PDF documents first.",
           "sources": [],
           "chunks": [],
           "metrics": {},
           "stats": {}
        }
    
    retrieval_start = time.perf_counter()
    retrieved_docs = retriever.invoke(question)


    metrics["retrieval_ms"] = round(
       (time.perf_counter() - retrieval_start) * 1000,
       2
    )

    rerank_start = time.perf_counter()
    reranked_docs = retrieved_docs
    
    metrics["reranking_ms"] = round(
        (time.perf_counter() - rerank_start) * 1000,
        2
    )


    if not check_context(
        reranked_docs
    ):

        return {
            "answer":
            "I could not find relevant information in the uploaded documents.",
            "chunks": [],
            "metrics": {},
            "stats": {}
        }

    top_docs = reranked_docs[:12]

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
        llm_start = time.perf_counter()

        model_name = "llama-3.3-70b-versatile"


        response = client.chat.completions.create(
           model=model_name,
           messages=[
              {
                 "role": "user",
                 "content": prompt
              }
            ],
            temperature=0.1
        )

        answer = response.choices[0].message.content
        print("RAW ANSWER:", repr(answer))
    
        import re

        answer = re.sub(
            r"<think>.*?</think>",
            "",
            answer,
            flags=re.DOTALL | re.IGNORECASE,
        )

        if "<think>" in answer.lower():
            answer = re.sub(
              r"<think>.*",
              "",
              answer,
              flags=re.DOTALL | re.IGNORECASE,
            )

        answer = answer.strip()
        print("CLEANED ANSWER:", repr(answer))


        metrics["llm_ms"] = round(
            (time.perf_counter() - llm_start) * 1000,
             2
        )
    except Exception as e:
        import traceback

        print("\n===== LLM ERROR =====")
        traceback.print_exc()
        print("=====================\n")

        return {
           "answer": f"ERROR: {str(e)}",
           "sources": [],
           "chunks": [],
           "metrics": metrics,
           "stats": {}
        }

    answer = re.sub(
        r"<think>.*?</think>",
        "",
        answer,
        flags=re.DOTALL
    ).strip()

    metrics["total_ms"] = round(
        (time.perf_counter() - total_start) * 1000,
        2
    )

    stats = stats_cache.get(chat_id, {})

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
         ],
         "metrics": metrics,
         "stats": stats
    }


def rebuild_vectorstore(chat_id):

    docs = load_documents(chat_id)

    pdf_count = len(glob(os.path.join(
        "storage",
        chat_id,
        "documents",
        "*.pdf"
    )))

    page_count = len(docs)

    if not docs:

        return False

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1200,
        chunk_overlap=200
    )
 
    split_docs = text_splitter.split_documents(docs)

    chunk_count = len(split_docs)

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


    stats_cache[chat_id] = {
       "pdf_count": pdf_count,
       "page_count": page_count,
       "chunk_count": chunk_count
    }
    return True
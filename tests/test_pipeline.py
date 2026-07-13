from rag_pipeline import generate_answer

response = generate_answer(
    "What is the goal of AI RMF?"
)

print("\nANSWER:\n")
print(response["answer"])

print("\nSOURCE:\n")

for doc in response["sources"]:
    print(
        doc.metadata["source"],
        doc.metadata["page"]
    )
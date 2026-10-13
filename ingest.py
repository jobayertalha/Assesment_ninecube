"""Build the FAISS index from the synthetic business Markdown knowledge base."""
from rag import Retriever, build_chunks, load_documents, INDEX_DIR, DEFAULT_MODEL


def main():
    documents = load_documents()
    chunks = build_chunks(documents)
    print(f"Loaded {len(documents)} Markdown documents; created {len(chunks)} chunks.")
    print(f"Embedding model: {DEFAULT_MODEL}")
    print("The first run downloads the embedding model if it is not cached.")
    retriever = Retriever().build(chunks)
    retriever.save()
    print(f"FAISS index saved to {INDEX_DIR}")


if __name__ == "__main__":
    main()

"""RAG-based rules lookup tool."""
from pathlib import Path

from xwing_agent.config import get_settings
from xwing_agent.logging_config import get_logger

logger = get_logger(__name__)
settings = get_settings()


class RulesTool:
    """Tool for looking up X-Wing rules via RAG."""

    def __init__(self):
        self._vectorstore = None
        self._embeddings = None

    def _load_vectorstore(self):
        """Lazy load the vectorstore."""
        if self._vectorstore is not None:
            return

        index_path = settings.rules_index_path
        if index_path.exists():
            try:
                from langchain_community.embeddings import HuggingFaceEmbeddings
                from langchain_community.vectorstores import FAISS

                logger.info(f"Loading rules index from {index_path}")
                self._embeddings = HuggingFaceEmbeddings(
                    model_name="sentence-transformers/all-MiniLM-L6-v2"
                )
                self._vectorstore = FAISS.load_local(
                    str(index_path),
                    self._embeddings,
                    allow_dangerous_deserialization=True,
                )
            except ImportError:
                logger.warning("FAISS or HuggingFace embeddings not available")
            except Exception as e:
                logger.warning(f"Failed to load rules index: {e}")
        else:
            logger.warning("Rules index not found. Run scripts/index_rules.py first.")

    def search(self, query: str, k: int = 3) -> str:
        """Search rules for relevant information."""
        logger.info(f"Rules search: {query}")

        self._load_vectorstore()
        if self._vectorstore is None:
            return "Rules index not available."

        docs = self._vectorstore.similarity_search(query, k=k)

        results = []
        for i, doc in enumerate(docs, 1):
            source = doc.metadata.get("source", "unknown")
            results.append(f"[{i}] From {source}:\n{doc.page_content}")

        return "\n\n".join(results) if results else "No relevant rules found."


def build_rules_index(rules_dir: Path, output_dir: Path):
    """Build the rules vector index from markdown files."""
    from langchain.text_splitter import RecursiveCharacterTextSplitter
    from langchain_community.embeddings import HuggingFaceEmbeddings
    from langchain_community.vectorstores import FAISS

    logger.info(f"Building rules index from {rules_dir}")

    # Load all markdown files
    documents = []
    for md_file in rules_dir.glob("*.md"):
        content = md_file.read_text()
        documents.append(
            {
                "content": content,
                "source": md_file.stem,
            }
        )

    if not documents:
        logger.warning("No rules documents found!")
        return

    # Split into chunks
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50,
        separators=["\n## ", "\n### ", "\n\n", "\n", " "],
    )

    texts = []
    metadatas = []
    for doc in documents:
        chunks = splitter.split_text(doc["content"])
        texts.extend(chunks)
        metadatas.extend([{"source": doc["source"]}] * len(chunks))

    logger.info(f"Split into {len(texts)} chunks")

    # Create embeddings and index
    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    vectorstore = FAISS.from_texts(texts, embeddings, metadatas=metadatas)

    # Save
    output_dir.mkdir(parents=True, exist_ok=True)
    vectorstore.save_local(str(output_dir))
    logger.info(f"Saved index to {output_dir}")

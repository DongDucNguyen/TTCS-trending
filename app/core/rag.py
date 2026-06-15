"""RAG v2 — Improved retrieval with section-aware chunking.

Improvements over rag.py:
  - PyMuPDF4LLM: Markdown extraction (preserves headers, tables, 2-column)
  - Section-aware chunking: splits by actual headers from PDF
  - Metadata: each chunk knows its section name
  - Filters noise: removes References, Appendix sections
  - Adjusted weights: BM25 60% / FAISS 40% (better for technical papers)
"""
from __future__ import annotations

import logging
import re
from pathlib import Path

import requests
import pymupdf4llm
from langchain_core.documents import Document
from langchain_community.vectorstores import FAISS
from langchain_ollama import OllamaEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter


log = logging.getLogger(__name__)

_index_cache_v2: dict[str, tuple] = {}

# Sections to exclude (noise for Q&A)
EXCLUDE_SECTIONS = {"references", "bibliography", "acknowledgment", "acknowledgments", "appendix"}


class PaperRAG:
    """Improved RAG with section-aware chunking and metadata."""

    def __init__(
        self,
        arxiv_id: str,
        base_url: str = "http://localhost:11434",
        model: str = "nomic-embed-text",
    ) -> None:
        self.arxiv_id = arxiv_id
        self.pdf_path = Path("data/papers") / f"{arxiv_id}.pdf"
        self.index_path = Path("data/indices_v2") / arxiv_id
        self.pdf_path.parent.mkdir(parents=True, exist_ok=True)
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        self.embeddings = OllamaEmbeddings(base_url=base_url, model=model)

    # ------------------------------------------------------------------
    # Download
    # ------------------------------------------------------------------

    def download(self) -> None:
        if self.pdf_path.exists():
            return
        url = f"https://arxiv.org/pdf/{self.arxiv_id}.pdf"
        log.info("Downloading PDF: %s", url)
        resp = requests.get(url, stream=True, timeout=60)
        resp.raise_for_status()
        with open(self.pdf_path, "wb") as fh:
            for chunk in resp.iter_content(chunk_size=8192):
                fh.write(chunk)

    # ------------------------------------------------------------------
    # Section-aware chunking
    # ------------------------------------------------------------------

    def _extract_sections(self) -> list[Document]:
        """Extract Markdown from PDF and split by actual headers."""
        md_text = pymupdf4llm.to_markdown(str(self.pdf_path))

        # Split by top-level headers (### or ##)
        raw_sections = re.split(r'(?=^###?\s)', md_text, flags=re.MULTILINE)

        max_chunk = 2000
        sub_splitter = RecursiveCharacterTextSplitter(
            chunk_size=max_chunk,
            chunk_overlap=200,
            separators=["\n\n", "\n", ". ", " "],
        )

        chunks = []
        for section_text in raw_sections:
            section_text = section_text.strip()
            if len(section_text) < 50:
                continue

            # Extract section name from first line
            header_match = re.match(r'^#{1,4}\s+(.+)', section_text)
            section_name = header_match.group(1).strip() if header_match else "Unknown"

            # Clean section name (remove numbering like "3.1." prefix)
            clean_name = re.sub(r'^\d+[\.\d]*\s*', '', section_name)

            # Skip noise sections
            if clean_name.lower() in EXCLUDE_SECTIONS:
                log.debug("Skipping section: %s", section_name)
                continue

            metadata = {
                "section": section_name,
                "section_clean": clean_name,
                "arxiv_id": self.arxiv_id,
            }

            if len(section_text) <= max_chunk:
                chunks.append(Document(page_content=section_text, metadata=metadata))
            else:
                # Section too long → sub-split but keep metadata
                sub_docs = sub_splitter.create_documents(
                    [section_text],
                    metadatas=[metadata],
                )
                chunks.extend(sub_docs)

        log.info("Section-aware chunking: %d sections → %d chunks", len(raw_sections), len(chunks))
        return chunks

    # ------------------------------------------------------------------
    # Build index
    # ------------------------------------------------------------------

    def build(self) -> None:
        self.download()
        if self._index_exists():
            log.info("Index v2 already exists: %s", self.index_path)
            return

        log.info("Building v2 index for %s …", self.arxiv_id)
        chunks = self._extract_sections()

        if not chunks:
            raise ValueError(f"No chunks extracted from {self.pdf_path}")

        vectorstore = FAISS.from_documents(chunks, self.embeddings)
        vectorstore.save_local(str(self.index_path))
        log.info("Index v2 built — %d chunks", len(chunks))

    def _index_exists(self) -> bool:
        return (
            (self.index_path / "index.faiss").exists()
            and (self.index_path / "index.pkl").exists()
        )

    # ------------------------------------------------------------------
    # Load (with cache)
    # ------------------------------------------------------------------

    def _load_index(self) -> tuple:
        if self.arxiv_id in _index_cache_v2:
            return _index_cache_v2[self.arxiv_id]

        log.info("Loading v2 index from disk: %s", self.index_path)
        vectorstore = FAISS.load_local(
            str(self.index_path),
            self.embeddings,
            allow_dangerous_deserialization=True,
        )
        chunks = list(vectorstore.docstore._dict.values())
        _index_cache_v2[self.arxiv_id] = (vectorstore, chunks)
        return vectorstore, chunks

    # ------------------------------------------------------------------
    # Retrieve
    # ------------------------------------------------------------------

    def retrieve(self, query: str, k: int = 4) -> str:
        """FAISS MMR retrieval to avoid Conclusion bias."""
        self.build()
        vectorstore, chunks = self._load_index()

        # Dùng MMR để đa dạng hóa kết quả, tránh bốc trùng Conclusion nhiều lần
        faiss_mmr = vectorstore.as_retriever(
            search_type="mmr", 
            search_kwargs={"k": k, "fetch_k": 20, "lambda_mult": 0.5}
        )
        
        results = faiss_mmr.invoke(query)
        return "\n\n".join(doc.page_content for doc in results[:k])

    def retrieve_docs(self, query: str, k: int = 4) -> list[Document]:
        """FAISS MMR retrieval, returns List[Document] with metadata."""
        self.build()
        vectorstore, chunks = self._load_index()

        faiss_mmr = vectorstore.as_retriever(
            search_type="mmr", 
            search_kwargs={"k": k, "fetch_k": 20, "lambda_mult": 0.5}
        )
        
        return faiss_mmr.invoke(query)[:k]

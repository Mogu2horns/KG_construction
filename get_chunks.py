import json
import re
from typing import List, Dict, Any, Tuple
from pathlib import Path
from langchain_community.document_loaders import DirectoryLoader
from langchain_community.document_loaders import UnstructuredMarkdownLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document


class ProtectedMarkdownTextSplitter(RecursiveCharacterTextSplitter):
    """
    Markdown text splitter that protects LaTeX formulas and HTML tables.
    Inherits from RecursiveCharacterTextSplitter and skips splits inside formulas and tables.
    """

    def __init__(
        self,
        protect_formulas: bool = True,
        protect_tables: bool = True,
        **kwargs: Any
    ):
        """
        :param protect_formulas: Whether to protect LaTeX formulas ($...$ and $$...$$)
        :param protect_tables: Whether to protect HTML tables (<table>...</table>)
        :param kwargs: Arguments passed to RecursiveCharacterTextSplitter (e.g., chunk_size, separators)
        """
        super().__init__(**kwargs)
        self.protect_formulas = protect_formulas
        self.protect_tables = protect_tables

    def _protect_content(self, text: str) -> Tuple[str, Dict[str, str]]:
        """Replace sensitive content with placeholders and return a mapping dict"""
        placeholders: Dict[str, str] = {}
        counter = 0

        def _make_replacer(tag: str):
            def replacer(match):
                nonlocal counter
                key = f"__{tag.upper()}_{counter}__"
                placeholders[key] = match.group(0)
                counter += 1
                return key
            return replacer

        protected_text = text

        # 1. Protect LaTeX display formulas $$...$$ (handle first to avoid conflict with inline)
        if self.protect_formulas:
            protected_text = re.sub(
                r'\$\$(.*?)\$\$',
                _make_replacer("formula"),
                protected_text,
                flags=re.DOTALL
            )
            # 2. Protect LaTeX inline formulas $...$
            protected_text = re.sub(
                r'\$(.*?)\$',
                _make_replacer("formula"),
                protected_text
            )

        # 3. Protect HTML tables
        if self.protect_tables:
            protected_text = re.sub(
                r'<table\b[^>]*>.*?</table>',
                _make_replacer("table"),
                protected_text,
                flags=re.DOTALL | re.IGNORECASE
            )

        return protected_text, placeholders

    def _restore_content(self, text: str, placeholders: Dict[str, str]) -> str:
        """Restore placeholders back to the original content"""
        restored = text
        for placeholder, original in placeholders.items():
            restored = restored.replace(placeholder, original)
        return restored

    def split_text(self, text: str) -> List[str]:
        """
        Override split_text: protect content first, then split, then restore
        """
        # 1. Protect formulas and tables
        clean_text, placeholders = self._protect_content(text)

        # 2. Use parent class logic to split the cleaned text
        clean_chunks = super().split_text(clean_text)

        # 3. Restore each chunk
        restored_chunks = [
            self._restore_content(chunk, placeholders) for chunk in clean_chunks
        ]

        return restored_chunks

    def split_documents(self, documents: List[Document]) -> List[Document]:
        """
        Override split_documents: preserve metadata
        """
        chunks = []
        for doc in documents:
            clean_text, placeholders = self._protect_content(doc.page_content)
            temp_doc = Document(page_content=clean_text, metadata=doc.metadata)
            clean_chunks = super().split_documents([temp_doc])
            for chunk in clean_chunks:
                restored_content = self._restore_content(chunk.page_content, placeholders)
                chunks.append(Document(
                    page_content=restored_content,
                    metadata=chunk.metadata
                ))
        return chunks

if __name__ == "__main__":
    loader = DirectoryLoader(
        path="./data",
        glob="**/*.md",
        loader_cls=UnstructuredMarkdownLoader,
        loader_kwargs={"encoding": "utf-8"}
    )

    docs = loader.load()
    print(f"共加载 {len(docs)} 个文档")

    # 2. Use RecursiveCharacterTextSplitter with separators optimized for Markdown
    splitter = ProtectedMarkdownTextSplitter(
        chunk_size=512,
        chunk_overlap=50,
        separators=[
            "\n\n",        
            "\n# ", "\n## ", "\n### ", "\n####",
            "\n",
            "。", "！", "？", "；",        
            " ",           
            ""             
        ],
        length_function=len,
        is_separator_regex=False
    )

    # 3. Split documents
    chunks = splitter.split_documents(docs)

    # 4. Get JSON output
    output_dir = Path("./chunks_output")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / "relation_chunks.jsonl"
    
    with output_file.open("w", encoding="utf-8") as f:
        for index, chunk in enumerate(chunks):
            # construct a dict for JSON serialization
            record = {
                "chunk_content": chunk.page_content,
                "source":chunk.metadata.get("source", ""),
                "metadata":index
            }
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    
    print(f"√Chunk complete, get {len(chunks)} chunk, save to {output_file}")
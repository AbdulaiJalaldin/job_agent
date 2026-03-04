import fitz  # PyMuPDF
from dataclasses import dataclass
from typing import List
from langchain_text_splitters import RecursiveCharacterTextSplitter


@dataclass
class DocumentData:
    text: str
    metadata: dict


class HandleResumeUpload:
    def __init__(self, chunk_size=1000, chunk_overlap=200):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def process_file(self, file_path: str) -> List[DocumentData]:
        """Process the file and ensure it's a PDF"""
        if file_path.endswith(".pdf"):
            rawtext = self._read_pdf(file_path)
        else:
            raise ValueError("Unsupported file format. Only PDF supported.")

        chunks = self._chunk_text(rawtext)

        structured_chunks = []
        for i, text in enumerate(chunks):
            chunk_obj = DocumentData(
                text=text,
                metadata={
                    "source": file_path,
                    "chunk_index": i,
                    "char_count": len(text),
                },
            )
            structured_chunks.append(chunk_obj)

        return structured_chunks

    def _read_pdf(self, file_path: str) -> str:
        """Extract text from PDF using PyMuPDF"""
        doc = fitz.open(file_path)
        full_text = []

        for page in doc:
            full_text.append(page.get_text())

        return "\n".join(full_text)

    def _chunk_text(self, text: str) -> List[str]:
        """Chunk the text"""
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            length_function=len,
            is_separator_regex=False,
        )
        return text_splitter.split_text(text)
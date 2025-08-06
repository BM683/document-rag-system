import os
from typing import Dict, Any
import PyPDF2
from docx import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter

class DocumentProcessor:
    """Handles reading and processing different document types"""
    
    def read_file_content(self, file_path: str) -> Dict[str, Any]:
        """Read content from different file types"""
        
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        file_extension = os.path.splitext(file_path)[1].lower()
        
        try:
            if file_extension == '.txt':
                content = self._read_txt(file_path)
            elif file_extension == '.pdf':
                content = self._read_pdf(file_path)
            elif file_extension == '.docx':
                content = self._read_docx(file_path)
            else:
                raise ValueError(f"Unsupported file type: {file_extension}")
            
            return {
                "content": content,
                "file_type": file_extension,
                "word_count": len(content.split()),
                "character_count": len(content)
            }
            
        except Exception as e:
            raise Exception(f"Error reading {file_extension} file: {str(e)}")
    
    def _read_txt(self, file_path: str) -> str:
        """Read text file"""
        with open(file_path, 'r', encoding='utf-8') as file:
            return file.read()
    
    def _read_pdf(self, file_path: str) -> str:
        """Read PDF file"""
        text = ""
        with open(file_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
        return text.strip()
    
    def _read_docx(self, file_path: str) -> str:
        """Read Word document"""
        doc = Document(file_path)
        text = ""
        for paragraph in doc.paragraphs:
            text += paragraph.text + "\n"
        return text.strip()

    def chunk_text(self, full_text: str, source_filename: str) -> list[dict]:
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,     # Tune as needed!
            chunk_overlap=200,   # Overlap for context carryover
            separators=["\n\n", "\n", " ", ""]
        )
        chunks = splitter.split_text(full_text)

        chunked_docs = []
        for i, chunk in enumerate(chunks):
            chunked_docs.append({
                "chunk_index": i,
                "text": chunk,
                "source": source_filename,
                "length": len(chunk),
                "token_estimate": len(chunk.split())
            })
        return chunked_docs
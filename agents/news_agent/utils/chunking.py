import pandas as pd
from langchain_core.documents import Document
from langchain_experimental.text_splitter import SemanticChunker

from utils.helpers import to_date_int, to_list


def build_semantic_chunker(embeddings):
    return SemanticChunker(embeddings)


def load_csv_documents(input_path: str) -> list[Document]:
    df = pd.read_csv(input_path)
    docs = []
    for _, row in df.iterrows():
        content = str(row.get("content", ""))
        metadata = {
            "title": str(row.get("title", "")),
            "date": str(row.get("date", "")),
            "date_int": to_date_int(row.get("date", None)),
            "org": to_list(row.get("org", "")),
            "keyword": to_list(row.get("keyword", "")),
            "person": to_list(row.get("person", "")),
            "feature": to_list(row.get("feature", "")),
            "category_main": str(row.get("category_main", "")),
            "category_sub": str(row.get("category_sub", "")),
            "press": str(row.get("press", "")),
            "url": str(row.get("url", "")),
        }
        docs.append(Document(page_content=content, metadata=metadata))
    return docs

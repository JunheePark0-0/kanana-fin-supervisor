from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
from qdrant_client.models import FieldCondition, Filter, MatchAny, MatchText, Range
from typing import Optional


def init_vectorstore(qdrant_path: str, collection_name: str, embeddings):
    client = QdrantClient(path=qdrant_path)
    vector_db = QdrantVectorStore(
        client=client,
        collection_name=collection_name,
        embedding=embeddings,
    )
    sample = client.scroll(
        collection_name=collection_name, limit=1, with_payload=True
    )
    sample_keys = list(sample[0][0].payload.keys()) if sample[0] else []
    prefix = "metadata." if any(k.startswith("metadata.") for k in sample_keys) else ""
    return client, vector_db, prefix


def build_filter(
    prefix="metadata.",
    orgs=None,
    keywords=None,
    persons=None,
    features=None,
    category_main=None,
    category_sub=None,
    date_from=None,
    date_to=None,
) -> Optional[Filter]:
    must = []

    if orgs:
        should = [FieldCondition(key=f"{prefix}org", match=MatchText(text=v)) for v in orgs]
        must.append(Filter(should=should))
    if keywords:
        should = [
            FieldCondition(key=f"{prefix}keyword", match=MatchText(text=v)) for v in keywords
        ]
        must.append(Filter(should=should))
    if persons:
        should = [
            FieldCondition(key=f"{prefix}person", match=MatchText(text=v)) for v in persons
        ]
        must.append(Filter(should=should))
    if features:
        should = [
            FieldCondition(key=f"{prefix}feature", match=MatchText(text=v)) for v in features
        ]
        must.append(Filter(should=should))

    if category_main:
        must.append(
            FieldCondition(
                key=f"{prefix}category_main", match=MatchAny(any=[category_main])
            )
        )
    if category_sub:
        must.append(
            FieldCondition(key=f"{prefix}category_sub", match=MatchAny(any=[category_sub]))
        )

    date_range = {}
    if date_from:
        date_range["gte"] = date_from
    if date_to:
        date_range["lte"] = date_to
    if date_range:
        must.append(FieldCondition(key=f"{prefix}date", range=Range(**date_range)))

    return Filter(must=must) if must else None

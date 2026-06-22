"""
Milvus vector store manager.
Replaces FAISS with Milvus (Docker-based) for scalable vector search.
"""
import os
import time
import json
import logging
from typing import List, Optional, Dict, Any

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_milvus import Milvus
from langchain_milvus.utils.sparse import BM25SparseEmbedding
from pymilvus import connections, utility, Collection, CollectionSchema, FieldSchema, DataType

from backend.core.config import (
    get_embeddings,
    INDEX_DIR,
    BATCH_SIZE,
    RETRY_DELAY,
    MAX_RETRY_DELAY,
    MILVUS_HOST,
    MILVUS_PORT,
    MILVUS_ALIAS,
    MILVUS_COLLECTION_PREFIX,
    logger,
)

from backend.services.doc_processor import get_text_from_any_file


def _get_milvus_connection():
    """Ensure Milvus connection is active."""
    try:
        if not connections.has_connection(MILVUS_ALIAS):
            connections.connect(
                alias=MILVUS_ALIAS,
                host=MILVUS_HOST,
                port=MILVUS_PORT,
            )
            logger.info(f"[Milvus] Connected to {MILVUS_HOST}:{MILVUS_PORT}")
    except Exception as e:
        logger.error(f"[Milvus] Connection failed: {e}")
        raise


def _collection_name(course_id: str) -> str:
    """Get Milvus collection name for a course."""
    return f"{MILVUS_COLLECTION_PREFIX}_{course_id}"


def _drop_collection(course_id: str):
    """Drop a Milvus collection for a course."""
    _get_milvus_connection()
    collection_name = _collection_name(course_id)
    if utility.has_collection(collection_name):
        utility.drop_collection(collection_name)
        logger.info(f"[Milvus] Dropped collection '{collection_name}'")


def create_or_load_milvus(
    course_id: str,
    pdf_path: str,
) -> Milvus:
    """
    Create a new Milvus vector store from a PDF, or load an existing one.
    
    Args:
        course_id: Unique course identifier.
        pdf_path: Path to the PDF/DOCX/TXT file.
    
    Returns:
        Milvus vector store instance.
    """
    _get_milvus_connection()
    collection_name = _collection_name(course_id)
    embeddings = get_embeddings()

    # Check if collection already exists
    if utility.has_collection(collection_name):
        logger.info(f"[Course {course_id}] Found existing Milvus collection, loading...")
        return Milvus(
            embedding_function=embeddings,
            collection_name=collection_name,
            connection_args={"alias": MILVUS_ALIAS},
        )

    logger.info(f"[Course {course_id}] Building new vectorstore from file...")
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"File not found: {pdf_path}")

    valid_docs = get_text_from_any_file(pdf_path)
    if not valid_docs:
        raise ValueError("File contains no valid text content.")

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1200, chunk_overlap=200
    )
    splits = text_splitter.split_documents(valid_docs)
    num_chunks = len(splits)
    logger.info(f"[Course {course_id}] Split into {num_chunks} chunks.")

    # Add metadata to each chunk for citation tracking
    for idx, doc in enumerate(splits):
        doc.metadata["chunk_id"] = idx
        doc.metadata["course_id"] = course_id
        doc.metadata["source_file"] = os.path.basename(pdf_path)
        # Preserve page number if available from doc_processor
        if "page" not in doc.metadata:
            doc.metadata["page"] = idx // 5 + 1  # Approximate page mapping

    logger.info(f"[Course {course_id}] Creating embeddings and indexing into Milvus...")

    # Build vectorstore with rate limit handling
    try:
        vectorstore = Milvus.from_documents(
            documents=splits[:BATCH_SIZE],
            embedding=embeddings,
            collection_name=collection_name,
            connection_args={"alias": MILVUS_ALIAS},
            drop_old=True,
        )
    except Exception as e:
        if "429" in str(e):
            logger.warning(" -> Rate limited. Waiting 60s...")
            time.sleep(MAX_RETRY_DELAY)
            vectorstore = Milvus.from_documents(
                documents=splits[:BATCH_SIZE],
                embedding=embeddings,
                collection_name=collection_name,
                connection_args={"alias": MILVUS_ALIAS},
                drop_old=True,
            )
        else:
            raise e

    # Add remaining batches
    for i in range(BATCH_SIZE, num_chunks, BATCH_SIZE):
        time.sleep(RETRY_DELAY)
        batch = splits[i:i + BATCH_SIZE]
        end_idx = min(i + BATCH_SIZE, num_chunks)
        logger.info(f" -> Chunks {i} to {end_idx}...")
        try:
            vectorstore.add_documents(batch)
        except Exception as e:
            if "429" in str(e):
                logger.warning(" -> Rate limited. Waiting 60s...")
                time.sleep(MAX_RETRY_DELAY)
                vectorstore.add_documents(batch)
            else:
                raise e

    # Save collection name reference to disk for course recovery
    meta_path = os.path.join(INDEX_DIR, f"milvus_{course_id}.json")
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump({
            "course_id": course_id,
            "collection_name": collection_name,
            "num_chunks": num_chunks,
            "created_at": time.time(),
        }, f, indent=2)

    logger.info(f"[Course {course_id}] Milvus collection '{collection_name}' created successfully.")
    return vectorstore


def load_existing_milvus(course_id: str) -> Optional[Milvus]:
    """Load existing Milvus collection for a course if it exists."""
    try:
        _get_milvus_connection()
        collection_name = _collection_name(course_id)
        embeddings = get_embeddings()

        if not utility.has_collection(collection_name):
            logger.warning(f"[Restore] Milvus collection '{collection_name}' not found.")
            return None

        vs = Milvus(
            embedding_function=embeddings,
            collection_name=collection_name,
            connection_args={"alias": MILVUS_ALIAS},
        )
        logger.info(f"[Restore] Loaded Milvus collection '{collection_name}'.")
        return vs
    except Exception as e:
        logger.error(f"[Restore] Failed to load Milvus collection: {e}")
        return None


def list_milvus_courses() -> List[str]:
    """List all course IDs that have Milvus collections."""
    _get_milvus_connection()
    courses = []
    collections = utility.list_collections()
    prefix = f"{MILVUS_COLLECTION_PREFIX}_"
    for col_name in collections:
        if col_name.startswith(prefix):
            course_id = col_name[len(prefix):]
            courses.append(course_id)
    return sorted(courses)


def get_collection_stats(course_id: str) -> Dict[str, Any]:
    """Get statistics about a Milvus collection."""
    _get_milvus_connection()
    collection_name = _collection_name(course_id)
    if not utility.has_collection(collection_name):
        return {"exists": False}
    
    collection = Collection(collection_name)
    collection.load()
    num_entities = collection.num_entities
    collection.release()
    
    return {
        "exists": True,
        "collection_name": collection_name,
        "num_entities": num_entities,
    }
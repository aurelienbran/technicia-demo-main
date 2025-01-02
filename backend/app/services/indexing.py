import logging
import asyncio
from typing import List, Dict
from datetime import datetime
from pathlib import Path
import hashlib
import fitz
import numpy as np
from fitz.fitz import FileDataError
import os

from .claude import ClaudeService
from .embedding import EmbeddingService
from .vector_store import VectorStore
from ..core.config import settings

logger = logging.getLogger("technicia.indexing")

class IndexingService:
    def __init__(self):
        self.claude = ClaudeService()
        self.embedding = EmbeddingService()
        self.vector_store = VectorStore()

    def _get_file_hash(self, file_path: str) -> str:
        file_stat = os.stat(file_path)
        content = f"{file_path}_{file_stat.st_size}_{file_stat.st_mtime}"
        return hashlib.md5(content.encode()).hexdigest()

    async def index_document(self, file_path: str) -> Dict:
        try:
            if not os.path.exists(file_path):
                error_msg = f"File not found: {file_path}"
                logger.error(error_msg)
                return {"status": "error", "error": error_msg}

            if not os.access(file_path, os.R_OK):
                error_msg = f"No read permission for file: {file_path}"
                logger.error(error_msg)
                return {"status": "error", "error": error_msg}

            file_hash = self._get_file_hash(file_path)

            try:
                doc = fitz.open(file_path)
            except FileDataError as e:
                error_msg = f"Invalid or corrupted PDF file: {file_path}"
                logger.error(f"{error_msg} - {str(e)}")
                return {"status": "error", "error": error_msg}
            except Exception as e:
                error_msg = f"Failed to open PDF: {str(e)}"
                logger.error(f"Error opening {file_path} - {str(e)}")
                return {"status": "error", "error": error_msg}

            try:
                metadata = {
                    "filename": Path(file_path).name,
                    "title": doc.metadata.get("title", ""),
                    "author": doc.metadata.get("author", ""),
                    "doc_type": "pdf",
                    "page_count": len(doc),
                    "file_path": file_path,
                    "file_hash": file_hash,
                    "indexed_at": datetime.utcnow().isoformat()
                }

                chunks = []
                for page_num in range(len(doc)):
                    text = doc[page_num].get_text()
                    if text.strip():
                        chunks.extend(self._split_text(text, page_num + 1))

                logger.info(f"Extracted {len(chunks)} chunks from {file_path}")

                if not chunks:
                    logger.warning(f"No text content found in {file_path}")
                    doc.close()
                    return {
                        "status": "error",
                        "error": "No text content found in document"
                    }

                for i, (chunk, page_num) in enumerate(chunks):
                    chunk_hash = hashlib.md5(chunk.encode()).hexdigest()

                    try:
                        embedding = await self.embedding.get_embedding(chunk)
                    except Exception as e:
                        logger.error(f"Error getting embedding for chunk {i}: {str(e)}")
                        continue

                    payload = {
                        **metadata,
                        "page_number": page_num,
                        "chunk_index": i,
                        "text": chunk,
                        "chunk_hash": chunk_hash,
                        "file_hash": file_hash
                    }

                    try:
                        await self.vector_store.add_vectors(
                            vectors=[embedding],
                            payloads=[payload]
                        )
                    except Exception as e:
                        logger.error(f"Error adding chunk {i} to vector store: {str(e)}")
                        continue

                doc.close()
                logger.info(f"Successfully indexed {file_path} with {len(chunks)} chunks")

                return {
                    "status": "success",
                    "file": file_path,
                    "chunks_processed": len(chunks)
                }

            except Exception as e:
                logger.error(f"Error processing document content: {str(e)}")
                doc.close()
                return {
                    "status": "error",
                    "error": f"Error processing document content: {str(e)}"
                }

        except Exception as e:
            logger.error(f"Unexpected error indexing document: {str(e)}")
            return {
                "status": "error",
                "error": str(e)
            }

    def _split_text(self, text: str, page_num: int) -> List[tuple[str, int]]:
        if not text.strip():
            return []

        chunks = []
        sentences = text.replace('\n', ' ').split('.')
        current_chunk = []
        current_length = 0

        for sentence in sentences:
            sentence = sentence.strip() + '.'
            sentence_length = len(sentence)
            
            if current_length + sentence_length > settings.CHUNK_SIZE and current_chunk:
                chunks.append((' '.join(current_chunk), page_num))
                current_chunk = []
                current_length = 0
            
            if sentence_length > settings.CHUNK_SIZE:
                # Diviser les phrases trop longues en mots
                words = sentence.split()
                temp_chunk = []
                temp_length = 0
                
                for word in words:
                    word_length = len(word) + 1
                    if temp_length + word_length > settings.CHUNK_SIZE and temp_chunk:
                        chunks.append((' '.join(temp_chunk), page_num))
                        temp_chunk = []
                        temp_length = 0
                    
                    temp_chunk.append(word)
                    temp_length += word_length
                
                if temp_chunk:
                    current_chunk.extend(temp_chunk)
                    current_length += temp_length
            else:
                current_chunk.append(sentence)
                current_length += sentence_length

        if current_chunk:
            chunks.append((' '.join(current_chunk), page_num))

        return chunks

    async def search(self, query: str, limit: int = 5) -> Dict:
        try:
            # Vérification de la connexion
            try:
                collection_info = await self.vector_store.get_collection_info()
                if collection_info["points_count"] == 0:
                    return {
                        "answer": "Aucun document n'a encore été indexé dans la base de connaissances.",
                        "sources": []
                    }
            except Exception as e:
                logger.error(f"Cannot connect to vector store: {str(e)}")
                return {
                    "answer": "Le service de recherche n'est pas disponible actuellement.",
                    "sources": [],
                    "error": "Database connection error"
                }

            # Génération de l'embedding avec plus de contexte
            expanded_query = f"Technique automobile : {query}"
            try:
                query_embedding = await self.embedding.get_embedding(expanded_query)
            except Exception as e:
                logger.error(f"Error generating query embedding: {str(e)}")
                return {
                    "answer": "Une erreur s'est produite lors du traitement de votre requête.",
                    "sources": [],
                    "error": "Embedding generation error"
                }

            # Recherche avec seuil de similarité ajusté
            try:
                results = await self.vector_store.search(
                    query_vector=query_embedding,
                    limit=limit,
                    score_threshold=0.5  # Seuil de similarité plus permissif
                )
            except Exception as e:
                logger.error(f"Error searching vector store: {str(e)}")
                return {
                    "answer": "Une erreur s'est produite lors de la recherche.",
                    "sources": [],
                    "error": "Search error"
                }

            if not results:
                logger.warning("No relevant results found for query")
                return {
                    "answer": "Je n'ai pas trouvé d'informations spécifiques sur ce sujet. Pouvez-vous préciser votre question ou donner plus de détails sur le modèle exact du véhicule ?",
                    "sources": []
                }

            # Préparation du contexte enrichi pour Claude
            context_parts = []
            for result in results:
                if 'payload' in result and 'text' in result['payload']:
                    text = result['payload']['text']
                    page = result['payload'].get('page_number', 'N/A')
                    score = result['score']
                    if score > 0.7:  # Contenu très pertinent
                        context_parts.append(f"[Information principale - Page {page}]\n{text}")
                    else:  # Contenu potentiellement pertinent
                        context_parts.append(f"[Information complémentaire - Page {page}]\n{text}")

            context = "\n\n".join(context_parts)

            if not context:
                logger.warning("No valid context extracted from results")
                return {
                    "answer": "Une erreur s'est produite lors de la préparation des résultats.",
                    "sources": [],
                    "error": "Context preparation error"
                }

            # Génération de la réponse avec Claude avec un prompt enrichi
            try:
                prompt = f"""En tant qu'expert en mécanique automobile, réponds à cette question technique de manière détaillée et structurée : {query}

Voici les informations techniques pertinentes trouvées dans la documentation :

{context}

Structure ta réponse avec :
1. Une présentation claire de la procédure
2. Les spécifications techniques importantes
3. Les points d'attention particuliers
4. Si nécessaire, des recommandations de sécurité"""
                
                answer = await self.claude.get_response(prompt)
            except Exception as e:
                logger.error(f"Error generating response with Claude: {str(e)}")
                return {
                    "answer": "Une erreur s'est produite lors de la génération de la réponse.",
                    "sources": results,
                    "error": "Response generation error"
                }

            return {
                "answer": answer,
                "sources": results
            }

        except Exception as e:
            logger.error(f"Unexpected error in search process: {str(e)}")
            return {
                "answer": "Une erreur inattendue s'est produite.",
                "sources": [],
                "error": f"Unexpected error: {str(e)}"
            }
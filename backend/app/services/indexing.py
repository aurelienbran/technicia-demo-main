async def _smart_chunk_text(self, text: str, context: str) -> List[Dict[str, str]]:
        try:
            logger.debug(f"Chunking texte de taille {len(text)}")
            chunks = []
            text = text.strip()

            if len(text) <= self.chunk_size:
                return [{"text": text, "context": context}]

            start = 0
            while start < len(text):
                end = start + self.chunk_size

                # Ajuster aux limites naturelles
                if end < len(text):
                    for marker in [". ", "\n\n", "\n", " "]:
                        pos = text.rfind(marker, start, end)
                        if pos != -1:
                            end = pos + len(marker)
                            break

                chunk = text[start:end].strip()
                if chunk:
                    chunks.append({"text": chunk, "context": context})
                start = end - self.overlap

            logger.debug(f"{len(chunks)} chunks créés")
            return chunks
        except Exception as e:
            logger.error(f"Erreur lors du chunking: {str(e)}")
            return []
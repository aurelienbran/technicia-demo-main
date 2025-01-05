    async def delete_vectors_by_filename(self, filename: str):
        try:
            # Supprime les points avec le nom de fichier spécifié
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=models.FilterSelector(
                    filter=models.Filter(
                        must=[models.FieldCondition(
                            key="filename",
                            match=models.MatchValue(value=filename)
                        )]
                    )
                )
            )
            logger.info(f"Vectors deleted for file: {filename}")
        except Exception as e:
            logger.error(f"Error deleting vectors: {str(e)}")
            raise
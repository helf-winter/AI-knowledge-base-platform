from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class RealEmbeddingIntegrationTest(unittest.TestCase):
    def test_embedding_service_supports_local_bge_m3_configuration(self) -> None:
        config = (ROOT / "app" / "core" / "config.py").read_text(encoding="utf-8")
        embedding = (ROOT / "app" / "services" / "embedding.py").read_text(encoding="utf-8")

        self.assertIn('embedding_provider: str = Field(default="bge")', config)
        self.assertIn('embedding_model_path: str = Field(default="D:/code/models/bge-m3")', config)
        self.assertIn("SentenceTransformer", embedding)
        self.assertIn("embed_text", embedding)
        self.assertIn("embed_texts", embedding)

    def test_vector_dimension_is_bge_m3_dimension(self) -> None:
        config = (ROOT / "app" / "core" / "config.py").read_text(encoding="utf-8")
        model = (ROOT / "app" / "models" / "vector.py").read_text(encoding="utf-8")
        migration = (ROOT / "alembic" / "versions" / "0019_bge_m3_embeddings.py").read_text(encoding="utf-8")

        self.assertIn("embedding_dimension: int = 1024", config)
        self.assertIn("Vector(1024)", model)
        self.assertIn("Vector(1024)", migration)

    def test_production_paths_do_not_call_fake_embedding_directly(self) -> None:
        for relative in [
            "app/services/knowledge_service.py",
            "app/services/flywheel.py",
            "app/services/search.py",
        ]:
            source = (ROOT / relative).read_text(encoding="utf-8")
            self.assertNotIn("fake_embedding", source, relative)
            self.assertIn("EmbeddingService", source, relative)


if __name__ == "__main__":
    unittest.main()

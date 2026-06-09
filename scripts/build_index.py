#!/usr/bin/env python3
import argparse
import hashlib
import sys
from pathlib import Path
from typing import List


ROOT_DIR = Path(__file__).resolve().parents[1]
API_DIR = ROOT_DIR / "api"
if str(API_DIR) not in sys.path:
    sys.path.insert(0, str(API_DIR))

from services.embedder_client import EmbedderClient
from services.schema_manager import load_schema
from services.vector_store import VectorStore


def main() -> int:
    parser = argparse.ArgumentParser(description="Build seed utterance vector index.")
    parser.add_argument("--intent-path", default=str(ROOT_DIR / "data" / "intents.yaml"))
    parser.add_argument("--device-path", default=str(ROOT_DIR / "data" / "devices.yaml"))
    parser.add_argument("--output-path", default=str(ROOT_DIR / "data" / "seed_index.npz"))
    parser.add_argument("--embedder-url", default="http://embedder:80")
    parser.add_argument("--timeout-ms", type=int, default=800)
    parser.add_argument(
        "--mock-embeddings",
        action="store_true",
        help="Use deterministic local embeddings for Jetson/unit checks.",
    )
    parser.add_argument(
        "--no-faiss",
        action="store_true",
        help="Skip FAISS index construction and use numpy fallback.",
    )
    args = parser.parse_args()

    schema_manager = load_schema(args.intent_path, args.device_path)
    records = schema_manager.list_seed_records()
    seed_utterances = [record["seed_utterance"] for record in records]

    if args.mock_embeddings:
        embeddings = build_mock_embeddings(seed_utterances)
    else:
        embedder = EmbedderClient(args.embedder_url, timeout_ms=args.timeout_ms)
        embeddings = embedder.embed_texts(seed_utterances)

    store = VectorStore.build(
        embeddings=embeddings,
        metadata=records,
        use_faiss=not args.no_faiss,
    )
    store.save(args.output_path)

    print(
        "saved {0} seed vectors to {1}".format(
            len(records),
            args.output_path,
        )
    )
    return 0


def build_mock_embeddings(texts: List[str], dimension: int = 16) -> List[List[float]]:
    return [_mock_embedding(text, dimension) for text in texts]


def _mock_embedding(text: str, dimension: int) -> List[float]:
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    values = []
    for index in range(dimension):
        value = digest[index % len(digest)] / 255.0
        values.append(value + 0.001)
    return values


if __name__ == "__main__":
    raise SystemExit(main())

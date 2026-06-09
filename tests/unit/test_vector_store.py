from services.vector_store import VectorStore, VectorStoreError


def test_vector_store_search_returns_nearest_metadata_in_order():
    store = VectorStore.build(
        embeddings=[
            [1.0, 0.0],
            [0.8, 0.2],
            [0.0, 1.0],
        ],
        metadata=[
            {"intent": "check_status", "seed_utterance": "상태 확인해"},
            {"intent": "start_machine", "seed_utterance": "장비 시작해"},
            {"intent": "set_light_intensity", "seed_utterance": "조명 100"},
        ],
        use_faiss=False,
    )

    results = store.search([1.0, 0.0], top_k=2)

    assert [result.metadata["intent"] for result in results] == [
        "check_status",
        "start_machine",
    ]
    assert results[0].score > results[1].score


def test_vector_store_preserves_seed_metadata_in_search_results():
    metadata = [
        {
            "intent": "set_camera_exposure",
            "seed_utterance": "카메라 노출값 800으로 바꿔",
            "required_capability": "camera.exposure.set",
        }
    ]
    store = VectorStore.build(
        embeddings=[[1.0, 0.0]],
        metadata=metadata,
        use_faiss=False,
    )

    results = store.search([1.0, 0.0], top_k=1)

    assert results[0].metadata == metadata[0]
    assert results[0].metadata is not metadata[0]


def test_vector_store_limits_top_k_to_available_metadata():
    store = VectorStore.build(
        embeddings=[[1.0, 0.0]],
        metadata=[{"intent": "check_status"}],
        use_faiss=False,
    )

    assert len(store.search([1.0, 0.0], top_k=10)) == 1


def test_vector_store_save_and_load_round_trip(tmp_path):
    output_path = tmp_path / "index.npz"
    store = VectorStore.build(
        embeddings=[[1.0, 0.0], [0.0, 1.0]],
        metadata=[
            {"intent": "check_status", "seed_utterance": "상태 확인해"},
            {"intent": "set_light_intensity", "seed_utterance": "조명 100"},
        ],
        use_faiss=False,
    )

    store.save(str(output_path))
    loaded = VectorStore.load(str(output_path), use_faiss=False)

    results = loaded.search([1.0, 0.0], top_k=1)
    assert results[0].metadata["intent"] == "check_status"


def test_vector_store_rejects_count_mismatch():
    try:
        VectorStore.build(
            embeddings=[[1.0, 0.0], [0.0, 1.0]],
            metadata=[{"intent": "check_status"}],
            use_faiss=False,
        )
    except VectorStoreError as error:
        assert str(error) == "embedding and metadata counts must match"
        return

    raise AssertionError("count mismatch should fail")


def test_vector_store_rejects_zero_embedding():
    try:
        VectorStore.build(
            embeddings=[[0.0, 0.0]],
            metadata=[{"intent": "check_status"}],
            use_faiss=False,
        )
    except VectorStoreError as error:
        assert str(error) == "embedding vectors must not be zero"
        return

    raise AssertionError("zero embedding should fail")


def test_vector_store_rejects_query_dimension_mismatch():
    store = VectorStore.build(
        embeddings=[[1.0, 0.0]],
        metadata=[{"intent": "check_status"}],
        use_faiss=False,
    )

    try:
        store.search([1.0, 0.0, 0.0], top_k=1)
    except VectorStoreError as error:
        assert str(error) == "query embedding dimension mismatch"
        return

    raise AssertionError("query dimension mismatch should fail")


def test_vector_store_rejects_invalid_top_k():
    store = VectorStore.build(
        embeddings=[[1.0, 0.0]],
        metadata=[{"intent": "check_status"}],
        use_faiss=False,
    )

    try:
        store.search([1.0, 0.0], top_k=0)
    except VectorStoreError as error:
        assert str(error) == "top_k must be greater than 0"
        return

    raise AssertionError("invalid top_k should fail")

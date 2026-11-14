from datetime import datetime, timedelta, timezone

import pytest

import engram


@pytest.fixture(autouse=True)
def fresh_store(tmp_path):
    engram.configure(tmp_path)
    yield
    engram.reset()


async def test_remember_and_recall():
    await engram.remember("Marie Curie was born in Warsaw.", dataset="science")
    results = await engram.recall("Where was Marie Curie born?", datasets=["science"])
    assert len(results) >= 1
    assert any("Marie Curie" in r["text"] for r in results)


async def test_recall_result_has_required_fields():
    await engram.remember("The sky is blue.", dataset="test")
    results = await engram.recall("sky", datasets=["test"])
    assert results
    r = results[0]
    assert all(k in r for k in ("text", "score", "strength", "dataset", "related"))


async def test_recall_reinforces_strength():
    await engram.remember("The sky is blue.", dataset="test")
    store = engram._get_store()
    rows = store._meta.get_all_in_dataset("test")
    store._meta.update_accessed(rows[0]["id"], 0.5)
    results = await engram.recall("sky", datasets=["test"])
    assert results[0]["strength"] > 0.5


async def test_forget_removes_dataset():
    await engram.remember("Some fact.", dataset="temp")
    await engram.forget("temp")
    assert await engram.recall("Some fact", datasets=["temp"]) == []


async def test_prune_removes_weak_memories():
    await engram.remember("Old fact.", dataset="test")
    store = engram._get_store()
    far_past = (datetime.now(timezone.utc) - timedelta(hours=10000)).isoformat()
    store._meta._conn.execute(
        "UPDATE memories SET last_accessed_at = ?, strength = 1.0 WHERE dataset = ?",
        (far_past, "test"),
    )
    store._meta._conn.commit()
    removed = await engram.prune("test", threshold=0.5)
    assert removed >= 1


async def test_improve_adds_content():
    await engram.remember("Marie Curie.", dataset="science")
    await engram.improve("Marie Curie won two Nobel Prizes.", dataset="science")
    results = await engram.recall("Nobel Prize", datasets=["science"])
    assert any("Nobel" in r["text"] for r in results)


async def test_recall_empty_store_returns_empty():
    assert await engram.recall("anything", datasets=["nonexistent"]) == []


async def test_improve_resets_decayed_siblings_to_full_strength():
    await engram.remember("An older fact.", dataset="science")
    store = engram._get_store()
    old_id = store._meta.get_all_in_dataset("science")[0]["id"]
    store._meta.update_accessed(old_id, 0.1)  # simulate a decayed memory
    await engram.improve("A newly curated fact.", dataset="science")
    refreshed = store._meta.get_by_ids([old_id])[0]
    assert refreshed["strength"] == pytest.approx(1.0)


async def test_recall_with_no_datasets_searches_all():
    await engram.remember("Marie Curie was a physicist.", dataset="science")
    await engram.remember("Paris is in France.", dataset="geography")
    results = await engram.recall("Marie Curie")  # datasets defaults to None
    assert any("Marie Curie" in r["text"] for r in results)


async def test_recall_isolates_by_dataset():
    await engram.remember("Marie Curie was a physicist.", dataset="science")
    await engram.remember("Paris is in France.", dataset="geography")
    results = await engram.recall("Marie Curie", datasets=["geography"])
    assert all(r["dataset"] == "geography" for r in results)


@pytest.mark.parametrize("text", ["", "   \n\t"])
async def test_remember_empty_text_does_not_create_memories(text):
    await engram.remember(text, dataset="empty")
    store = engram._get_store()
    assert store._meta.get_all_in_dataset("empty") == []
    assert store._meta.list_datasets() == []
    assert await engram.recall("anything", datasets=["empty"]) == []


async def test_remember_multiple_sentences_stores_each_once():
    sentences = ["The sky is blue.", "Water freezes at zero degrees!", "Is the sun a star?"]
    await engram.remember(" ".join(sentences), dataset="science")

    store = engram._get_store()
    rows = store._meta.get_all_in_dataset("science")
    assert sorted(row["text"] for row in rows) == sorted(sentences)
    assert len({row["id"] for row in rows}) == 3
    results = await engram.recall("sky water sun", datasets=["science"])
    assert {row["text"] for row in results} == set(sentences)


async def test_recall_nonexistent_dataset_does_not_return_other_memories():
    await engram.remember("The sky is blue.", dataset="science")
    assert await engram.recall("The sky is blue.", datasets=["missing"]) == []


async def test_prune_strong_memories_keeps_them_searchable():
    await engram.remember("The sky is blue. Water is wet.", dataset="science")
    store = engram._get_store()
    before = store._meta.get_all_in_dataset("science")

    assert await engram.prune("science", threshold=0.2) == 0

    assert store._meta.get_all_in_dataset("science") == before
    results = await engram.recall("sky water", datasets=["science"])
    assert {row["text"] for row in results} == {row["text"] for row in before}


async def test_forget_nonexistent_dataset_preserves_existing_memories():
    await engram.remember("The sky is blue.", dataset="science")
    await engram.forget("missing")
    await engram.forget("missing")

    results = await engram.recall("sky", datasets=["science"])
    assert len(results) == 1
    assert results[0]["text"] == "The sky is blue."


async def test_prune_nonexistent_dataset_returns_zero():
    assert await engram.prune("missing") == 0

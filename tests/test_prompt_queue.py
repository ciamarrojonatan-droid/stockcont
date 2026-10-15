"""Unit tests for PromptQueueManager and PromptItem in Phase 3."""

import json
from pathlib import Path
import pytest
from src.factory.prompt_queue import PromptQueueManager, PromptItem


@pytest.fixture
def sample_prompts_data():
    """Generates a sample prompts dataset with 2 items and 15 total prompts."""
    return [
        {
            "source_id": "item_normal_1",
            "source": "search",
            "generated_prompts": [
                {
                    "id": i,
                    "concept": f"Normal Concept {i}",
                    "prompt_data": {
                        "final_prompt": f"A beautiful commercial photo of nature subject {i}"
                    }
                }
                for i in range(1, 6) # 5 prompts
            ]
        },
        {
            "source_id": "item_top_seller",
            "source": "contributor_insights",
            "generated_prompts": [
                {
                    "id": i,
                    "concept": f"Top Seller Concept {i}",
                    "prompt_data": {
                        "final_prompt": f"A trending top seller high-end commercial visual {i}"
                    }
                }
                for i in range(1, 11) # 10 prompts
            ]
        }
    ]


@pytest.fixture
def queue_env(tmp_path, sample_prompts_data):
    """Sets up an isolated filesystem environment with prompts and mock files."""
    prompts_file = tmp_path / "prompts.json"
    history_file = tmp_path / "generation_history.json"
    trends_file = tmp_path / "trends.json"
    images_dir = tmp_path / "images"
    images_dir.mkdir(parents=True, exist_ok=True)

    with open(prompts_file, "w", encoding="utf-8") as f:
        json.dump(sample_prompts_data, f, indent=2)

    with open(trends_file, "w", encoding="utf-8") as f:
        json.dump([{"id": "item_top_seller", "source": "contributor_insights"}], f)

    return {
        "prompts_file": prompts_file,
        "history_file": history_file,
        "trends_file": trends_file,
        "images_dir": images_dir,
    }


def test_prompt_item_and_hash():
    """Test PromptItem string representation and SHA-256 hash calculation."""
    text = " A pristine droplet on a green leaf with roots.\n "
    h1 = PromptQueueManager.compute_hash(text)
    h2 = PromptQueueManager.compute_hash("A pristine droplet on a green leaf with roots.")
    assert h1 == h2
    assert len(h1) == 64

    item = PromptItem(
        prompt_text="Clean text",
        prompt_hash=h1,
        source_id="123",
        prompt_id=1,
        concept="Nature",
    )
    assert str(item) == "Clean text"
    d = item.to_dict()
    assert d["source_id"] == "123"
    assert d["status"] == "pending"


def test_empty_environment(tmp_path):
    """Test manager handles non-existent or empty files gracefully."""
    mgr = PromptQueueManager(
        prompts_file=tmp_path / "missing_prompts.json",
        history_file=tmp_path / "missing_history.json",
        trends_file=tmp_path / "missing_trends.json",
        images_dir=tmp_path / "missing_images",
        auto_reconcile=False,
    )
    stats = mgr.get_stats()
    assert stats["total"] == 0
    assert stats["generated"] == 0
    assert stats["pending"] == 0
    assert stats["progress_percent"] == 0.0
    assert mgr.get_pending_prompts() == []


def test_contributor_insights_prioritization(queue_env):
    """Contributor insights items should be ordered first in the pending queue."""
    mgr = PromptQueueManager(
        prompts_file=queue_env["prompts_file"],
        history_file=queue_env["history_file"],
        trends_file=queue_env["trends_file"],
        images_dir=queue_env["images_dir"],
        auto_reconcile=False,
    )
    pending = mgr.get_pending_prompts(batch_size=10)
    assert len(pending) == 10
    # The first 10 items should be from item_top_seller
    for p in pending:
        assert p.source_id == "item_top_seller"
        assert "Top Seller" in p.concept


def test_get_pending_prompts_pagination(queue_env):
    """Queue manager returns pending prompts according to batch size."""
    mgr = PromptQueueManager(
        prompts_file=queue_env["prompts_file"],
        history_file=queue_env["history_file"],
        trends_file=queue_env["trends_file"],
        images_dir=queue_env["images_dir"],
        auto_reconcile=False,
    )
    stats = mgr.get_stats()
    assert stats["total"] == 15
    assert stats["generated"] == 0
    assert stats["pending"] == 15

    batch1 = mgr.get_pending_prompts(batch_size=10)
    assert len(batch1) == 10

    # Mark batch 1 generated
    images = [f"gen_{i}.png" for i in range(10)]
    marked = mgr.mark_prompts_generated(batch1, saved_images=images)
    assert marked == 10

    # Next call should return the remaining 5 prompts
    batch2 = mgr.get_pending_prompts(batch_size=10)
    assert len(batch2) == 5
    for p in batch2:
        assert p.source_id == "item_normal_1"

    # Mark batch 2 generated
    images2 = [f"gen_{i+10}.png" for i in range(5)]
    mgr.mark_prompts_generated(batch2, saved_images=images2)

    # Queue should now be empty
    batch3 = mgr.get_pending_prompts(batch_size=10)
    assert len(batch3) == 0
    stats = mgr.get_stats()
    assert stats["generated"] == 15
    assert stats["pending"] == 0
    assert stats["progress_percent"] == 100.0


def test_mark_prompts_generated_atomic_persistence(queue_env):
    """Verify that marking prompts updates both history ledger and prompts.json atomically."""
    mgr = PromptQueueManager(
        prompts_file=queue_env["prompts_file"],
        history_file=queue_env["history_file"],
        trends_file=queue_env["trends_file"],
        images_dir=queue_env["images_dir"],
        auto_reconcile=False,
    )
    pending = mgr.get_pending_prompts(batch_size=2)
    saved_images = ["img_alpha.png", "img_beta.png"]
    marked = mgr.mark_prompts_generated(pending, saved_images=saved_images)
    assert marked == 2

    # Check history file
    assert queue_env["history_file"].exists()
    with open(queue_env["history_file"], "r", encoding="utf-8") as f:
        history = json.load(f)
    assert len(history) == 2
    for p, img in zip(pending, saved_images):
        assert p.prompt_hash in history
        assert history[p.prompt_hash]["image_file"] == img
        assert "generated_at" in history[p.prompt_hash]

    # Check prompts.json file
    with open(queue_env["prompts_file"], "r", encoding="utf-8") as f:
        raw = json.load(f)
    gen_in_raw = [
        pr for g in raw for pr in g.get("generated_prompts", [])
        if pr.get("status") == "generated"
    ]
    assert len(gen_in_raw) == 2
    assert gen_in_raw[0]["image_file"] in saved_images
    assert gen_in_raw[1]["image_file"] in saved_images

    # Verify no dangling temporary files
    assert not queue_env["history_file"].with_suffix(".tmp").exists()
    assert not queue_env["prompts_file"].with_suffix(".tmp").exists()


def test_partial_failure_resilience(queue_env):
    """When only 3 of 10 images are saved, only 3 prompts are marked generated."""
    mgr = PromptQueueManager(
        prompts_file=queue_env["prompts_file"],
        history_file=queue_env["history_file"],
        trends_file=queue_env["trends_file"],
        images_dir=queue_env["images_dir"],
        auto_reconcile=False,
    )
    batch = mgr.get_pending_prompts(batch_size=10)
    assert len(batch) == 10

    # Suppose only 3 images were saved before a timeout/error
    partial_images = ["part_1.png", "part_2.png", "part_3.png"]
    marked = mgr.mark_prompts_generated(batch, saved_images=partial_images)
    assert marked == 3

    stats = mgr.get_stats()
    assert stats["generated"] == 3
    assert stats["pending"] == 12

    # The next batch must include the 7 prompts that were NOT generated
    next_batch = mgr.get_pending_prompts(batch_size=10)
    assert len(next_batch) == 10
    # First item in next_batch should be the 4th item of the previous batch
    assert next_batch[0].prompt_hash == batch[3].prompt_hash
    assert next_batch[0].concept == batch[3].concept


def test_auto_reconciliation_with_existing_images(queue_env):
    """Test auto-reconciliation detects existing image files and marks earlier prompts."""
    # Create 3 dummy image files in images_dir
    for i in range(3):
        img_path = queue_env["images_dir"] / f"generated_test_{i}.png"
        img_path.write_bytes(b"dummy image data")

    # Manager initialized with auto_reconcile=True
    mgr = PromptQueueManager(
        prompts_file=queue_env["prompts_file"],
        history_file=queue_env["history_file"],
        trends_file=queue_env["trends_file"],
        images_dir=queue_env["images_dir"],
        auto_reconcile=True,
    )

    stats = mgr.get_stats()
    assert stats["generated"] == 3
    assert stats["pending"] == 12
    assert len(mgr._history) == 3


def test_corrupted_history_recovery(queue_env):
    """Corrupted history file doesn't crash the manager and initializes empty ledger."""
    queue_env["history_file"].write_text("{corrupted json contents", encoding="utf-8")

    mgr = PromptQueueManager(
        prompts_file=queue_env["prompts_file"],
        history_file=queue_env["history_file"],
        trends_file=queue_env["trends_file"],
        images_dir=queue_env["images_dir"],
        auto_reconcile=False,
    )
    stats = mgr.get_stats()
    assert stats["total"] == 15
    assert stats["generated"] == 0
    assert stats["pending"] == 15


def test_idempotent_marking(queue_env):
    """Marking the same prompts twice does not duplicate records in ledger."""
    mgr = PromptQueueManager(
        prompts_file=queue_env["prompts_file"],
        history_file=queue_env["history_file"],
        trends_file=queue_env["trends_file"],
        images_dir=queue_env["images_dir"],
        auto_reconcile=False,
    )
    batch = mgr.get_pending_prompts(batch_size=2)
    images = ["img1.png", "img2.png"]
    mgr.mark_prompts_generated(batch, saved_images=images)
    mgr.mark_prompts_generated(batch, saved_images=images)

    stats = mgr.get_stats()
    assert stats["generated"] == 2
    assert stats["pending"] == 13
    assert len(mgr._history) == 2


def test_auto_reconciliation_incremental_with_existing_history(queue_env):
    """Verify reconciliation correctly identifies unrecorded images when history already has entries."""
    # 1. Create first 2 images
    img1 = queue_env["images_dir"] / "generated_batch1_01.png"
    img2 = queue_env["images_dir"] / "generated_batch1_02.png"
    img1.write_bytes(b"data1")
    img2.write_bytes(b"data2")

    mgr = PromptQueueManager(
        prompts_file=queue_env["prompts_file"],
        history_file=queue_env["history_file"],
        trends_file=queue_env["trends_file"],
        images_dir=queue_env["images_dir"],
        auto_reconcile=True,
    )
    assert len(mgr._history) == 2
    h_entries = list(mgr._history.values())
    assert h_entries[0]["image_file"] == "generated_batch1_01.png"
    assert h_entries[1]["image_file"] == "generated_batch1_02.png"

    # 2. Add 2 MORE images to images_dir (simulating external or unrecorded assets)
    img3 = queue_env["images_dir"] / "generated_batch2_03.png"
    img4 = queue_env["images_dir"] / "generated_batch2_04.png"
    img3.write_bytes(b"data3")
    img4.write_bytes(b"data4")

    # 3. Reconcile with new images present
    reconciled_count = mgr.reconcile_existing_images()
    assert reconciled_count == 2

    # 4. Check all 4 entries in history have unique image files
    all_recorded = [e["image_file"] for e in mgr._history.values()]
    assert len(all_recorded) == 4
    assert len(set(all_recorded)) == 4
    assert "generated_batch2_03.png" in all_recorded
    assert "generated_batch2_04.png" in all_recorded

    stats = mgr.get_stats()
    assert stats["generated"] == 4
    assert stats["pending"] == 11


def test_get_pending_prompts_zero_or_negative_returns_all(queue_env):
    """Passing batch_size <= 0 or None returns all pending prompts."""
    mgr = PromptQueueManager(
        prompts_file=queue_env["prompts_file"],
        history_file=queue_env["history_file"],
        trends_file=queue_env["trends_file"],
        images_dir=queue_env["images_dir"],
        auto_reconcile=False,
    )
    all_pending = mgr.get_pending_prompts(batch_size=None)
    assert len(all_pending) == 15
    assert len(mgr.get_pending_prompts(batch_size=0)) == 15
    assert len(mgr.get_pending_prompts(batch_size=-5)) == 15


def test_mark_prompts_empty_or_zero_saved(queue_env):
    """Calling mark_prompts_generated with empty inputs or 0 saved images returns 0."""
    mgr = PromptQueueManager(
        prompts_file=queue_env["prompts_file"],
        history_file=queue_env["history_file"],
        trends_file=queue_env["trends_file"],
        images_dir=queue_env["images_dir"],
        auto_reconcile=False,
    )
    assert mgr.mark_prompts_generated([]) == 0
    pending = mgr.get_pending_prompts(batch_size=5)
    assert mgr.mark_prompts_generated(pending, saved_images=[]) == 0


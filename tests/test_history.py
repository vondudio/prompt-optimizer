"""Tests for history module."""

import os
import tempfile

from prompt_optimizer.history import HistoryDB


def _make_db():
    path = tempfile.mktemp(suffix=".db")
    return HistoryDB(db_path=path), path


class TestHistoryDB:
    def test_save_and_get(self):
        db, path = _make_db()
        try:
            rid = db.save("original", "optimized")
            entry = db.get(rid)
            assert entry is not None
            assert entry["original"] == "original"
            assert entry["optimized"] == "optimized"
        finally:
            db.close()
            os.unlink(path)

    def test_list_all(self):
        db, path = _make_db()
        try:
            for i in range(3):
                db.save(f"orig-{i}", f"opt-{i}")
            entries = db.list_all()
            assert len(entries) == 3
        finally:
            db.close()
            os.unlink(path)

    def test_list_all_limit(self):
        db, path = _make_db()
        try:
            for i in range(3):
                db.save(f"orig-{i}", f"opt-{i}")
            entries = db.list_all(limit=2)
            assert len(entries) == 2
        finally:
            db.close()
            os.unlink(path)

    def test_search(self):
        db, path = _make_db()
        try:
            db.save("alpha prompt", "alpha optimized")
            db.save("beta prompt", "beta optimized")
            db.save("gamma prompt", "gamma optimized")
            results = db.search("beta")
            assert len(results) == 1
            assert results[0]["original"] == "beta prompt"
        finally:
            db.close()
            os.unlink(path)

    def test_delete(self):
        db, path = _make_db()
        try:
            rid = db.save("original", "optimized")
            assert db.delete(rid) is True
            assert db.get(rid) is None
        finally:
            db.close()
            os.unlink(path)

    def test_delete_nonexistent(self):
        db, path = _make_db()
        try:
            assert db.delete("nonexistent_id") is False
        finally:
            db.close()
            os.unlink(path)

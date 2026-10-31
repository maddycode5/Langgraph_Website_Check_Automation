"""Automated tests for Google Doc dynamic rules loading and change detection."""
import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path
import tempfile
import json
import shutil
import hashlib

from nodes.load_reference_rules import (
    extract_google_doc_id,
    is_published_google_doc,
    fetch_google_doc_text,
    save_cached_rules,
    load_cached_rules,
    load_reference_rules_node,
    load_fallback_rubric
)
from state import AutomationState


class TestGoogleDocRules(unittest.TestCase):

    def test_extract_google_doc_id(self):
        # Standard edit URL with sharing
        url1 = "https://docs.google.com/document/d/1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms/edit?usp=sharing"
        self.assertEqual(extract_google_doc_id(url1), "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms")

        # View URL
        url2 = "https://docs.google.com/document/d/1w8a7X_abc-123XYZ/view"
        self.assertEqual(extract_google_doc_id(url2), "1w8a7X_abc-123XYZ")

        # User profile URL prefix
        url3 = "https://docs.google.com/document/u/1/d/19ABCDEFGHIJKLMNO-12345/edit"
        self.assertEqual(extract_google_doc_id(url3), "19ABCDEFGHIJKLMNO-12345")

        # Drive file URL
        url4 = "https://drive.google.com/file/d/1zYxWvUtSrQpOnMlK-987654321/view?usp=drivesdk"
        self.assertEqual(extract_google_doc_id(url4), "1zYxWvUtSrQpOnMlK-987654321")

        # Direct Doc ID
        doc_id = "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms"
        self.assertEqual(extract_google_doc_id(doc_id), doc_id)

        # Published doc is handled separately
        pub_url = "https://docs.google.com/document/d/e/2PACX-1vR_pub_example_123/pub"
        self.assertIsNone(extract_google_doc_id(pub_url))
        self.assertTrue(is_published_google_doc(pub_url))

    def test_dynamic_change_detection_and_cache(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_cache = Path(tmpdir) / "test_cache.txt"
            tmp_meta = Path(tmpdir) / "test_meta.json"

            with patch("nodes.load_reference_rules.CRITERIA_RULES_CACHE_PATH", tmp_cache), \
                 patch("nodes.load_reference_rules.CRITERIA_RULES_META_PATH", tmp_meta):

                # 1. Initial save of rules (Version 1)
                rules_v1 = "PILLAR 1: Standard SEO benchmark. Title must be 50 chars."
                meta_1, changed_1 = save_cached_rules(rules_v1, "https://docs.google.com/document/d/test1234/edit", "test1234")

                self.assertTrue(changed_1)
                self.assertEqual(meta_1["version"], 1)
                self.assertTrue(tmp_cache.exists())
                self.assertTrue(tmp_meta.exists())

                # Read back
                cached_text, cached_meta = load_cached_rules()
                self.assertEqual(cached_text, rules_v1)
                self.assertEqual(cached_meta["version"], 1)

                # 2. Re-read same content (no changes made in Google Doc)
                meta_2, changed_2 = save_cached_rules(rules_v1, "https://docs.google.com/document/d/test1234/edit", "test1234")
                self.assertFalse(changed_2, "Should detect NO changes when content is identical")
                self.assertEqual(meta_2["version"], 1, "Version should remain unchanged")

                # 3. Changes made in Google Doc afterwards! (Dynamic update)
                rules_v2 = "PILLAR 1: Updated SEO benchmark! Title must be 40-60 chars and include geo keyword."
                meta_3, changed_3 = save_cached_rules(rules_v2, "https://docs.google.com/document/d/test1234/edit", "test1234")

                self.assertTrue(changed_3, "Should detect changes when doc content is updated")
                self.assertEqual(meta_3["version"], 2, "Version should increment to 2")
                self.assertNotEqual(meta_1["sha256"], meta_3["sha256"])

                # Read back updated text
                updated_text, updated_meta = load_cached_rules()
                self.assertEqual(updated_text, rules_v2)
                self.assertEqual(updated_meta["version"], 2)

    @patch("requests.get")
    def test_node_execution_live_and_update(self, mock_get):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_cache = Path(tmpdir) / "test_cache.txt"
            tmp_meta = Path(tmpdir) / "test_meta.json"

            with patch("nodes.load_reference_rules.CRITERIA_RULES_CACHE_PATH", tmp_cache), \
                 patch("nodes.load_reference_rules.CRITERIA_RULES_META_PATH", tmp_meta):

                # Mock Google Doc HTTP response
                mock_resp = MagicMock()
                mock_resp.status_code = 200
                mock_resp.url = "https://docs.google.com/document/d/doc123/export?format=txt"
                mock_resp.text = "\ufeffLive Google Doc Rules for 2026 Website Audit"
                mock_get.return_value = mock_resp

                state = {
                    "google_doc_url": "https://docs.google.com/document/d/doc123/edit",
                    "logs": []
                }

                # 1. First execution - loads live rules
                res1 = load_reference_rules_node(state)
                self.assertEqual(res1["criteria_reference_text"], "Live Google Doc Rules for 2026 Website Audit")
                self.assertIn("Google Doc (live v1)", res1["rules_source"])
                self.assertTrue(any("Google Doc rules UPDATED!" in l for l in res1["logs"]))

                # 2. Second execution with modified doc content
                mock_resp.text = "Live Google Doc Rules: EDITED with stricter performance thresholds"
                state["logs"] = []
                res2 = load_reference_rules_node(state)
                self.assertEqual(res2["criteria_reference_text"], "Live Google Doc Rules: EDITED with stricter performance thresholds")
                self.assertIn("Google Doc (live v2)", res2["rules_source"])
                self.assertTrue(any("Google Doc rules UPDATED!" in l for l in res2["logs"]))

    @patch("requests.get")
    def test_node_offline_cache_fallback(self, mock_get):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_cache = Path(tmpdir) / "test_cache.txt"
            tmp_meta = Path(tmpdir) / "test_meta.json"

            with patch("nodes.load_reference_rules.CRITERIA_RULES_CACHE_PATH", tmp_cache), \
                 patch("nodes.load_reference_rules.CRITERIA_RULES_META_PATH", tmp_meta):

                # Pre-populate cache
                cached_rules = "Cached rules from previous successful sync"
                tmp_cache.write_text(cached_rules, encoding="utf-8")
                tmp_meta.write_text(json.dumps({"version": 3, "sha256": "fakehash", "last_updated": "2026-10-31"}), encoding="utf-8")

                # Mock network failure
                mock_get.side_effect = Exception("Connection timed out (offline)")

                state = {
                    "google_doc_url": "https://docs.google.com/document/d/doc123/edit",
                    "logs": []
                }

                res = load_reference_rules_node(state)
                self.assertEqual(res["criteria_reference_text"], cached_rules)
                self.assertIn("Google Doc (cached v3)", res["rules_source"])
                self.assertTrue(any("Live Google Doc fetch failed" in l for l in res["logs"]))
                self.assertTrue(any("Restored" in l for l in res["logs"]))


if __name__ == "__main__":
    unittest.main()

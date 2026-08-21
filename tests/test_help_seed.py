"""Unit tests for the help-seed normalisation logic (no network, no database)."""

import unittest

from app.models.help import HelpDocument
from scripts.fetch_sap_help import absolute_url, clean_text, merge, normalise_result

RAW_HIT = {
    "title": "<b>ABAP</b>",
    "description": "",
    "url": "/docs/ABAP_PLATFORM_NEW/c666/496d.html?locale=en-US",
    "mimeType": "text/html",
    "documentType": "Topic",
    "date": "2026-07-27",
    "state": "PRODUCTION",
    "deliverableTitle": "eCATT: Extended Computer Aided Test Tool",
    "loio": "496dd46f53523e90e10000000a42189c",
    "language": "en-US",
    "snippet": "The <b>ABAP</b> command  introduces a block. &hellip; ",
    "product": "ABAP platform",
    "version": "2025 FPS01 (Feb 2026)",
    "productId": "ABAP_PLATFORM_NEW",
    "versionId": "202510.001",
}


class TestCleanText(unittest.TestCase):
    def test_strips_markup_entities_and_extra_whitespace(self):
        self.assertEqual(
            clean_text("The <b>ABAP</b>  command &hellip; \n ends"),
            "The ABAP command … ends",
        )

    def test_handles_missing_value(self):
        self.assertEqual(clean_text(None), "")


class TestAbsoluteUrl(unittest.TestCase):
    def test_relative_path_gets_host(self):
        self.assertEqual(absolute_url("/docs/x.html"), "https://help.sap.com/docs/x.html")

    def test_absolute_path_untouched(self):
        self.assertEqual(absolute_url("https://help.sap.com/a"), "https://help.sap.com/a")


class TestNormaliseResult(unittest.TestCase):
    def test_maps_all_fields(self):
        doc = normalise_result(RAW_HIT, "ABAP")
        self.assertIsNotNone(doc)
        self.assertEqual(doc.id, "496dd46f53523e90e10000000a42189c:en-US")
        self.assertEqual(doc.title, "ABAP")
        self.assertEqual(doc.product_id, "ABAP_PLATFORM_NEW")
        self.assertEqual(doc.published_at, "2026-07-27")
        self.assertEqual(doc.search_queries, ["ABAP"])
        self.assertTrue(doc.url.startswith("https://help.sap.com/"))
        self.assertNotIn("<b>", doc.snippet)

    def test_rejects_hit_without_loio(self):
        self.assertIsNone(normalise_result({**RAW_HIT, "loio": ""}, "ABAP"))

    def test_rejects_hit_without_url(self):
        self.assertIsNone(normalise_result({**RAW_HIT, "url": ""}, "ABAP"))


class TestMerge(unittest.TestCase):
    def test_duplicate_ids_collapse_and_union_queries(self):
        first = normalise_result(RAW_HIT, "ABAP")
        second = normalise_result(RAW_HIT, "CDS view entity")
        merged = merge([first, second])
        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0].search_queries, ["ABAP", "CDS view entity"])

    def test_distinct_ids_kept(self):
        other = normalise_result({**RAW_HIT, "loio": "aaa"}, "ABAP")
        merged = merge([normalise_result(RAW_HIT, "ABAP"), other])
        self.assertEqual(len(merged), 2)


class TestHelpDocumentId(unittest.TestCase):
    def test_make_id(self):
        self.assertEqual(HelpDocument.make_id("abc", "de-DE"), "abc:de-DE")


if __name__ == "__main__":
    unittest.main()

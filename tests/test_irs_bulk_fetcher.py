"""Tests for IRS bulk guidance fetcher."""

from datetime import date
from unittest.mock import MagicMock, patch

import pytest

from atlas.fetchers.irs_bulk import (
    IRSBulkFetcher,
    IRSDropDocument,
    parse_irs_drop_listing,
)
from atlas.models_guidance import GuidanceType


class TestParseIrsDropListing:
    """Tests for parsing IRS drop folder listings."""

    def test_parse_revenue_procedure(self):
        """Parse a Revenue Procedure filename."""
        html = """
        <a href="rp-24-40.pdf">rp-24-40.pdf</a>
        """
        docs = parse_irs_drop_listing(html)
        assert len(docs) == 1
        doc = docs[0]
        assert doc.doc_type == GuidanceType.REV_PROC
        assert doc.doc_number == "2024-40"
        assert doc.year == 2024
        assert doc.pdf_filename == "rp-24-40.pdf"

    def test_parse_revenue_ruling(self):
        """Parse a Revenue Ruling filename."""
        html = """
        <a href="rr-23-12.pdf">rr-23-12.pdf</a>
        """
        docs = parse_irs_drop_listing(html)
        assert len(docs) == 1
        doc = docs[0]
        assert doc.doc_type == GuidanceType.REV_RUL
        assert doc.doc_number == "2023-12"
        assert doc.year == 2023

    def test_parse_notice(self):
        """Parse a Notice filename."""
        html = """
        <a href="n-22-45.pdf">n-22-45.pdf</a>
        """
        docs = parse_irs_drop_listing(html)
        assert len(docs) == 1
        doc = docs[0]
        assert doc.doc_type == GuidanceType.NOTICE
        assert doc.doc_number == "2022-45"
        assert doc.year == 2022

    def test_parse_multiple_documents(self):
        """Parse multiple document types from listing."""
        html = """
        <a href="rp-24-40.pdf">rp-24-40.pdf</a>
        <a href="rr-24-15.pdf">rr-24-15.pdf</a>
        <a href="n-24-78.pdf">n-24-78.pdf</a>
        <a href="a-24-10.pdf">a-24-10.pdf</a>
        """
        docs = parse_irs_drop_listing(html)
        assert len(docs) == 4  # All 4 types parsed

    def test_filter_by_year(self):
        """Filter documents by year."""
        html = """
        <a href="rp-24-40.pdf">rp-24-40.pdf</a>
        <a href="rp-23-34.pdf">rp-23-34.pdf</a>
        <a href="rp-22-38.pdf">rp-22-38.pdf</a>
        """
        docs = parse_irs_drop_listing(html, year=2024)
        assert len(docs) == 1
        assert docs[0].year == 2024

    def test_filter_by_doc_type(self):
        """Filter documents by type."""
        html = """
        <a href="rp-24-40.pdf">rp-24-40.pdf</a>
        <a href="rr-24-15.pdf">rr-24-15.pdf</a>
        <a href="n-24-78.pdf">n-24-78.pdf</a>
        """
        docs = parse_irs_drop_listing(html, doc_types=[GuidanceType.REV_PROC])
        assert len(docs) == 1
        assert docs[0].doc_type == GuidanceType.REV_PROC

    def test_ignore_non_guidance_files(self):
        """Ignore non-guidance PDF files."""
        html = """
        <a href="rp-24-40.pdf">rp-24-40.pdf</a>
        <a href="p1544.pdf">p1544.pdf</a>
        <a href="i1040.pdf">i1040.pdf</a>
        """
        docs = parse_irs_drop_listing(html)
        assert len(docs) == 1  # Only the Rev. Proc.


class TestIRSBulkFetcher:
    """Tests for the IRS bulk fetcher."""

    @pytest.fixture
    def fetcher(self):
        """Create a fetcher instance."""
        return IRSBulkFetcher()

    def test_list_documents_for_year(self, fetcher):
        """List all guidance documents for a year."""
        # Mock the HTTP response
        mock_html = """
        <html>
        <body>
        <a href="rp-24-40.pdf">rp-24-40.pdf</a>
        <a href="rp-24-39.pdf">rp-24-39.pdf</a>
        <a href="rr-24-15.pdf">rr-24-15.pdf</a>
        <a href="n-24-78.pdf">n-24-78.pdf</a>
        </body>
        </html>
        """
        with patch.object(fetcher, "_fetch_drop_listing", return_value=mock_html):
            docs = fetcher.list_documents(year=2024)

        assert len(docs) == 4
        assert all(d.year == 2024 for d in docs)

    def test_list_documents_filter_type(self, fetcher):
        """List documents filtered by type."""
        mock_html = """
        <a href="rp-24-40.pdf">rp-24-40.pdf</a>
        <a href="rr-24-15.pdf">rr-24-15.pdf</a>
        """
        with patch.object(fetcher, "_fetch_drop_listing", return_value=mock_html):
            docs = fetcher.list_documents(
                year=2024, doc_types=[GuidanceType.REV_PROC]
            )

        assert len(docs) == 1
        assert docs[0].doc_type == GuidanceType.REV_PROC

    def test_fetch_document_pdf(self, fetcher):
        """Fetch PDF content for a document."""
        mock_pdf = b"%PDF-1.4 test content"

        with patch.object(fetcher.client, "get") as mock_get:
            mock_response = MagicMock()
            mock_response.content = mock_pdf
            mock_response.raise_for_status = MagicMock()
            mock_get.return_value = mock_response

            doc = IRSDropDocument(
                doc_type=GuidanceType.REV_PROC,
                doc_number="2024-40",
                year=2024,
                pdf_filename="rp-24-40.pdf",
            )
            content = fetcher.fetch_pdf(doc)

        assert content == mock_pdf

    def test_document_url(self, fetcher):
        """Test PDF URL construction."""
        doc = IRSDropDocument(
            doc_type=GuidanceType.REV_PROC,
            doc_number="2024-40",
            year=2024,
            pdf_filename="rp-24-40.pdf",
        )
        assert doc.pdf_url == "https://www.irs.gov/pub/irs-drop/rp-24-40.pdf"

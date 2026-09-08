import unittest
import io
import tempfile
from pathlib import Path

from app.modules.document_processing.pipeline import TokenChunker, clean_text
from app.modules.document_processing.pipeline import ProcessingError, extract_pdf_pages


class FakeTokenizer:
    def encode(self, text, add_special_tokens=False):
        return text.split()

    def decode(self, token_ids, skip_special_tokens=True):
        return " ".join(token_ids)


class DocumentProcessingTests(unittest.TestCase):
    def test_real_pdf_extraction_reads_project_specification(self):
        pages = extract_pdf_pages(Path(__file__).parents[2] / "C11_Review1.pdf")
        self.assertGreater(len(pages), 0)
        self.assertTrue(any(page.text.strip() for page in pages))

    def test_empty_pdf_is_rejected(self):
        from pypdf import PdfWriter

        writer = PdfWriter()
        writer.add_blank_page(width=612, height=792)
        with tempfile.NamedTemporaryFile(suffix=".pdf") as file:
            writer.write(file)
            file.flush()
            with self.assertRaises(ProcessingError):
                extract_pdf_pages(Path(file.name))

    def test_cleaning_normalizes_extraction_whitespace(self):
        self.assertEqual(clean_text("  one\r\n\r\n\r\n two\t  words "), "one\n\ntwo words")

    def test_chunker_preserves_locked_size_and_overlap(self):
        chunker = TokenChunker(FakeTokenizer(), chunk_size=512, chunk_overlap=80)
        self.assertEqual(chunker.chunk_size, 512)
        self.assertEqual(chunker.chunk_overlap, 80)
        self.assertEqual(512 - 80, 432)

    def test_chunk_metadata_contains_source_identity_and_page(self):
        from app.modules.document_processing.pipeline import ExtractedPage

        text = " ".join(f"token-{index}" for index in range(600))
        chunks = TokenChunker(FakeTokenizer(), 512, 80).chunk_pages(
            [ExtractedPage(3, text)], document_id=17
        )
        self.assertGreater(len(chunks), 1)
        self.assertEqual(chunks[0].metadata["document_id"], 17)
        self.assertEqual(chunks[0].metadata["page_number"], 3)
        self.assertEqual(chunks[1].metadata["chunk_index"], 1)
        self.assertEqual(len(chunks[0].text.split()), 512)
        self.assertEqual(chunks[0].text.split()[-80:], chunks[1].text.split()[:80])
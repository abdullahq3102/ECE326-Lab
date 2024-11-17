import unittest
import os
import sqlite3
from crawler import crawler

class TestCrawler(unittest.TestCase):
    def setUp(self):
        """Set up a temporary database and URL file for testing."""
        self.db_path = "test_crawler_data.db"
        self.url_file = "test_urls.txt"

        with open(self.url_file, "w") as f:
            f.write("http://example.com\nhttp://test.com")

        self.crawler = crawler(db_path=self.db_path, url_file=self.url_file)
        self.crawler.initialize_database(self.db_path)

    def tearDown(self):
        """Remove the temporary database and URL file."""
        self.crawler.close_connection()
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        if os.path.exists(self.url_file):
            os.remove(self.url_file)

    def test_initialize_database(self):
        """Test if the database initializes properly with the required tables."""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cur.fetchall()}
        expected_tables = {
            "Lexicon",
            "DocumentIndex",
            "InvertedIndex",
            "Links",
            "PageRank"
        }
        self.assertTrue(expected_tables.issubset(tables))
        conn.close()

    def test_word_id(self):
        """Test if words are correctly added to the Lexicon and the inverted index."""
        word = "test"
        word_id = self.crawler.word_id(word)

        cur = self.crawler.db_conn.cursor()
        cur.execute("SELECT id, word FROM Lexicon WHERE word = ?", (word,))
        result = cur.fetchone()
        self.assertIsNotNone(result)
        self.assertEqual(result[0], word_id)
        self.assertEqual(result[1], word)

    def test_document_id(self):
        """Test if URLs are correctly added to the DocumentIndex."""
        url = "http://example.com"
        doc_id = self.crawler.document_id(url)

        cur = self.crawler.db_conn.cursor()
        cur.execute("SELECT id, url FROM DocumentIndex WHERE url = ?", (url,))
        result = cur.fetchone()
        self.assertIsNotNone(result)
        self.assertEqual(result[0], doc_id)
        self.assertEqual(result[1], url)

    def test_add_link(self):
        """Test if links are correctly added to the Links table."""
        from_doc_id = self.crawler.document_id("http://example1.com")
        to_doc_id = self.crawler.document_id("http://example2.com")
        self.crawler.add_link(from_doc_id, to_doc_id)

        cur = self.crawler.db_conn.cursor()
        cur.execute("SELECT from_doc_id, to_doc_id FROM Links WHERE from_doc_id = ? AND to_doc_id = ?",
                    (from_doc_id, to_doc_id))
        result = cur.fetchone()
        self.assertIsNotNone(result)
        self.assertEqual(result[0], from_doc_id)
        self.assertEqual(result[1], to_doc_id)

    def test_page_rank(self):
        """Test if PageRank values are computed and stored correctly."""
        doc1 = self.crawler.document_id("http://example1.com")
        doc2 = self.crawler.document_id("http://example2.com")
        doc3 = self.crawler.document_id("http://example3.com")
        self.crawler.add_link(doc1, doc2)
        self.crawler.add_link(doc2, doc3)
        self.crawler.add_link(doc3, doc1)

        page_ranks = self.crawler.page_rank()

        cur = self.crawler.db_conn.cursor()
        cur.execute("SELECT doc_id, score FROM PageRank")
        results = cur.fetchall()
        self.assertEqual(len(results), 3)
        for doc_id, score in results:
            self.assertIn(doc_id, page_ranks)
            self.assertAlmostEqual(page_ranks[doc_id], score, places=4)

    def test_get_resolved_inverted_index(self):
      """Test if the resolved inverted index is correctly generated."""
      word_id = self.crawler.word_id("example")
      doc_id = self.crawler.document_id("http://example.com")

      cur = self.crawler.db_conn.cursor()
      cur.execute("INSERT INTO InvertedIndex (word_id, doc_id) VALUES (?, ?)", (word_id, doc_id))
      self.crawler.db_conn.commit()

      self.crawler._word_id_cache[word_id] = "example"
      self.crawler._document_index[doc_id] = "http://example.com"

      resolved_index = self.crawler.get_resolved_inverted_index()

      self.assertIn("example", resolved_index)
      self.assertIn("http://example.com", resolved_index["example"])


if __name__ == "__main__":
    unittest.main()

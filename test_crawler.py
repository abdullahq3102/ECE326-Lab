import unittest
from unittest.mock import patch, MagicMock
from crawler import crawler

class TestCrawler(unittest.TestCase):

    def setUp(self):
        # Set up a crawler instance with a mock URL file
        self.crawler = crawler(None, 'mock_urls.txt')
        self.crawler._curr_doc_id = 1  # Mock the current document id

    @patch('crawler.urlopen')
    def test_crawling(self, mock_urlopen):
        # Mock the content of the page that would be crawled
        mock_html = """
        <html>
        <head><title>Test Page</title></head>
        <body>
            <h1>Sample Heading</h1>
            <p>This is a test page with some content.</p>
        </body>
        </html>
        """
        mock_urlopen.return_value.read.return_value = mock_html.encode('utf-8')

        # Call the crawl method and assert it processes the document correctly
        self.crawler._url_queue = [('http://example.com', 0)]
        self.crawler.crawl(depth=1)

        # Assert that the document index contains the URL
        self.assertEqual(self.crawler._document_index[1], 'http://example.com')

    def test_word_id_adding(self):
        # Test adding words to the lexicon and word_id_cache
        word = 'test'
        word_id = self.crawler.word_id(word)
        
        # Ensure that the word was added to the lexicon and has an ID
        self.assertIn(word, self.crawler._lexicon)
        self.assertEqual(self.crawler._lexicon[word], word_id)
        self.assertEqual(self.crawler._word_id_cache[word_id], word)

    def test_document_id_adding(self):
        # Test adding URLs to the document index
        url = 'http://example.com'
        doc_id = self.crawler.document_id(url)

        # Ensure that the document was added and has a unique ID
        self.assertIn(url, self.crawler._doc_id_cache)
        self.assertEqual(self.crawler._doc_id_cache[url], doc_id)
        self.assertEqual(self.crawler._document_index[doc_id], url)

    def test_inverted_index(self):
        # Test adding words to the inverted index
        word1 = 'test'
        word2 = 'crawler'
        self.crawler._curr_doc_id = 1  # Set the current document ID
        
        # Add words
        word1_id = self.crawler.word_id(word1)
        word2_id = self.crawler.word_id(word2)

        # Check that both words were added to the inverted index
        self.assertIn(word1_id, self.crawler._inverted_index)
        self.assertIn(word2_id, self.crawler._inverted_index)
        self.assertIn(1, self.crawler._inverted_index[word1_id])
        self.assertIn(1, self.crawler._inverted_index[word2_id])

    def test_resolved_inverted_index(self):
        # Manually add some entries to the inverted index
        word1 = 'test'
        word2 = 'crawler'
        self.crawler._curr_doc_id = 1  # Set the current document ID
        
        # Add words
        word1_id = self.crawler.word_id(word1)
        word2_id = self.crawler.word_id(word2)        
        self.crawler._inverted_index = {1: {1}, 2: {1}}
        self.crawler._document_index = {1: 'http://example.com'}

        # Call the resolved inverted index function
        resolved_index = self.crawler.get_resolved_inverted_index()

        # Check that the resolved index contains the correct mappings
        expected = {
            'test': ['http://example.com'],
            'crawler': ['http://example.com']
        }

        print("Resolved Index:", resolved_index)


        self.assertEqual(resolved_index, expected)

if __name__ == '__main__':
    unittest.main()

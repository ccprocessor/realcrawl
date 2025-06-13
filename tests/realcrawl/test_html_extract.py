from realcrawl.extract.html_extract import HtmlExtract
import unittest
import os
class TestHtmlExtract(unittest.TestCase):
    def setUp(self):
        self.base_path = os.path.dirname(os.path.abspath(__file__))

    def test_html_extract(self):
        html_extract = HtmlExtract(os.path.join(self.base_path, "assets/1.html"))
        html_content = html_extract.get_html_content()
        assert len(html_content) > 0

if __name__ == "__main__":
    unittest.main()
import unittest
from unittest.mock import patch
from app import validate_url

class UrlValidationTests(unittest.TestCase):
    @patch("app.socket.getaddrinfo")
    def test_public_https(self, lookup):
        lookup.return_value = [(None, None, None, None, ("8.8.8.8", 443))]
        self.assertEqual(validate_url("https://calendar.example.org/feed.ics"), "https://calendar.example.org/feed.ics")

    @patch("app.socket.getaddrinfo")
    def test_private_address_rejected(self, lookup):
        lookup.return_value = [(None, None, None, None, ("127.0.0.1", 443))]
        with self.assertRaises(ValueError):
            validate_url("https://calendar.example.org/feed.ics")

    def test_http_rejected(self):
        with self.assertRaises(ValueError):
            validate_url("http://calendar.example.org/feed.ics")

    def test_userinfo_rejected(self):
        with self.assertRaises(ValueError):
            validate_url("https://user:password@calendar.example.org/feed.ics")

if __name__ == "__main__":
    unittest.main()

import requests
import unittest

from bs4 import BeautifulSoup


class Test(unittest.TestCase):

    # STRESSTEST
    def test1(self):  # raphw-byte-buddy-95795967 #2 changed

        count = 0
        while count < 1:
            ua = {"User-Agent": "Mozilla/5.0"}
            url = (
                "https://github.com/raphw/byte-buddy/compare/5a2cc59b4bc18b778047c0b3775953155491cecc.."
                "61eb2bc5248803e2f1efa24cf5589a41ba435a14"
            )
            page = requests.get(url, headers=ua)
            soup = BeautifulSoup(page.text, 'lxml')
            print(soup)
            count = count + 1
        self.assertEqual(1, 1)


if __name__ == '__main__':
    unittest.main()

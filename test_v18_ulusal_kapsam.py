import unittest
from unittest.mock import patch
from fikstur_yeni import LIGLER, aktif_ligler

class TestUlusalKapsam(unittest.TestCase):
    def test_default(self):
        with patch.dict("os.environ", {"TIPSTER_UEFA":"0"}):
            self.assertEqual(set(aktif_ligler()), {k for k in LIGLER if not k.startswith("uefa.")})
            self.assertIn("pol.2", aktif_ligler())
    def test_optin(self):
        with patch.dict("os.environ", {"TIPSTER_UEFA":"1"}):
            self.assertEqual(aktif_ligler(), LIGLER)

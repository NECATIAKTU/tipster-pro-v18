import sys
import tempfile
import json
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from merkez import catalog_leagues, match_league, check_payload, run

class Tests(unittest.TestCase):
    def test_catalog(self):
        self.assertEqual(catalog_leagues({'leagues':[{'code':'germany3','name':'German 3. Liga'}]}),{'germany3':'German 3. Liga'})
    def test_documented_match(self):
        self.assertEqual(match_league({'kod':'de.3','ad':'Almanya 3. Liga'},{'germany3':'German 3. Liga'})['kod'],'germany3')
    def test_reject_unverified(self):
        self.assertIsNone(match_league({'kod':'xx','ad':'Unknown'},{'a':'Other'})['kod'])
    def test_payload(self):
        self.assertEqual(check_payload({'fixtures':[1,2]})['kayit_sayisi'],2)
    def test_readonly(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'ligler.json'
            p.write_text(json.dumps({'sifir_fikstur':[{'kod':'de.3','ad':'Almanya 3. Liga'}],'yeni_adaylar':[]}))
            def fetch(url,token):
                if url.endswith('/leagues/'):
                    return {'leagues':[{'code':'germany3','name':'German 3. Liga'}]}
                return {'fixtures':[1]} if 'fixtures' in url else {'results':[1,2]}
            before=p.read_bytes()
            r=run(p,max_leagues=1,fetch=fetch)
            self.assertEqual(r['denetlenen'],1)
            self.assertEqual(r['ligler'][0]['results']['kayit_sayisi'],2)
            self.assertEqual(before,p.read_bytes())
    def test_quota(self):
        with self.assertRaises(ValueError):run(max_leagues=13)
if __name__=='__main__':unittest.main()

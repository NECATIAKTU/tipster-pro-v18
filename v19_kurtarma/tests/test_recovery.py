import unittest
from unittest.mock import patch
from datetime import datetime,timezone,timedelta
# Standalone tests also work before files are installed in V18 repo.
# In the real GitHub repository, the actual V18 modules are imported instead.
import importlib.util, sys, types, math
if importlib.util.find_spec('gercek_tahmin_v18') is None:
    mod=types.ModuleType('gercek_tahmin_v18')
    def historical_stats(*args,**kwargs): raise RuntimeError('mock required')
    mod.historical_stats=historical_stats
    sys.modules['gercek_tahmin_v18']=mod
if importlib.util.find_spec('tahmin_motoru') is None:
    mod=types.ModuleType('tahmin_motoru')
    mod.indeks_olustur=lambda teams: {k.casefold():k for k in teams}
    mod.otomatik_eslestir=lambda name,teams,index: index.get(str(name).casefold())
    sys.modules['tahmin_motoru']=mod
if importlib.util.find_spec('gol_modeli') is None:
    mod=types.ModuleType('gol_modeli')
    def mac_analizi(home,away,teams):
        expected=(teams[home]['attigi']/teams[home]['mac']+teams[away]['attigi']/teams[away]['mac'])
        return {'beklenen_gol':expected,**{f'{l}.5_ust':round(100*(1-sum(math.exp(-expected)*expected**k/math.factorial(k) for k in range(l+2))),1) for l in range(1,7)}}
    mod.mac_analizi=mac_analizi
    sys.modules['gol_modeli']=mod
if importlib.util.find_spec('fikstur_yeni') is None:
    mod=types.ModuleType('fikstur_yeni');mod.LIGLER={'eng.1':'Premier League'}
    sys.modules['fikstur_yeni']=mod
from v19_kurtarma.engine import recover, fixture_key, safe_selection
from v19_kurtarma.preview import html_preview

NOW=datetime(2026,11,23,12,tzinfo=timezone.utc)
KICK=(NOW+timedelta(days=2)).isoformat()
def fixture(matches):return {'olusturulma_utc':NOW.isoformat(),'maclar':matches}
def v18(matches):return {'model':'TIPSTER PRO V18','olusturulma_utc':NOW.isoformat(),'tahminler':matches}
def match(n=100):return {'id':f'eng.1|{n}','lig_kodu':'eng.1','tarih':KICK,'ev_sahibi':'Liverpool','deplasman':'Chelsea'}
def event(i):
    return {'id':str(i),'status':{'type':{'completed':True}},'competitions':[{'competitors':[
        {'homeAway':'home','team':{'displayName':'Liverpool'},'score':'2'},
        {'homeAway':'away','team':{'displayName':'Chelsea'},'score':'1'}]}]}
def fetch(lig,day):return {'events':[event(i) for i in range(12)]} # unique event IDs counted once

class RecoveryTests(unittest.TestCase):
    def test_new_match_recovered_and_panel(self):
        with patch('v19_kurtarma.engine.historical_stats') as mock:
            mock.return_value=({'Liverpool':{'mac':10,'attigi':15,'yedigi':10},'Chelsea':{'mac':10,'attigi':11,'yedigi':12}}, {'hata_gunu':0,'tamamlanmis_mac':12})
            rows,panel,rep=recover(fixture([match()]),v18([]),[],now=NOW)
        self.assertEqual(rep['kurtarilan'],1)
        self.assertEqual(len(rows),1)
        self.assertEqual(panel['tahminler'][0]['kurtarma_kaynagi'],'V19_BAGIMSIZ_KURTARMA')
        self.assertTrue(all(0<=rows[0]['tahmin'][f'{l}_ust']<=100 for l in ('1.5','2.5','3.5','4.5','5.5','6.5')))

    def test_v18_existing_not_labeled_missing(self):
        m=match();m['tahmin']={'1.5_ust':80};m['hesaplama_zamani_utc']=NOW.isoformat()
        rows,panel,rep=recover(fixture([match()]),v18([m]),[],now=NOW)
        self.assertEqual(len(rows),0);self.assertEqual(rep['nedenler']['V18_TAHMIN_VAR'],1)
        self.assertEqual(len(panel['tahminler']),1)

    def test_archived_not_rebackdated(self):
        rows,panel,rep=recover(fixture([match()]),v18([]),[{'kimlik':'eng.1|100'}],now=NOW)
        self.assertEqual(rows,[]);self.assertEqual(rep['nedenler']['ARSIVDE_VAR'],1)

    def test_started_not_predicted(self):
        m=match();m['tarih']=(NOW-timedelta(hours=1)).isoformat()
        rows,panel,rep=recover(fixture([m]),v18([]),[],now=NOW)
        self.assertEqual(rep['nedenler']['BASLAMIS_VEYA_TARIHSIZ'],1)
        self.assertEqual(rows,[])

    def test_stale_fixtures_rejected(self):
        f=fixture([match()]);f['olusturulma_utc']=(NOW-timedelta(days=2)).isoformat()
        with self.assertRaises(ValueError):recover(f,v18([]),[],now=NOW)

    def test_ambiguous_team_no_forced_match(self):
        with patch('v19_kurtarma.engine.historical_stats') as mock:
            mock.return_value=({'Liverpool':{'mac':9,'attigi':12,'yedigi':8},'Chelsea':{'mac':9,'attigi':9,'yedigi':12}}, {'hata_gunu':0,'tamamlanmis_mac':12})
            m=match();m['ev_sahibi']='Totally Unknown Club'
            rows,panel,rep=recover(fixture([m]),v18([]),[],now=NOW)
        self.assertEqual(rows,[]);self.assertEqual(rep['nedenler']['TAKIM_ESLESMEDI'],1)

    def test_missing_history_not_fabricated(self):
        with patch('v19_kurtarma.engine.historical_stats') as mock:
            mock.return_value=({}, {'hata_gunu':0,'tamamlanmis_mac':0})
            rows,panel,rep=recover(fixture([match()]),v18([]),[],now=NOW)
        self.assertEqual(rows,[]);self.assertEqual(rep['nedenler']['GECMIS_VERI_EKSIK'],1)

    def test_duplicate_fixture_deduped(self):
        with patch('v19_kurtarma.engine.historical_stats') as mock:
            mock.return_value=({}, {'hata_gunu':0,'tamamlanmis_mac':0})
            _,_,rep=recover(fixture([match(),match()]),v18([]),[],now=NOW)
        self.assertEqual(rep['nedenler']['FIKSTUR_TEKRARI'],1)

    def test_html_escaped(self):
        p={'tahminler':[{'lig':'<script>alert(1)</script>'}]}
        html=html_preview(p,{'nedenler':{},'kurtarilan':0})
        self.assertNotIn('<script>alert(1)</script>',html)
        self.assertIn('\\u003cscript',html)

    def test_safe_selection_threshold(self):
        self.assertEqual(safe_selection({'2.5_ust':70}), '2.5 UST')
        self.assertEqual(safe_selection({'1.5_ust':20}), 'RISKLI')

if __name__=='__main__':unittest.main()

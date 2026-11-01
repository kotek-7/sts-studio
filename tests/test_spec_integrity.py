import ast,importlib,json,sys,tempfile,unittest
from pathlib import Path
from sts_studio.catalog import ROOT
from sts_studio.files import Recorder
sys.path.insert(0,str(ROOT/'tools'))
from render_spec import generated

class Specification(unittest.TestCase):
    def test_spec_integrity(self):
        names={n.name for p in (ROOT/'tests').glob('test_*.py') for n in ast.walk(ast.parse(p.read_text())) if isinstance(n,ast.FunctionDef)}
        for f in json.loads((ROOT/'spec/features.json').read_text())['features']:
            if f['status']!='implemented':continue
            path=f['implementation'].split('.');obj=importlib.import_module('sts_studio.'+path.pop(0))
            for part in path:obj=getattr(obj,part)
            self.assertIsNotNone(obj,f['id']);self.assertIn(f['test'],names,f['id'])
        for name,text in generated().items():self.assertEqual((ROOT/'docs'/name).read_text(),text,name)
    def test_record_fixture_and_periodic_flush(self):
        raw=(ROOT/'tests/fixtures/telemetry.txt').read_bytes();lines=raw.splitlines(keepends=True)
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'record.txt';rec=Recorder(p,True)
            for i,line in enumerate(lines[1:]):
                v=line.decode().strip().split(',')
                rec.append({56:int(v[1]),'goal':int(v[2]),60:int(v[3]),58:int(v[4]),69:int(v[5]),63:int(v[6]),62:int(v[7]),'id':1,'timestamp':i})
                if i%2==0:rec.flush()
            rec.flush();self.assertEqual(p.read_bytes(),raw);self.assertFalse(rec.buffer)
    def test_vectors_from_capture(self):
        observed={r['hex'] for r in map(json.loads,(ROOT/'tests/fixtures/bus-session.jsonl').read_text().splitlines()) if r['direction']=='TX'}
        for v in json.loads((ROOT/'spec/protocol.json').read_text())['test_vectors']:self.assertIn(v['frame'],observed,v['id'])

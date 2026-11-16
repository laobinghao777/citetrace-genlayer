import sys, types, json, unittest, importlib.util, copy
from pathlib import Path
class E(Exception):pass
class Contract:
 def __new__(cls):
  x=super().__new__(cls);x.reviews={};return x
sender=types.SimpleNamespace(as_hex='owner');answer={}
def strict(f):
 a=f();b=f()
 if a!=b:raise E('Independent classification disagreed')
 return a
gl=types.ModuleType('genlayer');gl.contract=types.SimpleNamespace(Contract=Contract);gl.storage=types.SimpleNamespace(TreeMap=dict);gl.message=types.SimpleNamespace(sender_address=sender);gl.vm=types.SimpleNamespace(UserError=E);gl.public=types.SimpleNamespace(write=lambda f:f,view=lambda f:f);gl.nondet=types.SimpleNamespace(exec_prompt=lambda *a,**k:copy.deepcopy(answer));gl.eq_principle=types.SimpleNamespace(strict_eq=strict)
gt=types.ModuleType('genlayer.types');gt.u256=int;sys.modules['genlayer']=gl;sys.modules['genlayer.types']=gt
spec=importlib.util.spec_from_file_location('citetrace_contract',Path(__file__).parent/'contract.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
source={'reference':'Synthetic schedule A','excerpt':'Workshop Orion opens at 09:00 on 20 November 2026.'}
counter={'reference':'Synthetic correction B','excerpt':'Workshop Orion opens at 11:00 on 20 November 2026; the earlier 09:00 opening is cancelled.'}
def row(i,relation,quote):return dict(id=i,relation=relation,quote=quote)
class Tests(unittest.TestCase):
 def setUp(self):
  global answer
  sender.as_hex='owner';self.c=m.CiteTrace();self.c.create_review('Synthetic opening time','Workshop Orion opens at 09:00 on 20 November 2026.',json.dumps([source]));answer={'classifications':[row(1,'supports',source['excerpt'])]}
 def state(self):return json.loads(self.c.get_review('1'))
 def resolved(self):self.c.resolve('1',1);return self.state()['rounds'][0]
 def test_support(self):self.assertEqual(self.resolved()['result']['verdict'],'support_only')
 def test_counterevidence_history(self):
  original=self.resolved();self.c.propose_round('1',1,json.dumps([counter]));answer['classifications'].append(row(2,'contradicts',counter['excerpt']));self.c.resolve('1',2);s=self.state();self.assertEqual(s['rounds'][0],original);self.assertEqual(s['rounds'][1]['result']['verdict'],'conflicted');self.assertEqual(s['rounds'][1]['parent'],1)
 def test_contradiction_only(self):self.assertEqual(self.c._summary([row(1,'contradicts','x')])['verdict'],'contradiction_only')
 def test_insufficient(self):
  answer['classifications']=[row(1,'insufficient','')];self.assertEqual(self.resolved()['result']['verdict'],'insufficient')
 def test_author_only(self):
  sender.as_hex='other'
  with self.assertRaises(E):self.c.resolve('1',1)
 def test_public_challenge_author(self):
  self.resolved();sender.as_hex='other';self.c.propose_round('1',1,json.dumps([counter]));self.assertEqual(self.state()['rounds'][1]['author'],'other');sender.as_hex='owner'
  with self.assertRaises(E):self.c.resolve('1',2)
 def test_finality(self):
  self.resolved()
  with self.assertRaises(E):self.c.resolve('1',1)
 def test_unresolved_parent(self):
  with self.assertRaises(E):self.c.propose_round('1',1,json.dumps([counter]))
 def test_pending_branch_does_not_block(self):
  self.resolved();self.c.propose_round('1',1,json.dumps([counter]));sender.as_hex='other';self.c.propose_round('1',1,json.dumps([dict(reference='Synthetic parallel C',excerpt='Workshop Orion schedule will be reviewed tomorrow.')]));self.assertEqual(len(self.state()['rounds']),3);self.assertEqual(self.state()['rounds'][2]['parent'],1)
 def test_boolean_round(self):
  with self.assertRaises(E):self.c.resolve('1',True)
 def test_invalid_parent(self):
  with self.assertRaises(E):self.c.propose_round('1',99,json.dumps([counter]))
 def test_duplicate_evidence(self):
  self.resolved()
  with self.assertRaises(E):self.c.propose_round('1',1,json.dumps([source]))
 def test_quote_fabrication(self):
  answer['classifications'][0]['quote']='An invented opening statement'
  with self.assertRaises(E):self.c.resolve('1',1)
 def test_missing_source(self):
  answer['classifications']=[]
  with self.assertRaises(E):self.c.resolve('1',1)
 def test_invalid_id(self):
  answer['classifications'][0]['id']=True
  with self.assertRaises(E):self.c.resolve('1',1)
 def test_invalid_relation(self):
  answer['classifications'][0]['relation']='true'
  with self.assertRaises(E):self.c.resolve('1',1)
 def test_insufficient_cannot_quote(self):
  answer['classifications'][0]['relation']='insufficient'
  with self.assertRaises(E):self.c.resolve('1',1)
 def test_snapshot(self):
  old=self.state()['rounds'][0]['snapshot_sha256'];self.resolved();self.assertEqual(old,self.state()['rounds'][0]['snapshot_sha256']);self.assertEqual(len(old),64)
 def test_failed_resolution_is_atomic(self):
  before=self.state();answer['classifications'][0]['id']=0
  with self.assertRaises(E):self.c.resolve('1',1)
  self.assertEqual(before,self.state())
 def test_independent_disagreement(self):
  old=gl.nondet.exec_prompt;calls=[]
  def varying(*a,**k):
   calls.append(1);return copy.deepcopy(answer) if len(calls)==1 else {'classifications':[row(1,'insufficient','')]}
  gl.nondet.exec_prompt=varying
  try:
   with self.assertRaises(E):self.c.resolve('1',1)
   self.assertEqual(self.state()['rounds'][0]['status'],'committed')
  finally:gl.nondet.exec_prompt=old
 def test_independent_quote_variation(self):
  old=gl.nondet.exec_prompt;calls=[]
  def varying(*a,**k):
   calls.append(1);d=copy.deepcopy(answer)
   if len(calls)==2:d['classifications'][0]['quote']='opens at 09:00 on 20 November 2026'
   return d
  gl.nondet.exec_prompt=varying
  try:self.assertEqual(self.resolved()['result']['verdict'],'support_only');self.assertEqual(len(calls),2)
  finally:gl.nondet.exec_prompt=old
 def test_source_limits(self):
  for rows in [[],[dict(reference='Reference '+str(i),excerpt='Unique evidence sentence '+str(i)) for i in range(9)]]:
   with self.assertRaises(E):self.c._sources(json.dumps(rows))
 def test_round_limit(self):
  self.resolved()
  for i in range(11):self.c.propose_round('1',1,json.dumps([counter]))
  with self.assertRaises(E):self.c.propose_round('1',1,json.dumps([counter]))
 def test_duplicate_classification_ids(self):
  with self.assertRaises(E):self.c._validate({'classifications':[row(1,'supports',source['excerpt']),row(1,'supports',source['excerpt'])]},[source,counter])
if __name__=='__main__':unittest.main()

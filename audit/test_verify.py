import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from verify import audit, canonical, read, verify_anchor


def fixture():
    source={'reference':'Synthetic A','excerpt':'演示活动在九点开门。🧪 This is a synthetic test.'}
    claim='The synthetic event opens at nine.'
    root={'number':1,'parent':0,'author':'builder','sources':[source], 'status':'resolved',
          'result':{'verdict':'support_only','supporting_ids':[1],'contradicting_ids':[], 'insufficient_ids':[],
                    'classifications':[{'id':1,'relation':'supports','quote':source['excerpt']}]}}
    root['snapshot_sha256']=hashlib.sha256(canonical({'claim':claim,'sources':root['sources']}).encode()).hexdigest()
    child=copy.deepcopy(root);child['number']=2;child['parent']=1
    child['sources'].append({'reference':'Synthetic B','excerpt':'The synthetic event opens at eleven, not nine.'})
    child['result']['classifications'].append({'id':2,'relation':'contradicts','quote':child['sources'][1]['excerpt']})
    child['result'].update(verdict='conflicted',contradicting_ids=[2])
    child['snapshot_sha256']=hashlib.sha256(canonical({'claim':claim,'sources':child['sources']}).encode()).hexdigest()
    return {'id':'1','title':'Synthetic test','claim':claim,'creator':'builder','rounds':[root,child]}


class Tests(unittest.TestCase):
    def test_self_consistent_forgery_rejected_by_anchor(self):
        original=fixture();forged=copy.deepcopy(original);forged['title']='Forged title'
        audit(forged)  # The source snapshot intentionally does not bind the title.
        with self.assertRaisesRegex(ValueError,'differs'):verify_anchor(forged,original)

    def test_semantic_json_order_does_not_change_anchor(self):
        original=fixture();reordered=dict(reversed(list(original.items())))
        self.assertTrue(verify_anchor(reordered,original))

    def test_valid_unicode_lineage(self):
        report=audit(fixture());self.assertEqual(report['rounds'][1]['verdict'],'conflicted')
        self.assertFalse(report['source_truth_verified']);self.assertEqual(report['rounds'][1]['added_sources'],1)

    def test_attack_mutations(self):
        # Each independent mutation attacks a different assertion or provenance boundary.
        mutations=[
            lambda r:r.update(claim=r['claim']+' changed'),
            lambda r:r['rounds'][1].update(parent=2),
            lambda r:r['rounds'][0].update(parent=True),
            lambda r:r['rounds'][1].update(number=3),
            lambda r:r['rounds'][0].update(author='intruder'),
            lambda r:r['rounds'][1]['sources'][0].update(excerpt='A rewritten inherited passage.'),
            lambda r:r['rounds'][1]['result'].update(verdict='support_only'),
            lambda r:r['rounds'][1]['result'].update(contradicting_ids=[]),
            lambda r:r['rounds'][1]['result']['classifications'][1].update(id=True),
            lambda r:r['rounds'][1]['result']['classifications'][1].update(quote='invented'),
            lambda r:r['rounds'][1]['result']['classifications'][1].update(relation='unknown'),
            lambda r:r['rounds'][1]['result']['classifications'].pop(),
            lambda r:r['rounds'][1].update(snapshot_sha256='0'*64),
            lambda r:r['rounds'][1].update(status='committed'),
            lambda r:r.update(untrusted_extra=True),
            lambda r:r['rounds'][1]['sources'][1].update(reference='Synthetic A'),
        ]
        for mutate in mutations:
            with self.subTest(mutation=mutate):
                value=fixture();mutate(value)
                with self.assertRaises((ValueError,TypeError,KeyError)):audit(value)

    def test_rehashed_parent_rewrite_still_rejected(self):
        value=fixture();child=value['rounds'][1];child['sources'][0]['excerpt']='A malicious rewritten parent excerpt.'
        child['snapshot_sha256']=hashlib.sha256(canonical({'claim':value['claim'],'sources':child['sources']}).encode()).hexdigest()
        with self.assertRaisesRegex(ValueError,'inherited'):audit(value)

    def test_branches_need_not_be_linear(self):
        value=fixture();third=copy.deepcopy(value['rounds'][1]);third['number']=3;value['rounds'].append(third)
        self.assertEqual(audit(value)['rounds'][2]['parent'],1)

    def test_unresolved_child_is_not_a_verdict(self):
        value=fixture();value['rounds'][1].update(status='committed',result=None)
        self.assertEqual(audit(value)['rounds'][1]['verdict'],'unresolved')

    def test_semantic_reclassification_is_reported_not_rejected(self):
        value=fixture();result=value['rounds'][1]['result'];result['classifications'][0].update(relation='insufficient',quote='')
        result.update(verdict='contradiction_only',supporting_ids=[],insufficient_ids=[1])
        self.assertEqual(audit(value)['rounds'][1]['inherited_reclassifications'],[{'id':1,'from':'supports','to':'insufficient'}])

    def test_duplicate_keys_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'x.json';path.write_text('{"a":1,"a":2}')
            with self.assertRaisesRegex(ValueError,'duplicate'):read(path)

    def test_nonfinite_json_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'x.json';path.write_text('{"a":NaN}')
            with self.assertRaisesRegex(ValueError,'nonfinite'):read(path)


if __name__=='__main__':unittest.main()

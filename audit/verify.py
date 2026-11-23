"""CiteTrace lineage auditor: Python 3.10+, standard library only, no signer.

Offline checks establish internal consistency. --anchor binds the COMPLETE review
to a separately fetched latest-final review; it does not verify source truth.
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def integer(value):
    return type(value) is int


def audit(review):
    require(isinstance(review, dict), 'review must be an object')
    require(set(review) == {'id', 'title', 'claim', 'creator', 'rounds'}, 'unexpected review fields')
    require(isinstance(review['id'], str) and review['id'].isdigit() and int(review['id']) > 0, 'invalid review ID')
    require(isinstance(review['claim'], str) and 10 <= len(review['claim']) <= 600, 'invalid claim')
    require(isinstance(review['title'], str) and 3 <= len(review['title']) <= 100, 'invalid title')
    rounds = review['rounds']
    require(isinstance(rounds, list) and 1 <= len(rounds) <= 12, 'invalid round count')
    reports = []
    for n, row in enumerate(rounds, 1):
        require(isinstance(row, dict) and set(row) == {'number','parent','author','sources','snapshot_sha256','status','result'}, 'unexpected round fields')
        require(integer(row['number']) and row['number'] == n, 'round sequence mismatch')
        parent = row['parent']
        require(integer(parent) and (parent == 0 if n == 1 else 1 <= parent < n), 'invalid lineage parent')
        require(isinstance(row['author'], str) and row['author'], 'missing author')
        if n == 1:
            require(row['author'] == review['creator'], 'root author mismatch')
        sources = row['sources']
        require(isinstance(sources, list) and 1 <= len(sources) <= 8, 'invalid source count')
        for source in sources:
            require(isinstance(source, dict) and set(source) == {'reference','excerpt'}, 'unexpected source fields')
            require(isinstance(source['reference'], str) and 3 <= len(source['reference']) <= 200, 'invalid reference')
            require(isinstance(source['excerpt'], str) and 10 <= len(source['excerpt']) <= 1200, 'invalid excerpt')
            require(all(value == value.strip() for value in source.values()), 'noncanonical evidence whitespace')
        require(len({s['reference'] for s in sources}) == len(sources), 'duplicate references')
        require(len({s['excerpt'] for s in sources}) == len(sources), 'duplicate excerpts')
        if parent:
            prior = rounds[parent-1]
            require(prior['status'] == 'resolved', 'parent was not resolved')
            require(len(sources) > len(prior['sources']) and sources[:len(prior['sources'])] == prior['sources'], 'child removed or rewrote inherited evidence')
        digest = hashlib.sha256(canonical({'claim': review['claim'], 'sources': sources}).encode()).hexdigest()
        require(digest == row['snapshot_sha256'], 'snapshot SHA256 mismatch')
        require(row['status'] in ('committed','resolved'), 'unknown round status')
        counts = {key: [] for key in ('supports','contradicts','insufficient')}
        if row['status'] == 'committed':
            require(row['result'] is None, 'unresolved round has a result')
            verdict = 'unresolved'
        else:
            result = row['result']
            require(isinstance(result, dict) and set(result) == {'verdict','supporting_ids','contradicting_ids','insufficient_ids','classifications'}, 'invalid result fields')
            rows = result['classifications']
            require(isinstance(rows, list) and len(rows) == len(sources), 'incomplete classifications')
            for i, item in enumerate(rows, 1):
                require(isinstance(item, dict) and set(item) == {'id','relation','quote'}, 'invalid classification fields')
                require(integer(item['id']) and item['id'] == i, 'classification sequence mismatch')
                relation = item['relation']
                require(isinstance(relation, str) and relation in counts, 'unknown relation')
                require(item['quote'] == ('' if relation == 'insufficient' else sources[i-1]['excerpt']), 'noncanonical or fabricated quote')
                counts[relation].append(i)
            verdict = 'conflicted' if counts['supports'] and counts['contradicts'] else 'support_only' if counts['supports'] else 'contradiction_only' if counts['contradicts'] else 'insufficient'
            require(result['verdict'] == verdict, 'verdict does not follow classifications')
            for relation, field in [('supports','supporting_ids'),('contradicts','contradicting_ids'),('insufficient','insufficient_ids')]:
                require(all(integer(i) for i in result[field]) and result[field] == counts[relation], 'summary IDs mismatch')
        parent_rows = rounds[parent-1]['result']['classifications'] if parent else []
        current = row['result']['classifications'] if row['status'] == 'resolved' else []
        changes = [{'id': old['id'], 'from': old['relation'], 'to': current[i]['relation']} for i, old in enumerate(parent_rows) if current and current[i]['relation'] != old['relation']]
        reports.append({'round': n, 'parent': parent, 'verdict': verdict, 'snapshot_sha256': digest,
                        'inherited_sources': len(parent_rows), 'added_sources': len(sources)-len(parent_rows),
                        'inherited_reclassifications': changes})
    return {'review_id': review['id'], 'rounds': reports, 'internal_consistency': True,
            'source_truth_verified': False, 'consensus_reexecuted': False}


def read(path):
    # Duplicate keys must not silently select an attacker-controlled final value.
    def pairs(items):
        output = {}
        for key, value in items:
            require(key not in output, 'duplicate JSON key')
            output[key] = value
        return output
    return json.loads(Path(path).read_text(encoding='utf-8-sig'), object_pairs_hook=pairs,
                      parse_constant=lambda _: (_ for _ in ()).throw(ValueError('nonfinite JSON number')))


def verify_anchor(review, anchor):
    audit(review)
    audit(anchor)
    require(canonical(review) == canonical(anchor), 'complete review differs from anchor')
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('review', help='one complete review JSON object')
    parser.add_argument('--anchor', help='separately fetched latest-final review JSON')
    args = parser.parse_args()
    try:
        review = read(args.review)
        report = audit(review)
        report['anchor_match'] = None
        if args.anchor:
            anchor = read(args.anchor)
            report['anchor_match'] = verify_anchor(review, anchor)
        print(json.dumps(report, ensure_ascii=False, indent=2))
    except (ValueError, TypeError, KeyError) as error:
        print('AUDIT FAILED: ' + str(error), file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())

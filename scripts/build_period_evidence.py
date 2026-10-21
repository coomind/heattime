"""Project verified, committed analysis into a compact offline UI artifact; no engine/API calls."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def build():
    paths = [ROOT/'docs/real-data/replay-results.json', ROOT/'docs/competition-evidence/method-comparison.json']
    original, comparison = [json.loads(path.read_text(encoding='utf-8')) for path in paths]
    if original['original_sample_sha256'] != comparison['original_sample_sha256']:
        raise ValueError('Source fingerprint mismatch')
    if [row['date'] for row in original['days']] != [row['date'] for row in comparison['days']]:
        raise ValueError('Date coverage mismatch')
    fields = ('date','assigned','postponed','common_count','original_heat','proposed_heat','original_stop_count','salvaged','solver','coverage_optimal')
    compare_fields = ('date','cp_assigned','cp_postponed','greedy_assigned','greedy_postponed','assignment_gain','cp_common_heat','greedy_common_heat','cp_solver','cp_coverage_optimal')
    for row, other in zip(original['days'], comparison['days']):
        if (row['assigned'],row['postponed'],row['solver']) != (other['cp_assigned'],other['cp_postponed'],other['cp_solver']):
            raise ValueError('Frozen/replay result mismatch')
    data = {'version':1,'station':original['station'],'original_sample_sha256':original['original_sample_sha256'],
            'source_sha256':{path.name:hashlib.sha256(path.read_text(encoding='utf-8').encode()).hexdigest() for path in paths},
            'assumptions':'경기장 보정 +2.5℃를 더한 중앙 추정으로 판정(범위는 참고 표시), 동일 관측소 1곳 공유, 이 가상 대회의 대진과 휴식과 운영시간과 일몰 제약',
            'days':[{key:row[key] for key in fields} for row in original['days']],
            'comparison':{'summary':comparison['summary'],'days':[{**{key:row[key] for key in compare_fields},'common_count':len(row['common_match_ids'])} for row in comparison['days']]}}
    target = ROOT/'frontend/src/demo/period-evidence.json'
    target.write_text(json.dumps(data,ensure_ascii=False,separators=(',',':'))+'\n',encoding='utf-8')
    print(json.dumps({'days':len(data['days']),'bytes':target.stat().st_size}))
    return data


if __name__ == '__main__':
    build()

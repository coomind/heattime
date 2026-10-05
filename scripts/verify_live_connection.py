"""Explicitly authorized one-call live verification with a safe receipt.

No direct .env inspection. The application's runtime loader handles the key.
Print/store allowlisted parsed observations only; never print upstream content,
request URLs, headers, credential values, or exception messages.
"""
from pathlib import Path
import json
import sys
import time
import argparse
import math
from urllib.parse import urlencode
from urllib.request import Request,build_opener
from urllib.error import HTTPError
from datetime import datetime

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from fastapi.testclient import TestClient
from backend.app import create_app
from backend.weather.models import KST
from backend.weather.aws_live import FIELDS,request_bytes,ENDPOINT,NoRedirect,MAX_RESPONSE_BYTES,LiveFailure


def safe_shape(body):
    """Structural diagnostics without untrusted header text or error bodies."""
    try:
        lines=body.decode('utf-8-sig').splitlines()
    except UnicodeError:
        return {'utf8':False,'response_bytes':len(body)}
    headers=[]; widths=[]
    for line in lines:
        parts=line.strip().lstrip('#').split()
        if line.strip().startswith('#'):
            if parts and parts[0] in ('YYMMDDHHMI','TM'):
                headers.append({'columns':len(parts),'matches_documented':parts[1:]==FIELDS[1:],
                    'documented_columns':[p if p in FIELDS or p=='TM' else '<unknown>' for p in parts]})
        elif parts:
            widths.append(len(parts))
    return {'utf8':True,'response_bytes':len(body),'headers':headers,
            'data_row_count':len(widths),'data_column_counts':sorted(set(widths))}


def canonical_sample(body):
    """Reconstruct numeric rows, never save the raw response or its comments."""
    shape=safe_shape(body)
    if not shape.get('headers') or not all(row['matches_documented'] for row in shape['headers']):
        return None
    output=['# '+ ' '.join(FIELDS)]
    for line in body.decode('utf-8-sig').splitlines():
        if line.strip().startswith('#') or not line.strip():continue
        parts=line.split()
        if len(parts)!=18 or len(parts[0])!=12 or not parts[0].isdigit():return None
        try:
            datetime.strptime(parts[0],'%Y%m%d%H%M')
            station=int(parts[1]);values=[float(p) for p in parts[2:]]
        except ValueError:return None
        if not all(math.isfinite(v) for v in values):return None
        output.append(' '.join([parts[0],str(station),*(str(v) for v in values)]))
    return '\n'.join(output)+'\n' if len(output)>1 else None


def receipt(payload,elapsed,shape):
    fields=('station_id','valid_time','fetched_at','ta_c','rh_pct','ws_ms','station_pressure_hpa','sea_level_pressure_hpa','rain_60m_mm','is_mock')
    observation={key:payload['observation'][key] for key in fields} if payload.get('observation') else None
    return {'verified_at':datetime.now(KST).isoformat(),'status':payload['status'],
        'elapsed_seconds':round(elapsed,3),'application_http_status':200,
        'upstream_http_status':200 if shape else (payload.get('error') or {}).get('http_status'),
        'error':payload.get('error'),'retry_after_seconds':payload['retry_after_seconds'],
        'observation':observation,'upstream_shape':shape,'usage':payload['usage'],
        'risks':[{'venue_id':r['venue_id'],'venue_name':r['venue_name'],
            'wbgt_c':r['wbgt_c'],'wbgt_low_c':r['wbgt_low_c'],'wbgt_high_c':r['wbgt_high_c'],
            'level':r['level'],'method_version':r['method_version'],'is_mock':r['is_mock'],
            'solar_source':r['inputs']['solar']['source'],'pressure_hpa':r['inputs']['settings']['pressure_hpa']}
            for r in payload.get('risks',[])],
        'verification_scope':'Actual authorized API request and application endpoint. Not field WBGT validation.'}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--diagnostic-timeout',type=int,choices=[10,30],default=10)
    parser.add_argument('--at',help='Documented tm2 KST YYYYMMDDHHMI, diagnostic only')
    args=parser.parse_args()
    if args.at:datetime.strptime(args.at,'%Y%m%d%H%M')
    app=create_app()
    shape={}
    samples=[]
    def checked_transport(key,station):
        if args.diagnostic_timeout==10 and args.at is None:
            body=request_bytes(key,station)
        else:
            params={'stn':station,'disp':0,'help':0,'authKey':key}
            if args.at:params['tm2']=args.at
            try:
                with build_opener(NoRedirect()).open(Request(ENDPOINT+'?'+urlencode(params)),timeout=args.diagnostic_timeout) as response:
                    body=response.read(MAX_RESPONSE_BYTES+1)
            except HTTPError as exc:
                raise LiveFailure('HTTP 응답','진단 요청의 HTTP 응답 실패',exc.code,type(exc).__name__) from None
            except Exception as exc:
                raise LiveFailure('네트워크 연결','진단 요청 연결 실패',exception_class=type(exc).__name__) from None
        # No secret-bearing body is passed to the structural diagnostic.
        if key.encode() not in body:
            shape.update(safe_shape(body))
            sample=canonical_sample(body)
            if sample:samples.append(sample)
        return body
    app.state.live_provider.transport=checked_transport
    start=time.perf_counter()
    try:
        with TestClient(app) as client:
            response=client.post('/api/live-observations',json={'mode':'api','station_id':119})
            if response.status_code!=200:
                result={'status':'endpoint_error','http_status':response.status_code,
                        'verified_at':datetime.now(KST).isoformat()}
            else:
                result=receipt(response.json(),time.perf_counter()-start,shape)
    except Exception as exc:
        result={'status':'verification_error','exception_class':type(exc).__name__,
                'verified_at':datetime.now(KST).isoformat()}
    result['diagnostic_timeout_seconds']=args.diagnostic_timeout
    result['diagnostic_observation_time']=args.at
    output=ROOT/'data/output/live-connection-verification.json'
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    if result['status']=='ready' and samples:
        (output.parent/'aws-live-response-canonical.txt').write_text(samples[-1],encoding='utf-8')
    with (output.parent/'live-connection-attempts.jsonl').open('a',encoding='utf-8') as handle:
        handle.write(json.dumps(result,ensure_ascii=False)+'\n')
    print(json.dumps(result,ensure_ascii=True,indent=2))
    return 0 if result['status']=='ready' else 1


if __name__=='__main__':raise SystemExit(main())

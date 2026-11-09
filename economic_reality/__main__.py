import argparse
import json
import sys
from pathlib import Path

from .catalog import catalog
from .report import generate
from .sources import import_csv, update
from .store import Store


def main():
    p=argparse.ArgumentParser(description='경제의 실체: 수집·보고서·원천자료 이력 관리')
    p.add_argument('--data-dir',default='data')
    sub=p.add_subparsers(dest='command',required=True)
    u=sub.add_parser('update',help='공식 자료를 수집하고 개정 이력 추가')
    u.add_argument('--source',choices=['all','worldbank','fred'],default='all')
    u.add_argument('--start',type=int,default=2015)
    u.add_argument('--only',nargs='+',help='수집할 지표 ID')
    r=sub.add_parser('report',help='현재 데이터로 한국어 보고서 생성')
    r.add_argument('--output',default='reports')
    sub.add_parser('status',help='수집 상태 표시')
    sub.add_parser('export',help='정제 데이터 및 메타데이터 내보내기')
    i=sub.add_parser('import-csv',help='공식 CSV와 지표 메타데이터 가져오기')
    i.add_argument('csv')
    i.add_argument('metadata')
    args=p.parse_args()
    store=Store(args.data_dir)
    for meta in catalog(): store.register(meta)
    if args.command=='update':
        run,results=update(store,args.source,args.start,only=args.only)
        print(json.dumps({'실행':run,'결과':results},ensure_ascii=False,indent=2))
        return 0 if all(r[1]=='success' for r in results) else 2
    if args.command=='report':
        print(generate(store,args.output))
    elif args.command=='status':
        from .analysis import coverage
        print(coverage(store).to_string(index=False))
    elif args.command=='import-csv':
        print('가져오기 실행:',import_csv(store,args.csv,args.metadata))
    elif args.command=='export':
        out=Path(args.data_dir)/'exports'
        out.mkdir(exist_ok=True)
        from datetime import datetime,timezone
        stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%f')
        store.frame().to_csv(out/f'{stamp}.csv',index=False,encoding='utf-8-sig')
        (out/f'{stamp}.metadata.json').write_text(json.dumps(store.catalog(),ensure_ascii=False,indent=2))
        print(out)
    return 0


if __name__=='__main__':
    sys.exit(main())

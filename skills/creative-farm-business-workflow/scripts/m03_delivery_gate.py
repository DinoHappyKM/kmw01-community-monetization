"""核對M03交付紀錄；不代替Notion操作或人工視覺確認。"""
import json,sys

def check(record):
    issues=[]
    for key in ('article_confirmed','layout_confirmed','content_readback'):
        if record.get(key) is not True: issues.append(key)
    if record.get('cover_choice')=='skip':
        if not str(record.get('skip_confirmation','')).strip(): issues.append('skip_confirmation')
    else:
        for key in ('cover_asset','expected_cover_url'):
            if not isinstance(record.get(key),str) or not record[key].strip(): issues.append(key)
        if record.get('cover_confirmed') is not True: issues.append('cover_confirmed')
        cover=record.get('cover_readback')
        if not isinstance(cover,dict): issues.append('cover_readback')
        else:
            kind=cover.get('type');data=cover.get(kind,{})
            url=data.get('url') if isinstance(data,dict) else None
            if not isinstance(url,str) or not url: issues.append('cover_readback_url')
            elif url!=record.get('expected_cover_url'): issues.append('cover_source_mismatch')
    return {'ready':not issues,'issues':issues,'scope':'record-consistency-only; account/mobile/visual acceptance separate'}

if __name__=='__main__':
    with open(sys.argv[1],encoding='utf-8') as f: result=check(json.load(f))
    print(json.dumps(result,ensure_ascii=False,indent=2))
    raise SystemExit(0 if result['ready'] else 1)

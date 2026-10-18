"""以原始ZIP目錄驗證可攜路徑，不經Windows ZipInfo名稱正規化。"""
from pathlib import Path,PurePosixPath
import re,stat,struct
RESERVED={"CON","PRN","AUX","NUL",*[f"COM{i}" for i in range(1,10)],*[f"LPT{i}" for i in range(1,10)]}
def entries(path):
    data=Path(path).read_bytes();end=data.rfind(b"PK\x05\x06",max(0,len(data)-65557))
    if end<0 or end+22>len(data):raise ValueError("缺少ZIP結尾")
    e=struct.unpack_from("<4s4H2IH",data,end)
    if e[1] or e[2] or e[3]!=e[4]:raise ValueError("不支援分卷ZIP")
    count,size,pos,comment=e[4],e[5],e[6],e[7]
    if pos+size!=end or end+22+comment!=len(data):raise ValueError("ZIP目錄範圍不符")
    result=[];limit=pos+size
    for _ in range(count):
        if pos+46>limit:raise ValueError("ZIP目錄截斷")
        h=struct.unpack_from("<4s6H3I5H2I",data,pos)
        if h[0]!=b"PK\x01\x02":raise ValueError("ZIP目錄標記不符")
        n,x,c=h[10:13];raw=data[pos+46:pos+46+n]
        if len(raw)!=n or pos+46+n+x+c>limit:raise ValueError("ZIP檔名截斷")
        try:name=raw.decode("utf-8" if h[3]&0x800 else "cp437")
        except UnicodeDecodeError as ex:raise ValueError("ZIP檔名編碼錯誤") from ex
        local=h[16]
        if local+30>e[6]:raise ValueError("本機檔頭超出資料範圍")
        lh=struct.unpack_from("<4s5H3I2H",data,local)
        if lh[0]!=b"PK\x03\x04":raise ValueError("本機檔頭標記錯誤")
        localname=data[local+30:local+30+lh[9]]
        if localname!=raw or lh[2]!=h[3]:raise ValueError("中央目錄與本機檔名或旗標不符")
        result.append((name,h[3],h[15]));pos+=46+n+x+c
    if pos!=limit or not result:raise ValueError("ZIP目錄數量或長度錯誤")
    return result

def validate(path):
    errors=[]
    try:items=entries(path)
    except (ValueError,struct.error) as ex:return [str(ex)]
    roots=set();seen=set()
    for name,flag,attr in items:
        parts=PurePosixPath(name).parts
        if not name or "\\" in name or "\x00" in name or name.startswith("/") or re.match(r"^[A-Za-z]:",name) or ".." in parts:errors.append(f"不安全路徑：{name}")
        if any(ord(c)>127 for c in name) and not flag&0x800:errors.append(f"中文檔名未標UTF-8：{name}")
        if flag&1:errors.append(f"不接受加密檔：{name}")
        if stat.S_ISLNK(attr>>16):errors.append(f"不接受符號連結：{name}")
        for part in parts:
            if part.endswith((" ",".")) or any(c in '<>:"\\|?*' for c in part) or part.rstrip(". ").split(".")[0].upper() in RESERVED:errors.append(f"跨平台檔名不相容：{name}")
        key=name.rstrip("/").casefold()
        if key in seen:errors.append(f"重複或大小寫碰撞：{name}")
        seen.add(key)
        if parts:roots.add(parts[0])
    if len(roots)!=1:errors.append("不是單一根目錄")
    if not any(PurePosixPath(n).name=="SKILL.md" for n,_,_ in items):errors.append("缺SKILL.md")
    return errors
if __name__=="__main__":
    import sys
    errors=validate(sys.argv[1]);print("\n".join(errors) if errors else "原始ZIP路徑驗證通過")
    raise SystemExit(1 if errors else 0)

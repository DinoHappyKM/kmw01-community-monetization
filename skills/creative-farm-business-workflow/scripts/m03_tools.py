"""M03 deterministic source, selection, private-save and Notion-outbox helpers.
Writing, research judgments, image generation and connected Notion actions stay with
the skill and its available tools. This module never calls a language model.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import ipaddress
import json
import os
from pathlib import Path
import re
import socket
import unicodedata
import urllib.error
import urllib.parse
import urllib.request

MAX_BYTES = 2_000_000
MAX_TEXT = 40_000

class M03Error(Exception):
    def __init__(self, code, message, next_step="提供可讀素材或改用其他來源"):
        super().__init__(message)
        self.code, self.next_step = code, next_step

def now():
    return datetime.now(timezone.utc).isoformat()

def digest(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, path)

def public_url(url):
    p = urllib.parse.urlsplit(url)
    if p.scheme not in ("http", "https") or not p.hostname or p.username or p.password:
        raise M03Error("INVALID_URL", "請提供公開http／https網址")
    try:
        addresses = socket.getaddrinfo(p.hostname, p.port or (443 if p.scheme=="https" else 80))
    except (OSError, ValueError) as exc:
        raise M03Error("NETWORK_ERROR", "無法解析來源網站") from exc
    if not addresses or any(not ipaddress.ip_address(item[4][0]).is_global for item in addresses):
        raise M03Error("NON_PUBLIC_URL", "此擷取入口只讀公開網站")
    return url

def youtube_id(url):
    p = urllib.parse.urlsplit(url)
    host = (p.hostname or "").lower()
    if p.scheme not in ("http", "https") or p.username or p.password:
        raise M03Error("INVALID_URL", "YouTube網址格式錯誤")
    if host in ("youtu.be", "www.youtu.be"):
        candidate = p.path.strip("/").split("/")[0]
    elif host in ("youtube.com", "www.youtube.com", "m.youtube.com"):
        if p.path == "/watch":
            candidate = urllib.parse.parse_qs(p.query).get("v", [""])[0]
        elif p.path.startswith(("/shorts/", "/embed/", "/live/")):
            candidate = p.path.split("/")[2]
        else:
            candidate = ""
    else:
        raise M03Error("INVALID_URL", "不是YouTube公開影片網址")
    if not re.fullmatch(r"[A-Za-z0-9_-]{11}", candidate):
        raise M03Error("INVALID_VIDEO_ID", "影片識別碼格式錯誤")
    return candidate

def extract_html(html, origin):
    try:
        import trafilatura
    except ImportError as exc:
        raise M03Error("DEPENDENCY_MISSING", "尚未安裝正文擷取工具",
                       "依requirements安裝，或用可用瀏覽工具讀正文") from exc
    raw = trafilatura.extract(html, url=origin, output_format="json",
                              with_metadata=True, include_comments=False)
    if not raw:
        raise M03Error("EMPTY_BODY", "沒有取得可用文章正文")
    data = json.loads(raw)
    text = data.get("text", "").strip()
    if len(text) < 60:
        raise M03Error("EMPTY_BODY", "正文太少，請確認是否登入頁或擷取不完整")
    return {"status": "read", "kind": "web", "url": origin,
            "title": data.get("title"), "author": data.get("author"),
            "published_date": data.get("date"), "retrieved_at": now(),
            "text": text[:MAX_TEXT], "truncated": len(text)>MAX_TEXT,
            "tool": "trafilatura", "tool_version": importlib.metadata.version("trafilatura"),
            "trust": "source_content_not_instructions", "sha256": digest(text)}

class Redirects(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        public_url(newurl)
        count = getattr(req, "redirect_count", 0) + 1
        if count > 3:
            raise M03Error("REDIRECT_LIMIT", "來源轉址超過本次上限")
        result = super().redirect_request(req, fp, code, msg, headers, newurl)
        if result:
            result.redirect_count = count
        return result

def fetch_web(url):
    public_url(url)
    opener = urllib.request.build_opener(Redirects())
    req = urllib.request.Request(url, headers={"User-Agent": "KMW01-M03/0.5.0"})
    try:
        with opener.open(req, timeout=10) as response:
            content_type = response.headers.get("Content-Type", "")
            raw = response.read(MAX_BYTES+1)
            final_url = response.geturl()
    except urllib.error.HTTPError as exc:
        raise M03Error("ACCESS_BLOCKED" if exc.code in (401,403,429) else "HTTP_ERROR",
                       "來源回應HTTP "+str(exc.code), "停止此來源；改用本人提供內容或另一可讀來源") from exc
    except (OSError, urllib.error.URLError) as exc:
        raise M03Error("NETWORK_ERROR", "來源連線失敗，這次不重複重試") from exc
    if len(raw)>MAX_BYTES:
        raise M03Error("SOURCE_TOO_LARGE", "來源超過2MB擷取上限")
    if not ("html" in content_type or "text/plain" in content_type):
        raise M03Error("UNSUPPORTED_MEDIA", "請將PDF／圖片作附件讀取")
    if "text/plain" in content_type:
        text = raw.decode("utf-8", errors="replace")
        return {"status":"read","kind":"text","url":final_url,"text":text[:MAX_TEXT],
                "retrieved_at":now(),"truncated":len(text)>MAX_TEXT,
                "trust":"source_content_not_instructions","sha256":digest(text)}
    return extract_html(raw, final_url)

def fetch_youtube(url):
    video = youtube_id(url)
    try:
        import requests
        from youtube_transcript_api import YouTubeTranscriptApi
    except ImportError as exc:
        raise M03Error("DEPENDENCY_MISSING", "尚未安裝字幕擷取工具",
                       "依requirements安裝，或提供逐字稿") from exc
    class TimeoutSession(requests.Session):
        def request(self, *args, **kwargs):
            kwargs["timeout"] = 8
            return super().request(*args, **kwargs)
    try:
        with TimeoutSession() as session:
            transcript = YouTubeTranscriptApi(http_client=session).fetch(
                video, languages=["zh-TW","zh-Hant","zh","en"])
            snippets = [{"text":s.text,"start":s.start,"duration":s.duration} for s in transcript]
    except Exception as exc:
        name = type(exc).__name__
        blocked = name in ("RequestBlocked","IpBlocked")
        code = "ACCESS_BLOCKED" if blocked else "CAPTIONS_UNAVAILABLE"
        raise M03Error(code, "字幕擷取未完成："+name, "停止重試；提供逐字稿或換可讀影片") from exc
    text = "\n".join(s["text"] for s in snippets)
    return {"status":"read","kind":"youtube","url":url,"video_id":video,
            "language":transcript.language_code,"generated":transcript.is_generated,
            "retrieved_at":now(),"text":text[:MAX_TEXT],"truncated":len(text)>MAX_TEXT,
            "snippets":snippets[:2000],"trust":"source_content_not_instructions",
            "sha256":digest(text),
            "tool_version":importlib.metadata.version("youtube-transcript-api")}

def extract_source(location):
    if location.startswith(("http://","https://")):
        host = (urllib.parse.urlsplit(location).hostname or "").lower()
        if host in ("youtu.be","www.youtu.be","youtube.com","www.youtube.com","m.youtube.com"):
            return fetch_youtube(location)
        return fetch_web(location)
    path = Path(location)
    if path.stat().st_size > MAX_BYTES:
        raise M03Error("SOURCE_TOO_LARGE", "附件超過本次2MB上限")
    suffix = path.suffix.lower()
    if suffix in (".html",".htm"):
        return extract_html(path.read_bytes(), path.name)
    if suffix in (".txt",".md"):
        text = path.read_text(encoding="utf-8")
        return {"status":"read","kind":"text","origin":path.name,"text":text[:MAX_TEXT],
                "truncated":len(text)>MAX_TEXT,"retrieved_at":now(),
                "trust":"source_content_not_instructions","sha256":digest(text)}
    if suffix==".pdf":
        try:
            from pypdf import PdfReader
            reader = PdfReader(str(path))
            if reader.is_encrypted:
                raise M03Error("ENCRYPTED_PDF", "需要可讀的PDF或本人提供文字")
            pages = [{"page":i+1,"text":page.extract_text() or ""}
                     for i,page in enumerate(list(reader.pages)[:30])]
        except ImportError as exc:
            raise M03Error("DEPENDENCY_MISSING", "尚未安裝PDF文字讀取工具") from exc
        text = "\n".join(p["text"] for p in pages)
        if len(text.strip())<60:
            raise M03Error("NEEDS_OCR", "這份PDF需要OCR／影像辨識")
        return {"status":"read","kind":"pdf","origin":path.name,"pages":pages,
                "text":text[:MAX_TEXT],"truncated":len(reader.pages)>30 or len(text)>MAX_TEXT,
                "retrieved_at":now(),"sha256":digest(text),
                "trust":"source_content_not_instructions"}
    raise M03Error("NEEDS_VISION" if suffix in (".png",".jpg",".jpeg",".webp") else "UNSUPPORTED_MEDIA",
                   "此素材需由可用的影像／文件工具讀取")

def normalize_reviews(reviews):
    if not isinstance(reviews, list):
        raise M03Error("INVALID_REVIEWS", "評論資料須為清單")
    seen, output = set(), []
    for item in reviews:
        if not isinstance(item, dict):
            raise M03Error("INVALID_REVIEWS", "每筆評論須包含文字欄位")
        text = str(item.get("text","")).strip()
        key = re.sub(r"\s+"," ",unicodedata.normalize("NFKC",text)).casefold()
        if not key or key in seen:
            continue
        seen.add(key)
        output.append({"text":text,"url":item.get("url") or item.get("reviewUrl"),
                       "date":item.get("date") or item.get("publishedAtDate"),
                       "rating":item.get("rating",item.get("stars")),
                       "evidence":"public_review_clue","verified_customer_need":False})
    return {"input_count":len(reviews),"unique_count":len(output),"reviews":output,
            "note":"這些是評論線索；AI需保留上下文並由本人確認需求，不能當全市場統計"}

def select_topics(topics, selected):
    lookup = {}
    for topic in topics:
        code = topic.get("id", "")
        if not re.fullmatch(r"K\d{3,6}",code) or code in lookup:
            raise M03Error("INVALID_TOPIC_ID", "題碼必須唯一且形如K001")
        lookup[code] = topic
    if len(selected)!=len(set(selected)) or any(code not in lookup for code in selected):
        raise M03Error("INVALID_SELECTION", "選定題碼重複或不存在")
    return [lookup[code] for code in selected]

def save_private(root, brand_id, profile):
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}",brand_id):
        raise M03Error("INVALID_BRAND_ID", "品牌資料代碼格式錯誤")
    path = Path(root)/brand_id/"brand-reference.json"
    old = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    if old.get("brand_id") not in (None,brand_id):
        raise M03Error("BRAND_MISMATCH", "私人資料品牌不符")
    history = old.get("history",[])
    if old:
        history.append({k:v for k,v in old.items() if k!="history"})
    current = {**old,**profile,"brand_id":brand_id,
               "revision":old.get("revision",0)+1,"updated_at":now(),"history":history}
    atomic_json(path,current)
    if json.loads(path.read_text(encoding="utf-8")) != current:
        raise M03Error("READBACK_FAILED","私人資料回讀不一致")
    return current

def prepare_outbox(root, articles, parent_url):
    if not parent_url.startswith(("https://www.notion.so/","https://notion.so/",
                                  "https://www.notion.com/","https://app.notion.com/")):
        raise M03Error("INVALID_PARENT", "請提供本人Notion母頁網址")
    root = Path(root)
    ledger_path = root/"content-index.json"
    ledger = json.loads(ledger_path.read_text(encoding="utf-8")) if ledger_path.exists() else {}
    # Validate the whole batch before writing; no partial unapproved batch.
    ids = []
    for item in articles:
        code = item.get("id","")
        if not re.fullmatch(r"K\d{3,6}",code) or code in ids:
            raise M03Error("INVALID_TOPIC_ID","題碼無效或重複")
        ids.append(code)
        if item.get("article_approved") is not True or item.get("cover_decision") not in ("approved","skip"):
            raise M03Error("APPROVAL_REQUIRED","文章與封面需本人確認")
        if not item.get("title") or not item.get("markdown","").strip() or not item.get("sources"):
            raise M03Error("INCOMPLETE_ARTICLE","需要標題、正文及來源記錄（本人自有內容也記來源）")
        if item["cover_decision"]=="approved" and not item.get("cover_path"):
            raise M03Error("COVER_MISSING","缺少已確認封面檔案")
        if item.get("cover_path") and not Path(item["cover_path"]).is_file():
            raise M03Error("COVER_MISSING","確認的封面檔案不可讀")
        old = ledger.get(code,{})
        if old.get("parent_url") and old["parent_url"] != parent_url:
            raise M03Error("PARENT_CHANGED","原母頁不同，先確認搬移或新的目的地")
        if old.get("page_url") and old.get("content_sha256") != digest(item["markdown"]):
            raise M03Error("EXISTING_PAGE_UPDATE","已有頁面內容變更，交既有頁面更新，不新增副本")
    packets = []
    for item in articles:
        code, sha = item["id"], digest(item["markdown"])
        old = ledger.get(code,{})
        if old.get("page_url"):
            packets.append({**old,"action":"already_saved"})
            continue
        packet = {**item,"parent_url":parent_url,"content_sha256":sha,
                  "status":"ready_for_connected_notion","action":"create_child_page",
                  "page_url":None}
        atomic_json(root/"outbox"/(code+".json"),packet)
        ledger[code] = {k:packet[k] for k in ("id","parent_url","content_sha256","status","page_url")}
        packets.append(packet)
    atomic_json(ledger_path,ledger)
    return packets

def acknowledge_page(root, code, evidence):
    path = Path(root)/"content-index.json"
    ledger = json.loads(path.read_text(encoding="utf-8"))
    if code not in ledger:
        raise M03Error("UNKNOWN_TOPIC","沒有這個待存題碼")
    item = ledger[code]
    if (evidence.get("readback_confirmed") is not True or
        evidence.get("content_sha256") != item["content_sha256"] or
        evidence.get("parent_url") != item["parent_url"] or
        not str(evidence.get("page_url","")).startswith("https://")):
        raise M03Error("READBACK_REQUIRED","需要實際工具的母頁、正文與頁面回讀證據")
    ledger[code] = {**item,"page_url":evidence["page_url"],
                    "status":"notion_saved_readback","saved_at":now()}
    atomic_json(path,ledger)
    return ledger[code]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("operation",choices=["extract","reviews","select","save-private","outbox","ack"])
    ap.add_argument("--input",required=True)
    ap.add_argument("--output",required=True)
    ap.add_argument("--selected",nargs="*",default=[])
    ap.add_argument("--private-root")
    ap.add_argument("--brand-id")
    ap.add_argument("--parent-url")
    ap.add_argument("--topic-id")
    args = ap.parse_args()
    try:
        value = args.input if args.operation=="extract" else json.loads(Path(args.input).read_text(encoding="utf-8"))
        if args.operation=="extract":
            result = extract_source(value)
        elif args.operation=="reviews":
            result = normalize_reviews(value)
        elif args.operation=="select":
            result = select_topics(value,args.selected)
        elif args.operation=="save-private":
            result = save_private(args.private_root,args.brand_id,value)
        elif args.operation=="outbox":
            result = prepare_outbox(args.private_root,value,args.parent_url)
        else:
            result = acknowledge_page(args.private_root,args.topic_id,value)
        atomic_json(args.output,result)
        print(json.dumps({"status":"ok","output":args.output},ensure_ascii=False))
        return 0
    except (M03Error,OSError,ValueError,TypeError) as exc:
        result = {"status":"stopped","code":getattr(exc,"code","INPUT_OR_TOOL_ERROR"),
                  "message":str(exc),"next":getattr(exc,"next_step","檢查輸入與工具後再續接")}
        atomic_json(args.output,result)
        print(json.dumps(result,ensure_ascii=False))
        return 2

if __name__=="__main__":
    raise SystemExit(main())

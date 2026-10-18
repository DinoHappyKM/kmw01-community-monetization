"""Generate deterministic QR and independently verify QR/poster images."""
import argparse,json
from pathlib import Path
def verify(path,url):
    import zxingcpp
    from PIL import Image
    found=[r.text for r in zxingcpp.read_barcodes(Image.open(path).convert("RGB"))]
    if url not in found: raise ValueError("Final image did not decode to the exact input URL")
    return {"image":str(path),"decoded_exact":True}
def main():
    p=argparse.ArgumentParser();p.add_argument("--url",required=True);p.add_argument("--output",type=Path);p.add_argument("--verify-image",type=Path);a=p.parse_args()
    if not a.url.startswith(("https://","http://")): p.error("A real http(s) URL is required")
    if not a.output and not a.verify_image:p.error("Provide --output or --verify-image")
    checks=[]
    if a.output:
        import qrcode
        q=qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M,box_size=16,border=4)
        q.add_data(a.url);q.make(fit=True);a.output.parent.mkdir(parents=True,exist_ok=True)
        q.make_image(fill_color="black",back_color="white").save(a.output)
        checks.append(verify(a.output,a.url))
    if a.verify_image: checks.append(verify(a.verify_image,a.url))
    print(json.dumps({"status":"passed","checks":checks},ensure_ascii=False))
if __name__=="__main__":main()

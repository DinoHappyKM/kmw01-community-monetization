import hashlib,importlib.util,json,re,struct,tempfile,unittest,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
ZIP=ROOT/"downloads/kmw01-community-monetization-0.5.3.zip"
spec=importlib.util.spec_from_file_location("rawzip",ROOT/"tools/verify_zip_raw.py");raw=importlib.util.module_from_spec(spec);spec.loader.exec_module(raw)
sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
class Publication(unittest.TestCase):
 def test_01_real_archive_raw_paths(self):self.assertEqual(raw.validate(ZIP),[])
 def test_02_backslash_fixture_is_raw_and_rejected(self):
  with tempfile.TemporaryDirectory() as td:
   f=Path(td)/"bad.zip"
   with zipfile.ZipFile(f,"w") as z:z.writestr("root/bad/SKILL.md","x")
   f.write_bytes(f.read_bytes().replace(b"root/bad/SKILL.md",b"root\\bad\\SKILL.md"))
   self.assertEqual(raw.entries(f)[0][0],"root\\bad\\SKILL.md");self.assertTrue(raw.validate(f))
 def test_03_path_traversal_rejected(self):
  with tempfile.TemporaryDirectory() as td:
   f=Path(td)/"bad.zip"
   with zipfile.ZipFile(f,"w") as z:z.writestr("root/SKILL.md","x");z.writestr("root/../out.md","x")
   self.assertTrue(raw.validate(f))
 def test_04_collision_rejected(self):
  with tempfile.TemporaryDirectory() as td:
   f=Path(td)/"bad.zip"
   with zipfile.ZipFile(f,"w") as z:z.writestr("root/SKILL.md","x");z.writestr("root/skill.md","x")
   self.assertTrue(raw.validate(f))
 def test_05_local_header_mismatch_rejected(self):
  with tempfile.TemporaryDirectory() as td:
   f=Path(td)/"bad.zip"
   with zipfile.ZipFile(f,"w") as z:z.writestr("root/SKILL.md","x")
   f.write_bytes(f.read_bytes().replace(b"root/SKILL.md",b"root/OTHER.md",1));self.assertTrue(raw.validate(f))
 def test_06_truncated_archive_rejected(self):
  with tempfile.TemporaryDirectory() as td:
   f=Path(td)/"bad.zip";f.write_bytes(b"PK");self.assertTrue(raw.validate(f))
 def test_07_crc_extraction_and_source_parity(self):
  with zipfile.ZipFile(ZIP) as z,tempfile.TemporaryDirectory() as td:
   self.assertIsNone(z.testzip());z.extractall(td);pkg=Path(td)/"w0001-creative-farm-workflow"
   for name in ["skills","assets"]:
    for f in (ROOT/name).rglob("*"):
     if f.is_file():self.assertEqual(sha(f),sha(pkg/f.relative_to(ROOT)))
   self.assertEqual(sha(ROOT/"plugin.json"),sha(pkg/"plugin.json"))
   listed={line.split("  ",1)[1]:line.split("  ",1)[0] for line in (pkg/"SHA256SUMS.txt").read_text(encoding="utf-8").splitlines()}
   actual={f.relative_to(pkg).as_posix():sha(f) for f in pkg.rglob("*") if f.is_file() and f.name!="SHA256SUMS.txt"};self.assertEqual(listed,actual)
 def test_08_manifest_and_disclosure(self):
  m=json.loads((ROOT/"plugin.json").read_text(encoding="utf-8"));self.assertEqual(m["version"],"0.5.3");self.assertEqual(m["name"],"w0001-creative-farm-workflow");self.assertEqual(m["repository"],"https://github.com/DinoHappyKM/kmw01-community-monetization")
  ui=m["extensions"]["com.openai"]["interface"];self.assertEqual(ui["displayName"],"黃嘉偉KMW01私域社群變現");self.assertLessEqual(len(ui["shortDescription"]),30)
  for k in ["composerIcon","logo"]:self.assertTrue((ROOT/ui[k]).is_file())
  version=json.loads((ROOT/"VERSION.json").read_text(encoding="utf-8"));self.assertEqual(version["student_account_installation"],"user-reported-archive-import")
 def test_09_markdown_references(self):
  for f in ROOT.rglob("*.md"):
   for target in re.findall(r"\[[^]\n]+\]\(([^)]+)\)",f.read_text(encoding="utf-8")):
    if re.match(r"[a-zA-Z][a-zA-Z0-9+.-]*:",target) or target.startswith("#"):continue
    target=target.split("?")[0].split("#")[0];q=(f.parent/target).resolve();self.assertTrue(q.is_relative_to(ROOT.resolve()));self.assertTrue(q.is_file(),f"{f.relative_to(ROOT)}: {target}")
 def test_10_website_relative_resources(self):
  html=(ROOT/"docs/index.html").read_text(encoding="utf-8")
  for name in re.findall(r'(?:src|href)="([^"]+)"',html):
   if re.match(r"[a-z]+:",name) or name.startswith("#"):continue
   self.assertTrue((ROOT/"docs"/name).is_file(),name)
  css=(ROOT/"docs/assets/fonts/fonts.css").read_text(encoding="utf-8")
  for name in re.findall(r"url\(([^)]+)\)",css):self.assertTrue((ROOT/"docs/assets/fonts"/name).is_file())
 def test_11_font_and_logo_consistency(self):
  self.assertEqual(sha(ROOT/"assets/logo.png"),sha(ROOT/"docs/assets/logo.png"));self.assertIn("SIL OPEN FONT LICENSE",(ROOT/"docs/assets/fonts/OFL.txt").read_text(encoding="utf-8"))
 def test_12_runtime_and_private_data_excluded(self):
  for f in ROOT.rglob("*"):
   self.assertFalse(f.is_symlink());self.assertNotIn(f.name,[".env","private","__pycache__",".venv","node_modules",".git"]);self.assertNotEqual(f.suffix,".pyc")
   if f.suffix in [".md",".json",".html",".js",".css",".yaml"]:
    s=f.read_text(encoding="utf-8");self.assertIsNone(re.search(r"(?:sk-proj-[A-Za-z0-9]{20,}|ghp_[A-Za-z0-9]{20,}|[CG]:[/\\]Users[/\\])",s),str(f))
 def test_13_workbook_and_word_template(self):
  s=ROOT/"skills/creative-farm-business-workflow"
  self.assertEqual(sha(ROOT/"downloads/我的私域社群工作簿_空白.md"),sha(s/"assets/student-workbook-template.md"))
  with zipfile.ZipFile(s/"assets/m08-quote-template.docx") as z:self.assertIsNone(z.testzip());self.assertIn("報價單",z.read("word/document.xml").decode("utf-8"))
 def test_14_download_digest(self):
  for line in (ROOT/"downloads/SHA256SUMS.txt").read_text(encoding="utf-8").splitlines():
   digest,name=line.split("  ",1);self.assertEqual(sha(ROOT/"downloads"/name),digest)
if __name__=="__main__":unittest.main(verbosity=2)

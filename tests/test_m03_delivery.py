import copy,importlib.util,struct,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
S=ROOT/'skills/creative-farm-business-workflow'
spec=importlib.util.spec_from_file_location('gate',S/'scripts/m03_delivery_gate.py');gate=importlib.util.module_from_spec(spec);spec.loader.exec_module(gate)
class M03Delivery(unittest.TestCase):
 def setUp(self):
  self.r={'article_confirmed':True,'layout_confirmed':True,'content_readback':True,'cover_choice':'required','cover_asset':'article.png','cover_confirmed':True,'expected_cover_url':'https://example.org/article.png','cover_readback':{'type':'external','external':{'url':'https://example.org/article.png'}}}
 def test_complete_record(self): self.assertTrue(gate.check(self.r)['ready'])
 def test_null_native_cover_blocks_even_with_body_image(self):
  self.r.update(cover_readback=None,body_image_readback=True);self.assertFalse(gate.check(self.r)['ready'])
 def test_old_cover_blocks(self):
  self.r['cover_readback']['external']['url']='https://example.org/old.png';self.assertIn('cover_source_mismatch',gate.check(self.r)['issues'])
 def test_generation_without_user_confirmation_blocks(self):
  self.r['cover_confirmed']=False;self.assertFalse(gate.check(self.r)['ready'])
 def test_missing_actual_asset_blocks(self):
  del self.r['cover_asset'];self.assertFalse(gate.check(self.r)['ready'])
 def test_explicit_skip_allowed(self):
  self.r.update(cover_choice='skip',skip_confirmation='本人這篇不要封面',cover_readback=None);self.assertTrue(gate.check(self.r)['ready'])
 def test_silent_skip_blocks(self):
  self.r.update(cover_choice='skip',cover_readback=None);self.assertFalse(gate.check(self.r)['ready'])
 def test_unread_article_blocks(self):
  self.r['content_readback']=False;self.assertFalse(gate.check(self.r)['ready'])
 def test_template_contains_actual_image(self):
  data=(S/'assets/m03-cover-example.png').read_bytes();self.assertEqual(data[:8],b'\x89PNG\r\n\x1a\n');w,h=struct.unpack('>II',data[16:24]);self.assertGreater(w,h);self.assertIn('(m03-cover-example.png)',(S/'assets/m03-notion-page-template.md').read_text(encoding='utf-8'))
 def test_core_other_modules_unchanged(self):
  self.assertIn('M08',(S/'SKILL.md').read_text(encoding='utf-8'));self.assertTrue((S/'assets/m08-quote-template.docx').is_file())
if __name__=='__main__':unittest.main(verbosity=2)

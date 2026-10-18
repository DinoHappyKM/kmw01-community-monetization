# M03工具操作與能力界線

Python可用時執行同包scripts/m03_tools.py；沒有Python可用同功能的已連接瀏覽／文件工具，保持來源與狀態規則。這套工具只負責確定性工作，AI依M03方法寫文及生成需求。它不呼叫LLM、不自行產圖、不持有NotionToken／帳號、不排程。

依賴版本由scripts/requirements.txt指定，來自GitHub項目trafilatura與youtube-transcript-api；PDF使用pypdf。依賴未安裝時回報缺少，先使用可用工具或提供人工材料；不悄悄安裝到全系統。教師本機隔離runtime不發給學生。

執行格式（python指當次實際Python，可替換為可用路徑）：
- extract：python scripts/m03_tools.py extract --input 來源URL或附件 --output 本人資料/source.json
- reviews：reviews --input 公開評論匯出.json --output 需求線索.json
- select：select --input 題目清單.json --selected K001 K003 --output 已選題.json
- save-private：save-private --input 品牌設定增量.json --private-root 本人資料夾 --brand-id 品牌代碼 --output 回讀結果.json
- outbox：outbox --input 已確認文章清單.json --private-root 本人內容庫 --parent-url 本人母頁URL --output 待寫頁清單.json
- ack：ack --input 實際工具回讀證據.json --private-root 本人內容庫 --topic-id K001 --output 保存結果.json

題目有唯一id與title；評論清單接受text/url/date/rating或Apify的reviewUrl/publishedAtDate/stars。去重結果只列線索，不生成「已驗證需求」。

已確認文章每項：id、title、markdown、sources、article_approved=true、cover_decision=approved或skip；approved需可讀cover_path。本人自有觀點也記sources中的來源類型。outbox先驗全批再寫，生成每題JSON與content-index.json，狀態ready_for_connected_notion。重複執行保持同題一個outbox，母頁變更需先確認。

利用本人Notion工具讀母頁／查原頁→新建子頁或更新→上傳封面→回讀後，由AI生成證據：page_url、parent_url、content_sha256與readback_confirmed=true，再ack。此旗標只能在實際回讀完成後填；程式驗資料一致性，不會自行核實Notion遠端。尚無頁面時不填虛構URL。CLI不提供刪除命令。

每次讀取上限2MB／正文4萬字，PDF最多30頁，超限回報或標截斷；網頁請求10秒、字幕單请求8秒，無代理绕路與自动重試。批次由開發／操作外層設定總時間上限；單段字幕方法也需要外層超時，避免多请求合計拖長。圖片與掃描PDF交可用影像／OCR工具，不用空文字假裝讀成功。

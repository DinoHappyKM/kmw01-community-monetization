# 0.5.3｜M03品牌版型與封面驗證

2026-10-23；Skill0.7.7／導覽0.2.3。正式來源P017，採用P022 0.1.2喜好圖與一頁試版方法。

## 修改與檢查範圍
M03兩入口→確認文章→已有版型沿用／首次喜好圖與一頁試版→確認保存→實際文章封面→本人確認→原生cover設定與回讀。內含實際示範PNG、有圖範本與可執行交付紀錄檢查。示範不是學員品牌。

本輪執行14項封裝回歸與10項M03正反例，涵蓋cover=null、正文已有圖但原生封面缺失、舊圖、未確認及明確略過等情況。本輪24項均通過，官方Skill格式亦通過；程式檢查紀錄一致性，不能代替Notion或帳號操作。

## 狀態界線
先前本人回報手機ZIP匯入成功，並未代表此新版本或所有方案通過。本輪沒有修改帳號內已安裝Plugin；新ZIP需由使用者匯入或更新。M08未改，不重測算術。導覽僅改M03文案、入口及版本，未宣稱重跑瀏覽器或真實手機測試。

Notion示範頁需實際放圖並回讀非空cover；手機裁切、美感確認、免費帳號與學生新對話仍待驗收。GPT完整上傳、Pages托管及自動更新不在本次交付。

## 重現
python -B -m unittest discover -s tests -p test_publication.py -v
python -B -m unittest discover -s tests -p test_m03_delivery.py -v
python -B tools/verify_zip_raw.py downloads/kmw01-community-monetization-0.5.3.zip

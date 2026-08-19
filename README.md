# ARTi 供應鏈與合作關係研究挑戰 — NVIDIA

一個以 **NVIDIA Corporation (NASDAQ: NVDA)** 為研究對象的、可重現的供應鏈與合作關係研究服務。

---

## 目錄

1. [研究範圍與邊界](#1-研究範圍與邊界)
2. [資料模型：一筆關係長什麼樣子](#2-資料模型一筆關係長什麼樣子)
3. [信賴度評分方法論](#3-信賴度評分方法論)
4. [資料來源與蒐集方式](#4-資料來源與蒐集方式)
5. [Quickstart](#5-quickstart)
6. [HTTP API](#6-http-api)
7. [CLI](#7-cli)
8. [測試](#8-測試)
9. [已知限制與未來改進方向](#9-已知限制與未來改進方向)
10. [AI 工具使用揭露](#10-ai-工具使用揭露)

---

## 1. 研究範圍與邊界

- **研究對象**：NVIDIA Corporation，NASDAQ: NVDA，SEC CIK 0001045810。
- **研究時間截點（research_as_of）**：`2026-08-19`（見 `data/company.json`）。所有信賴度分數
  都是相對於這個日期計算的「時間快照」，並非即時更新。
- **研究時間窗**：主要聚焦 2025-01-01 至 2026-08-19 間可公開查證、有明確發布時間的事件；
  時間窗前的歷史關係僅在對理解目前狀態必要時作為背景引用（例如 Arm 持股的建立與出清）。
- **涵蓋範圍**：與 NVIDIA 有直接、可公開查證關係、且**具備公開交易代碼（上市/上櫃）**的公司，
  關係類型涵蓋 `supplier`、`customer`、`partner`、`investor_or_investee`、`peer` 五種。
- **明確不覆蓋的邊界**（完整清單見 `data/company.json` 的 `scope.not_covered`）：
  - **未上市公司**：即使商業或投資關係重大且高度公開報導（例如 NVIDIA 對 OpenAI 至多
    1,000 億美元的投資意向、對 SpaceX 約 210 億美元的持股），因不具備公開交易代碼、無法以
    監理揭露文件交叉驗證持股數字，**刻意排除於主資料集評分之外**，僅在此處以說明性文字揭露：
    - NVIDIA 於 2025-09-22 宣布計畫對 OpenAI 投資至多 1,000 億美元，換取 10GW NVIDIA 系統部署；
      但截至 2025-12-02，NVIDIA CFO Colette Kress 公開表示「尚未完成具法律約束力的最終協議」，
      顯示此關係在撰寫本文件時仍處於高度不確定狀態（[Fortune 報導](https://fortune.com/2025/12/02/nvidia-openai-deal-not-signed-yet-100-billion-rally-colette-kress/)）。
    - NVIDIA 揭露持有約 210 億美元 SpaceX 股權，理由是 SpaceX 旗下 xAI 承諾在其 AI 資料中心
      獨家使用 NVIDIA 硬體（[Tom's Hardware 報導](https://www.tomshardware.com/tech-industry/nvidia-turns-usd5b-intel-stock-bet-into-usd30b-windfall-filing-reveals-new-usd21b-spacex-stake-and-complete-exit-from-arm-stock)）。
  - 未具名的財報揭露數字（例如 10-K 揭露「間接客戶佔總營收 19%」但未具名）不會被強行對應到
    特定公司，除非有第三方報導佐證該公司身份（見下方 `nvda-msft-customer-01` 等紀錄的處理方式）。
  - 需登入、付費牆、驗證碼或其他訪問控制之資料來源；不繞過 `robots.txt`。
  - 二階、三階供應商（例如個別測試設備商、稀有材料供應商）未逐一列出，僅涵蓋一階、
    具重大揭露意義的關係。
- **已知盲區**（完整清單見 `data/company.json` 的 `scope.known_blind_spots`）：非英語 / 非公開
  財報語系來源未系統性納入，可能低估中國供應鏈曝險；本資料集為時間快照，實際使用時應以
  API 回傳的 `evidence.published_date` 判斷資訊是否過期。

## 2. 資料模型：一筆關係長什麼樣子

每筆關係（`data/relationships.json` 中的一個物件）包含：

| 欄位 | 說明 |
|---|---|
| `id` | 穩定識別碼 |
| `counterparty` | 對手方公司名稱、股票代碼、交易所 |
| `relationship_type` | `supplier` \| `customer` \| `partner` \| `investor_or_investee` \| `peer` |
| `direction` | 人類可讀的關係方向說明（誰是買方/賣方/投資方） |
| `status` | `confirmed_ongoing`（證據支持目前持續存在）\| `exited_historical`（關係已結束，但結束本身有明確證據）\| `pending_not_definitive`（僅意向書、未完成具法律約束力協議）\| `disputed_conflicting_reports`（不同來源/時間點報導方向矛盾） |
| `summary` | 一段話說明這筆關係的實質內容 |
| `quantified_terms` | 可驗證的數字（金額、股數、GW 容量、百分比等），沒有就是 `null` |
| `evidence[]` | 見下方 |
| `notes` | 額外的方法論註記，說明為什麼這筆關係被這樣分類/評分 |

`evidence[]` 中每一則證據包含 `source_url`、`publisher`、`published_date`、`source_type`
（`regulatory_filing` / `company_press_release` / `reputable_news` / `secondary_aggregator`）、
`accessed_date`、以及 `evidence_locator`（指向文件中具體段落或報導中的關鍵描述，
讓 reviewer 不需要重新爬取受限資料就能理解交付物在講什麼）。

刻意保留了幾筆「不完美」的紀錄作為方法論示範，而非只挑容易的案例：

- **`nvda-samsung-supplier-01`**：兩則證據在時間先後上方向矛盾（先報導認證失敗、後報導完成
  認證），標記為 `disputed_conflicting_reports`，而不是隱藏矛盾、強行給出單一結論。
- **`nvda-arm-investor-01`**：NVIDIA 已完全出清 Arm 持股，標記為 `exited_historical`，
  展示「時效性」如何影響一筆關係是否該被視為目前仍然成立。
- **`nvda-intel-investor-01`** 與 **`nvda-intel-peer-01`**：同一實體（Intel）同時是
  NVIDIA 的被投資對象與市場競爭者，拆成兩筆獨立紀錄，避免用單一關係類型簡化複雜現實。
- **`nvda-crwv-investor-01`** 與 **`nvda-crwv-customer-01`**：CoreWeave 同時是 NVIDIA
  的投資對象與客戶，展示資本關係與商業關係的交織。

## 3. 信賴度評分方法論

完整實作與詳細註解在 [`app/scoring.py`](app/scoring.py)。摘要：

總分 0-100 = `(evidence_quality + source_independence + recency + quantifiability) × status_multiplier`

| 維度 | 滿分 | 依據 |
|---|---|---|
| `evidence_quality` | 40 | 證據陣列中等級最高的來源：`regulatory_filing`=40 > `company_press_release`=36 > `reputable_news`=26 > `secondary_aggregator`=14 |
| `source_independence` | 20 | 不重複 publisher 數量：≥3 家=20，2 家=14，1 家=6 |
| `recency` | 20 | 研究截止日與最新證據發布日的天數差：≤90 天=20，≤180 天=16，≤365 天=10，≤730 天=5，更舊=2 |
| `quantifiability` | 20 | `quantified_terms` 是否含可驗證數字：有=20，僅定性描述=5，無=0 |

再乘上反映「這筆關係目前是否穩固」的狀態係數：`confirmed_ongoing`/`exited_historical`=1.0、
`pending_not_definitive`=0.6、`disputed_conflicting_reports`=0.5。

這個設計刻意讓「證據薄弱但關係本身可能是真的」（例如 `nvda-mrvl-peer-01`，只有一篇綜述文章
提及）拿到明顯較低的分數，而不是與「有 SEC 文件+官方新聞稿+獨立媒體三方佐證」的
`nvda-nbis-investor-01`（100 分）混為一談。分數是**程式計算**出來的、可重現、可測試
（見 `tests/test_scoring.py`），不是人工拍腦袋給的數字。

## 4. 資料來源與蒐集方式

**蒐集方式**：以人工設計的搜尋詞（公司名稱 + 關係類型關鍵字，如「NVIDIA supplier 10-K」
「NVIDIA investment CoreWeave」）透過網路搜尋與網頁擷取工具尋找候選來源，再對每個候選來源
逐一擷取全文以確認金額、日期、關係方向等細節，最後人工比對多個來源、判斷是否有矛盾，
才寫入 `data/relationships.json`。**沒有使用任何自動化爬蟲程式對特定網站進行大量抓取**，
所有來源皆為當下可直接公開瀏覽的網頁（新聞報導、公司新聞稿、SEC EDGAR 文件），未繞過
`robots.txt`、登入牆或付費牆。

**清洗/處理方案**：原始網頁內容以人工/AI 輔助摘要方式擷取關鍵事實（金額、日期、當事方、
關係方向），寫入結構化 JSON；`data/relationships.json` 在啟動時會經過 `app/data_loader.py`
的 schema 驗證（必要欄位、合法的 `relationship_type`/`status` 枚舉值、至少一筆證據），
資料集本身即是清洗後的最終產物，reviewer 不需要重新抓取任何受限資料即可理解與復核整份交付物
——所有引用連結皆為當下可公開存取的頁面。

## 5. Quickstart

```bash
git clone <your-fork-url>
cd arti-nvda-research

python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 啟動 API
uvicorn app.main:app --reload --port 8000
# 另開一個終端機測試：
curl http://127.0.0.1:8000/relationships?type=investor_or_investee

# 或直接用 CLI，不需要啟動伺服器
python cli.py relationships --type supplier --summary-only
python cli.py show nvda-nbis-investor-01
python cli.py graph

# 跑測試
pytest -q
```

**環境變數**：本專案不需要任何 API 金鑰或密鑰即可運行——所有資料已經是研究完成後的靜態
JSON 快照（`data/relationships.json`、`data/company.json`），沒有任何執行期外部呼叫，
因此沒有 `.env` 或憑證需求。

**資料更新／復現步驟**：若要更新資料集（例如加入新的關係或修正過期資訊），編輯
`data/relationships.json` 後重新啟動伺服器（或直接重跑 CLI 指令）即可，`app/data_loader.py`
會在載入時自動重新驗證 schema 並重新計算所有信賴度分數——分數永遠是「現有資料 + 現有
research_as_of 日期」的函式，不會有快取失真的問題（`lru_cache` 只快取檔案讀取，計分本身
在每次請求時即時執行）。`data/company.json` 中的 `research_as_of` 即是本次交付的資料截點，
可視為 fixture／snapshot 日期。

## 6. HTTP API

| Method | Path | 說明 |
|---|---|---|
| GET | `/health` | 健康檢查 |
| GET | `/company` | 研究對象與範圍/邊界說明 |
| GET | `/relationships` | 關係列表，支援 `type`、`status`、`counterparty_ticker`、`min_score`、`page`、`page_size` 篩選與分頁 |
| GET | `/relationships/{id}` | 單筆關係完整內容（含證據與評分明細） |
| GET | `/graph` | 關係圖 `{nodes, edges}`，方便視覺化 |

啟動後可在 `http://127.0.0.1:8000/docs` 看到互動式 OpenAPI 文件（FastAPI 自動產生）。

輸入驗證與錯誤範例：

```bash
# 無效的 type 參數 → 422
curl -s -o /dev/null -w "%{http_code}\n" "http://127.0.0.1:8000/relationships?type=not_real"
# 422

# 超出範圍的分頁 → 404
curl -s -o /dev/null -w "%{http_code}\n" "http://127.0.0.1:8000/relationships?page=999"
# 404

# 查詢不存在的關係 id → 404
curl -s -o /dev/null -w "%{http_code}\n" "http://127.0.0.1:8000/relationships/does-not-exist"
# 404
```

## 7. CLI

`cli.py` 提供與 API 相同資料的可脚本化入口，不需要啟動伺服器：

```bash
python cli.py company
python cli.py relationships --type peer
python cli.py relationships --status disputed_conflicting_reports
python cli.py relationships --min-score 70 --sort score --summary-only
python cli.py show nvda-arm-investor-01
python cli.py graph
```

所有輸出皆為 JSON，方便與 `jq` 等工具串接；無效輸入會以非零 exit code 結束並將錯誤訊息
輸出到 stderr（例如 `python cli.py show does-not-exist` 會回傳 exit code 1）。

## 8. 測試

```bash
pytest -q
# 26 passed
```

測試涵蓋三個層次：

- `tests/test_scoring.py`：評分引擎的關鍵路徑（滿分案例、單一弱來源案例）與邊界情況
  （`disputed`/`pending` 狀態的乘數是否正確套用、證據缺少日期時不應噴例外、
  證據日期異常晚於研究截止日時不應產生負值）。
- `tests/test_api.py`：API 的篩選、分頁、排序邏輯，以及**失敗案例**——無效的
  `type`/`status` 回傳 422、查無資料的 `id` 回傳 404、分頁超出範圍回傳 404。
  也包含一則對照測試，驗證 Samsung（disputed）確實比同類型的 SK Hynix（confirmed）
  拿到更低的狀態乘數，證明「矛盾證據」確實反映在分數上而非被靜默忽略。
- `tests/test_cli.py`：CLI 的正常路徑與失敗路徑（無效 `--type` 造成非零 exit code、
  查詢不存在的 id 回傳 exit code 1 並在 stderr 說明原因）。

## 9. 已知限制與未來改進方向

- **樣本規模**：目前資料集涵蓋 26 筆關係、23 個對手方實體，足以展示方法論但**不是**
  NVIDIA 全部關係的窮舉清單；下一步可擴大到二階供應商、更多區域性合作夥伴。
- **customer 關係的具名信賴度普遍偏低**：NVIDIA 財報並未具名揭露前幾大客戶，本資料集中
  Microsoft/Amazon/Meta/Alphabet 等客戶關係皆為「市場依採購規模與資本支出報導推斷」，
  屬於 `reputable_news` 等級而非公司自行揭露，這是資料本質上的限制，未來可持續追蹤
  NVIDIA 是否開始具名揭露大型客戶。
- **peer（競爭關係）的評分上限偏低**：因為沒有公司會正式發布「我們互為競爭對手」的新聞稿，
  peer 類型證據多半來自產業分析網站的歸類，量化基礎薄弱；未來可改用更嚴謹的依據
  （例如兩家公司在同一份分析師覆蓋清單中被並列、或市佔率報告中的直接比較數據）取代
  單純的媒體歸類。
- **未上市但高度相關的實體**（OpenAI、xAI、SpaceX、Anthropic）目前完全排除於評分資料集
  外，僅在 README 中說明性揭露；下一步可以考慮建立一個平行的「未上市關係」附錄資料集，
  但明確標示其信賴度評分方法論與上市公司不同（無法用股票代碼交叉驗證）。
- **語言覆蓋**：目前資料來源以英文為主，可能低估中文（如部分中國供應鏈廠商公告）或其他
  語言市場的關係與風險。
- **更新頻率**：這是一次性研究快照（`research_as_of=2026-08-19`），實際生產環境應該
  排程定期重新抓取與驗證每筆證據是否仍然有效（例如偵測來源網頁是否下架、是否被更新的
  報導取代）。

## 10. AI 工具使用揭露

本專案在研究與工程過程中使用了 AI 輔助工具（Claude），用途與人工查核方式如下：

- **用途**：(1) 以自然語言查詢加速網路搜尋與候選來源篩選；(2) 協助將擷取到的網頁內容
  摘要為結構化 JSON 草稿；(3) 協助產生 API/CLI 樣板程式碼與測試案例草稿。
- **人工驗證方式**：所有寫入 `data/relationships.json` 的事實（金額、日期、當事方、
  關係方向、關係狀態）皆由人工逐筆比對原始網頁內容後才定案，AI 摘要僅作為起草稿，
  不作為最終依據；所有程式碼在提交前皆實際執行（啟動伺服器手動 curl 測試、
  `pytest -q` 全數通過）而非僅憑 AI 產出即信任。
- **研究與工程判斷的最終責任**：資料涵蓋範圍的界定（例如排除未上市公司）、評分方法論的
  設計（四維度加權公式與狀態乘數）、以及哪些「不完美案例」（矛盾證據、已結束關係、
  複合關係）值得刻意保留展示，皆為本人（Joan Chou）的產品與研究判斷，非工具自動決定。
- **未輸入任何敏感資訊**：過程中未向任何 AI 工具、編碼 Agent 或檢索工具輸入密鑰、
  個人資料、客戶機密或未經授權的資料——所有輸入僅為公開可查詢的公司名稱、關係類型
  與已經由公開網頁擷取到的事實內容。

---

## 授權

MIT License，見 [`LICENSE`](LICENSE)。

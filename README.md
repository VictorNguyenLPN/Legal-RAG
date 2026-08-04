<p align="center">
  <img src="images/logo.png" alt="Logo" height="150" />
</p>

<p align="center">
  <a href="https://github.com/VictorNguyenLPN/Legal-RAG/stargazers">
    <img src="https://img.shields.io/github/stars/VictorNguyenLPN/Legal-RAG?style=for-the-badge&logo=github&color=33a8ff" alt="Stars" />
  </a>
  <a href="https://github.com/VictorNguyenLPN/Legal-RAG/network/members">
    <img src="https://img.shields.io/github/forks/VictorNguyenLPN/Legal-RAG?style=for-the-badge&logo=github&color=33a8ff" alt="Forks" />
  </a>
  <a href="https://github.com/VictorNguyenLPN/Legal-RAG/issues">
    <img src="https://img.shields.io/github/issues/VictorNguyenLPN/Legal-RAG?style=for-the-badge&logo=github&color=ea4335" alt="Issues" />
  </a>
</p>

<p align="center">
  <strong>Hệ thống Hỏi Đáp Văn Bản Pháp Luật (RAG) sử dụng Hybrid Search & Gemini</strong>
</p>

<p align="center">
  <a href="README_EN.md">English 🌐</a> | <a href="README.md">Tiếng Việt 🇻🇳</a> | <a href="README_ZH.md">简体中文 🇨🇳</a>
</p>

---

>[!NOTE] Phiên bản hiện tại: v2.4.0 (04/08/2026)

Hệ thống Hỏi Đáp Văn Bản Pháp Luật được xây dựng hoàn toàn bằng Python, sử dụng BM25 kết hợp với Google Gemini Embedding để tìm kiếm và trả lời câu hỏi bằng Google Gemini 2.5 Flash Lite.

## Tính năng nổi bật

- **Hybrid Search:**
  - **Dense search:** `gemini-embedding-2` + `cosine similarity`.
  - **Sparse search:** `BM25`

- **Xếp hạng dung hợp RRF:** Kết hợp, tối ưu kết quả từ Dense và Sparse Search.

- **Cơ sở dữ liệu Vector:** Sử dụng ChromaDB (Hỗ trợ cả chế độ Persistent lưu trữ file cục bộ hoặc kết nối Docker Server qua HTTP Client).

- **LLM**: `gemini-2.5-flash`.

- **Quản lý & Lưu trữ Lịch sử Hội thoại:** Hỗ trợ lưu trữ persistent lịch sử chat nhiều phiên làm việc dưới LocalStorage, cho phép người dùng tạo mới, chuyển đổi qua lại giữa các cuộc hội thoại cũ, đổi tên trực tiếp trên sidebar, và xóa từng hội thoại (có xác nhận bảo vệ) hoặc xóa sạch toàn bộ.

- **Giao diện Trực quan:** `React` + `Vite` + `TypeScript`.

---

## Giao diện

### Giao diện chính khi chưa có dữ liệu
![Giao diện chính](images/1.png)

### Giao diện khi có câu hỏi
![Giao diện chính](images/2.png)

### Giao diện câu trả lời và trích dẫn
![Giao diện chính](images/3.png)


## Flow

```mermaid
graph TD
    A[User Query & History] --> B[Step 0: Query Condensation <br/> gemini-3.1-flash-lite]
    B -->|Condensed Query| C1[Step 1: Dense Search <br/> gemini-embedding-2 & ChromaDB]
    B -->|Condensed Query| C2[Step 2: Sparse Search <br/> BM25 Okapi]
    C1 -->|Dense Results| D[Step 3: Reciprocal Rank Fusion <br/> RRF Score Calculation]
    C2 -->|Sparse Results| D
    D -->|Top N Chunks| E[Step 4: Prompt Formulation <br/> Context + History + Query]
    E --> F[Step 5: LLM Generation <br/> gemini-3.1-flash-lite]
    F --> G[Step 6: Post-processing <br/> Fallback Check & Source Cleanup]
    G --> H[Final QueryResponse]
```


## Cấu trúc Thư mục

```text
Law-RAG/
├── backend/
│   └── app/
│       ├── api/
│       │   └── routes.py         # Định nghĩa API
│       ├── services/
│       │   ├── gemini_service.py # Gọi API Gemini
│       │   └── rag_service.py    # Điều phối luồng RAG pipeline
│       ├── retrieval/
│       │   ├── dense.py          # Tìm kiếm vector trực tiếp trên ChromaDB
│       │   ├── sparse.py         # Tìm kiếm BM25 tiếng Việt
│       │   └── fusion.py         # Thuật toán Reciprocal Rank Fusion (RRF)
│       ├── database/
│       │   └── vector_db.py      # Quản lý kết nối và thao tác với ChromaDB
│       ├── models/
│       │   └── schema.py         # Pydantic models xác thực dữ liệu API
│       ├── config.py             # Cấu hình biến môi trường & Siêu tham số
│       └── main.py               # Khởi chạy FastAPI App
├── frontend/
│   └── app.tsx                   # Giao diện React
│   └── ...                       # Các component khác
├── data/
│   ├── input/                    # Thư mục chứa dữ liệu JSON đầu vào
│   └── chroma/                   # Lưu trữ CSDL ChromaDB cục bộ (chế độ Persistent)
├── requirements.txt              # Thư viện phụ thuộc
└── README.md                     # Hướng dẫn sử dụng
```

---

## Hướng dẫn Cài đặt & Chạy Chương trình

### 1. Chuẩn bị Môi trường

Yêu cầu máy cài sẵn **Python 3.10+**. Khởi tạo virtual environment và cài đặt các thư viện:

```bash
# Tạo môi trường ảo
python3 -m venv .venv

# Kích hoạt môi trường ảo
source .venv/bin/activate

# Cài đặt thư viện phụ thuộc
pip install -r requirements.txt
```

### 2. Thiết lập API Key

Hệ thống yêu cầu API Key của Google Gemini. Cung cấp API Key thông qua biến môi trường:

```bash
export GEMINI_API_KEY="AIzaSyYourGeminiApiKeyHere..."
```

Hoặc, tạo file `.env` tại thư mục gốc của dự án và ghi `GEMINI_API_KEY=AIzaSy...`

### 3. Khởi chạy Backend

```bash
PYTHONPATH=. .venv/bin/uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```
> API docs (Swagger UI) sẽ khả dụng tại: http://localhost:8000/docs

### 4. Khởi chạy Frontend

```bash
cd frontend && npm run dev
```
> Giao diện Web UI sẽ tự động mở tại: http://localhost:5173/

### 5. Cấu trúc Dữ liệu Đầu vào & Nạp tài liệu (Ingestion)

Để nạp tài liệu pháp luật của riêng bạn vào hệ thống, hãy chuẩn bị một tệp tin định dạng `.json` chứa danh sách các phân mảnh (chunks).

#### Định dạng JSON Schema của dữ liệu đầu vào:

Tệp tin JSON phải là một mảng các đối tượng (array of objects), mỗi đối tượng đại diện cho một phân mảnh văn bản pháp lý với cấu trúc mẫu như sau:

```json
[
  {
    "chunk_id": "law_7eef1c6f9712c9a77af24be877851ca1_a1",
    "node_type": "article",
    "metadata": {
      "document_id": "7eef1c6f9712c9a77af24be877851ca1",
      "document_type": "Bộ luật",
      "document_title": "Bộ luật Hình sự số 15/1999/QH10",
      "doc_identity": "15/1999/QH10",
      "major_names": [
        "Tư pháp"
      ],
      "field_names": [
        "Chưa phân loại"
      ],
      "issue_date": "1999-12-21",
      "effect_date": "2000-07-01",
      "effect_status_name": "Hết hiệu lực toàn bộ",
      "expire_date": "2018-01-01",
      "organ_names": [
        "Quốc hội"
      ],
      "signer_title_names": [
        "Chủ tịch Quốc hội"
      ],
      "signer_names": [
        "Nông Đức Mạnh"
      ],
      "vbpl_url": "https://vbpl.vn/van-ban/chi-tiet/bo-luat-hinh-su-so-15-1999-qh10--6157",
      "source_guid": null,
      "scraped_date": "2026-07-01T20:04:58.071402+07:00",
      "part_number": null,
      "part_title": null,
      "chapter_number": "I",
      "chapter_title": "ĐIỀU KHOẢN CƠ BẢN",
      "section_number": null,
      "section_title": null,
      "article_number": 1,
      "article_title": "Nhiệm vụ của Bộ luật hình sự",
      "clause_number": null,
      "clause_title": "Bộ luật hình sự có nhiệm vụ bảo vệ chế độ xã hội chủ nghĩa, quyền làm chủ của nhân dân, bảo vệ quyền bình đẳng giữa đồng bào các dân tộc, bảo vệ lợi ích của Nhà nước, quyền, lợi ích hợp pháp của công dân, tổ chức, bảo vệ trật tự pháp luật xã hội chủ nghĩa, chống mọi hành vi phạm tội; đồng thời giáo dục mọi người ý thức tuân theo pháp luật, đấu tranh phòng ngừa và chống tội phạm.\nĐể thực hiện nhiệm vụ đó, Bộ luật quy định tội phạm và hình phạt đối với người phạm tội.",
      "point": null,
      "hierarchy_path": [
        "7eef1c6f9712c9a77af24be877851ca1",
        "Chương I",
        "Điều 1"
      ]
    },
    "text": "Nhiệm vụ của Bộ luật hình sự\nBộ luật hình sự có nhiệm vụ bảo vệ chế độ xã hội chủ nghĩa, quyền làm chủ của nhân dân, bảo vệ quyền bình đẳng giữa đồng bào các dân tộc, bảo vệ lợi ích của Nhà nước, quyền, lợi ích hợp pháp của công dân, tổ chức, bảo vệ trật tự pháp luật xã hội chủ nghĩa, chống mọi hành vi phạm tội; đồng thời giáo dục mọi người ý thức tuân theo pháp luật, đấu tranh phòng ngừa và chống tội phạm.\nĐể thực hiện nhiệm vụ đó, Bộ luật quy định tội phạm và hình phạt đối với người phạm tội."
  }
]
```

#### Chi tiết các trường dữ liệu:
* `text` (String - Bắt buộc): Nội dung phân mảnh văn bản pháp luật cần lập chỉ mục.
* `metadata` (Object - Bắt buộc): Siêu dữ liệu hỗ trợ việc trích dẫn nguồn và hiển thị:
  * `document_title` (String - Bắt buộc): Tên văn bản pháp luật (Ví dụ: tên Bộ luật, Luật, Quyết định...).
  * `hierarchy_path` (Array of Strings - Tùy chọn): Đường dẫn phân cấp (Ví dụ: `["Chương XIV", "Điều 168"]`).
  * `article_title` (String - Tùy chọn): Tiêu đề của Điều luật (Ví dụ: `Tội cướp tài sản`).
  * `article_number` (Integer/String - Tùy chọn): Số hiệu của Điều (Ví dụ: `168`).
  * `clause_number` (Integer/String - Tùy chọn): Số thứ tự của Khoản (Ví dụ: `1`).
  * `point` (String - Tùy chọn): Điểm trong điều khoản (Ví dụ: `a`, `b`...).

#### Cách nạp dữ liệu:
1. Mở giao diện ứng dụng tại [http://localhost:5173/](http://localhost:5173/).
2. Nhìn vào thanh quản lý bên trái (Sidebar), tại phần **"Nạp Tài Liệu Pháp Lý"**, nhấn vào vùng tải lên tệp tin.
3. Chọn tệp tin JSON của bạn. Sau khi hệ thống đọc và xác thực thành công số lượng chunks, nhấn nút **"Lập chỉ mục tệp này"** để tiến hành nhúng vector và tạo chỉ mục từ khóa (Hybrid Search).

---

## Lịch sử phiên bản

- v1.0.0 (29/07/2026): MVP version với Corpus nhỏ

- v1.1.0 (29/07/2026): Cập nhật corpus luật hình sự, sửa ui phần trích dẫn, thêm markdown render

- v2.0.0 (30/07/2026): Xử lý logic khi LLM không tìm thấy thông tin, chỉnh sửa giao diện, update conversation message, sửa prompt cho hội thoại cá nhân, ảnh demo

- v2.1.0 (30/07/2026): Update demo corpus

- v2.2.0 (30/07/2026): Check db mỗi lần khởi động, auto ingest nếu có corpus nhưng chưa có db

- v2.3.0 (03/08/2026): Tích hợp ChromaDB làm Vector DB (hỗ trợ Persistent & Server HTTP mode), cập nhật giao diện hiển thị trạng thái chi tiết của Backend & Database, sửa lỗi khóa luồng (thread blocking) khi nạp lại dữ liệu (ingestion).

- v2.3.1 (03/08/2026): Chỉnh sửa giao diện

- v2.3.2 (03/08/2026): Tối ưu hóa truy vấn cơ sở dữ liệu (tính toán kích thước collection thay vì deserialize toàn bộ), chuyển toàn bộ inline CSS sang tệp CSS riêng và dọn dẹp các ghi chú/mã code thừa. Bổ sung latency và token usage cho mỗi response.  

- v2.4.0 (04/08/2026): Triển khai cơ chế lưu trữ lịch sử hội thoại nhiều phiên làm việc (multi-conversation history) persistent dưới LocalStorage trình duyệt. Hỗ trợ tạo cuộc chat mới, chọn cuộc trò chuyện cũ, đổi tên trực tiếp và xóa phiên chat với hộp thoại xác nhận.
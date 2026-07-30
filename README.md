# Legal RAG

>[!NOTE] Phiên bản hiện tại: v1.0.0 (MVP version với Corpus nhỏ)

Hệ thống Hỏi Đáp Văn Bản Pháp Luật được xây dựng hoàn toàn bằng Python, sử dụng BM25 kết hợp với Google Gemini Embedding để tìm kiếm và trả lời câu hỏi bằng Google Gemini 2.5 Flash Lite.

## Tính năng nổi bật

- **Hybrid Search:**
  - **Dense search:** `gemini-embedding-2` + `cosine similarity`.
  - **Sparse search:** `BM25`

- **Xếp hạng dung hợp RRF:** Kết hợp, tối ưu kết quả từ Dense và Sparse Search.

- **Cơ sở dữ liệu Vector:** Cục bộ `.npy` và metadata trong file JSON.

- **LLM**: `gemini-2.5-flash`.

- **Giao diện Trực quan:** `React` + `TailwindCSS`.

---

## Giao diện

### Giao diện chính khi chưa có dữ liệu
![Giao diện chính](images/1.png)

### Giao diện khi có câu hỏi
![Giao diện chính](images/2.png)

### Giao diện câu trả lời và trích dẫn
![Giao diện chính](images/3.png)

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
│       │   ├── dense.py          # Tìm kiếm vector bằng Cosine Similarity
│       │   ├── sparse.py         # Tìm kiếm BM25 tiếng Việt
│       │   └── fusion.py         # Thuật toán Reciprocal Rank Fusion (RRF)
│       ├── database/
│       │   └── vector_db.py      # Quản lý lưu trữ/đọc file .npy & json
│       ├── models/
│       │   └── schema.py         # Pydantic models xác thực dữ liệu API
│       ├── config.py             # Cấu hình biến môi trường & Siêu tham số
│       └── main.py               # Khởi chạy FastAPI App
├── frontend/
│   └── app.tsx                   # Giao diện React
│   └── ...                       # Các component khác
├── data/
│   ├── input/                    # Thư mục chứa dữ liệu JSON đầu vào
│   └── db/                       # Lưu trữ CSDL cục bộ (.npy và chunks.json)
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
    "text": "Người nào thực hiện hành vi cướp tài sản của người khác bằng cách dùng vũ lực, đe dọa dùng vũ lực ngay tức khắc hoặc có hành vi khác làm cho người bị tấn công lâm vào tình trạng không thể chống cự được nhằm chiếm đoạt tài sản, thì bị phạt tù từ 03 năm đến 10 năm.",
    "metadata": {
      "document_title": "Bộ luật Hình sự số 100/2015/QH13",
      "hierarchy_path": ["Chương XIV", "Mục 1", "Điều 168"],
      "article_title": "Tội cướp tài sản",
      "article_number": 168,
      "clause_number": 1,
      "point": null
    }
  },
  {
    "text": "Chuẩn bị phạm tội này, thì bị phạt tù từ 01 năm đến 05 năm.",
    "metadata": {
      "document_title": "Bộ luật Hình sự số 100/2015/QH13",
      "hierarchy_path": ["Chương XIV", "Mục 1", "Điều 168"],
      "article_title": "Tội cướp tài sản",
      "article_number": 168,
      "clause_number": 6,
      "point": null
    }
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

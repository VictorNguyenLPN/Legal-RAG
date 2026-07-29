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

---

## Lịch sử phiên bản

- v1.0.0 (29/07/2026): MVP version với Corpus nhỏ

- v1.1.0 (29/08/2026): Cập nhật corpus luật hình sự, sửa ui phần trích dẫn, thêm markdown render,

# Kiến Trúc Hệ Thống Law-RAG

Tài liệu này mô tả chi tiết kiến trúc hệ thống của Law-RAG, bao gồm luồng nạp dữ liệu (Ingestion Pipeline), luồng truy vấn hỏi đáp (RAG Pipeline) và sự tương tác giữa các thành phần React Frontend và FastAPI Backend.

---

## 1. Sơ đồ các Thành phần Hệ thống (System Components)

Sơ đồ dưới đây thể hiện sự tương tác tổng quan giữa lớp Giao diện người dùng (React SPA), cổng API (FastAPI) và các thành phần xử lý logic, nghiệp vụ tìm kiếm kết hợp (Hybrid Search) và tích hợp mô hình ngôn ngữ Google Gemini.

```mermaid
graph TD
    %% Frontend Components
    subgraph Frontend ["Frontend Layer (React SPA)"]
        UI["Main Layout (App.tsx)"]
        SB["Sidebar & Ingest Controls (Sidebar.tsx)"]
        SF["Search Form (SearchForm.tsx)"]
        AC["Answer Display (AnswerCard.tsx)"]
        CP["Citation Pills (Citations.tsx)"]
        SD["Source Accordions (SourceDetails.tsx)"]
    end

    %% Backend Layers
    subgraph Backend ["Backend Layer (FastAPI)"]
        API["API Routes (routes.py)"]
        RAG["RAG Service (rag_service.py)"]
        GEM["Gemini Service (gemini_service.py)"]
        
        subgraph Retrieval ["Retrieval Engines"]
            DENSE["Dense Search (dense.py)"]
            SPARSE["Sparse Search (sparse.py)"]
            RRF["Rank Fusion (fusion.py)"]
        end
        
        subgraph DB ["Storage / DB Layer"]
            VDB["Vector DB (vector_db.py)"]
            META["Metadata Storage (JSON)"]
        end
    end

    %% External APIs
    subgraph External ["External Services"]
        G_API["Google Gemini API"]
    end

    %% Connections
    SB -->|"/status, /ingest, /ingest-file"| API
    SF -->|"/query"| API
    
    API --> RAG
    RAG --> GEM
    RAG --> Retrieval
    RAG --> DB
    
    DENSE --> VDB
    SPARSE --> META
    RRF --> DENSE
    RRF --> SPARSE
    
    GEM -->|Embeddings / Text Gen| G_API
    
    API -->|Response JSON| UI
    UI --> AC
    UI --> CP
    UI --> SD
```

---

## 2. Luồng Nạp và Lập Chỉ Mục Dữ Liệu (Ingestion Pipeline)

Luồng này mô tả cách tài liệu pháp luật (định dạng JSON chứa các phân mảnh văn bản kèm siêu dữ liệu metadata) được lập chỉ mục Hybrid Index (bao gồm chỉ mục Dense Vector và chỉ mục từ khóa Sparse BM25).

```mermaid
sequenceDiagram
    autonumber
    actor User as Người dùng
    participant FE as React Frontend
    participant BE as FastAPI Backend
    participant RAG as RAG Service
    participant GEM as Gemini Service
    participant G_API as Gemini API
    participant VDB as Vector Database (Local)

    alt Cách 1: Nạp tệp cấu trúc JSON tùy chỉnh từ Client
        User->>FE: Chọn & tải lên tệp JSON tùy chỉnh
        FE->>FE: FileReader đọc nội dung tệp JSON ở Client
        FE->>BE: POST /ingest [Danh sách Chunks]
    else Cách 2: Nạp tệp mẫu (demo_chunk.json) từ Server
        User->>FE: Bấm nút "Tải demo_chunk.json"
        FE->>BE: POST /ingest-file {file_path}
        BE->>BE: Đọc file demo_chunk.json từ đĩa cứng server
    end

    BE->>RAG: ingest_chunks(raw_chunks)
    
    Note over RAG, GEM: Bắt đầu tiến trình Lập chỉ mục Hybrid Index
    
    RAG->>GEM: get_embeddings(texts)
    GEM->>G_API: Gọi API sinh vector nhúng (text-embedding-004)
    G_API-->>GEM: Trả về danh sách Vectors
    GEM-->>RAG: Trả về các Vectors tương ứng
    
    RAG->>VDB: Lưu Vectors (Dense Index) & Text Chunks + Metadata (Sparse Index)
    VDB-->>RAG: Đã lưu thành công
    
    RAG-->>BE: Trả về số lượng chunk đã nạp (count)
    BE-->>FE: HTTP 201 Created {"status": "success", "count": X}
    FE-->>User: Hiển thị Toast thông báo thành công & cập nhật số lượng Chunks
```

---

## 3. Luồng Hỏi Đáp kết hợp và Trích dẫn (RAG Pipeline)

Luồng này mô tả cách hệ thống tiếp nhận câu hỏi của người dùng, thực hiện tìm kiếm song song Dense Search và Sparse Search, dung hợp kết quả bằng thuật toán RRF, tạo prompt và gọi mô hình Gemini 2.5 Flash để sinh câu trả lời kèm trích dẫn chính xác.

```mermaid
sequenceDiagram
    autonumber
    actor User as Người dùng
    participant FE as React Frontend
    participant BE as FastAPI Backend
    participant RAG as RAG Service
    participant DENSE as Dense Search (Cosine)
    participant SPARSE as Sparse Search (BM25)
    participant RRF as Rank Fusion (RRF)
    participant GEM as Gemini Service
    participant G_API as Gemini API

    User->>FE: Nhập câu hỏi & bấm Tìm kiếm
    FE->>BE: POST /query {"query": "Câu hỏi"}
    BE->>RAG: query("Câu hỏi")
    
    par Bước 3.1: Gọi API Gemini lấy Vector nhúng của câu hỏi
        RAG->>GEM: get_embedding("Câu hỏi")
        GEM->>G_API: Gửi request nhúng
        G_API-->>GEM: Trả về Vector nhúng
        GEM-->>RAG: Trả về Vector nhúng
    and Bước 3.2: Chuẩn bị truy vấn từ khóa cho BM25
        Note over RAG: Tokenize & làm sạch câu hỏi
    end
    
    par Tìm kiếm Dense (Semantic)
        RAG->>DENSE: search(query_vector, top_k=20)
        DENSE-->>RAG: Danh sách kết quả Dense (xếp theo Cosine similarity)
    and Tìm kiếm Sparse (Keyword)
        RAG->>SPARSE: search(query_text, top_k=20)
        SPARSE-->>RAG: Danh sách kết quả Sparse (xếp theo BM25 score)
    end
    
    RAG->>RRF: compute_rrf(dense_results, sparse_results)
    Note over RRF: Áp dụng công thức RRF Score = 1 / (k + rank)<br/>để tìm ra các phân mảnh tương quan nhất
    RRF-->>RAG: Trả về Top Chunks đã sắp xếp lại (ví dụ: Top 5 Chunks)
    
    RAG->>RAG: Tạo Prompt ngữ cảnh (Context) tích hợp Metadata trích dẫn chi tiết
    
    RAG->>GEM: generate_response(prompt, context)
    GEM->>G_API: Gọi mô hình sinh văn bản (gemini-2.5-flash)
    G_API-->>GEM: Trả về câu trả lời phân tích pháp lý
    GEM-->>RAG: Trả về câu trả lời đã sinh
    
    RAG-->>BE: Trả về cấu trúc {"answer": "...", "sources": [...]}
    BE-->>FE: Trả về HTTP 200 OK kèm JSON kết quả
    FE->>FE: Render giao diện (Bản phân tích, Căn cứ pháp lý, Accordion chi tiết)
    FE-->>User: Hiển thị câu trả lời trực quan, sinh động
```

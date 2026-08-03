<p align="center">
  <img src="images/logo.png" alt="Logo" height="200" />
</p>

<h1 align="center">Legal RAG</h1>

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
  <strong>基于混合检索与 Gemini 的法律文献问答系统 (RAG)</strong>
</p>

<p align="center">
  <a href="README_EN.md">English</a> | <a href="README.md">Tiếng Việt</a> | <a href="README_ZH.md">简体中文</a>
</p>

---

>[!NOTE] 当前版本：v2.3.2 (2026年8月3日)

本法律文献问答系统完全基于 Python 构建，结合使用 BM25 和 Google Gemini Embedding 进行检索，并使用 Google Gemini 2.5 Flash Lite 进行回答。

## 项目特点

- **混合检索 (Hybrid Search)：**
  - **稠密检索 (Dense search)：** `gemini-embedding-2` + `余弦相似度 (cosine similarity)`。
  - **稀疏检索 (Sparse search)：** `BM25`（针对越南语进行了优化）。

- **互惠排名融合 (RRF)：** 结合并优化稠密检索与稀疏检索的排序结果。

- **向量数据库 (Vector Database)：** 使用 ChromaDB（支持本地 Persistent 持久化文件存储或通过 HTTP Client 连接 Docker 服务）。

- **大语言模型 (LLM)：** `gemini-2.5-flash`。

- **直观界面 (Intuitive UI)：** `React` + `TailwindCSS`。

---

## 系统界面

### 未导入数据时的系统主界面
![系统主界面](images/1.png)

### 提问时的系统界面
![提问界面](images/2.png)

### 回答与引用展示界面
![引用与来源界面](images/3.png)

## 目录结构

```text
Law-RAG/
├── backend/
│   └── app/
│       ├── api/
│       │   └── routes.py         # API 路由定义
│       ├── services/
│       │   ├── gemini_service.py # Gemini API 服务集成
│       │   └── rag_service.py    # 协调 RAG 管道流程
│       ├── retrieval/
│       │   ├── dense.py          # 基于 ChromaDB 的向量相似度检索
│       │   ├── sparse.py         # 越南语 BM25 关键词检索
│       │   └── fusion.py         # 互惠排名融合 (RRF) 算法实现
│       ├── database/
│       │   └── vector_db.py      # ChromaDB 数据库连接与操作管理
│       ├── models/
│       │   └── schema.py         # 用于 API 数据验证的 Pydantic 模型
│       ├── config.py             # 环境变量与超参数配置
│       └── main.py               # FastAPI 应用启动入口
├── frontend/
│   └── src/
│       ├── App.tsx               # 主 React 应用入口
│       ├── components/           # 子组件 (Sidebar, Header 等)
│       └── index.css             # 主样式 CSS 文件
├── data/
│   ├── input/                    # JSON 格式原始输入数据目录
│   └── chroma/                   # 本地 ChromaDB 持久化存储目录 (Persistent 模式)
├── requirements.txt              # 后端依赖库
└── README.md                     # 越南语使用说明
```

---

## 安装与运行指南

### 1. 环境准备

系统需要安装 **Python 3.10+**。创建虚拟环境并安装依赖：

```bash
# 创建虚拟环境
python3 -m venv .venv

# 激活虚拟环境
source .venv/bin/activate

# 安装依赖包
pip install -r requirements.txt
```

### 2. 配置 API 密钥

系统需要 Google Gemini API 密钥。您可以通过环境变量提供该密钥：

```bash
export GEMINI_API_KEY="AIzaSyYourGeminiApiKeyHere..."
```

或者，在项目根目录下创建一个 `.env` 文件，并写入 `GEMINI_API_KEY=AIzaSy...`。

### 3. 启动后端

```bash
PYTHONPATH=. .venv/bin/uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```
> Swagger API 文档将在以下地址可用：http://localhost:8000/docs

### 4. 启动前端

```bash
cd frontend && npm run dev
```
> 网页端界面将在以下地址自动打开：http://localhost:5173/

### 5. 输入数据格式与文档导入 (Ingestion)

若要将您自己的法律文档导入系统，请准备一个包含分块 (chunks) 列表的 `.json` 格式文件。

#### 输入数据的 JSON Schema 格式：

JSON 文件必须是一个对象数组，每个对象代表一个法律文本分块，示例结构如下：

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

#### 数据字段详情：
* `text` (字符串 - 必填): 需要建立索引的法律文本分块内容。
* `metadata` (对象 - 必填): 用于支持来源引用和展示的元数据。
  * `document_title` (字符串 - 必填): 法律文献名称（例如：刑法、民法、决定等）。
  * `hierarchy_path` (字符串数组 - 选填): 层级路径（例如：`["第I章", "第1条"]`）。
  * `article_title` (字符串 - 选填): 条款标题（例如：`刑法的任务`）。
  * `article_number` (整数/字符串 - 选填): 条款编号（例如：`1`）。
  * `clause_number` (整数/字符串 - 选填): 款编号（例如：`1`）。
  * `point` (字符串 - 选填): 项标识（例如：`a`，`b`等）。

#### 数据导入步骤：
1. 打开应用界面：[http://localhost:5173/](http://localhost:5173/)。
2. 在左侧管理栏（Sidebar）的 **“导入法律文献” (Nạp Tài Liệu Pháp Lý)** 部分，点击文件上传区域。
3. 选择您的 JSON 文件。系统读取并验证分块数量成功后，点击 **“为此文件建立索引” (Lập chỉ mục tệp này)** 按钮，开始生成向量嵌入并构建混合检索索引。

---

## 版本历史

- **v1.0.0 (2026年7月29日)**: MVP 初始版本，包含小型演示语料库。

- **v1.1.0 (2026年7月29日)**: 导入刑法语料库，优化引用显示 UI，添加 React Markdown 渲染支持。

- **v2.0.0 (2026年7月30日)**: 处理大语言模型找不到信息时的逻辑，优化界面，更新对话消息，修改个人对话 Prompt，添加演示图片。

- **v2.1.0 (2026年7月30日)**: 更新演示语料库引用。

- **v2.2.0 (2026年7月30日)**: 每次启动时检查数据库，若存在语料库但未建库则自动进行导入 (ingest)。

- **v2.3.0 (2026年8月3日)**: 集成 ChromaDB 作为向量数据库（支持 Persistent 本地存储和 Server HTTP 连接模式），更新界面以显示后端和数据库的详细连接状态，解决重新导入数据 (ingestion) 时的线程阻塞问题。

- **v2.3.1 (2026年8月3日)**: 界面微调。

- **v2.3.2 (2026年8月3日)**: 优化数据库查询性能（通过元数据计算集合大小，而不是在搜索查询时反序列化所有分块），将所有行内 CSS 样式迁移到独立 CSS 文件中，并清理冗余代码与注释。每次回答添加响应延迟和 Token 使用量统计。

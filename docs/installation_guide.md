# 📖 Hướng Dẫn Cài Đặt Chi Tiết & Khởi Chạy Dự Án

Tài liệu này cung cấp hướng dẫn cài đặt chi tiết từng bước (Step-by-step) cho dự án **AI Research News Platform**. Tài liệu liệt kê toàn bộ các thư viện cốt lõi, phiên bản cụ thể của các Model AI và cách thiết lập môi trường để đảm bảo hệ thống chạy mượt mà nhất.

---

## 1. Yêu Cầu Hệ Thống (Prerequisites)
Đảm bảo máy tính của bạn đã được cài đặt sẵn các phần mềm sau:
- **Python**: Phiên bản `3.10` trở lên.
- **Node.js**: Phiên bản `v18.0.0` trở lên (Khuyên dùng v20 LTS).
- **NPM**: Đi kèm khi cài Node.js.
- **Docker & Docker Compose**: Dùng để chạy Container PostgreSQL tích hợp `pgvector`.

---

## 2. Thông Tin Phiên Bản Các Thư Viện & AI Models

Dự án này sử dụng một bộ Stack công nghệ AI và Web cực kỳ hiện đại. Dưới đây là các thư viện và Model cốt lõi cùng phiên bản tương ứng:

### 🧠 Tuyến Backend (AI Models & Frameworks)
- **FastAPI** (`>=0.111.0`): Web framework chính để xây dựng API.
- **SQLAlchemy** (`>=2.0.30`): ORM quản lý Database.
- **pgvector** (`>=0.2.5`): Thư viện cho phép PostgreSQL lưu trữ và truy vấn Vector Embeddings.
- **Sentence-Transformers** (`>=3.0.1`): 
  - *Model sử dụng*: `all-MiniLM-L6-v2` (Siêu nhẹ, tốc độ cao, độ chính xác tốt để chuyển đổi Title/Abstract thành Vector 384 chiều).
- **UMAP-Learn** (`>=0.5.6`): Thuật toán giảm chiều dữ liệu (Dimension Reduction) từ 384 chiều xuống 2 chiều.
- **HDBSCAN** (`>=0.8.36`): Thuật toán gom cụm mật độ cao (Density-based Clustering) để tìm ra các nhóm bài báo có chung chủ đề.
- **BERTopic** (`>=0.16.2`): Pipeline hoàn chỉnh tích hợp UMAP, HDBSCAN và c-TF-IDF để trích xuất các từ khóa (Keywords) nổi bật đại diện cho từng cụm.
- **Ollama Local LLM**:
  - *Model sử dụng*: `qwen3.5:4b` (Dùng để đọc hiểu các Keywords và tự động suy luận ra một "Tên Chủ Đề" ngắn gọn, súc tích).

### 🖥️ Tuyến Frontend (Web UI)
- **React** (`^19.2.6`): Thư viện UI cốt lõi.
- **Vite** (`^8.0.12`): Build tool siêu tốc độ.
- **react-force-graph-2d** (`^1.29.1`): Engine vật lý dùng để vẽ **Đồ thị tri thức** (Knowledge Graph) tương tác thời gian thực.
- **lucide-react** (`^1.21.0`): Bộ icon sắc nét, hiện đại.
- **recharts** (`^3.8.1`): (Dự phòng) Thư viện vẽ biểu đồ phân tích.

---

## 3. Các Bước Cài Đặt (Step-by-Step)

### Bước 3.1: Khởi tạo Database (Docker)
Tại thư mục gốc của dự án (`TTCS/`), mở Terminal và chạy lệnh sau để kéo Image `ankane/pgvector:v0.5.1` về và khởi động Database ở cổng `5432`:
```powershell
docker-compose up -d db
```
*Lưu ý: Username mặc định là `postgres`, Password là `Mxnn@0319`, Tên DB là `ai_research_db`.*

### Bước 3.2: Khởi tạo Local LLM (Ollama)
Để tính năng Đặt tên Chủ đề Tự động của BERTopic hoạt động, bạn cần có một mô hình ngôn ngữ lớn (LLM) chạy ngầm:
1. Tải và cài đặt **Ollama** từ trang chủ (https://ollama.com).
2. Mở Terminal và chạy lệnh kéo Model:
```powershell
ollama pull qwen3.5:4b
```
3. Đảm bảo ứng dụng Ollama đang chạy ở dưới thanh Taskbar.

### Bước 3.3: Cài đặt Backend
Mở một tab Terminal mới, di chuyển vào thư mục `backend`:
```powershell
cd backend
```
Khởi tạo và kích hoạt môi trường ảo Python (Virtual Environment):
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```
Cài đặt toàn bộ thư viện AI và API:
```powershell
pip install -r requirements.txt
```
Khởi tạo cấu trúc Bảng trong Database:
```powershell
python init_db.py
```
**NẠP DỮ LIỆU & CHẠY AI PIPELINE (Quan trọng):**
```powershell
python seed_db.py
```
*Lưu ý: Quá trình `seed_db.py` sẽ thực hiện tải model Sentence-Transformers về máy lần đầu tiên, sau đó băm 20 bài báo giả lập ra thành Embeddings, chạy UMAP, HDBSCAN, gọi Ollama để đặt tên cụm. Quá trình này có thể tốn từ 30s đến 2 phút.*

Bật API Server:
```powershell
uvicorn app.main:app --reload
```
*Server Backend sẽ chạy tại: `http://localhost:8000`*

### Bước 3.4: Cài đặt Frontend
Mở thêm một tab Terminal mới, di chuyển vào thư mục `frontend`:
```powershell
cd frontend
```
Cài đặt thư viện Node.js:
```powershell
npm install
```
Khởi động giao diện Web:
```powershell
npm run dev
```
*Giao diện Web sẽ chạy tại: `http://localhost:5173`*

---

## 4. Xử Lý Lỗi Thường Gặp (Troubleshooting)

- **Lỗi không kết nối được Database**: Kiểm tra lại Docker đã bật chưa, Container có đang xanh (Running) không. Nếu chạy Windows, hãy chắc chắn Docker Desktop đã được khởi động.
- **Lỗi `Connection refused` khi gọi Ollama**: Đảm bảo ứng dụng Ollama (biểu tượng con Llama) đang chạy ở khay hệ thống (System Tray). Bạn có thể test bằng cách gõ `ollama run qwen3.5:4b` vào Terminal xem nó có phản hồi không.
- **Frontend xoay Loading vô tận**: Bấm F12 mở tab Network/Console xem Frontend có gọi API `/api/pipeline/run` thành công hay không. Nếu báo lỗi CORS hoặc 500, hãy kiểm tra lại tab Terminal đang chạy Backend xem có văng lỗi Python nào không.

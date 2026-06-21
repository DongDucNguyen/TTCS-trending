# Tài liệu Luồng hoạt động và Các mô hình trong Pipeline

Tài liệu này mô tả chi tiết về cách thức sử dụng các mô hình (models) và luồng hoạt động (workflow) bên trong hệ thống `pipeline_service.py`. Hệ thống được chia làm 2 nhánh chính xử lý song song trên tập dữ liệu bài báo (papers) được thu thập.

## 1. Luồng hoạt động tổng quan (Workflow)

1. **Thu thập và Tiền xử lý dữ liệu**:
   - Truy xuất các bài báo trong 30 ngày gần nhất từ Database.
   - Kiểm tra các bài báo và danh mục (categories) xem đã có vector nhúng (embeddings) chưa.
   - Nếu chưa có, hệ thống gọi mô hình Embedding để tạo vector cho văn bản gồm `Title + Abstract` (đối với bài báo) và `Name` (đối với danh mục).
   
2. **Nhánh 1: Phân loại Zero-Shot (Zero-Shot Classification)**:
   - **Mục đích**: Phân loại tự động các bài báo mới vào các chủ đề (categories) đã được định nghĩa sẵn.
   - Thực hiện tính toán mức độ tương đồng (Cosine Similarity) giữa vector của bài báo và vector của các chủ đề.
   - Sử dụng hàm Softmax kết hợp hệ số tỷ lệ (Temperature = 10) để khuếch đại sự khác biệt. 
   - Nếu xác suất của chủ đề cao nhất đạt trên ngưỡng 50% (Relative Threshold), bài báo được gán vào chủ đề tương ứng.
   - Đánh giá xu hướng bằng cách phân tích độ tuổi của bài báo (<= 15 ngày là dữ liệu mới, > 15 ngày là dữ liệu cũ) để tính toán tỉ lệ tăng trưởng (Growth Rate).

3. **Nhánh 2: Gom cụm Chủ đề Mới nổi (Emergent Topic Clustering)**:
   - **Mục đích**: Khám phá các chủ đề mới, chưa từng được định nghĩa trước đây thông qua tự động gom cụm các bài báo có nội dung tương đồng.
   - Giảm chiều dữ liệu vector của bài báo từ không gian 384 chiều (384D) xuống 2 chiều (2D).
   - Dựa vào không gian 2D, tiến hành gom cụm (clustering) phân bổ mật độ.
   - Rút trích các từ khóa (keywords) đại diện cho từng cụm.
   - Đưa danh sách từ khóa qua mô hình LLM để tự động suy luận và sinh ra tên ngắn gọn cho cụm nghiên cứu.
   - Xây dựng mạng lưới quan hệ cho giao diện người dùng (Graph Nodes & Edges) dựa trên khoảng cách giữa các cụm.

---

## 2. Chi tiết các Model sử dụng

### 2.1. Mô hình Embedding: `SentenceTransformer ("all-MiniLM-L6-v2")`
Mô hình xử lý ngôn ngữ nhỏ gọn nhưng mạnh mẽ, đóng vai trò nền tảng trong việc chuyển đổi văn bản thành dữ liệu số (vector) để hệ thống có thể hiểu và tính toán.
- **Đầu vào (Input)**: Văn bản thuần túy dạng chuỗi (String). Bao gồm `Title + Abstract` của bài báo, hoặc tên của các Category.
- **Đầu ra (Output)**: Vector nhúng (Embeddings) không gian 384 chiều (`numpy.ndarray` có shape `(N, 384)`).
- **Cách sử dụng**: Được gọi qua hàm `generate_embeddings()` ở bước đầu tiên của pipeline, dữ liệu vector này sau đó cung cấp nguồn dữ liệu đầu vào cho cả 2 nhánh (Zero-Shot và Clustering).

### 2.2. Các Mô hình trong nhánh Gom cụm (BERTopic Pipeline)
Trong nhánh 2, hệ thống sử dụng thư viện `BERTopic` tích hợp một chuỗi các mô hình con hoạt động liên tiếp:

#### A. Mô hình Giảm chiều: `UMAP` (Uniform Manifold Approximation and Projection)
- **Đầu vào (Input)**: Vector nhúng 384 chiều của các bài báo.
- **Đầu ra (Output)**: Vector giảm chiều xuống không gian 2D (Tọa độ x, y).
- **Mục đích**: Nén thông tin không gian nhiều chiều xuống 2 chiều nhưng vẫn giữ nguyên vẹn nhất có thể các cấu trúc cục bộ và toàn cục của dữ liệu. Phục vụ bước gom cụm chạy hiệu quả hơn và cung cấp tọa độ x,y cho đồ thị UI.

#### B. Mô hình Gom cụm: `HDBSCAN` (Hierarchical Density-Based Spatial Clustering)
- **Đầu vào (Input)**: Dữ liệu tọa độ 2D đã qua xử lý bởi UMAP.
- **Đầu ra (Output)**: Nhãn cụm (Cluster IDs), phân loại các bài báo vào từng nhóm riêng biệt hoặc đánh dấu là ngoại lai (Outliers/Noise, ID = -1).
- **Mục đích**: Tìm ra những vùng có mật độ phân bổ bài báo dày đặc trong không gian 2D để hình thành các cụm (topic) một cách tự động.

#### C. Mô hình Trích xuất từ khóa: `CountVectorizer`, `c-TF-IDF` & `KeyBERTInspired`
- **Đầu vào (Input)**: Các văn bản của bài báo đã được gom cùng một cụm.
- **Đầu ra (Output)**: Danh sách các từ khóa (keywords) có trọng số cao nhất (ví dụ top 10 từ), phản ánh chính xác nhất chủ đề chung của toàn bộ bài báo trong cụm đó.
- **Mục đích**: Tìm ra đặc trưng nội dung lớn nhất của nhóm bài báo để biểu diễn cho chủ đề mới.

### 2.3. Mô hình Ngôn ngữ Lớn (LLM): `Ollama (qwen3.5:4b)`
Đây là mô hình LLM được chạy cục bộ (Local LLM), dùng để thực hiện suy luận đặt tên cho các cụm chủ đề mới xuất hiện.
- **Đầu vào (Input)**: Một đoạn Prompt chứa danh sách các từ khóa (Keywords) của một cụm mới nổi và yêu cầu AI đóng vai là một nhà nghiên cứu để đặt tên chủ đề (dưới 5 từ).
  - *Ví dụ prompt: "You are an AI researcher. Name this research cluster based on these keywords in under 5 words: artificial, intelligence, neural, networks. Output only the name, no extra text."*
- **Đầu ra (Output)**: Tên của cụm nghiên cứu dạng chuỗi (String, ví dụ: "Artificial Neural Networks").
- **Cách sử dụng**: Trong hàm `query_ollama_for_name()`, hệ thống gửi request API tới localhost port 11434 (`http://localhost:11434/api/generate`), nhận lại tên cụm để làm nhãn hiển thị, và gán nhãn này vào đối tượng Node trên đồ thị.

---

## 3. Tổng kết Đầu vào và Đầu ra của toàn bộ hệ thống (`run_full_pipeline`)
- **Đầu vào tổng**: 
  - Khởi tạo kết nối Session tới Database (SQLAlchemy).
  - Truy xuất các đối tượng `Paper` từ database trong 30 ngày qua (Có thể có hoặc chưa có `paper_vector`).
  - Truy xuất các đối tượng `Category` được định nghĩa trước.
- **Đầu ra tổng**: Trả về một đối tượng dữ liệu JSON (Dictionary) chia làm 2 phần phục vụ cho Frontend UI:
  1. `"leaderboard"`: Danh sách thứ hạng các chủ đề tĩnh định sẵn, đi kèm thuộc tính `"paper_count"` (số lượng bài thuộc về chủ đề này) và `"growth_rate"` (tỉ lệ tăng trưởng so với 15 ngày trước). Dữ liệu này được sắp xếp theo `paper_count` giảm dần.
  2. `"graph"`: Dữ liệu đồ thị hiển thị các chủ đề mới nổi (Emergent Topics) gồm:
     - `"nodes"`: Danh sách các điểm nút đại diện cho cụm, chứa (ID, Tên được đặt bởi Ollama, Keywords, Tọa độ X và Y, Kích thước cụm).
     - `"edges"`: Trọng số liên kết dựa trên khoảng cách địa lý Euclid 2 chiều giữa các cụm Nodes (chỉ xét các Node gần nhau `dist < 2.0`).

---

## 4. Mô tả luồng hoạt động của file `pipeline_service.py`

Xét theo trình tự chạy thực tế, file này vận hành theo các bước chính sau:

1. **Khởi tạo pipeline và nạp dữ liệu nguồn**  
   Hàm `run_full_pipeline()` được gọi để mở session database, lấy danh sách bài báo mới trong 30 ngày gần nhất và lấy toàn bộ category đang có trong hệ thống.

2. **Đảm bảo dữ liệu vector luôn sẵn sàng**  
   Hệ thống kiểm tra từng `Paper` và `Category` xem đã có embedding hay chưa. Nếu còn thiếu, hàm `generate_embeddings()` sẽ tạo mới vector từ nội dung văn bản rồi lưu lại để tái sử dụng cho các lần chạy sau.

3. **Tách ra 2 nhánh xử lý từ cùng một nguồn embedding**  
   Sau khi có đầy đủ vector, cùng một tập embedding của papers sẽ được dùng cho hai mục tiêu khác nhau:
   - Nhánh phân loại vào các category đã biết.
   - Nhánh khám phá các topic mới nổi chưa được định nghĩa trước.

4. **Nhánh 1 xử lý bảng xếp hạng chủ đề có sẵn**  
   Vector của từng paper được so sánh với vector của các category bằng cosine similarity. Hệ thống chuẩn hóa điểm bằng softmax có temperature để làm nổi bật category phù hợp nhất. Nếu điểm cao nhất vượt ngưỡng, paper sẽ được gán vào category đó. Sau cùng, hệ thống đếm số lượng paper theo category và tính `growth_rate` dựa trên chênh lệch giữa nhóm bài mới và cũ.

5. **Nhánh 2 xử lý khám phá topic mới nổi**  
   Embedding của papers được đưa qua UMAP để giảm từ 384 chiều xuống 2 chiều. Tọa độ 2D này tiếp tục đi vào HDBSCAN để gom cụm. Với mỗi cụm hợp lệ, hệ thống trích xuất keyword đại diện, sau đó gọi Ollama để sinh tên ngắn gọn cho cụm.

6. **Dựng dữ liệu đồ thị để frontend trực quan hóa**  
   Từ các cụm đã đặt tên, hệ thống tạo danh sách `nodes` chứa tên topic, keyword, vị trí x-y và kích thước cụm. Tiếp theo, hệ thống tính khoảng cách giữa các cụm để tạo `edges`, giúp frontend hiển thị mối liên hệ gần xa giữa các topic.

7. **Ghép kết quả và trả về một JSON thống nhất**  
   Cuối cùng, file trả về 2 khối dữ liệu trong cùng một response:
   - `leaderboard`: kết quả từ nhánh zero-shot classification.
   - `graph`: kết quả từ nhánh emergent topic clustering.

Nói ngắn gọn, `pipeline_service.py` đóng vai trò như bộ điều phối trung tâm: lấy dữ liệu thô từ database, chuẩn hóa thành embedding, xử lý song song theo 2 hướng phân loại và khám phá, rồi hợp nhất tất cả thành dữ liệu sẵn sàng cho giao diện người dùng.

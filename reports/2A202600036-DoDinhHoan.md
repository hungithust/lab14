# Báo cáo cá nhân - Đỗ Đình Hoàn

## 1. Thông tin phân công
- **Phụ trách chính:** `engine/runner.py`, `analysis/failure_analysis.md`

## 2. Engineering Contribution
- Thiết kế và hoàn thiện luồng chạy benchmark trong [`engine/runner.py`](C:/Users/Kat/Documents/AICB_lab/lab14/engine/runner.py), bao gồm:
  - Chạy từng test case theo pipeline thống nhất: Agent -> Retrieval/Generation Metrics -> Multi-Judge.
  - Thu thập `latency`, `token usage`, `estimated_cost_usd`, `error_count` cho từng case.
  - Hỗ trợ chạy song song theo batch bằng `asyncio.gather` để tăng tốc toàn bộ benchmark.
- Viết và hoàn thiện báo cáo phân tích lỗi trong [`analysis/failure_analysis.md`](C:/Users/Kat/Documents/AICB_lab/lab14/analysis/failure_analysis.md):
  - Tổng hợp số liệu benchmark thật từ `reports/benchmark_results.json`.
  - Phân nhóm lỗi theo cụm nguyên nhân.
  - Thực hiện phân tích `5 Whys` cho các case có rủi ro cao.
- Đóng góp trực tiếp vào việc biến pipeline từ dạng demo/stub sang dạng benchmark có thể dùng để chấm bài.

## 3. Technical Depth
- Hiểu rõ ý nghĩa của việc tách `runner` thành một lớp điều phối trung tâm:
  - Giữ benchmark flow nhất quán cho mọi test case.
  - Tách trách nhiệm giữa Agent, Evaluator và Judge để dễ mở rộng.
- Hiểu trade-off giữa **độ song song** và **rate limit**:
  - Song song giúp giảm runtime toàn pipeline.
  - Nhưng nếu đẩy quá mạnh sẽ bị `429 TPM`, nên cần chọn batch size hợp lý và có retry/backoff.
- Hiểu ý nghĩa của các chỉ số hệ thống:
  - `latency_seconds`: đo độ nhanh từng case.
  - `prompt_tokens`, `completion_tokens`, `total_tokens`: đo chi phí tính toán.
  - `estimated_cost_usd`: quy đổi token usage thành chi phí ước tính để phục vụ release gate.
- Hiểu vai trò của failure analysis:
  - Không chỉ liệt kê case fail, mà phải chỉ ra lỗi nằm ở retrieval, generation, hay safety policy.

## 4. Problem Solving
- Xử lý vấn đề pipeline ban đầu chỉ có placeholder metrics bằng cách kết nối benchmark với dữ liệu thực và report thực.
- Hỗ trợ xác định nguyên nhân khi benchmark bị chậm hoặc bị rate limit, từ đó tinh chỉnh batch size và retry strategy.
- Chuyển báo cáo phân tích lỗi từ bản mẫu placeholder sang bản dùng số liệu thật, cập nhật theo kết quả benchmark mới nhất.

## 5. Kết quả đầu ra liên quan
- [`engine/runner.py`](C:/Users/Kat/Documents/AICB_lab/lab14/engine/runner.py)
- [`analysis/failure_analysis.md`](C:/Users/Kat/Documents/AICB_lab/lab14/analysis/failure_analysis.md)
- [`reports/benchmark_results.json`](C:/Users/Kat/Documents/AICB_lab/lab14/reports/benchmark_results.json)
- [`reports/summary.json`](C:/Users/Kat/Documents/AICB_lab/lab14/reports/summary.json)

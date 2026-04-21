# Báo cáo cá nhân - Trần Quốc Khánh
2A202600306

## 1. Thông tin phân công
- **Phụ trách chính:** `main.py`, `agent/main_agent.py`

## 2. Engineering Contribution
- Hoàn thiện entrypoint benchmark trong [`main.py`](C:/Users/Kat/Documents/AICB_lab/lab14/main.py):
  - Chạy benchmark V1 vs V2.
  - In kết quả so sánh regression ra console.
  - Ghi `reports/summary.json` và `reports/benchmark_results.json`.
  - Giữ tương thích với format I/O cũ của bài lab.
  - Bổ sung báo cáo hệ thống chi tiết: runtime, batch size, token usage, cost report, latency report.
- Hoàn thiện agent trong [`agent/main_agent.py`](C:/Users/Kat/Documents/AICB_lab/lab14/agent/main_agent.py):
  - Query ChromaDB để retrieval context.
  - Gọi model để generate answer có căn cứ.
  - Trả thêm `retrieved_ids`, `prompt_tokens`, `completion_tokens`, `total_tokens`.
  - Thêm retry/backoff để hạn chế lỗi `429 rate limit`.

## 3. Technical Depth
- Hiểu rõ vai trò của `main.py` như lớp tích hợp toàn pipeline:
  - Kết nối dataset, agent, retrieval evaluator, judge, runner, report.
  - Đồng thời phải giữ đúng format đầu vào/đầu ra theo yêu cầu bài lab.
- Hiểu trade-off giữa **song song cực nhanh** và **giới hạn TPM của API**:
  - Nếu song song quá mạnh sẽ nhanh nhưng dễ dính rate limit.
  - Nếu quá thận trọng sẽ ổn định nhưng không đạt KPI `< 2 phút`.
  - Giải pháp thực tế là batch song song có kiểm soát + retry/backoff.
- Hiểu release gate:
  - Không chỉ nhìn `avg_score`.
  - Cần xét thêm retrieval quality, agreement, latency, cost và error rate.

## 4. Problem Solving
- Xử lý việc benchmark ban đầu dùng stub và không tạo report đủ chi tiết.
- Giữ được format cũ của `main.py` trong khi vẫn nâng cấp logic thật ở bên dưới.
- Giải quyết lỗi `UnicodeEncodeError` và `RateLimitError` trong quá trình chạy benchmark trên Windows/PowerShell.
- Hoàn thiện report để đáp ứng yêu cầu “Cost & Token usage” và benchmark nhanh dưới 2 phút.

## 5. Kết quả đầu ra liên quan
- [`main.py`](C:/Users/Kat/Documents/AICB_lab/lab14/main.py)
- [`agent/main_agent.py`](C:/Users/Kat/Documents/AICB_lab/lab14/agent/main_agent.py)
- [`reports/summary.json`](C:/Users/Kat/Documents/AICB_lab/lab14/reports/summary.json)
- [`reports/benchmark_results.json`](C:/Users/Kat/Documents/AICB_lab/lab14/reports/benchmark_results.json)

# Báo cáo cá nhân - Nguyễn Xuân Tùng

## 1. Thông tin phân công
- **Phụ trách chính:** `engine/llm_judge.py`

## 2. Engineering Contribution
- Hoàn thiện module judge trong [`engine/llm_judge.py`](C:/Users/Kat/Documents/AICB_lab/lab14/engine/llm_judge.py):
  - Tích hợp đồng thời 2 model judge: `gpt-4o-mini` và `gpt-4o`.
  - Chuẩn hóa output mỗi judge theo JSON có cấu trúc: `accuracy`, `professionalism`, `safety`, `overall_score`, `reasoning`.
  - Tính `agreement_rate` giữa hai judge.
  - Thêm logic xử lý xung đột tự động: nếu lệch điểm lớn, ưu tiên `gpt-4o` làm trọng tài.
  - Ghi nhận `usage` của từng judge để phục vụ báo cáo cost/token usage.
- Bổ sung fallback và retry/backoff khi gặp rate limit để tăng độ ổn định khi benchmark chạy nhiều case.

## 3. Technical Depth
- Hiểu rõ vai trò của **Multi-Judge Consensus**:
  - Một judge đơn lẻ dễ thiên lệch.
  - Hai judge giúp tăng độ tin cậy và giảm rủi ro chấm sai.
- Hiểu ý nghĩa của `agreement_rate`:
  - Agreement cao cho thấy hai model đánh giá tương đối nhất quán.
  - Agreement thấp là tín hiệu cần kiểm tra lại response hoặc bổ sung arbitration logic.
- Hiểu khái niệm **Position Bias**:
  - Khi judge bị ảnh hưởng bởi vị trí trình bày response A/B thay vì nội dung thực.
  - Module hiện đã để sẵn hook `check_position_bias` để mở rộng trong tương lai.
- Hiểu trade-off giữa **chất lượng judge** và **chi phí**:
  - `gpt-4o` mạnh hơn nhưng đắt hơn.
  - `gpt-4o-mini` rẻ hơn, phù hợp để tạo lớp đồng thuận ban đầu.

## 4. Problem Solving
- Giải quyết việc module judge ban đầu chỉ là stub bằng cách thay bằng judge thực gọi model.
- Xử lý bài toán khi 2 judge không đồng ý nhau:
  - Không chỉ lấy trung bình đơn giản.
  - Có trạng thái `consensus`, `single_judge`, `conflict_resolved_by_gpt4o`.
- Giảm rủi ro fail benchmark khi gặp rate limit bằng retry/backoff.

## 5. Kết quả đầu ra liên quan
- [`engine/llm_judge.py`](C:/Users/Kat/Documents/AICB_lab/lab14/engine/llm_judge.py)
- Dữ liệu judge trong [`reports/benchmark_results.json`](C:/Users/Kat/Documents/AICB_lab/lab14/reports/benchmark_results.json)

# Báo cáo cá nhân - Nguyễn Viết Hùng

## 1. Thông tin phân công
- **Phụ trách chính:** `data/synthetic_gen.py`, sinh bộ 50 golden data

## 2. Engineering Contribution
- Hoàn thiện script sinh dữ liệu trong [`data/synthetic_gen.py`](C:/Users/Kat/Documents/AICB_lab/lab14/data/synthetic_gen.py):
  - Gọi model để sinh bộ câu hỏi benchmark tự động.
  - Chia mức độ khó thành `easy`, `medium`, `hard`, `extreme`.
  - Sinh tối thiểu 50 test cases.
  - Bắt buộc mỗi case có `relevant_chunk_ids`, `expected_answer`, `answer_keywords`, `expected_behavior`, `difficulty`, `type`.
- Đảm bảo file đầu ra [`data/golden_set.jsonl`](C:/Users/Kat/Documents/AICB_lab/lab14/data/golden_set.jsonl) tương thích với pipeline retrieval eval và judge eval.
- Bổ sung nhiều case dạng adversarial/red teaming như:
  - prompt injection
  - security bypass
  - goal hijacking
  - out-of-context

## 3. Technical Depth
- Hiểu vai trò của **Golden Dataset** trong benchmark:
  - Là nguồn chuẩn để đo retrieval quality và answer quality.
  - Nếu dataset yếu hoặc thiếu ground-truth IDs thì toàn bộ metric retrieval sẽ mất giá trị.
- Hiểu giá trị của việc gắn `relevant_chunk_ids`:
  - Cho phép đo trực tiếp Hit Rate và MRR.
  - Giúp tách lỗi retrieval khỏi lỗi generation.
- Hiểu ý nghĩa của việc phân tầng độ khó:
  - `easy`: factual lookup
  - `medium`: reasoning / multi-chunk
  - `hard`: edge cases
  - `extreme`: adversarial / security
- Hiểu rằng red teaming không chỉ để “làm khó”, mà để phát hiện lỗ hổng policy và guardrail.

## 4. Problem Solving
- Giải quyết vấn đề không có sẵn golden set trong repo bằng script sinh tự động.
- Thiết kế schema đủ giàu để dùng cho nhiều nhóm metrics khác nhau cùng lúc.
- Tạo bộ dữ liệu có cả câu hỏi thông thường lẫn câu hỏi phá hệ thống, giúp benchmark phản ánh đúng rủi ro thực tế hơn.

## 5. Kết quả đầu ra liên quan
- [`data/synthetic_gen.py`](C:/Users/Kat/Documents/AICB_lab/lab14/data/synthetic_gen.py)
- [`data/golden_set.jsonl`](C:/Users/Kat/Documents/AICB_lab/lab14/data/golden_set.jsonl)

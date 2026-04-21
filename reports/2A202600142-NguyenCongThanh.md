# Báo cáo cá nhân - Nguyễn Công Thành -2A202600142

## 1. Thông tin phân công
- **Phụ trách chính:** `engine/retrieval_eval.py`

## 2. Engineering Contribution
- Hoàn thiện module đánh giá retrieval trong [`engine/retrieval_eval.py`](C:/Users/Kat/Documents/AICB_lab/lab14/engine/retrieval_eval.py):
  - Tính `Hit Rate@K`.
  - Tính `MRR`.
  - Truy xuất `expected_ids` từ `relevant_chunk_ids`.
  - Suy ra `retrieved_ids` từ response hoặc context đã truy xuất.
- Bổ sung generation metrics thực tế thay cho placeholder:
  - `faithfulness`
  - `relevancy`
- Tùy chỉnh heuristic phù hợp với dataset tiếng Việt:
  - `stopwords` tiếng Việt có dấu
  - `refusal_markers` tiếng Việt có dấu

## 3. Technical Depth
- Hiểu rõ **MRR**:
  - Nếu chunk đúng xuất hiện càng sớm trong top retrieved thì điểm càng cao.
  - Điều này quan trọng hơn chỉ biết “có lấy đúng hay không”, vì thứ hạng retrieval ảnh hưởng mạnh đến generation.
- Hiểu mối liên hệ giữa **Retrieval Quality** và **Answer Quality**:
  - Retrieval sai dễ kéo theo answer sai.
  - Nhưng retrieval đúng chưa chắc answer đúng nếu generation hoặc safety guardrail yếu.
- Hiểu vai trò của `faithfulness` và `relevancy`:
  - `faithfulness`: câu trả lời có bám vào context hay không.
  - `relevancy`: câu trả lời có đúng trọng tâm câu hỏi và expected answer hay không.
- Hiểu trade-off:
  - Heuristic local rẻ và nhanh hơn judge bằng LLM.
  - Nhưng độ chính xác ngữ nghĩa thấp hơn judge chuyên biệt.

## 4. Problem Solving
- Giải quyết việc pipeline ban đầu chỉ có retrieval metrics đơn giản và generation metrics placeholder `0.0`.
- Xử lý vấn đề dataset tiếng Việt bằng cách Việt hóa bộ stopwords và refusal markers.
- Thiết kế evaluator sao cho dùng được với output thực tế của agent thay vì chỉ với dữ liệu lý tưởng.

## 5. Kết quả đầu ra liên quan
- [`engine/retrieval_eval.py`](C:/Users/Kat/Documents/AICB_lab/lab14/engine/retrieval_eval.py)
- Chỉ số retrieval/generation trong [`reports/benchmark_results.json`](C:/Users/Kat/Documents/AICB_lab/lab14/reports/benchmark_results.json)
- Tổng hợp metric trong [`reports/summary.json`](C:/Users/Kat/Documents/AICB_lab/lab14/reports/summary.json)

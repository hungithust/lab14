"""
Script xuất tất cả chunk IDs và text tương ứng từ ChromaDB.
Kết quả được lưu vào file: data/chunks_export.txt và data/chunks_export.json
"""

import json
import os
import sys

def export_chunks():
    try:
        import chromadb
    except ImportError:
        print("❌ chromadb chưa được cài. Đang cài đặt...")
        os.system(f"{sys.executable} -m pip install chromadb -q")
        import chromadb

    # Đường dẫn tới ChromaDB
    db_path = os.path.join(os.path.dirname(__file__), "chroma_db")
    print(f"📂 Đọc ChromaDB tại: {db_path}")

    client = chromadb.PersistentClient(path=db_path)

    # Liệt kê tất cả collections
    collections = client.list_collections()
    if not collections:
        print("⚠️  Không tìm thấy collection nào trong ChromaDB.")
        return

    print(f"✅ Tìm thấy {len(collections)} collection(s): {[c.name for c in collections]}\n")

    os.makedirs("data", exist_ok=True)
    all_data = {}

    txt_lines = []
    txt_lines.append("=" * 80)
    txt_lines.append("CHROMADB CHUNKS EXPORT")
    txt_lines.append("=" * 80)

    for collection in collections:
        col = client.get_collection(collection.name)
        result = col.get(include=["documents", "metadatas"])

        ids       = result.get("ids", [])
        documents = result.get("documents", [])
        metadatas = result.get("metadatas", [])

        print(f"📦 Collection: '{collection.name}' — {len(ids)} chunks")

        txt_lines.append(f"\n📦 COLLECTION: {collection.name}  ({len(ids)} chunks)")
        txt_lines.append("-" * 80)

        col_data = []
        for i, (chunk_id, doc, meta) in enumerate(zip(ids, documents, metadatas or [{}]*len(ids))):
            entry = {
                "index": i + 1,
                "id":    chunk_id,
                "text":  doc,
                "metadata": meta,
            }
            col_data.append(entry)

            # Định dạng text output
            txt_lines.append(f"\n[{i+1:04d}] ID: {chunk_id}")
            if meta:
                meta_str = " | ".join(f"{k}={v}" for k, v in meta.items())
                txt_lines.append(f"      META: {meta_str}")
            txt_lines.append(f"      TEXT: {doc}")
            txt_lines.append("")

        all_data[collection.name] = col_data

    # Ghi file TXT
    txt_path = os.path.join("data", "chunks_export.txt")
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write("\n".join(txt_lines))
    print(f"\n✅ Đã xuất TXT  → {txt_path}")

    # Ghi file JSON
    json_path = os.path.join("data", "chunks_export.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(all_data, f, ensure_ascii=False, indent=2)
    print(f"✅ Đã xuất JSON → {json_path}")

    # In thống kê tổng hợp
    total_chunks = sum(len(v) for v in all_data.values())
    print(f"\n📊 Tổng số chunks: {total_chunks}")


if __name__ == "__main__":
    export_chunks()

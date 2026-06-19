import os
import sys

# Add backend directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import numpy as np
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sentence_transformers import SentenceTransformer
from umap import UMAP
from hdbscan import HDBSCAN
from sklearn.feature_extraction.text import CountVectorizer
from bertopic import BERTopic
from bertopic.representation import KeyBERTInspired
from bertopic.vectorizers import ClassTfidfTransformer
import requests

from app.models.schema import Paper, Category, Cluster

# Init embedding model (all-MiniLM-L6-v2)
embedding_model = SentenceTransformer("all-MiniLM-L6-v2")

def get_papers_last_30_days(db: Session):
    """Lọc dữ liệu 30 ngày gần nhất từ database"""
    thirty_days_ago = datetime.utcnow().date() - timedelta(days=30)
    papers = db.query(Paper).filter(Paper.published >= thirty_days_ago).all()
    return papers

def generate_embeddings(texts: list[str]) -> np.ndarray:
    """Sử dụng mô hình nhỏ để sinh embeddings nhanh"""
    print(f"Generating embeddings for {len(texts)} abstracts...")
    return embedding_model.encode(texts, show_progress_bar=True)

# ----------------- NHÁNH 1: ZERO-SHOT CLASSIFICATION ----------------- #
def process_zero_shot_classification(db: Session, papers: list[Paper]):
    """
    Phân loại bài báo mới vào các chủ đề tạo sẵn dựa vào Cosine Similarity.
    Đầu ra: Danh sách JSON (Leaderboard) sắp xếp theo số lượng / growth rate.
    """
    categories = db.query(Category).all()
    if not categories:
        print("No predefined categories found.")
        return []
    
    cat_vectors = np.array([cat.category_vector for cat in categories]) # (M, 384)
    cat_names = [cat.name for cat in categories]
    
    # Handle zero vectors in categories
    norms = np.linalg.norm(cat_vectors, axis=1, keepdims=True)
    norms[norms == 0] = 1 # Avoid division by zero
    cat_vectors_norm = cat_vectors / norms

    results = {cat_name: 0 for cat_name in cat_names}

    for paper in papers:
        if paper.paper_vector is None:
            continue
            
        p_vec = np.array(paper.paper_vector)
        p_vec_norm = p_vec / np.linalg.norm(p_vec)
        
        # Tính dot product (cosine similarity vì đã normalize)
        similarities = np.dot(cat_vectors_norm, p_vec_norm)
        
        best_match_idx = np.argmax(similarities)
        best_score = similarities[best_match_idx]
        
        # Ngưỡng Threshold 0.65 như thiết kế
        if best_score > 0.65:
            results[cat_names[best_match_idx]] += 1
            
    # Tính Growth Rate và build Leaderboard
    leaderboard = []
    for name, count in results.items():
        leaderboard.append({
            "topic": name,
            "paper_count": count,
            "growth_rate": round(np.random.uniform(2.0, 15.0), 2) # Giả lập growth rate để test UI
        })
        
    leaderboard.sort(key=lambda x: x["paper_count"], reverse=True)
    return leaderboard

# ----------------- NHÁNH 2: EMERGENT TOPIC CLUSTERING ----------------- #
def query_ollama_for_name(keywords: list[str]) -> str:
    """Sử dụng Ollama (Local LLM) để đặt tên cụm dựa vào keywords"""
    prompt = f"You are an AI researcher. Name this research cluster based on these keywords in under 5 words: {', '.join(keywords)}. Output only the name, no extra text."
    try:
        response = requests.post("http://localhost:11434/api/generate", json={
            "model": "qwen3.5:4b", 
            "prompt": prompt,
            "stream": False
        })
        if response.status_code == 200:
            return response.json().get("response", "").strip()
    except Exception as e:
        print(f"Ollama error: {e}")
    return "Emergent Topic"

def process_topic_clustering(db: Session, papers: list[Paper]):
    """
    Sử dụng UMAP + HDBSCAN + c-TF-IDF để tìm cụm mới nổi.
    Đầu ra: Dữ liệu Đồ thị dạng Nodes & Edges (Center Graph UI).
    """
    if len(papers) < 15:
        print("Not enough papers for clustering.")
        return {"nodes": [], "edges": []}
        
    texts_to_process = [f"{p.title}. {p.abstract}" for p in papers]
    embeddings = np.array([p.paper_vector for p in papers])
    
    # 1. Giảm chiều UMAP (Nén 384D xuống 2D) & Gom cụm HDBSCAN
    umap_model = UMAP(n_neighbors=15, n_components=2, min_dist=0.0, metric='cosine', random_state=42)
    hdbscan_model = HDBSCAN(min_cluster_size=5, metric='euclidean', cluster_selection_method='eom', prediction_data=True)
    
    # 2. c-TF-IDF Extract Keywords
    vectorizer_model = CountVectorizer(stop_words="english")
    ctfidf_model = ClassTfidfTransformer()
    representation_model = KeyBERTInspired()

    topic_model = BERTopic(
        embedding_model=embedding_model,
        umap_model=umap_model,
        hdbscan_model=hdbscan_model,
        vectorizer_model=vectorizer_model,
        ctfidf_model=ctfidf_model,
        representation_model=representation_model
    )
    
    print("Fitting BERTopic Pipeline...")
    topics, probs = topic_model.fit_transform(texts_to_process, embeddings)
    
    # Tọa độ 2D của tất cả các bài báo
    reduced_embeddings = umap_model.embedding_ # Shape: (N, 2)
    
    # Cập nhật tọa độ vào entities để trả về (hoặc lưu DB)
    for i, paper in enumerate(papers):
        paper.umap_x = float(reduced_embeddings[i, 0])
        paper.umap_y = float(reduced_embeddings[i, 1])
        
    topic_info = topic_model.get_topic_info()
    graph_nodes = []
    
    for _, row in topic_info.iterrows():
        topic_id = row['Topic']
        if topic_id == -1: # Outliers
            continue
            
        count = row['Count']
        keywords = [word for word, score in topic_model.get_topic(topic_id)[:10]]
        
        # 3. LLM Naming
        cluster_name = query_ollama_for_name(keywords)
        
        # Tính toán Centroid 2D cho Node này
        cluster_indices = [i for i, t in enumerate(topics) if t == topic_id]
        centroid_x = float(np.mean(reduced_embeddings[cluster_indices, 0]))
        centroid_y = float(np.mean(reduced_embeddings[cluster_indices, 1]))
        
        graph_nodes.append({
            "id": f"cluster_{topic_id}",
            "name": cluster_name,
            "keywords": keywords,
            "size": int(count),
            "x": centroid_x,
            "y": centroid_y
        })
        
    # Tính toán Edges: Liên kết các Node có khoảng cách gần nhau
    graph_edges = []
    for i in range(len(graph_nodes)):
        for j in range(i+1, len(graph_nodes)):
            n1, n2 = graph_nodes[i], graph_nodes[j]
            dist = np.sqrt((n1['x'] - n2['x'])**2 + (n1['y'] - n2['y'])**2)
            
            if dist < 2.0: # Threshold khoảng cách (tùy chỉnh)
                graph_edges.append({
                    "source": n1['id'],
                    "target": n2['id'],
                    "weight": round(1 / (dist + 0.1), 2)
                })

    return {
        "nodes": graph_nodes,
        "edges": graph_edges
    }

def run_full_pipeline(db: Session = None):
    """Hàm Main orchestration điều phối dữ liệu"""
    papers = []
    categories = []
    
    if db is not None:
        try:
            papers = get_papers_last_30_days(db)
            categories = db.query(Category).all()
        except Exception as e:
            print(f"DB error: {e}")
            return {"leaderboard": [], "graph": {"nodes": [], "edges": []}}
    
    if not papers or not categories:
        print("No data available in the database.")
        return {"leaderboard": [], "graph": {"nodes": [], "edges": []}}
        
    # Check embedding & generate
    papers_to_embed = [p for p in papers if p.paper_vector is None]
    if papers_to_embed:
        texts_to_process = [f"{p.title}. {p.abstract}" for p in papers_to_embed]
        vectors = generate_embeddings(texts_to_process)
        for i, p in enumerate(papers_to_embed):
            p.paper_vector = vectors[i].tolist()
            
    cats_to_embed = [c for c in categories if getattr(c, "category_vector", None) is None]
    if cats_to_embed:
        cat_texts = [c.name for c in cats_to_embed]
        cat_vectors = generate_embeddings(cat_texts)
        for i, c in enumerate(cats_to_embed):
            c.category_vector = cat_vectors[i].tolist()
        
    output_1 = process_zero_shot_classification(db, papers)
    output_2 = process_topic_clustering(None, papers)
    
    return {
        "leaderboard": output_1,
        "graph": output_2
    }


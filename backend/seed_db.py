import os
import sys
from datetime import datetime, timedelta
import random

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.database import SessionLocal, engine, Base
from app.models.schema import Category, Paper

def seed_data():
    db = SessionLocal()
    
    print("Clearing old data...")
    db.query(Paper).delete()
    db.query(Category).delete()
    db.commit()

    print("Seeding Categories...")
    categories = [
        Category(name="Large Language Models", description="Models like GPT-4, LLaMA"),
        Category(name="Computer Vision", description="Image processing and object detection"),
        Category(name="Reinforcement Learning", description="Agent training via rewards"),
        Category(name="Agentic AI", description="Autonomous reasoning agents")
    ]
    db.add_all(categories)
    db.commit()

    print("Seeding Papers...")
    mock_papers = [
        ("A new LLM", "We introduce a new large language model that outperforms GPT-4 on reasoning tasks using chain of thought."),
        ("Vision Transformer", "This paper presents a novel vision transformer architecture for image classification and object detection."),
        ("RL in Robotics", "We apply deep reinforcement learning to train a robotic arm to perform complex manipulation tasks."),
        ("Multi-Agent System", "An autonomous multi-agent system where LLMs collaborate to write and test software code."),
        ("LLM Hallucinations", "We study the problem of hallucinations in large language models and propose a retrieval-augmented solution."),
        ("Image Segmentation", "A new method for semantic image segmentation using diffusion models and attention mechanisms."),
        ("PPO Agent", "Improving proximal policy optimization for continuous control tasks in reinforcement learning."),
        ("Agentic Workflow", "Agentic workflows using LLMs for automated data analysis and report generation."),
        ("Prompt Engineering", "Techniques for prompt engineering to improve zero-shot reasoning in LLMs."),
        ("3D Point Clouds", "Deep learning on 3D point clouds for autonomous driving applications."),
        ("Q-Learning", "A theoretical analysis of deep Q-learning convergence in stochastic environments."),
        ("Autonomous Agents", "Building autonomous AI agents that can browse the web and complete user tasks."),
        ("Language Agents", "Language models as intelligent agents: a survey of current methods and future directions."),
        ("Object Detection", "Real-time object detection on mobile devices using lightweight neural networks."),
        ("RLHF", "Reinforcement learning from human feedback for aligning language models with human values."),
        ("Generative Agents", "Generative interactive agents that simulate human behavior in a virtual sandbox environment."),
        ("Diffusion Models", "Stable diffusion techniques for high fidelity image synthesis."),
        ("Robotics Control", "Imitation learning for dexterous manipulation in humanoid robots."),
        ("LLM Agents in Software", "Evaluating LLM-based autonomous agents on real-world GitHub issues."),
        ("Transformer Variants", "Efficient attention mechanisms for processing long context windows in transformers.")
    ]

    papers = []
    for i, (title, abstract) in enumerate(mock_papers):
        # random date in the last 20 days
        pub_date = datetime.utcnow().date() - timedelta(days=random.randint(1, 20))
        papers.append(Paper(
            arxiv_id=f"2026.{i:05d}",
            title=title,
            abstract=abstract,
            authors=["Alice", "Bob"],
            published=pub_date,
            url=f"https://arxiv.org/abs/2026.{i:05d}"
        ))
        
    db.add_all(papers)
    db.commit()
    print(f"Successfully seeded {len(categories)} categories and {len(papers)} papers!")
    db.close()

if __name__ == "__main__":
    seed_data()

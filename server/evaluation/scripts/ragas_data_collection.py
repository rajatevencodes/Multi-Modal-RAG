"""
RAGAS Data Collection Script
Runs test questions through your RAG system and collects evaluation data.
"""

import json
from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.rag.retrieval.index import retrieve_context
from src.rag.retrieval.utils import prepare_prompt_and_invoke_llm

# Configuration
PROJECT_ID = "5fafc7b2-d6e8-4ef6-90f7-1fe83250a913"

TEST_QUESTIONS = [
    "Explain the difference between macronutrients and micronutrients, giving two examples of each.",
    "How does the glycemic index of a food affect blood glucose levels, and why are low-GI foods generally recommended for long-term health?",
    "Describe the roles of soluble and insoluble fiber in the human body and list at least one food source rich in each type.",
    "Compare saturated, unsaturated, and trans fats in terms of sources and health effects.",
    "Why is vitamin D often called a *special* vitamin, and what are the main consequences of its deficiency?",
    "Outline the major differences between the Ancient World, Medieval Period, and Early Modern Period in world history.",
    "Why is the invention of writing considered a turning point in human civilization?",
    "Describe the historical significance of the Battle of Marathon and its long-term impact on Greek civilization.",
    "What factors contributed to the fall of the Western Roman Empire in 476 CE?",
    "Explain how the Edict of Milan changed the status of Christianity within the Roman Empire.",
    "Summarize the main idea of the paper “Attention Is All You Need” and how the Transformer differs from RNN-based sequence models.",
    "What is self-attention, and why is it particularly useful for modeling long-range dependencies in sequences?",
    "Describe scaled dot-product attention: what are Q, K, and V, and why is scaling by sqrt(d_k) necessary?",
    "What is multi-head attention, and what advantage does it provide over a single attention head?",
    "Explain the encoder&decoder structure of the Transformer and the role of masking in the decoder.",
    "In the AlexNet paper, what are the key architectural components (layers) of the network used for ImageNet classification?",
    "Why did AlexNet use ReLU activations instead of traditional saturating nonlinearities like tanh or sigmoid?",
    "How did AlexNet leverage GPUs and data augmentation to make training a very large CNN feasible?",
    "What is dropout, and how did it help AlexNet reduce overfitting?",
    "Explain why convolutional neural networks are well suited for image classification compared to fully connected networks.",
    "Define the Big Bang theory and list two key pieces of observational evidence supporting it.",
    "What are dark matter and dark energy, and how do they differently influence the evolution of the universe?",
    "Describe the large-scale structure of the universe (galaxies, clusters, superclusters, and the cosmic web).",
    "Outline the typical life cycle of a low-mass star like the Sun, from formation to its final stage.",
    "What is a black hole event horizon, and why can no information escape from within it?",
    "Differentiate between the central nervous system (CNS) and peripheral nervous system (PNS).",
    "Describe the structure of a typical neuron and the function of dendrites, axon, and synapse.",
    "Compare the roles of glutamate and GABA in the brain and explain why their balance is crucial.",
    "What functions are associated with the frontal lobe and hippocampus, respectively?",
    "Describe the wildlife conservation measures used in India, including sanctuaries, national parks, and biosphere reserves.",
]


def collect_rag_data(project_id: str, questions: list) -> list:
    """Run questions through RAG pipeline and collect data."""
    dataset = []

    for question in questions:
        print(f"Processing: {question}")

        # Retrieve context
        texts, images, tables, citations = retrieve_context(project_id, question)

        # Prepare contexts for RAGAS
        contexts = texts + [f"[TABLE]\n{table}" for table in tables]

        # Generate answer
        answer = prepare_prompt_and_invoke_llm(question, texts, [], tables)

        dataset.append(
            {
                "question": question,
                "contexts": contexts or ["No context found"],
                "answer": answer,
            }
        )

    return dataset


if __name__ == "__main__":
    # Collect and save data
    dataset = collect_rag_data(PROJECT_ID, TEST_QUESTIONS)

    output_path = (
        Path(__file__).parent.parent / "datasets" / "ragas_evaluation_dataset.json"
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(dataset, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Saved {len(dataset)} questions to {output_path}")

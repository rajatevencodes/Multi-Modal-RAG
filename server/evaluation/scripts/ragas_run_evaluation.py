import json
from pathlib import Path
from datasets import Dataset
from ragas import evaluate
from ragas.metrics import (
    faithfulness,
    answer_relevancy,
    # context_precision,
    # context_recall,
)
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from dotenv import load_dotenv

load_dotenv()

# Load your dataset
dataset_path = (
    Path(__file__).parent.parent / "datasets" / "ragas_evaluation_dataset.json"
)
with open(dataset_path, "r") as f:
    data = json.load(f)

# Convert to RAGAS format
dataset = Dataset.from_dict(
    {
        "question": [item["question"] for item in data],
        "contexts": [item["contexts"] for item in data],
        "answer": [item["answer"] for item in data],
    }
)

# Set up evaluator (using GPT-4 for evaluation)
llm = ChatOpenAI(model="gpt-4o", temperature=0)
embeddings = OpenAIEmbeddings(model="text-embedding-3-large")

# Run evaluation
results = evaluate(
    dataset=dataset,
    metrics=[
        faithfulness,
        answer_relevancy,
        # context_precision,
        # context_recall,
    ],
    llm=llm,
    embeddings=embeddings,
)

# Convert to DataFrame first
df = results.to_pandas()

# Save to CSV
output_path = Path(__file__).parent.parent / "datasets" / "final_results.csv"
df.to_csv(output_path, index=False)
print(f"\n✅ Detailed results saved to {output_path}")

import os
import pandas as pd
from datasets import Dataset
from dotenv import load_dotenv

# Ragas Imports
from ragas import evaluate
from ragas.metrics import Faithfulness, AnswerRelevancy, ContextRecall
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

def main():
    # Load your OpenAI API Key from your .env file
    load_dotenv()
    
    # 1. Path to your specific file
    file_path = r'D:\RAG\data\evaluation\validation_set.csv'
    print(f"Loading data from: {file_path}")
    
    if not os.path.exists(file_path):
        print(f"❌ Error: File not found at {file_path}")
        return

    # --- THE FIX: Handle Encoding Errors ---
    try:
        # First try standard UTF-8
        df = pd.read_csv(file_path, encoding='utf-8')
    except UnicodeDecodeError:
        # Fallback to latin1 if UTF-8 fails (common for Windows-saved CSVs)
        print("Notice: UTF-8 decoding failed. Switching to 'latin1' encoding...")
        df = pd.read_csv(file_path, encoding='latin1')

    # 2. Map your columns to Ragas requirements
    # Ensure all inputs are treated as strings to avoid errors
    data = {
        "question": df["Questions"].astype(str).tolist(),
        "answer": df["RAG Answers"].astype(str).tolist(),
        "contexts": [[str(c)] for c in df["Context"].tolist()],
        "ground_truth": df["Ground Truth"].astype(str).tolist()
    }
    dataset = Dataset.from_dict(data)

    # 3. Setup the Judge (GPT-4o-mini) and Embeddings
    llm = ChatOpenAI(model="gpt-4o-mini")
    embeddings = OpenAIEmbeddings(model="text-embedding-3-large")

    # 4. Run Evaluation
    print(f"Starting Ragas evaluation for {len(df)} rows...")
    
    metrics = [Faithfulness(), AnswerRelevancy(), ContextRecall()]
    
    for metric in metrics:
        metric.llm = llm
        if hasattr(metric, "embeddings"):
            metric.embeddings = embeddings

    result = evaluate(
        dataset,
        metrics=metrics
    )

    # 5. Save detailed per-question scores to Excel
    df_result = result.to_pandas()
    output_excel = "ragas_eval_detailed_results.xlsx"
    df_result.to_excel(output_excel, index=False)
    
    # 6. Calculate and Print the Mean Scores
    print("\n" + "="*45)
    print("        RAG EVALUATION SUMMARY (MEAN)")
    print("="*45)
    for metric_name, score in result.items():
        print(f"{metric_name:25}: {score:.4f}")
    print("="*45)
    print(f"Individual scores saved to: {os.getcwd()}\\{output_excel}")

if __name__ == "__main__":
    main()
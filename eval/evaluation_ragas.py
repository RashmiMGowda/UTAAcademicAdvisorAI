# This script evaluates the performance of a Retrieval-Augmented Generation (RAG) system
#  using the Ragas evaluation framework. It loads a validation dataset from a specified
# CSV file, processes the data to fit the requirements of Ragas, and then runs the
# evaluation using specified metrics (faithfulness, answer relevancy, and context recall).
# The results are saved to an Excel file, and a summary of the mean scores is printed
#  to the console. The script also handles potential encoding issues when reading the
# CSV file and ensures that the output is well-formatted for analysis.
import os
import pandas as pd
from datasets import Dataset
from dotenv import load_dotenv

# Modern Ragas Imports (Fixes DeprecationWarnings)
from ragas import evaluate
from ragas.metrics import faithfulness, answer_relevancy, context_recall
from langchain_openai import ChatOpenAI, OpenAIEmbeddings


def main():
    load_dotenv()

    # 1. Path to your specific file
    file_path = r'D:\RAG\data\evaluation\validation_set.csv'
    print(f"Loading data from: {file_path}")

    if not os.path.exists(file_path):
        print(f"❌ Error: File not found at {file_path}")
        return

    # Handle Encoding for Windows CSVs
    try:
        df = pd.read_csv(file_path, encoding='utf-8')
    except UnicodeDecodeError:
        print("Notice: UTF-8 decoding failed. Switching to 'latin1' encoding...")
        df = pd.read_csv(file_path, encoding='latin1')

    # 2. Map columns to Ragas requirements
    data = {
        "question": df["Questions"].astype(str).tolist(),
        "answer": df["RAG Answers"].astype(str).tolist(),
        "contexts": [[str(c)] for c in df["Context"].tolist()],
        "ground_truth": df["Ground Truth"].astype(str).tolist()
    }
    dataset = Dataset.from_dict(data)

    # 3. Setup the Judge and Embeddings
    # Adding 'model_kwargs' to push the model toward cleaner JSON output
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    embeddings = OpenAIEmbeddings(model="text-embedding-3-large")

    # 4. Run Evaluation
    print(f"Starting Ragas evaluation for {len(df)} rows...")

    # Use the metric objects directly
    metrics = [faithfulness, answer_relevancy, context_recall]

    result = evaluate(
        dataset,
        metrics=metrics,
        llm=llm,
        embeddings=embeddings
    )

    # 5. Save detailed per-question scores to Excel
    df_result = result.to_pandas()
    output_excel = "ragas_eval_results.xlsx"
    df_result.to_excel(output_excel, index=False)

    # 6. Calculate and Print the Mean Scores (Fixes AttributeError)
    print("\n" + "="*45)
    print("        RAG EVALUATION SUMMARY (MEAN)")
    print("="*45)

    # Printing the result object directly shows the summary in recent Ragas versions
    print(result)

    print("="*45)
    print(
        f"Individual scores for each question saved to:\n{os.getcwd()}\\{output_excel}")


if __name__ == "__main__":
    main()

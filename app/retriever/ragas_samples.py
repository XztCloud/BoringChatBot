import argparse
import json
import pandas as pd
from datasets import Dataset
from ragas.metrics import faithfulness, answer_relevancy, context_precision, context_recall
from ragas import evaluate


def load_dataset(path: str) -> Dataset:
    """支持 JSONL / CSV 文件加载"""
    if path.endswith(".jsonl"):
        data = []
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                data.append(json.loads(line))
        df = pd.DataFrame(data)
    elif path.endswith(".csv"):
        df = pd.read_csv(path)
        # 确保 contexts 是 list 格式
        if df["contexts"].dtype == object:
            df["contexts"] = df["contexts"].apply(lambda x: json.loads(x) if isinstance(x, str) else x)
    else:
        raise ValueError("仅支持 .jsonl 或 .csv 文件")

    return Dataset.from_pandas(df)


def main(args):
    dataset = load_dataset(args.file)

    metrics = [
        faithfulness,
        answer_relevancy,
        context_precision,
        context_recall,
    ]

    results = evaluate(dataset, metrics)
    print("评测结果：")
    for k, v in results.items():
        print(f"{k}: {v:.4f}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="RAG Evaluation with ragas")
    parser.add_argument("--file", type=str, required=True, help="输入的 JSONL 或 CSV 文件路径")
    args = parser.parse_args()
    main(args)

"""
CLI for the Data Analyst Agent.

Usage:
    python app.py "What were the top 5 products by revenue?"
    python app.py                 # interactive mode
"""

import sys
from pathlib import Path

from agent.agent import DataAnalystAgent

DB_PATH = Path(__file__).parent / "db" / "ecommerce.db"


def main():
    if not DB_PATH.exists():
        print("No database found. Run this first:\n  python db/create_db.py\n")
        sys.exit(1)

    agent = DataAnalystAgent(verbose=True)

    if len(sys.argv) > 1:
        question = " ".join(sys.argv[1:])
        print(f"\nQ: {question}\n")
        answer = agent.ask(question)
        print(f"\nA: {answer}\n")
        return

    print("Data Analyst Agent — ask a question about the e-commerce database.")
    print("Examples:")
    print('  - "What were the top 5 products by revenue?"')
    print('  - "Which city has the most customers who signed up in 2025?"')
    print('  - "What is the cancellation rate by product category?"')
    print("Type 'exit' to quit.\n")

    while True:
        try:
            question = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye!")
            break

        if not question:
            continue
        if question.lower() in ("exit", "quit"):
            print("Bye!")
            break

        answer = agent.ask(question)
        print(f"\nAgent: {answer}\n")


if __name__ == "__main__":
    main()

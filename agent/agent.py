"""
DataAnalystAgent: a natural-language -> SQL -> insight agent built on Claude's
tool-use API. This is the centerpiece of the project — it shows an agentic
loop (not a single API call): the model can inspect the schema, run a query,
see the result (or an error), and decide whether to refine the query or
answer the user, up to a bounded number of steps.
"""

import json
import os
from anthropic import Anthropic

from agent.tools import get_schema, run_query, SQLValidationError

MODEL = "claude-sonnet-4-5"  # swap for claude-opus-4-8 for tougher/ambiguous questions
MAX_AGENT_STEPS = 6

SYSTEM_PROMPT = """You are a data analyst agent. You answer business questions about an \
e-commerce database by writing and running read-only SQL queries, then explaining the \
result in plain language.

Rules:
- Always call get_database_schema before writing your first query in a conversation, \
unless you already have the schema in context.
- Only ever write SELECT queries. You cannot modify data.
- If a query fails or returns something unexpected, look at the error and try again \
with a corrected query rather than giving up.
- When you have enough information, give a clear, concise final answer in plain \
English. Include the concrete numbers. Don't just say "the query ran successfully."
- If the question is ambiguous (e.g. "recent" or "top" without a number), state the \
assumption you made (e.g. "last 90 days", "top 5") rather than asking a follow-up.
"""

TOOLS = [
    {
        "name": "get_database_schema",
        "description": "Return the table and column definitions for the e-commerce database.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "run_sql_query",
        "description": (
            "Execute a read-only SELECT query against the e-commerce SQLite database "
            "and return the resulting rows. Only SELECT statements are allowed."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "A single SQL SELECT statement."}
            },
            "required": ["query"],
        },
    },
]


class DataAnalystAgent:
    def __init__(self, api_key: str | None = None, verbose: bool = True):
        self.client = Anthropic(api_key=api_key or os.environ.get("ANTHROPIC_API_KEY"))
        self.verbose = verbose

    def _log(self, message: str):
        if self.verbose:
            print(message)

    def _execute_tool(self, name: str, tool_input: dict) -> str:
        if name == "get_database_schema":
            self._log("  [tool] get_database_schema()")
            return get_schema()

        if name == "run_sql_query":
            query = tool_input.get("query", "")
            self._log(f"  [tool] run_sql_query: {query}")
            try:
                result = run_query(query)
                return json.dumps(result)
            except SQLValidationError as e:
                return json.dumps({"error": str(e)})
            except Exception as e:  # sqlite errors, syntax errors, etc.
                return json.dumps({"error": f"Query failed: {e}"})

        return json.dumps({"error": f"Unknown tool: {name}"})

    def ask(self, question: str) -> str:
        """Run the agent loop for a single question and return the final text answer."""
        messages = [{"role": "user", "content": question}]

        for step in range(MAX_AGENT_STEPS):
            response = self.client.messages.create(
                model=MODEL,
                max_tokens=1024,
                system=SYSTEM_PROMPT,
                tools=TOOLS,
                messages=messages,
            )

            if response.stop_reason != "tool_use":
                # Model gave a final text answer.
                return "".join(
                    block.text for block in response.content if block.type == "text"
                )

            # Append assistant's turn (including tool_use blocks) to history.
            messages.append({"role": "assistant", "content": response.content})

            # Execute every tool call requested and collect results.
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    result_text = self._execute_tool(block.name, block.input)
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": result_text,
                        }
                    )

            messages.append({"role": "user", "content": tool_results})

        return "I wasn't able to reach a confident answer within the step limit. Try rephrasing the question."

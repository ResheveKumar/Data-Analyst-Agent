# Data Analyst Agent

A natural-language-to-SQL agent that answers business questions about an
e-commerce database by autonomously inspecting a schema, writing SQL,
executing it, self-correcting on errors, and explaining the result in plain
English — built on Claude's tool-use API.

```
You: What were the top 3 product categories by revenue in 2025?

Agent:
  [tool] get_database_schema()
  [tool] run_sql_query: SELECT p.category, SUM(oi.quantity * oi.unit_price) ...

Agent: In 2025, the top 3 categories by revenue were Electronics ($48,210),
Home & Kitchen ($31,940), and Sports ($22,180).
```

## Why this project (not just "a chatbot that calls an LLM")

This is deliberately built to demonstrate the difference between calling an
API and building an **agent**:

- **Multi-step reasoning loop.** The agent isn't a single prompt → response.
  It inspects the schema, writes a query, sees the actual result (or error),
  and decides whether to refine the query or answer — up to a bounded number
  of steps (see `MAX_AGENT_STEPS` in `agent/agent.py`).
- **Self-correction.** If a query fails (bad column name, syntax error), the
  error is fed back to the model as a tool result, and it retries with a
  fixed query instead of failing outright.
- **Guardrails, not just capability.** The agent can *only* run `SELECT`
  statements. Writes, DDL, and multi-statement queries are rejected before
  they ever touch the database (`agent/tools.py`), and the SQLite connection
  itself is opened in `PRAGMA query_only` mode as a second layer of defense.
  This is the detail that signals production judgment, not just a demo.
- **Bounded and observable.** Every tool call is logged, row counts are
  capped, and the loop has a hard step limit — so a confused agent fails
  loudly and cheaply instead of looping forever or hallucinating an answer.

## Setup

```bash
cd data-analyst-agent
pip install -r requirements.txt
cp .env.example .env        # then add your ANTHROPIC_API_KEY
export ANTHROPIC_API_KEY=your-key-here   # or use python-dotenv / direnv

python db/create_db.py      # generates db/ecommerce.db (sample e-commerce data)
python app.py                # interactive mode
python app.py "Which city has the most customers?"   # one-shot mode
```

Run the tests:

```bash
python -m pytest tests/ -v
```

## Project structure

```
data-analyst-agent/
├── app.py                # CLI entry point
├── agent/
│   ├── agent.py          # Agent loop: calls Claude, executes tools, loops until answer
│   └── tools.py           # Schema inspection + safe, read-only SQL execution
├── db/
│   └── create_db.py      # Generates a sample e-commerce SQLite database
├── tests/
│   └── test_tools.py     # Unit tests for the safety-critical validation layer
└── requirements.txt
```

The sample database has 4 tables (`customers`, `products`, `orders`,
`order_items`) with realistic randomized data — enough to ask genuinely
interesting questions (revenue by category, cancellation rates, repeat
customers, cohort signups, etc.) without needing a real company's data.

## Example questions to try

- "What were the top 5 products by revenue?"
- "Which city has the most customers who signed up in 2025?"
- "What's the cancellation rate by product category?"
- "Who are the 10 highest-spending customers, and how much have they spent?"
- "What's the average order value by month?"

## Extending it (good next steps if you want to go further)

- Swap the CLI for a small FastAPI + web UI so it's demoable in a browser.
- Add a `create_chart` tool (matplotlib) so the agent can return a plot, not
  just text — nice for a portfolio screenshot.
- Add conversation memory so follow-up questions ("now break that down by
  month") work without repeating context.
- Point it at Postgres instead of SQLite for a "production-realistic" spin.
- Add a second agent that reviews the first agent's SQL for correctness
  before execution — a lightweight taste of multi-agent orchestration.

## For your resume

A concrete, honest bullet point (adjust numbers/scope to match what you
actually build and test):

> Built an autonomous data-analyst agent using Claude's tool-use API that
> translates natural-language business questions into validated, read-only
> SQL, executes them against a relational database, self-corrects on query
> errors, and returns plain-English insights — with a guardrail layer that
> rejects any non-SELECT statement before execution.

## Talking points for interviews

Be ready to explain, not just demo:

1. **Why an agent loop instead of one prompt?** Because the model can't know
   if a query is right until it sees the result — the loop is what lets it
   verify and fix its own work.
2. **Why validate SQL in your own code instead of trusting the model?**
   Models can be wrong or manipulated (e.g. by injected instructions in
   data); a safety-critical constraint like "never write" has to be enforced
   outside the model, not just requested inside the prompt.
3. **What did you deliberately not automate?** The agent never gets
   write access — a real system would put a human in the loop for anything
   that changes data, and you should be able to say why.
4. **How would this scale to a real company's database?** Talk through
   schema size limits (you can't dump a 200-table schema into every prompt —
   you'd need retrieval over schema docs), query timeouts, and read-replica
   isolation so the agent can never touch production writes.

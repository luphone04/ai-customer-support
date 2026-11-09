# AI Customer Support

An email support assistant for **Harbor & Pine**, a home and outdoor store selling on Amazon. It answers routine questions using company guidance and hands cases that need a person to the support team.

Customers continue using email. The team uses a dashboard to view conversations, check processing activity, and update the knowledge base.

**Run it on your own computer with Docker.** See [Run locally](#run-locally) for setup. Gmail, Anthropic, and Supabase still require an internet connection.

## What it does

- Answers questions about paddle boards, shelving, returns, warranties, and shipping.
- Reads the email thread to understand the latest message and previous replies.
- Asks for missing details, such as an order number or damaged part number.
- Sends an acknowledgement and flags cases that need human attention.
- Records incoming messages, outgoing replies, and processing outcomes.

## Demo

### Customer emails

**Product advice** — A customer asks which paddle board suits a 90 kg rider.

![Paddle board recommendation in Gmail](docs/images/email-board-recommendation.png)

**Troubleshooting** — A customer reporting air loss receives valve-check instructions and a request for follow-up details.

![Valve-check instructions sent in response to a leaking board](docs/images/email-valve-check.png)

**Human handoff** — A refund request receives an acknowledgement that a colleague will reply.

![Handoff acknowledgement for a refund request in Gmail](docs/images/email-human-handoff.png)

### Support dashboard

**Tickets** — The team can read the conversation and see that the refund request has been escalated.

![Escalated refund ticket and its conversation in the dashboard](docs/images/escalated-ticket.png)

**Events** — Processing history shows each event’s status, attempts, and errors.

![Events dashboard showing two processed emails](docs/images/processing-events.png)

**Knowledge base** — The team can edit the guidance used by the assistant, including escalation rules.

![Knowledge-base editor displaying escalation rules](docs/images/knowledge-base.png)

## Architecture

```mermaid
flowchart TD
    Gmail[Gmail inbox] --> Worker[Polling worker]
    Worker --> Pipeline[Email processing]
    Pipeline --> Classifier[AI classifier]
    Classifier --> Decision[Decision checks]
    Classifier --> Agent[Support agent]
    Agent <-->|Read guidance| KB[(Knowledge base)]
    Agent --> Decision
    Decision --> Reply[Send reply or handoff acknowledgement]
    Reply --> Gmail
    Decision --> Human[Flag thread for a colleague]
    Pipeline --> Records[(Events, tickets and messages)]
    Dashboard[Support dashboard] --> API[FastAPI]
    API <--> Records
    API <--> KB
    API -->|Manual inbox check| Pipeline
```

The worker checks Gmail on a schedule. The classifier identifies the topic and whether a person is needed. Routine cases go to the support agent, which can read company guidance through tools. Python checks the resulting proposal before the application sends a response.

The knowledge base and support records live in Supabase Postgres. FastAPI serves the dashboard and its API; the polling worker runs as a separate process.

## AI concepts

- **Classification** — Assigns a topic and identifies cases that need human attention before drafting a detailed answer.
- **Tool calling** — The support agent uses `list_sections` and `get_section` to fetch guidance as needed.
- **Knowledge retrieval** — Retrieves complete topic sections from the database. The small, curated knowledge base uses section lookups rather than vector search.
- **Structured outputs** — Pydantic models define the fields returned by the classifier and agent, including the reply, issue details, and proposed decision.
- **Conversation context** — Each run receives the email thread, with quoted text reduced, to interpret follow-up messages.
- **Output checks** — A validator rejects empty replies and certain references to internal AI terminology. Decision checks also use the agent’s information and action flags.
- **Human handoff** — Python business rules determine product-specific next steps. Cases requiring a shipment, exchange, or replacement are handed to a colleague.

## Backend concepts

- **API and authentication** — FastAPI provides password-protected endpoints for tickets, events, knowledge edits, and manual inbox checks.
- **Gmail integration** — OAuth credentials allow the application to read threads, send replies, and apply labels.
- **Background processing** — A polling worker processes new emails at a configurable interval.
- **Persistence** — Four database tables store events, tickets, messages, and knowledge entries.
- **Processing tracking** — Unique Gmail message IDs identify previously claimed messages. Failed events can be retried, with a three-attempt cutoff in the processing flow.
- **Business rules** — Product policies are expressed in Python, such as choosing the next step for a leak or damaged shelf panels.
- **Docker deployment** — One image contains the backend and built dashboard. Docker Compose runs separate API and worker services.

## Workflows

### A routine question

“I weigh 90 kg. Which paddle board should I choose?”

```mermaid
flowchart LR
    A[Customer asks a question] --> B[Read relevant guidance]
    B --> C[Write and check the answer]
    C --> D[Send reply]
```

### A product problem

“The pump was missing from my order.”

```mermaid
flowchart LR
    A[Customer reports a missing pump] --> B{Order number provided?}
    B -->|No| C[Ask for details]
    B -->|Yes| D[Acknowledge and hand to a colleague]
```

The proposed action is to ship the missing part. A colleague arranges the shipment.

### A human handoff

“I want my money back.”

```mermaid
flowchart LR
    A[Customer requests a refund] --> B[Identify need for a person]
    B --> C[Send acknowledgement]
    C --> D[Flag thread for the team]
```

The assistant leaves further messages to the team until the `needs-human` label is removed in Gmail.

### A knowledge update

```mermaid
flowchart LR
    A[Edit guidance in the dashboard] --> B[Save to the knowledge base]
    B --> C[Available for future replies]
```

## Run locally

The dashboard, API, and email worker run on your computer. No rented server is needed. The worker runs while your computer is awake and Docker is running; model calls use your own Anthropic credits.

### 1. Get ready

- Install Docker Desktop and keep it open.
- Install [uv](https://docs.astral.sh/uv/getting-started/installation/) for the Python setup scripts. The project uses Python 3.13 or newer.
- Have an Anthropic API key, a Supabase project, and a Gmail mailbox for testing.
- Clone or download this repository and open a terminal in its root folder.

Install the Python dependencies and create your configuration file. If you already have a configured `.env`, keep it and skip the copy command.

```bash
uv sync
cp .env.example .env
```

### 2. Connect Gmail

In Google Cloud, enable the Gmail API, configure OAuth consent, and create an OAuth client of type **Desktop app**. For an external app in testing mode, add your test mailbox as a test user. Download the client credentials as `credentials.json` into the project root. Google's [Gmail setup guide](https://developers.google.com/workspace/gmail/api/quickstart/python) covers the account setup.

Run the project's authorisation script and sign in with the mailbox the bot will use:

```bash
uv run python scripts/get_refresh_token.py
```

Copy the three printed `GOOGLE_*` values into `.env`. This script requests permission to read, label, and send mail. Keep `.env` and `credentials.json` private; both are gitignored.

### 3. Set up the database and configuration

For a fresh Supabase database, run [the table migration](supabase/migrations/20261109044852_create_tables.sql) once in the Supabase SQL Editor. Skip this if the tables already exist.

Complete these values in `.env`:

| Setting | What to enter |
| --- | --- |
| `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REFRESH_TOKEN` | Values from the Gmail authorisation script |
| `DATABASE_URL` | Your Supabase Postgres connection string, including the database password |
| `ANTHROPIC_API_KEY` | Your Anthropic API key |
| `DASHBOARD_USERNAME`, `DASHBOARD_PASSWORD` | Your chosen dashboard login; the password must not be empty |
| `CLASSIFIER_MODEL`, `AGENT_MODEL` | Anthropic model identifiers available to your account, using the `anthropic:` prefix |
| `POLL_INTERVAL_SECONDS` | Seconds to wait between inbox checks; `30` is useful for a demo |

Use a direct database connection or the session pooler if your network needs IPv4. See [Supabase connection options](https://supabase.com/docs/guides/database/connecting-to-postgres). This is a Postgres URL, not the Supabase website URL or an API key.

Load the included company guidance:

```bash
uv run python -m scripts.seed_knowledge_base
```

The seed script loads `knowledge_base/*.md` into the database. Re-running it updates entries with matching section and title, so it can overwrite edits made in the dashboard.

### 4. Start the app

Use a dedicated test mailbox: **starting the worker sends real replies to eligible inbox emails, including older unprocessed messages.** Stop any development poller already running in another terminal.

```bash
docker compose up -d --build
docker compose ps
```

Docker builds the React dashboard and starts the `api` and `poller` services. You do not need Node.js installed separately for this route.

Open **[localhost:8080](http://localhost:8080)** and sign in with your dashboard credentials. The dashboard is available only on your computer.

To start only the dashboard and API, use `docker compose up -d --build api` on a stopped setup. The **Check inbox now** button still processes real emails when clicked.

### 5. Try it

Send a message from another email address to your test mailbox, such as “Which paddle board should I get? I weigh 90 kg.” Wait for a poll, then check the reply in Gmail and the ticket in the dashboard.

| Task | Command |
| --- | --- |
| Follow worker activity | `docker compose logs -f poller` |
| Pause automatic email processing | `docker compose stop poller` |
| Resume the worker | `docker compose up -d poller` |
| Stop both services | `docker compose stop` |
| Apply code or configuration changes | `docker compose up -d --build` |
| Check API health | `curl http://localhost:8080/health` |

If Docker cannot connect, open Docker Desktop and wait for it to finish starting. If Gmail reports `invalid_grant`, rerun the authorisation script, update `.env`, and recreate the services with `docker compose up -d`.

## Evaluation

The evaluation dataset contains **18 example emails**, covering product questions, missing parts, leaks, returns, delivery enquiries, German-language input, and attempts to override the assistant’s instructions.

Each case checks two outcomes:

- **Category:** Did the system choose the expected knowledge section?
- **Action:** Did it choose the expected reply or escalation?

With the environment configured and knowledge base loaded, run:

```bash
uv run python -m evals.run_evals
```

This runs the decision pipeline with real model calls and knowledge-base access. It does not send emails. The report shows category and action results; it does not measure every factual claim, tone, or the complete Gmail workflow.

*Evaluation results: to be added after a recorded run.*

## Scope and limitations

- The current setup serves one support mailbox and one shared dashboard login.
- Guidance covers the products and policies in the six knowledge-base sections.
- Emails with attachments are escalated; attachments are not analysed.
- The assistant cannot look up Amazon orders, issue refunds, or arrange shipments.
- Classification and extracted issue details depend on model judgment. Output checks do not independently verify every statement against its source.
- The dashboard displays conversations and proposed actions. Human replies and handoff management happen in Gmail.

## Future potential

- Evaluate reply accuracy, language, and tone alongside routing decisions.
- Add source tracking so each answer can be checked against the guidance it used.
- Let support staff review drafts and manage handoffs from the dashboard.
- Connect authorised order and fulfilment systems for order-specific assistance.
- Extend knowledge retrieval as the product catalogue grows.

## Built with

Python · FastAPI · Pydantic AI · Anthropic models · Supabase Postgres · Gmail API · React · TypeScript · Tailwind CSS · shadcn/ui · Docker

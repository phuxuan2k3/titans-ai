import os
from datetime import datetime

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.agents import create_agent

from greennode_agentbase import (
    GreenNodeAgentBaseApp,
    RequestContext,
    PingStatus,
)
from greennode_agent_bridge import AgentBaseMemoryEvents

load_dotenv()

app = GreenNodeAgentBaseApp()

# --- Memory Configuration ---
# Create a memory with: /agentbase-memory
# Set the memory ID here or via MEMORY_ID env var
MEMORY_ID = os.environ.get("MEMORY_ID", "")
if not MEMORY_ID:
    raise ValueError("MEMORY_ID environment variable is required for memory-enabled agents")

# CheckpointSaver: persists conversation state as events in AgentBase Memory
# This enables multi-turn conversations (e.g. clarification follow-ups on
# the same Jira ticket) that survive restarts
checkpointer = AgentBaseMemoryEvents(memory_id=MEMORY_ID)

# --- LLM Configuration ---
# Uses any OpenAI-compatible LLM provider (GreenNode AIP, OpenAI, Ollama, etc.)
# Set LLM_BASE_URL, LLM_API_KEY, and LLM_MODEL in your .env file.
# For GreenNode AIP: use /agentbase-llm to manage API keys and browse models.
# For other providers: set the appropriate base URL and API key.
# Production: use /agentbase-identity to store API key, inject via @requires_api_key
LLM_MODEL = os.environ.get("LLM_MODEL", "")
LLM_BASE_URL = os.environ.get("LLM_BASE_URL", "")
LLM_API_KEY = os.environ.get("LLM_API_KEY", "")
if not LLM_MODEL or not LLM_BASE_URL or not LLM_API_KEY:
    raise ValueError(
        "LLM_MODEL, LLM_BASE_URL, and LLM_API_KEY environment variables are required. "
        "Set them in your .env file or use /agentbase-llm to get a platform API key."
    )

llm = ChatOpenAI(
    model=LLM_MODEL,
    base_url=LLM_BASE_URL,
    api_key=LLM_API_KEY,
)


# NOTE: the scaffold's long-term memory tools (remember/recall via
# MemoryClient) were removed here. They had a pre-existing bug
# (insert_memory_records_directly(request=[fact]) — passes a list where the
# SDK expects a mapping, raising "argument after ** must be a mapping, not
# list" at call time) and aren't needed for this agent: each Jira ticket is
# a one-shot, independent fee-config generation task with no cross-ticket
# facts to remember. Short-term memory (checkpointer, for multi-turn
# clarification within a single ticket's session) is kept.

# --- Fee Config Generator system prompt ---
# This agent's job: turn a Jira ticket's `description` (written by a
# non-technical business/product manager, normally in Vietnamese) into a
# single new `rule` object for cashier-fake's declarative fee engine
# (src/config/fees.json). Rules are evaluated in order; all matching rules
# are summed (no short-circuit) — see "description" field of fees.json.
FEE_CONFIG_SYSTEM_PROMPT = """\
You are a **Fee Config Generator** for the "cashier-fake" project. Your job
is to turn a non-technical Jira ticket written by a Business/Product manager
into a single, precise, valid `rule` object to be appended to the `rules`
array in `src/config/fees.json`.

You are NOT writing app business logic — you are translating a plain-English
fee rule into the structured rule below. A tech reviewer will check your
output before it ships, so prefer being explicit and asking questions over
guessing silently.

## How the fee engine works

`fees.json` holds a `rules` array. Rules are evaluated **in order**; **every
rule whose `conditions` match the transaction is applied, and their fees are
summed** (no short-circuit / no "first match wins" — unlike a typical
if/elif chain). Keep this in mind: a new rule does not need to exclude every
other rule, only describe its own trigger conditions accurately.

## Language

Jira tickets are normally written in Vietnamese, often informally (typos, no
punctuation, mixed terms). Parse it directly — don't ask the PM to rewrite in
English. Write the plain-language recap back in Vietnamese (the PM doesn't
read tech English); add a short English line for the tech reviewer if useful.
`displayLabel` is a user-facing string and should be Vietnamese (matching the
style of existing `displayLabel`s, e.g. "Phí dịch vụ nạp thẻ (0.5%)").

Common VN fee-ticket vocabulary:
- "miễn phí" = waived/free -> typically means no new rule is needed (or
  `value: 0`), or an existing rule should be disabled (`enabled: false`) —
  clarify which.
- "tối thiểu" = minimum -> `percentage_with_min` (`min` field).
- "tối đa" = maximum -> `percentage_with_max` (`max` field).
- "phí cố định" / a flat amount in đ -> `flat` type.
- "phí theo %" / "phần trăm" -> `percentage` type.
- "kể từ ngày dd/mm/yyyy" / "áp dụng từ" -> fees.json has no effective-date
  field today; flag this under "Needs engineering" rather than inventing one.
- "giao dịch trên X đ" / "từ X đ trở lên" -> `amountRange: {"min": X, "max": null}`.
- Currency written as "1000VND", "1.000đ", "1k" all mean the same — use plain
  numeric VNĐ values in `value`/`min`/`max`, and `đ`-style in `displayLabel`.

## Output schema (must match exactly — one rule object)

```json
{
  "id": "<unique snake_case id, new — must not collide with existing rule ids>",
  "name": "<Human readable Vietnamese name>",
  "enabled": true,
  "conditions": {
    "orderTypes": ["<order_type_token>", "..."] or null,
    "paymentMethods": ["<payment_method_token>", "..."] or null,
    "amountRange": {"min": <number or null>, "max": <number or null>} or null
  },
  "fee": {
    "type": "percentage" | "flat" | "percentage_with_min" | "percentage_with_max",
    "value": <number>,
    "min": <number>,   // only for percentage_with_min
    "max": <number>,   // only for percentage_with_max
    "displayLabel": "<Vietnamese label shown to user, matching existing style>"
  }
}
```

Rules for the rule object:
- `id` must be a new, unique snake_case identifier that doesn't collide with
  existing rule ids you've been shown (e.g. `phone_topup_service_fee`,
  `airline_booking_flat_fee`, `international_card_surcharge`, etc.).
- At least one of `orderTypes`, `paymentMethods`, `amountRange` should be
  non-null — a rule with all three null applies to every transaction
  unconditionally, which is rarely the intent. Flag it if that really is
  the intent.
- `fee.type` must be exactly one of the four feeTypes; only include `min`
  (for `percentage_with_min`) or `max` (for `percentage_with_max`) when the
  type requires it.
- `value` for `percentage`/`percentage_with_min`/`percentage_with_max` is a
  percent number (e.g. `2.0` means 2%, matching the existing `value: 2.0`
  convention), not a fraction.

## Known token vocabulary (infer, don't invent silently)

These are the order type / payment method tokens seen in the existing
`fees.json` — match the ticket's wording to one of these families. If the
ticket describes a product/payment method that doesn't clearly match any of
these, **do not invent a new token silently** — propose one explicitly and
flag it under "Needs engineering" for tech to confirm the real token name.

**orderTypes seen so far**: `phone_topup_mobifone`, `phone_topup_viettel`,
`phone_topup_vinaphone`, `phone_topup_gmobile`, `phone_topup_reddi`,
`airline_vietnam_airlines`, `airline_vietjet`, `airline_bamboo`,
`airline_pacific`, `bill_electricity_evn`, `bill_electricity_vinh_long`,
`bill_water_sawaco`, `bill_internet_vnpt`, `bill_internet_fpt`,
`bill_tv_vtvcab`, `game_garena`, `game_vcoin`, `game_steam`,
`tax_personal_income`, `tax_vat`, `tax_corporate`, `insurance_bic`,
`insurance_pvi`, `insurance_bao_viet`.

**paymentMethods seen so far**: `international_card`, `domestic_card`,
`bank_msb`, `bank_acb`.

A new product not in this list (e.g. a new airline, a new bank) should
follow the same naming pattern (e.g. `airline_<name>`, `bank_<code>`) but
must be flagged as unconfirmed/new in your output.

## Process

1. Read the ticket: fee name, which order types / payment methods / amount
   ranges it applies to, the fee type and amount, and the display label.
2. Map every condition clause to a token using the vocabulary above; flag
   anything unsure.
3. Pick the correct `fee.type` and fill only the fields that type requires.
4. Write the JSON exactly matching the schema above — a single rule object.
5. Write a short plain-language recap for the human PM (Vietnamese, no
   jargon, no token names) restating the rule so they can sanity-check it.
6. List "Needs engineering" items: any proposed new tokens, assumptions
   made, and anything you couldn't model (e.g. effective dates).

## Final output format

Respond with these sections, in order:

### 1. Plain-language recap (Vietnamese)

### 2. Generated config
A fenced ```json block containing exactly one rule object (not the whole
file, not a `rules` array — just the new rule). This is required — always
include it.

### 3. Needs engineering / open questions

### 4. Suggested PR
A short note confirming this rule should be appended to the `rules` array
in `src/config/fees.json`.

## Things you must NOT do
- Don't guess at exact numeric thresholds not stated in the ticket.
- Don't modify or remove existing rules you haven't been shown — only ever
  output a new, standalone rule object.
- Don't fabricate order type / payment method tokens and present them as
  confirmed to exist.
- Don't skip the plain-language recap.
"""

# --- Create Agent with Checkpointer ---
# create_agent builds a compiled LangGraph StateGraph. No tools are needed —
# this agent's job is pure text-in/text-out fee-config generation.
# checkpointer: persists conversation state via AgentBase Memory (short-term),
# so a clarification follow-up on the same Jira ticket/session keeps context.
agent = create_agent(
    llm,
    tools=[],
    system_prompt=FEE_CONFIG_SYSTEM_PROMPT,
    checkpointer=checkpointer,
)


@app.entrypoint
def handler(payload: dict, context: RequestContext) -> dict:
    """Main agent entrypoint: generates fee config from a Jira description.

    Args:
        payload: JSON body with "message"
        context: Request metadata (session_id, user_id, request_headers)
    """
    # Short-term memory (checkpointer) requires both user_id and session_id
    # to correctly persist and isolate conversation state per user per session.
    if not context.user_id or not context.session_id:
        return {
            "status": "error",
            "error": "Missing required headers: X-GreenNode-AgentBase-User-Id and X-GreenNode-AgentBase-Session-Id are required when using memory.",
        }

    message = payload.get("message", "Hello")

    # Map AgentBase context to LangGraph config
    # thread_id -> session persistence, actor_id -> per-user memory
    config = {
        "configurable": {
            "thread_id": context.session_id,
            "actor_id": context.user_id,
        }
    }

    result = agent.invoke(
        {"messages": [{"role": "user", "content": message}]},
        config=config,
    )
    ai_message = result["messages"][-1]
    return {
        "status": "success",
        "response": ai_message.content,
        "timestamp": datetime.now().isoformat(),
    }


@app.ping
def health_check() -> PingStatus:
    """Custom health check for GET /health endpoint."""
    return PingStatus.HEALTHY


if __name__ == "__main__":
    app.run(port=8080, host="0.0.0.0")

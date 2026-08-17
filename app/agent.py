

import inspect
import json
import os

from dotenv import load_dotenv
from openai import OpenAI

from app.retrieval import document_lookup
from app.tools import get_carrier_status, get_service_status, search_incidents, search_logs

load_dotenv()

client = OpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1",
)

ROUTER_MODEL = "openai/gpt-oss-20b"
ANSWER_MODEL = "openai/gpt-oss-120b"

AVAILABLE_TOOLS = {
    "get_service_status": get_service_status,
    "get_carrier_status": get_carrier_status,
    "search_logs": search_logs,
    "search_incidents": search_incidents,
}

TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "get_service_status",
            "description": (
                "Get the current health status of ParcelPilot services. Call this with "
                "no arguments to see ALL services and their status (use this for "
                "questions like 'which services are healthy' or 'what's degraded right "
                "now'), or pass a specific service_name for just one service."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "service_name": {"type": "string", "description": "e.g. 'orders', leave empty for all services"}
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_carrier_status",
            "description": "Get carrier/tracking status for a specific order (e.g. 'ORD-1003'), or a summary across all orders if no order_id is given.",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {"type": "string", "description": "e.g. 'ORD-1003', leave empty for a summary"}
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_logs",
            "description": "Search recent application logs, optionally filtered by service, level (INFO/WARN/ERROR), or error code (e.g. 'ORD-500').",
            "parameters": {
                "type": "object",
                "properties": {
                    "service": {"type": "string"},
                    "level": {"type": "string"},
                    "code": {"type": "string"},
                    "limit": {"type": "integer"}
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_incidents",
            "description": "Search past incident history. Prefer 'area' (the service name, e.g. 'orders', 'tracking') over 'keyword' when the question mentions a service or error code -- incident summaries are written in plain English and don't contain error codes directly, so searching by service area is much more reliable than searching by the error code text.",
            "parameters": {
                "type": "object",
                "properties": {
                    "keyword": {"type": "string"},
                    "area": {"type": "string"},
                    "limit": {"type": "integer"}
                },
                "required": []
            }
        }
    },
]


def normalize_args(fn, args):
    """If the model sends slightly wrong argument names (e.g. 'service_name'
    instead of 'service'), map common aliases so the tool call still works."""
    valid_params = set(inspect.signature(fn).parameters.keys())
    aliases = {
        "service_name": "service",
        "order": "order_id",
    }
    normalized = {}
    for key, value in args.items():
        if key in valid_params:
            normalized[key] = value
        elif key in aliases and aliases[key] in valid_params:
            normalized[aliases[key]] = value
    return normalized


def classify_question(question: str) -> str:
    system_prompt = (
        "Classify the user's support question into EXACTLY ONE category. "
        "Reply with only the category word, nothing else.\n\n"
        "- document: questions about how ParcelPilot works conceptually - what an error "
        "code means, how a service is supposed to behave, what a runbook says to do, "
        "how services depend on each other, API behavior.\n"
        "- system: questions asking about the CURRENT state of the system right now - "
        "is a service healthy, what do recent logs show, what's a specific order's "
        "carrier status, have there been similar past incidents.\n"
        "- conversation: greetings, small talk, or anything unrelated to ParcelPilot.\n\n"
        "Examples:\n"
        "'what does ORD-500 mean' -> document\n"
        "'is orders healthy right now' -> system\n"
        "'why is the orders service degraded' -> system\n"
        "'what should I check for a login failure' -> document\n"
        "'show me recent errors for tracking' -> system\n"
        "'has this happened before' -> system\n"
        "'hey how are you' -> conversation"
    )
    response = client.chat.completions.create(
        model=ROUTER_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": question},
        ],
        temperature=0,
    )
    label = response.choices[0].message.content.strip().lower()
    if "document" in label:
        return "document"
    if "system" in label:
        return "system"
    return "conversation"


def handle_document(question: str) -> str:
    context = document_lookup(question)
    prompt = (
        "You are a ParcelPilot support assistant. Answer using ONLY the context below, "
        "in 1-2 short sentences (max 40 words). If the answer isn't in the context, say you don't know.\n\n"
        f"Context:\n{context}\n\nQuestion: {question}"
    )
    response = client.chat.completions.create(
        model=ANSWER_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
    )
    return response.choices[0].message.content


def handle_system(question: str) -> str:
    messages = [
        {"role": "system", "content": (
            "You are a ParcelPilot support assistant with tools to check live system "
            "state: service status, carrier status, logs, and past incidents. Use the "
            "tools needed to answer the question. For any question about which services "
            "are healthy, degraded, up, or down, always call get_service_status with no "
            "arguments to see the full picture. If evidence is incomplete, say what "
            "is still unknown and suggest the next useful check, rather than guessing."
        )},
        {"role": "user", "content": question},
    ]

    try:
        response = client.chat.completions.create(
            model=ROUTER_MODEL,
            messages=messages,
            tools=TOOL_DEFINITIONS,
            tool_choice="auto",
            temperature=0,
        )
        response_message = response.choices[0].message
    except Exception:
        return "I wasn't able to check that just now. Please try rephrasing your question."

    if not response_message.tool_calls:
        return response_message.content

    messages.append(response_message)
    for tool_call in response_message.tool_calls:
        try:
            tool_name = tool_call.function.name
            raw_args = tool_call.function.arguments or "{}"
            tool_args = json.loads(raw_args)
            if not isinstance(tool_args, dict):
                tool_args = {}
            tool_fn = AVAILABLE_TOOLS[tool_name]
            tool_result = tool_fn(**normalize_args(tool_fn, tool_args))
        except Exception as e:
            tool_result = f"Tool call failed: {e}"
        messages.append({
            "role": "tool",
            "tool_call_id": tool_call.id,
            "content": tool_result,
        })

    messages.append({
        "role": "system",
        "content": (
            "Answer in 1-2 short sentences (max 40 words) using the tool results above. "
            "If a tool result clearly says something doesn't exist (e.g. 'No service "
            "named X' or 'No carrier data found for order X'), say plainly that it "
            "doesn't exist -- do not say 'unknown' or suggest checking logs for "
            "something that was never found. Only say evidence is incomplete when the "
            "thing DOES exist but the cause isn't fully clear."
        )
    })
    try:
        final = client.chat.completions.create(
            model=ANSWER_MODEL,
            messages=messages,
            tools=TOOL_DEFINITIONS,
            tool_choice="none",
            temperature=0,
        )
        return final.choices[0].message.content
    except Exception:
        return "I found some data but couldn't summarize it just now. Please try again."


def handle_conversation(question: str) -> str:
    response = client.chat.completions.create(
        model=ANSWER_MODEL,
        messages=[
            {"role": "system", "content": "You are a friendly ParcelPilot support assistant. Keep replies short and natural."},
            {"role": "user", "content": question},
        ],
        temperature=0,
    )
    return response.choices[0].message.content


def get_agent_response(question: str) -> dict:
    route = classify_question(question)
    if route == "document":
        answer = handle_document(question)
    elif route == "system":
        answer = handle_system(question)
    else:
        answer = handle_conversation(question)
    return {"route": route, "answer": answer}
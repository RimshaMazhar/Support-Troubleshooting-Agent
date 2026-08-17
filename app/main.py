from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from app.agent import get_agent_response
from app.storage import add_message, get_history, conversation_exists, count_turns

app = FastAPI(
    title="ParcelPilot Support Troubleshooting Agent",
    description="A conversational RAG + tool-use agent over ParcelPilot's docs and live system data.",
    version="1.0.0",
)


class ChatRequest(BaseModel):
    conversation_id: str
    message: str


class ChatResponse(BaseModel):
    conversation_id: str
    response: str
    route: str
    turns_so_far: int


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    if not req.message.strip():
        raise HTTPException(status_code=422, detail="message cannot be empty")

    result = get_agent_response(req.message)

    add_message(req.conversation_id, "user", req.message, result["route"])
    add_message(req.conversation_id, "agent", result["answer"], result["route"])

    return ChatResponse(
        conversation_id=req.conversation_id,
        response=result["answer"],
        route=result["route"],
        turns_so_far=count_turns(req.conversation_id),
    )


@app.get("/conversations/{conversation_id}")
def get_conversation(conversation_id: str):
    if not conversation_exists(conversation_id):
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"conversation_id": conversation_id, "history": get_history(conversation_id)}
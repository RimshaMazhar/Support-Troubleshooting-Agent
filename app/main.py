from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from app.agent import get_agent_response

app = FastAPI(
    title="ParcelPilot Support Troubleshooting Agent",
    description="A conversational RAG + tool-use agent over ParcelPilot's docs and live system data.",
    version="1.0.0",
)

sessions: dict[str, list] = {}


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

    if req.conversation_id not in sessions:
        sessions[req.conversation_id] = []

    history = sessions[req.conversation_id]

    result = get_agent_response(req.message)

    history.append({"role": "user", "message": req.message, "route": result["route"]})
    history.append({"role": "agent", "message": result["answer"], "route": result["route"]})

    return ChatResponse(
        conversation_id=req.conversation_id,
        response=result["answer"],
        route=result["route"],
        turns_so_far=len(history) // 2,
    )


@app.get("/conversations/{conversation_id}")
def get_conversation(conversation_id: str):
    if conversation_id not in sessions:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"conversation_id": conversation_id, "history": sessions[conversation_id]}
from datetime import date

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.assistant_parser import parse_assistant_message
from app.services.assistant_tools import (
    estimate_calories_from_past_entries,
    create_pending_diet_entry_action,
    get_latest_pending_diet_entry_action,
    add_diet_entry_from_pending_payload,
    complete_pending_action,
    cancel_pending_action,
)


router = APIRouter(prefix="/assistant", tags=["Assistant"])


class AssistantChatRequest(BaseModel):
    message: str

def should_treat_add_as_estimate(parsed) -> bool:
    """
    If the user sends a bare food phrase like "chicken and rice",
    Ollama may classify it as add_diet_entry.

    For this assistant, bare food phrases should first become estimates,
    then require confirmation before writing.
    """
    return (
        parsed.intent == "add_diet_entry"
        and bool(parsed.foods)
        and parsed.confirmation is None
    )


@router.post("/chat")
def assistant_chat(
    req: AssistantChatRequest,
    db: Session = Depends(get_db),
):
    try:
        parsed = parse_assistant_message(req.message)

        if parsed.intent == "estimate_calories" or should_treat_add_as_estimate(parsed):
            estimate = estimate_calories_from_past_entries(
                db=db,
                foods=parsed.foods,
                original_message=req.message,
            )

            if not estimate:
                return {
                    "ok": True,
                    "parsed": parsed.model_dump(),
                    "result": None,
                    "needs_confirmation": False,
                    "message": (
                        "I understood this as a calorie estimate request, "
                        "but I couldn't find a similar past entry yet."
                    ),
                }

            pending = create_pending_diet_entry_action(
                db=db,
                food=req.message,
                calories=estimate["calories"],
                meal=parsed.meal,
                log_date=date.today(),
                source=estimate["source"],
                confidence=estimate["confidence"],
                matches=estimate.get("matches", []),
            )

            return {
                "ok": True,
                "parsed": parsed.model_dump(),
                "result": estimate,
                "pending_action": {
                    "id": pending["id"],
                    "action_type": pending["action_type"],
                    "status": pending["status"],
                    "expires_at": pending["expires_at"].isoformat() if pending.get("expires_at") else None,
                },
                "needs_confirmation": True,
                "message": (
                    f"I found similar past entries. Estimate: "
                    f"{estimate['calories']} calories. Add this?"
                ),
            }

        if parsed.intent == "confirm_action":
            pending = get_latest_pending_diet_entry_action(db)

            if not pending:
                return {
                    "ok": True,
                    "parsed": parsed.model_dump(),
                    "result": None,
                    "needs_confirmation": False,
                    "message": "I don't have any pending diet entry to confirm.",
                }

            if parsed.confirmation == "no":
                cancel_pending_action(db, pending["id"])

                return {
                    "ok": True,
                    "parsed": parsed.model_dump(),
                    "result": None,
                    "needs_confirmation": False,
                    "message": "Okay, I won't add it.",
                }

            if parsed.confirmation != "yes":
                return {
                    "ok": True,
                    "parsed": parsed.model_dump(),
                    "result": pending,
                    "needs_confirmation": True,
                    "message": "Do you want me to add the pending diet entry?",
                }

            payload = pending["payload"]

            added = add_diet_entry_from_pending_payload(
                db=db,
                payload=payload,
                meal_override=parsed.meal,
            )

            complete_pending_action(db, pending["id"])

            return {
                "ok": True,
                "parsed": parsed.model_dump(),
                "result": added,
                "needs_confirmation": False,
                "message": (
                    f"Added {added['food']} for {added['meal']}: "
                    f"{added['calories']} calories."
                ),
            }

        return {
            "ok": True,
            "parsed": parsed.model_dump(),
            "result": None,
            "needs_confirmation": False,
            "message": f"Parsed intent: {parsed.intent}. No tool is connected for this intent yet.",
        }

    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Assistant chat failed: {str(exc)}",
        )
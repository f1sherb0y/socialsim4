from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import auth, database, schemas

router = APIRouter()


@router.post("/feedback")
async def submit_feedback(
    feedback_data: schemas.FeedbackCreate,
    current_user: schemas.User = Depends(auth.get_current_active_user),
    db: Session = Depends(database.SessionLocal),
):
    new_feedback = database.Feedback(
        user_username=current_user.username,
        feedback_text=feedback_data.feedback,
        timestamp=datetime.utcnow().isoformat(),
    )
    db.add(new_feedback)
    db.commit()
    db.refresh(new_feedback)
    return {"status": "success", "message": "Feedback submitted successfully."}


@router.get("/admin/feedbacks", response_model=List[schemas.FeedbackAdminResponse])
async def get_all_feedbacks(
    current_user: schemas.User = Depends(auth.get_current_active_user),
    db: Session = Depends(database.SessionLocal),
):
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this resource",
        )

    feedbacks = (
        db.query(database.Feedback).order_by(database.Feedback.timestamp.desc()).all()
    )

    # This is a simplified response. In a real application, you would
    # join with the users table to get the user's email.
    return [
        schemas.FeedbackAdminResponse(
            id=fb.id,
            user_username=fb.user_username,
            user_email="",  # Placeholder
            feedback_text=fb.feedback_text,
            timestamp=fb.timestamp,
        )
        for fb in feedbacks
    ]

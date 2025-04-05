from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from models import SessionLocal, User
from passlib.context import CryptContext
import smtplib, os, secrets
from email.mime.text import MIMEText

router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")

reset_tokens = {}  # token: email

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class ResetRequest(BaseModel):
    email: EmailStr

@router.post("/request_password_reset")
def request_password_reset(data: ResetRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.email).first()
    if not user:
        return {"message": "If your email exists in our system, you'll receive a reset link shortly."}


    token = secrets.token_urlsafe(24)
    reset_tokens[token] = data.email

    reset_link = f"https://flipfinder.onrender.com/reset_password_form?token={token}"

    msg = MIMEText(f"Click this link to reset your Flip Finder password:\n{reset_link}")
    msg["Subject"] = "Flip Finder Password Reset"
    msg["From"] = EMAIL_ADDRESS
    msg["To"] = data.email

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        server.send_message(msg)

    return {"message": "Reset link sent"}

@router.get("/reset_password_form", response_class=HTMLResponse)
def reset_form(token: str):
    if token not in reset_tokens:
        return HTMLResponse(content="Invalid or expired token.", status_code=400)
    return f"""
    <html>
    <head><title>Reset Password</title></head>
    <body style="font-family: 'Inter', sans-serif; padding: 40px; background-color: #f7f7f7; text-align: center;">
      <h2 style="color: #333;">Reset Your Password</h2>
      <form method="POST" action="/submit_new_password" style="max-width: 400px; margin: auto;">
        <input type="hidden" name="token" value="{token}" />
        <input type="email" name="email" placeholder="Your Email" required style="padding: 12px; width: 100%; margin-bottom: 15px; border-radius: 8px; border: 1px solid #ccc;" /><br/>
        <input type="password" name="new_password" placeholder="New Password" required style="padding: 12px; width: 100%; margin-bottom: 15px; border-radius: 8px; border: 1px solid #ccc;" /><br/>
        <button type="submit" style="padding: 12px 20px; border-radius: 8px; background-color: #4CAF50; color: white; border: none; cursor: pointer;">Submit</button>
      </form>
    </body>
    </html>
    """

@router.post("/submit_new_password")
async def submit_password(request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    token = form.get("token")
    email = form.get("email")
    new_password = form.get("new_password")

    if token not in reset_tokens or reset_tokens[token] != email:
        raise HTTPException(status_code=400, detail="Invalid token or email")

    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.hashed_password = pwd_context.hash(new_password)
    db.commit()

    del reset_tokens[token]

    return HTMLResponse(content="✅ Password reset successful. You may now close this tab.", status_code=200)

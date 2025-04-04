import os
import sys
import datetime
from dotenv import load_dotenv
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
load_dotenv()

from models import SessionLocal, SearchResultSnapshot, User

EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")

db = SessionLocal()
now = datetime.datetime.utcnow()

print("📬 Sending daily Flip Finder summary emails...")

# Get all snapshots from today
start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
snapshots = db.query(SearchResultSnapshot).filter(SearchResultSnapshot.created_at >= start_of_day).all()

# Group by user
user_map = {}
for snap in snapshots:
    if snap.user_id not in user_map:
        user_map[snap.user_id] = []
    user_map[snap.user_id].append(snap)

for user_id, user_snaps in user_map.items():
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        continue

    # Sort by profit and pick top 5
    sorted_snaps = sorted(user_snaps, key=lambda x: x.profit, reverse=True)
    top_5 = sorted_snaps[:5]

    if not top_5:
        continue

    print(f"📤 Preparing email for {user.username} ({user.email}) with top {len(top_5)} items")

    # Plain text fallback
    text_lines = [f"🔍 {s.query_text}\n{s.title}\n{s.url}\nProfit: ${s.profit:.2f}" for s in top_5]
    text_body = "\n\n".join(text_lines)

    # HTML version
    html_body = "<h2>Your Flip Finder Deals of the Day</h2><ul>"
    for item in top_5:
        html_body += f"""
        <li style='
            display: flex;
            align-items: center;
            padding: 12px;
            border-radius: 12px;
            background-color: #ffffff;
            margin-bottom: 16px;
            box-shadow: 0 4px 8px rgba(0,0,0,0.05);
            font-family: Arial, sans-serif;
        '>
            <img src="{item.thumbnail or ''}" alt="item image" style='
                width: 110px;
                height: auto;
                object-fit: cover;
                border-radius: 10px;
                margin-right: 20px;
                box-shadow: 0 0 4px rgba(0,0,0,0.1);
            ' />
            <div style='flex: 1; text-align: left;'>
                <a href="{item.url}" target="_blank" style='
                    font-size: 16px;
                    font-weight: bold;
                    color: #333;
                    text-decoration: none;
                '>{item.title}</a>
                <div style='font-size: 14px; color: #555; margin-top: 6px;'>
                    🔍 <b>Query:</b> {item.query_text}<br>
                    💵 <b>Price:</b> ${item.price:.2f} &nbsp;&nbsp;
                    📦 <b>Shipping:</b> ${item.shipping:.2f}
                </div>
                <div style='
                    font-size: 24px;
                    font-weight: bold;
                    margin-top: 6px;
                    color: {'#2ecc71' if item.profit >= 0 else 'red'};
                '>
                    Profit: ${item.profit:.2f}
                </div>
            </div>
        </li>
        """
    html_body += "</ul><p style='font-size: 12px;'>To stop receiving these emails, disable Auto-search in your Flip Finder account.</p>"

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = "📦 Your Flip Finder Deals of the Day"
        msg["From"] = EMAIL_ADDRESS
        msg["To"] = user.email

        msg.attach(MIMEText(text_body, "plain"))
        msg.attach(MIMEText(html_body, "html"))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            server.sendmail(EMAIL_ADDRESS, user.email, msg.as_string())

        print(f"✅ Email sent to {user.email}")

    except Exception as e:
        print(f"❌ Failed to send email to {user.email}: {e}")

# Delete all of today's other results for this user (excluding the top 5)
top_ids = [snap.id for snap in top_5]
to_delete = db.query(SearchResultSnapshot).filter(
    SearchResultSnapshot.user_id == user.id,
    SearchResultSnapshot.created_at >= start_of_day,
    ~SearchResultSnapshot.id.in_(top_ids)
).all()

for snap in to_delete:
    db.delete(snap)

db.commit()
print(f"🧹 Deleted {len(to_delete)} extra snapshots for {user.email}")


db.close()
print("✅ All emails processed.")
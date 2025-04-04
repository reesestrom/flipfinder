import os
import sys
import datetime
from dotenv import load_dotenv
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
load_dotenv()

from models import SessionLocal, SearchResultSnapshot, User, SavedSearch, EmailedSnapshot  # ✅ Added EmailedSnapshot

EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
if not EMAIL_ADDRESS or not EMAIL_PASSWORD:
    print("❌ Missing EMAIL_ADDRESS or EMAIL_PASSWORD in environment!")
    sys.exit(1)

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

    # ✅ Skip users with no active auto-searches
    active_searches = db.query(SavedSearch).filter_by(user_id=user.id, auto_search_enabled=True).all()
    if not active_searches:
        print(f"\u23e9 Skipping {user.username} — no active auto-searches")
        continue

    # ✅ Exclude previously emailed snapshots
    emailed_ids = db.query(EmailedSnapshot.snapshot_id).filter_by(user_id=user.id).all()
    emailed_ids = [id for (id,) in emailed_ids]
    fresh_snaps = [snap for snap in user_snaps if snap.id not in emailed_ids]

    # Sort and limit
    sorted_snaps = sorted(fresh_snaps, key=lambda x: x.profit, reverse=True)
    top_5 = sorted_snaps[:5]

    if not top_5:
        continue

    print(f"\ud83d\udce4 Preparing email for {user.username} ({user.email}) with top {len(top_5)} items")

    # Plain text fallback
    text_lines = [f"\ud83d\udd0d {s.query_text}\n{s.title}\n{s.url}\nProfit: ${s.profit:.2f}" for s in top_5]
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
            <img src=\"{item.thumbnail or ''}\" alt=\"item image\" style='
                width: 110px;
                height: auto;
                object-fit: cover;
                border-radius: 10px;
                margin-right: 20px;
                box-shadow: 0 0 4px rgba(0,0,0,0.1);
            ' />
            <div style='flex: 1; text-align: left;'>
                <a href=\"{item.url}\" target=\"_blank\" style='
                    font-size: 16px;
                    font-weight: bold;
                    color: #333;
                    text-decoration: none;
                '>{item.title}</a>
                <div style='font-size: 14px; color: #555; margin-top: 6px;'>
                    \ud83d\udd0d <b>Query:</b> {item.query_text}<br>
                    \ud83d\udcb5 <b>Price:</b> ${item.price:.2f} &nbsp;&nbsp;
                    \ud83d\ude9e <b>Shipping:</b> ${item.shipping:.2f}
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
        msg["Subject"] = "\ud83d\ude9e Your Flip Finder Deals of the Day"
        msg["From"] = EMAIL_ADDRESS
        msg["To"] = user.email

        msg.attach(MIMEText(text_body, "plain"))
        msg.attach(MIMEText(html_body, "html"))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            server.sendmail(EMAIL_ADDRESS, user.email, msg.as_string())

        print(f"\u2705 Email sent to {user.email}")

        # ✅ Save emailed snapshot records first
        for snap in top_5:
            record = EmailedSnapshot(user_id=user.id, snapshot_id=snap.id)
            db.add(record)

        db.commit()  # Save EmailedSnapshots first to preserve snapshot_ids

        # ✅ THEN delete today's snapshots
        db.query(SearchResultSnapshot).filter(
            SearchResultSnapshot.user_id == user.id,
            SearchResultSnapshot.created_at >= start_of_day
        ).delete()

        db.commit()
        print(f"📨 Logged {len(top_5)} emailed snapshots for {user.username}")



    except Exception as e:
        print(f"\u274c Failed to send email to {user.email}: {e}")


db.close()
print("\u2705 All emails processed.")
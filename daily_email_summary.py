import os
import sys
import datetime
from dotenv import load_dotenv
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
load_dotenv()

from models import SessionLocal, SearchResultSnapshot, User, SavedSearch, EmailedSnapshot

EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")

if not EMAIL_ADDRESS or not EMAIL_PASSWORD:
    print("❌ Missing EMAIL_ADDRESS or EMAIL_PASSWORD in environment!")
    sys.exit(1)

print("✅ Email credentials loaded.")

db = SessionLocal()
now = datetime.datetime.utcnow()
print("📬 Sending daily Flip Finder summary emails...")

# Get all snapshots from today
start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
snapshots = db.query(SearchResultSnapshot).filter(SearchResultSnapshot.created_at >= start_of_day).all()

print(f"📊 Total snapshots found: {len(snapshots)}")

# Group by user
user_map = {}
for snap in snapshots:
    if snap.user_id not in user_map:
        user_map[snap.user_id] = []
    user_map[snap.user_id].append(snap)

print(f"👥 Users to process: {len(user_map)}")

for user_id, user_snaps in user_map.items():
    print(f"➡️ Processing user ID {user_id}")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        print(f"⚠️ User ID {user_id} not found.")
        continue

    # Skip users with no active auto-searches
    active_searches = db.query(SavedSearch).filter_by(user_id=user.id, auto_search_enabled=True).all()
    if not active_searches:
        print(f"⏩ Skipping {user.username} — no active auto-searches")
        continue

    emailed_ids = db.query(EmailedSnapshot.snapshot_id).filter_by(user_id=user.id).all()
    emailed_ids = [id for (id,) in emailed_ids]
    fresh_snaps = [snap for snap in user_snaps if snap.id not in emailed_ids]

    print(f"📦 {user.username} has {len(fresh_snaps)} fresh snapshots")

    sorted_snaps = sorted(fresh_snaps, key=lambda x: x.profit, reverse=True)
    top_5 = sorted_snaps[:5]

    if not top_5:
        print(f"ℹ️ No top items to send to {user.username}")
        continue

    print(f"✉️ Preparing email for {user.username} with {len(top_5)} items")

    text_lines = [f"🔍 {s.query_text}\n{s.title}\n{s.url}\nProfit: ${s.profit:.2f}" for s in top_5]
    text_body = "\n\n".join(text_lines)

    html_body = "<h2>Your Flip Finder Deals of the Day</h2><ul>"
    for item in top_5:
        html_body += f"""
        <li style='padding:10px; margin-bottom:10px; border:1px solid #ccc;'>
            <img src="{item.thumbnail or ''}" width="100" style="float:left; margin-right:20px;" />
            <div>
                <a href="{item.url}" target="_blank">{item.title}</a><br/>
                <strong>Query:</strong> {item.query_text}<br/>
                <strong>Price:</strong> ${item.price:.2f} | <strong>Shipping:</strong> ${item.shipping:.2f}<br/>
                <strong>Profit:</strong> ${item.profit:.2f}
            </div>
            <div style="clear:both;"></div>
        </li>
        """
    html_body += "</ul><p style='font-size:12px;'>To stop receiving these emails, disable Auto-search in your Flip Finder account.</p>"

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = "Your Flip Finder Deals of the Day"
        msg["From"] = EMAIL_ADDRESS
        msg["To"] = user.email

        msg.attach(MIMEText(text_body, "plain"))
        msg.attach(MIMEText(html_body, "html"))

        print(f"📡 Connecting to Gmail SMTP...")
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            server.sendmail(EMAIL_ADDRESS, user.email, msg.as_string())
        print(f"✅ Email sent to {user.email}")

        # Save emailed snapshot records
        print(f"📝 Logging sent snapshots...")
        for snap in top_5:
            record = EmailedSnapshot(user_id=user.id, snapshot_id=snap.id)
            db.add(record)
        db.commit()

        print(f"🗑 Deleting today's snapshots...")
        db.query(SearchResultSnapshot).filter(
            SearchResultSnapshot.user_id == user.id,
            SearchResultSnapshot.created_at >= start_of_day
        ).delete()
        db.commit()
        print(f"📨 Completed cleanup for {user.username}")

    except Exception as e:
        print(f"❌ Failed to send/process email for {user.username}: {e}")

db.close()
print("✅ All emails processed.")

import os
import sys
import datetime
from dotenv import load_dotenv
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from models import SessionLocal, SearchResultSnapshot, User, SavedSearch, EmailedListing


sys.path.append(os.path.dirname(os.path.abspath(__file__)))
load_dotenv()

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

    emailed_urls = db.query(EmailedListing.url).filter_by(user_id=user.id).all()
    emailed_urls = {url for (url,) in emailed_urls}

    url_to_best_snapshot = {}
    for snap in user_snaps:
        if snap.url in emailed_urls:
            continue
        # Optional: still keep snapshot_id filter if you're tracking those
        #if snap.id in emailed_ids:
        #    continue
        if snap.url not in url_to_best_snapshot or snap.profit > url_to_best_snapshot[snap.url].profit:
            url_to_best_snapshot[snap.url] = snap

    sorted_unique_snaps = sorted(url_to_best_snapshot.values(), key=lambda x: x.profit, reverse=True)
    top_5 = sorted_unique_snaps[:5]




    if not top_5:
        print(f"ℹ️ No top items to send to {user.username}")
        continue

    print(f"✉️ Preparing email for {user.username} with {len(top_5)} items")

    text_lines = [f"🔍 {s.query_text}\n{s.title}\n{s.url}\nProfit: ${s.profit:.2f}" for s in top_5]
    text_body = "\n\n".join(text_lines)

    html_body = """
    <h2 style='font-family: Arial, sans-serif;'>Your Flip Finder Deals of the Day</h2>
    <ul style='padding: 0; list-style: none;'>
    """
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
                    💰 <b>Price:</b> ${item.price:.2f} &nbsp;&nbsp;
                    🚚 <b>Shipping:</b> ${item.shipping:.2f}
                </div>
                <div style='
                    font-size: 24px;
                    font-weight: bold;
                    margin-top: 6px;
                    color: {"#2ecc71" if item.profit >= 0 else "red"};
                '>
                    Profit: ${item.profit:.2f}
                </div>
            </div>
        </li>
        """
    html_body += """
    </ul>
    <p style='font-size: 12px; font-family: Arial, sans-serif;'>
    To stop receiving these emails, disable Auto-search in your Flip Finder account.
    </p>
    """

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
            db.add(EmailedListing(user_id=user.id, url=snap.url))
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

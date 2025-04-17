import os
import sys
import datetime
from dotenv import load_dotenv
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from models import SessionLocal, SearchResultSnapshot, User, SavedSearch, EmailedListing
from urllib.parse import urlparse, urlunparse

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
load_dotenv()

EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")

def clean_url(url):
    parsed = urlparse(url)
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, '', '', ''))

if not EMAIL_ADDRESS or not EMAIL_PASSWORD:
    print("❌ Missing EMAIL_ADDRESS or EMAIL_PASSWORD in environment!")
    sys.exit(1)

print("✅ Email credentials loaded.")

db = SessionLocal()
now = datetime.datetime.utcnow()
print("📬 Sending daily Resale Radar summary emails...")

start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
snapshots = db.query(SearchResultSnapshot).filter(SearchResultSnapshot.created_at >= start_of_day).all()
print(f"📊 Total snapshots found: {len(snapshots)}")

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

    active_searches = db.query(SavedSearch).filter_by(user_id=user.id, auto_search_enabled=True).all()
    active_queries = {s.query_text for s in active_searches}
    user_snaps = [snap for snap in user_snaps if snap.query_text in active_queries]
    if not active_searches:
        print(f"⏩ Skipping {user.username} — no active auto-searches")
        continue

    emailed_urls_raw = db.query(EmailedListing.url).filter_by(user_id=user.id).all()
    emailed_urls = {clean_url(url) for (url,) in emailed_urls_raw}

    url_to_best_snapshot = {}
    for snap in user_snaps:
        url_key = clean_url(snap.url)
        if url_key in emailed_urls:
            continue
        if url_key not in url_to_best_snapshot or snap.profit > url_to_best_snapshot[url_key].profit:
            url_to_best_snapshot[url_key] = snap

    sorted_unique_snaps = sorted(url_to_best_snapshot.values(), key=lambda x: x.profit, reverse=True)
    ebay_snaps = [s for s in sorted_unique_snaps if getattr(s, "source", "ebay") == "ebay"][:5]
    ksl_snaps = [s for s in sorted_unique_snaps if getattr(s, "source", "ebay") == "ksl"][:5]

    if not ebay_snaps and not ksl_snaps:
        print(f"ℹ️ No top items to send to {user.username}")
        continue

    print(f"✉️ Preparing email for {user.username} with {len(ebay_snaps)} eBay and {len(ksl_snaps)} KSL items")

    # TEXT email body
    text_body = ""
    if ebay_snaps:
        text_body += "🛒 Top eBay Deals:\n"
        text_body += "\n\n".join(
            f"🔍 {s.query_text}\n{s.title}\n{s.url}\nProfit: ${s.profit:.2f}" for s in ebay_snaps
        )
    if ksl_snaps:
        text_body += "\n\n🏠 Top Local (KSL) Deals:\n"
        text_body += "\n\n".join(
            f"🔍 {s.query_text}\n{s.title}\n{s.url}\nProfit: ${s.profit:.2f}" for s in ksl_snaps
        )

    # HTML email body
    html_body = """
    <h2 style='font-family: Arial, sans-serif;'>Your Resale Radar Deals of the Day</h2>
    """

    def render_html_items(items, source_label, is_ksl=False):
        html = f"<h3 style='font-family: Arial, sans-serif;'>{source_label}</h3><ul style='padding: 0; list-style: none;'>"
        for item in items:
            html += f"""
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
                        💰 <b>Price:</b> ${item.price:.2f} &nbsp;&nbsp;"""
            if is_ksl:
                location = getattr(item, "location", "")
                html += f"<b>Location:</b> {location or 'N/A'}"
            else:
                html += f"<b>Shipping:</b> ${item.shipping:.2f}"

            html += f"""
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
        html += "</ul>"
        return html
    
    if ksl_snaps:
        html_body += render_html_items(ksl_snaps, "Top Local Listings (KSL)", is_ksl=True)
    if ebay_snaps:
        html_body += render_html_items(ebay_snaps, "Top eBay Listings", is_ksl=False)
    
    html_body += """
    <p style='font-size: 12px; font-family: Arial, sans-serif;'>
    To stop receiving these emails, disable Auto-search in your Resale Radar account.
    </p>
    """

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = "Your Resale Radar Deals of the Day"
        msg["From"] = EMAIL_ADDRESS
        msg["To"] = user.email

        msg.attach(MIMEText(text_body, "plain"))
        msg.attach(MIMEText(html_body, "html"))

        print(f"📡 Connecting to Gmail SMTP...")
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            server.sendmail(EMAIL_ADDRESS, user.email, msg.as_string())
        print(f"✅ Email sent to {user.email}")

        # Log emailed listings
        print(f"📝 Logging sent snapshots...")
        for snap in ebay_snaps + ksl_snaps:
            db.add(EmailedListing(user_id=user.id, url=clean_url(snap.url)))
        db.commit()

        # Cleanup: delete all snapshots from today
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

import pdfplumber
import json
import os
import requests
import threading
import pandas as pd
from flask import Flask, request
from datetime import datetime
from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive

# --- IMPORT CONFIG VARIABLES ---
from config import ACCESS_TOKEN, PHONE_NUMBER_ID, VERSION

app = Flask(__name__)

# --- CONFIGURATION ---
VERIFY_TOKEN = "my_secure_token_2026"
DOWNLOAD_FOLDER = "downloaded_cvs"
EXCEL_FILE = "Candidate_Database.xlsx"
CREDENTIALS_FILE = "mycreds.txt"

# Your Specific Recieved_CVs Folder ID
CV_FOLDER_ID = "1daEjU47W2q68EinutSos2YT-jCByVlsK" 

user_states = {} 

if not os.path.exists(DOWNLOAD_FOLDER):
    os.makedirs(DOWNLOAD_FOLDER)

# --- GOOGLE DRIVE SYNC LOGIC ---
def sync_to_google_drive(local_path, drive_title, folder_id=None):
    """Handles One-Time Login, Master Excel Updating, and Folder Routing"""
    print(f"\n☁️ [CLOUD] Syncing: {drive_title}...")
    try:
        gauth = GoogleAuth()
        # FIX: Load saved credentials to avoid repeated logins
        if os.path.exists(CREDENTIALS_FILE):
            gauth.LoadCredentialsFile(CREDENTIALS_FILE)
        
        if gauth.credentials is None:
            print("🔑 [CLOUD] First-time setup. Please authenticate via the link in terminal.")
            gauth.CommandLineAuth()
        elif gauth.access_token_expired:
            print("🔄 [CLOUD] Token expired. Refreshing...")
            gauth.Refresh()
        else:
            gauth.Authorize()
        
        # Save credentials for future use
        gauth.SaveCredentialsFile(CREDENTIALS_FILE)
        drive = GoogleDrive(gauth)

        # File Metadata
        file_metadata = {'title': drive_title}
        if folder_id:
            file_metadata['parents'] = [{'id': folder_id}]

        # FIX: Update Master Excel instead of creating duplicates
        if drive_title == EXCEL_FILE:
            query = f"title='{EXCEL_FILE}' and trashed=false"
            file_list = drive.ListFile({'q': query}).GetList()
            file_drive = file_list[0] if file_list else drive.CreateFile(file_metadata)
            print(f"🔄 [CLOUD] Syncing Master Database...")
        else:
            # Always create a new entry for individual CVs
            file_drive = drive.CreateFile(file_metadata)

        file_drive.SetContentFile(local_path)
        file_drive.Upload()
        print(f"✅ [CLOUD] SUCCESS: {drive_title} is updated on Drive!\n")

    except Exception as e:
        print(f"❌ [CLOUD] Drive Sync Error: {e}\n")

# --- HR CATEGORIZATION ---
def get_rank_label(score_str):
    try:
        score = int(''.join(filter(str.isdigit, score_str)))
        if 80 <= score <= 100: return "Best candidate for the job role"
        if 60 <= score <= 79: return "Average for the job"
        if 40 <= score <= 59: return "Low fit for the job"
        return "Rejected"
    except:
        return "Manual Review Required"

# --- EXCEL LOGGING ---
def log_to_excel(phone, position, score, analysis):
    rank_label = get_rank_label(score)
    new_entry = {
        "Timestamp": [datetime.now().strftime("%Y-%m-%d %H:%M")],
        "Phone Number": [phone],
        "Position Applied": [position],
        "AI Score": [score],
        "Category": [rank_label],
        "AI Analysis": [analysis]
    }
    df = pd.DataFrame(new_entry)
    
    try:
        if not os.path.exists(EXCEL_FILE):
            df.to_excel(EXCEL_FILE, index=False)
        else:
            with pd.ExcelWriter(EXCEL_FILE, mode='a', engine='openpyxl', if_sheet_exists='overlay') as writer:
                existing_df = pd.read_excel(EXCEL_FILE)
                df.to_excel(writer, index=False, header=False, startrow=len(existing_df) + 1)
        
        print(f"📊 [LOCAL] Excel Updated.")
        # Database stays in main Drive root
        sync_to_google_drive(EXCEL_FILE, EXCEL_FILE)

    except PermissionError:
        print(f"❌ [LOCAL] ERROR: Permission Denied. Close '{EXCEL_FILE}'!")

# --- WHATSAPP HELPERS ---
def send_reply(to_number, text_body):
    url = f"https://graph.facebook.com/{VERSION}/{PHONE_NUMBER_ID}/messages"
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}", "Content-Type": "application/json"}
    payload = {"messaging_product": "whatsapp", "to": to_number, "type": "text", "text": {"body": text_body}}
    try:
        return requests.post(url, headers=headers, json=payload, timeout=10)
    except:
        return None

def download_media(media_id):
    try:
        url_info = f"https://graph.facebook.com/{VERSION}/{media_id}"
        headers = {"Authorization": f"Bearer {ACCESS_TOKEN}"}
        res = requests.get(url_info, headers=headers, timeout=10)
        if res.status_code == 200:
            media_url = res.json().get("url")
            file_res = requests.get(media_url, headers=headers, timeout=20)
            if file_res.status_code == 200:
                file_path = os.path.join(DOWNLOAD_FOLDER, f"cv_{media_id}.pdf")
                with open(file_path, "wb") as f:
                    f.write(file_res.content)
                return file_path
        return None
    except:
        return None

# --- BACKGROUND AI WORKER ---
def process_cv_background_task(file_path, from_number, position):
    print(f"🧵 [THREAD] Analyzing CV for {position}...")
    cv_text = ""
    try:
        with pdfplumber.open(file_path) as pdf:
            # Read first 2 pages for efficiency
            for page in pdf.pages[:2]: 
                cv_text += (page.extract_text() or "") + "\n"
    except Exception as e:
        print(f"❌ [PDF] Error: {e}")
        return

    prompt = (
        f"Role: {position}. Analyze this resume snippet: {cv_text[:1200]}. "
        f"Reply ONLY in this format: SCORE: [0-100] ANALYSIS: [1 sentence summary]."
    )

    try:
        # AI Stability: 180s timeout
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={"model": "llama3.2", "prompt": prompt, "stream": False}, 
            timeout=180 
        )
        
        if response.status_code == 200:
            ai_raw = response.json().get("response", "")
            try:
                score = ai_raw.split("SCORE:")[1].split("ANALYSIS:")[0].strip()
                analysis = ai_raw.split("ANALYSIS:")[1].strip()
            except:
                score, analysis = "0", "AI format parsing error"

            # 1. Update Excel & Master Database on Drive
            log_to_excel(from_number, position, score, analysis)
            
            # 2. Upload PDF CV to the dedicated folder
            timestamp = datetime.now().strftime("%Y%m%d-%H%M")
            drive_cv_name = f"CV-{position}-{from_number}-{timestamp}.pdf"
            sync_to_google_drive(file_path, drive_cv_name, folder_id=CV_FOLDER_ID)
            
            send_reply(from_number, "✅ Application and CV have been logged in the cloud database!")
        else:
            send_reply(from_number, "⚠️ AI Service busy. Data logged locally.")

    except Exception as e:
        print(f"❌ [AI] Error: {e}")

# --- WEBHOOK ROUTES ---
@app.route('/webhook', methods=['GET'])
def verify():
    if request.args.get("hub.verify_token") == VERIFY_TOKEN:
        return request.args.get("hub.challenge"), 200
    return "Forbidden", 403

@app.route('/webhook', methods=['POST'])
def receive_message():
    data = request.get_json(force=True)
    try:
        msg = data["entry"][0]["changes"][0]["value"]["messages"][0]
        num = msg["from"]
        
        if msg["type"] == "text":
            body = msg["text"]["body"].strip()
            if body == "1":
                send_reply(num, "Available Roles:\n- Python Developer\n- AI Engineer\n- Data Scientist")
            elif body in ["Python Developer", "AI Engineer", "Data Scientist"]:
                user_states[num] = body
                send_reply(num, f"Upload your PDF CV for the *{body}* role.")
            else:
                send_reply(num, "Welcome! Reply '1' to see roles.")

        elif msg["type"] == "document" and num in user_states:
            pos = user_states[num]
            send_reply(num, "📥 CV received! Processing for the cloud...")
            path = download_media(msg["document"]["id"])
            if path:
                threading.Thread(target=process_cv_background_task, args=(path, num, pos)).start()
                del user_states[num]
            else:
                send_reply(num, "❌ Error: Download failed.")

    except: pass
    return "EVENT_RECEIVED", 200

if __name__ == "__main__":
    app.run(port=5000, debug=True)

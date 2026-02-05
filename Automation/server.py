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

# Dictionary to track which position a user is applying for
user_states = {} 

if not os.path.exists(DOWNLOAD_FOLDER):
    os.makedirs(DOWNLOAD_FOLDER)

# --- GOOGLE DRIVE SYNC LOGIC ---
def sync_to_google_drive():
    """Uploads or Updates the local Excel file to Izaan's Google Drive"""
    try:
        print("☁️ Attempting to sync with Google Drive...")
        gauth = GoogleAuth()
        # This looks for 'client_secrets.json' in your folder
        gauth.LocalWebserverAuth() 
        drive = GoogleDrive(gauth)

        # Check if file already exists on Drive to update it
        query = f"title='{EXCEL_FILE}' and trashed=false"
        file_list = drive.ListFile({'q': query}).GetList()
        
        if file_list:
            file_drive = file_list[0] # Update existing
        else:
            file_drive = drive.CreateFile({'title': EXCEL_FILE}) # Create new

        file_drive.SetContentFile(EXCEL_FILE)
        file_drive.Upload()
        print(f"✅ Cloud Sync Success: {EXCEL_FILE} is now updated on Drive!")
    except Exception as e:
        print(f"❌ Drive Sync Error: {e}")

# --- HR CATEGORIZATION LOGIC ---
def get_rank_label(score_str):
    """Maps numerical AI score to your specific HR categories"""
    try:
        # Extract only digits (e.g., "85/100" -> 85)
        score = int(''.join(filter(str.isdigit, score_str)))
        if 80 <= score <= 100: return "Best candidate for the job role"
        if 60 <= score <= 79: return "Average for the job"
        if 40 <= score <= 59: return "Low fit for the job"
        return "Rejected"
    except:
        return "Manual Review Required"

# --- EXCEL LOGGING ---
def log_to_excel(phone, position, score, analysis):
    """Saves candidate data locally and then triggers cloud sync"""
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
    
    if not os.path.exists(EXCEL_FILE):
        df.to_excel(EXCEL_FILE, index=False)
    else:
        with pd.ExcelWriter(EXCEL_FILE, mode='a', engine='openpyxl', if_sheet_exists='overlay') as writer:
            try:
                existing_df = pd.read_excel(EXCEL_FILE)
                df.to_excel(writer, index=False, header=False, startrow=len(existing_df) + 1)
            except:
                df.to_excel(writer, index=False)
    
    print(f"📊 Local Excel Updated for {phone}.")
    # Now push the updated file to Google Drive
    sync_to_google_drive()

# --- HELPER: SEND MESSAGE ---
def send_reply(to_number, text_body):
    url = f"https://graph.facebook.com/{VERSION}/{PHONE_NUMBER_ID}/messages"
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}", "Content-Type": "application/json"}
    payload = {
        "messaging_product": "whatsapp",
        "to": to_number,
        "type": "text",
        "text": {"body": text_body}
    }
    try:
        return requests.post(url, headers=headers, json=payload)
    except Exception as e:
        print(f"❌ Send Error: {e}")
        return None

# --- HELPER: DOWNLOAD CV ---
def download_media(media_id):
    try:
        url_info = f"https://graph.facebook.com/{VERSION}/{media_id}"
        headers = {"Authorization": f"Bearer {ACCESS_TOKEN}"}
        info_res = requests.get(url_info, headers=headers)
        if info_res.status_code == 200:
            media_url = info_res.json().get("url")
            file_res = requests.get(media_url, headers=headers)
            if file_res.status_code == 200:
                filename = f"cv_{media_id}.pdf"
                file_path = os.path.join(DOWNLOAD_FOLDER, filename)
                with open(file_path, "wb") as f:
                    f.write(file_res.content)
                return file_path
        return None
    except Exception as e:
        print(f"❌ Download Error: {e}")
        return None

# --- BACKGROUND AI WORKER ---
def process_cv_background_task(file_path, from_number, position):
    print(f"🧵 Thread Started: Analyzing CV for {position}...")
    
    cv_text = ""
    try:
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                extracted = page.extract_text()
                if extracted: cv_text += extracted + "\n"
    except:
        send_reply(from_number, "⚠️ Error reading your PDF content.")
        return

    prompt = f"""
    Analyze this CV for the role of: {position}.
    CV TEXT: {cv_text[:2500]} 

    TASK:
    1. Give a numerical score out of 100.
    2. Provide a 2-sentence summary of the candidate's fit.

    Reply strictly in this format:
    SCORE: [Number]
    ANALYSIS: [Summary]
    """

    try:
        response = requests.post("http://localhost:11434/api/generate",
            json={"model": "llama3.2", "prompt": prompt, "stream": False})
        
        if response.status_code == 200:
            ai_raw = response.json().get("response", "")
            try:
                score = ai_raw.split("SCORE:")[1].split("ANALYSIS:")[0].strip()
                analysis = ai_raw.split("ANALYSIS:")[1].strip()
            except:
                score, analysis = "0", "Parsing Error"

            # Log to local Excel AND Sync to Drive
            log_to_excel(from_number, position, score, analysis)
            
            # Send Professional Confirmation
            send_reply(from_number, "✅ Your application has been logged! Our HR team will review your profile shortly.")
        else:
            send_reply(from_number, "⚠️ AI Service error. Please try again later.")
    except Exception as e:
        print(f"❌ AI Error: {e}")

# --- WEBHOOK ROUTES ---
@app.route('/webhook', methods=['GET'])
def verify():
    mode, token, challenge = request.args.get("hub.mode"), request.args.get("hub.verify_token"), request.args.get("hub.challenge")
    if mode == "subscribe" and token == VERIFY_TOKEN: return challenge, 200
    return "Forbidden", 403

@app.route('/webhook', methods=['POST'])
def receive_message():
    data = request.get_json(force=True)
    try:
        if data.get("object") == "whatsapp_business_account":
            value = data["entry"][0]["changes"][0]["value"]
            if "messages" in value:
                message = value["messages"][0]
                from_number = message["from"]

                # --- POSITION SELECTION ---
                if message["type"] == "text":
                    body = message["text"]["body"].strip()
                    if body == "1":
                        send_reply(from_number, "Which position are you applying for?\n\n- Python Developer\n- AI Engineer\n- Data Scientist")
                    elif body in ["Python Developer", "AI Engineer", "Data Scientist"]:
                        user_states[from_number] = body
                        send_reply(from_number, f"Great! Upload your CV (PDF) for the *{body}* role.")
                    else:
                        send_reply(from_number, "Welcome! Reply '1' to see available roles.")

                # --- DOCUMENT UPLOAD ---
                elif message["type"] == "document":
                    if from_number not in user_states:
                        send_reply(from_number, "⚠️ Please select a position first by replying '1'.")
                    else:
                        mime_type = message["document"].get("mime_type", "")
                        if "pdf" in mime_type:
                            position = user_states[from_number]
                            send_reply(from_number, f"📥 CV received for *{position}*. Logging your application now...")
                            
                            file_path = download_media(message["document"]["id"])
                            if file_path:
                                threading.Thread(target=process_cv_background_task, args=(file_path, from_number, position)).start()
                                del user_states[from_number] # Clear state
                        else:
                            send_reply(from_number, "⚠️ Please send only PDF files.")

    except Exception as e: print(f"❌ Webhook Error: {e}")
    return "EVENT_RECEIVED", 200

if __name__ == "__main__":
    app.run(port=5000, debug=True)

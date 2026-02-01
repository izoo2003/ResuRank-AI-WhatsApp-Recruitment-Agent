import pdfplumber
import json
import os
import requests
import threading  # <--- NEW IMPORT
from flask import Flask, request

# --- IMPORT CONFIG VARIABLES ---
from config import ACCESS_TOKEN, PHONE_NUMBER_ID, VERSION

app = Flask(__name__)

# --- CONFIGURATION ---
VERIFY_TOKEN = "my_secure_token_2026"
DOWNLOAD_FOLDER = "downloaded_cvs"

if not os.path.exists(DOWNLOAD_FOLDER):
    os.makedirs(DOWNLOAD_FOLDER)

# --- HELPER 1: SEND MESSAGE ---
def send_reply(to_number, text_body):
    url = f"https://graph.facebook.com/{VERSION}/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": to_number,
        "type": "text",
        "text": {"body": text_body}
    }
    try:
        response = requests.post(url, headers=headers, json=payload)
        return response
    except Exception as e:
        print(f"❌ Error sending reply: {e}")
        return None

# --- HELPER 2: DOWNLOAD CV ---
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
                print(f"✅ CV Saved as: {file_path}")
                return file_path
        return None
    except Exception as e:
        print(f"❌ Exception in download_media: {e}")
        return None

# --- HELPER 3: EXTRACT TEXT ---
def extract_text_from_pdf(filepath):
    text = ""
    try:
        with pdfplumber.open(filepath) as pdf:
            for page in pdf.pages:
                extracted = page.extract_text()
                if extracted:
                    text += extracted + "\n"
        return text.strip()
    except Exception as e:
        print(f"❌ PDF Read Error: {e}")
        return None

# --- HELPER 4: BACKGROUND AI WORKER (THE FIX) ---
def process_cv_background_task(file_path, from_number):
    """This runs in the background so it doesn't block Meta"""
    print(f"🧵 Thread Started for {from_number}...")
    
    # 1. Extract Text
    cv_text = extract_text_from_pdf(file_path)
    
    if not cv_text or len(cv_text) < 50:
        send_reply(from_number, "⚠️ This PDF seems empty or is an image scan. I need text!")
        return

    # 2. Analyze with Ollama (Llama 3.2)
    print("🤖 AI is thinking... (Sending to Ollama)")
    prompt = f"""
    You are an expert HR Recruiter. Analyze this CV.
    
    CV TEXT:
    {cv_text[:2500]} 

    TASK:
    1. Give a score out of 100.
    2. List 3 key strengths.
    3. List 1 main weakness.
    4. Give a one-sentence verdict.

    Reply strictly in this format:
    Score: [Number]/100
    Strengths: [List]
    Weakness: [Text]
    Verdict: [Sentence]
    """

    try:
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "llama3.2", 
                "prompt": prompt,
                "stream": False
            }
        )
        
        if response.status_code == 200:
            ai_result = response.json().get("response", "Error: No response.")
            # 3. Send the Final Result to User
            send_reply(from_number, f"✅ *Analysis Complete!*\n\n{ai_result}")
            print("✅ Result sent to user!")
        else:
            send_reply(from_number, "⚠️ My AI brain is having trouble connecting.")
            
    except Exception as e:
        print(f"❌ Background Error: {e}")

# --- WEBHOOK ROUTES ---
@app.route('/webhook', methods=['GET'])
def verify():
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")
    if mode == "subscribe" and token == VERIFY_TOKEN:
        return challenge, 200
    return "Forbidden", 403

@app.route('/webhook', methods=['POST'])
def receive_message():
    data = request.get_json(force=True)
    
    # Check if previously processed to avoid loop (Basic Check)
    # Note: In production, you'd check message IDs database
    
    try:
        if data.get("object") == "whatsapp_business_account":
            entry = data["entry"][0]
            if "changes" in entry and "value" in entry["changes"][0]:
                value = entry["changes"][0]["value"]
                
                if "messages" in value:
                    message = value["messages"][0]
                    from_number = message["from"]
                    msg_type = message["type"]

                    # --- TEXT HANDLING ---
                    if msg_type == "text":
                        text_body = message["text"]["body"].strip()
                        if text_body == "1":
                            send_reply(from_number, "🛠 Our Services:\n- AI Automation\n- Web Development")
                        elif text_body == "2":
                            send_reply(from_number, "📞 Contact Us:\nEmail: contact@agency.com")
                        elif text_body == "3":
                            send_reply(from_number, "📄 Please upload your CV (PDF format).")
                        else:
                            send_reply(from_number, "Reply with:\n1. Services\n2. Contact\n3. Rank CV")

                    # --- DOCUMENT HANDLING (THREADED) ---
                    elif msg_type == "document":
                        mime_type = message["document"].get("mime_type", "")
                        if "pdf" in mime_type:
                            media_id = message["document"]["id"]
                            
                            # 1. Immediate Reply to satisfy User
                            send_reply(from_number, "📥 CV Received! Analyzing... (This takes ~20s)")
                            
                            # 2. Download Sync (Fast enough)
                            file_path = download_media(media_id)
                            
                            if file_path:
                                # 3. START BACKGROUND THREAD for slow AI
                                thread = threading.Thread(target=process_cv_background_task, args=(file_path, from_number))
                                thread.start()
                            else:
                                send_reply(from_number, "❌ Download failed.")

    except Exception as e:
        print(f"❌ Error: {e}")

    # --- CRITICAL: RETURN 200 INSTANTLY ---
    return "EVENT_RECEIVED", 200

if __name__ == "__main__":
    app.run(port=5000, debug=True)
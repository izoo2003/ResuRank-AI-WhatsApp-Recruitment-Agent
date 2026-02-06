# 🤖 AI-Powered WhatsApp HR Recruiter

**An automated recruitment pipeline that screens CVs using local Llama 3.2, logs data to Excel, and synchronizes everything to Google Drive.**

---

## 🌟 Overview

This project transforms a WhatsApp Business account into an automated HR assistant. It guides candidates through job selection, accepts PDF CVs, analyzes them using a locally hosted **Llama 3.2** model via **Ollama**, and maintains a master database in the cloud.

---

## 🛠️ Tech Stack

* **Backend:** Python / Flask
* **AI Engine:** Llama 3.2 (via Ollama)
* **Messaging:** WhatsApp Cloud API (Meta)
* **Database:** Local Excel (`openpyxl` / `pandas`)
* **Cloud Storage:** Google Drive API (`PyDrive2`)
* **Tunneling:** Ngrok (for webhook exposure)

---

## 🚀 Key Features

* **Automated Workflow:** Greets users and manages application states.
* **Local AI Analysis:** Privacy-focused CV screening—no data leaves your machine for AI processing.
* **One-Time Authentication:** Uses credential caching to avoid repeated Google Drive logins.
* **Master Database Sync:** Intelligently updates a single master Excel file on the cloud instead of creating duplicates.
* **Organized Storage:** Routes all received CVs into a specific timestamped folder on Google Drive.
* **Threaded Processing:** Handles AI analysis in the background to ensure WhatsApp webhooks never time out.

---

## 📁 Project Structure

```text
├── server.py              # Main application logic
├── config.py              # Sensitive API keys & tokens
├── client_secrets.json    # Google Drive API credentials
├── mycreds.txt            # Cached Google Drive session (Auto-generated)
├── Candidate_Database.xlsx# Local master database
├── downloaded_cvs/        # Local storage for PDF resumes
└── README.md              # Project documentation

```

---

## ⚙️ Setup & Installation

### 1. Prerequisites

* **Python 3.10+**
* **Ollama:** Installed and running with the `llama3.2` model.
* **Ngrok:** Authenticated and ready to tunnel port 5000.
* **Meta Developer Account:** WhatsApp Business Cloud API configured.

### 2. Environment Setup

Install the required Python libraries:

```bash
pip install flask requests pandas openpyxl pdfplumber pydrive2

```

### 3. Google Drive API Configuration

1. Create a project in the **Google Cloud Console**.
2. Enable the **Google Drive API**.
3. Create an **OAuth 2.0 Client ID** (Desktop Application).
4. Download the JSON and rename it to `client_secrets.json` in the root folder.
5. Add your email to the **Test Users** in the OAuth Consent Screen.

### 4. Running the Project

1. **Start Ollama:**
```bash
ollama serve

```


2. **Start Ngrok:**
```bash
ngrok http 5000

```


3. **Update Webhook:** Copy the Ngrok URL to your Meta Developer Dashboard.
4. **Launch Server:**
```bash
python server.py

```



---

## 📝 Usage

1. Send **"1"** to the WhatsApp bot to view available roles.
2. Select a role (e.g., *AI Engineer*).
3. Upload a **PDF CV**.
4. The bot will:
* Download the file.
* Use **Llama 3.2** to generate a fit score and summary.
* Update the local `Candidate_Database.xlsx`.
* Sync the Excel file to Google Drive.
* Upload the PDF to the designated `Received_CVs` folder.



---

## ⚠️ Important Notes

* **File Locking:** Ensure `Candidate_Database.xlsx` is closed on your computer so Python can write to it.
* **Timeouts:** The AI analysis is set to a 180s timeout to accommodate varying hardware speeds.

---

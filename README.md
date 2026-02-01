# 🤖 ResuRank AI: WhatsApp Recruiter

**ResuRank AI** is an autonomous recruitment assistant integrated directly into WhatsApp. Powered by a local **Llama 3.2** model and **Flask**, it instantly parses PDF resumes and evaluates candidates with human-level insight. It features threaded processing for real-time feedback and local inference for total data privacy with zero API costs.

---

## ✨ Features

* **Instant Screening:** Automatically responds to users with a service menu.
* **AI Resume Analysis:** Uses Llama 3.2 via Ollama to rank PDFs.
* **Asynchronous Processing:** Multi-threading ensures Meta webhooks never timeout.
* **Data Privacy:** Resume parsing and AI inference happen 100% locally.
* **Automated Workflow:** From WhatsApp document upload to a structured HR report in seconds.

---

## 🛠 Tech Stack

* **Language:** Python 3.10+
* **Framework:** Flask
* **AI Engine:** Ollama (Llama 3.2)
* **Tunneling:** ngrok
* **API:** Meta WhatsApp Business API
* **Libraries:** `pdfplumber`, `requests`, `threading`

---

| Main Menu | AI CV Analysis |
| :---: | :---: |
| <img src="/Automation/screenshots/img1.png" width="250"> | <img src="Automation/screenshots/img2.png" width="250"> |

## 🚀 Getting Started

### 1. Prerequisites

* **Python:** Install via [python.org](https://python.org).
* **Ollama:** Download from [ollama.com](https://ollama.com) and run `ollama pull llama3.2`.
* **ngrok:** Install and authenticate your account.
* **Meta Developer Account:** Create a WhatsApp Business App at [developers.facebook.com](https://developers.facebook.com).

### 2. Installation

Clone the repository and install dependencies:

```bash
git clone https://github.com/yourusername/ResuRank-AI.git
cd ResuRank-AI
pip install flask requests pdfplumber

```

### 3. Setup Private Configuration (`config.py`)

For security, the sensitive credentials are kept in a separate file. **You must create this file yourself.**

Create a file named `config.py` in the root directory and paste the following:

```python
# config.py

# Found in Meta Dashboard > WhatsApp > API Setup
ACCESS_TOKEN = "YOUR_PERMANENT_ACCESS_TOKEN"
PHONE_NUMBER_ID = "YOUR_PHONE_NUMBER_ID"
VERSION = "v21.0" # Or the latest version

# Optional: Add any other private keys here

```

---

## 🚦 How to Run

Follow this exact order to ensure the webhook handshake succeeds:

1. **Start Ollama:**
Ensure the Ollama desktop app is running or run `ollama serve`.
2. **Start the Flask Server:**
```bash
python server.py

```


3. **Start the ngrok Tunnel:**
```bash
ngrok http 5000

```


4. **Configure Meta Webhook:**
* Copy the `https` URL from ngrok.
* Paste it into **Meta Dashboard > WhatsApp > Configuration** as the Callback URL.
* **Crucial:** Add `/webhook` to the end of the URL (e.g., `https://random-id.ngrok-free.app/webhook`).
* Verify with your chosen token.



---

## 📱 Usage

1. Send **"Hi"** to your WhatsApp Business number to see the menu.
2. Reply with **"3"** to initiate the CV Ranking process.
3. **Upload a PDF** resume.
4. Wait ~20 seconds for the AI to generate a score, list strengths/weaknesses, and provide a verdict.

---


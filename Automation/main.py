# main.py
import pandas as pd
import requests
import time
from config import ACCESS_TOKEN, PHONE_NUMBER_ID, VERSION
from logic import format_pakistan_number

def send_whatsapp_message(to_number):
    """Sends a message using the Meta Cloud API"""
    url = f"https://graph.facebook.com/{VERSION}/{PHONE_NUMBER_ID}/messages"
    
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    
    # NOTE: You MUST use a template for the first message.
    # 'hello_world' is the default template provided by Meta.
    payload = {
        "messaging_product": "whatsapp",
        "to": to_number,
        "type": "template",
        "template": {
            "name": "hello_world", 
            "language": { "code": "en_US" }
        }
    }
    
    response = requests.post(url, headers=headers, json=payload)
    return response

def start_automation(excel_file):
    df = pd.read_excel(excel_file)
    # Ensure your Excel column is named 'phone'
    phone_column = 'phone'

    for index, row in df.iterrows():
        formatted_num = format_pakistan_number(row[phone_column])
        
        if formatted_num:
            print(f"Sending to {formatted_num}...")
            res = send_whatsapp_message(formatted_num)
            
            if res.status_code == 200:
                print(f"Successfully sent to {formatted_num}")
            else:
                print(f"Failed for {formatted_num}: {res.text}")
            
            # Small delay to avoid hitting rate limits
            time.sleep(1) 
        else:
            print(f"Skipping invalid number at row {index+1}")

if __name__ == "__main__":
    start_automation('leads.xlsx')
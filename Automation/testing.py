# testing.py
import pandas as pd
from logic import format_pakistan_number

def test_data_cleaning(file_path):
    print(f"--- Testing Data Cleaning on: {file_path} ---")
    try:
        # Load your Excel sheet
        df = pd.read_excel(file_path)
        
        # We assume your column is named 'phone'. Change if different.
        column_name = 'phone' 
        
        for index, row in df.iterrows():
            raw = row[column_name]
            formatted = format_pakistan_number(raw)
            
            status = "✅ VALID" if formatted else "❌ INVALID"
            print(f"Row {index+1}: {raw} -> {formatted} [{status}]")
            
    except Exception as e:
        print(f"Error reading file: {e}")

if __name__ == "__main__":
    # Create a dummy Excel named 'sample.xlsx' to test this script
    test_data_cleaning('leads.xlsx')
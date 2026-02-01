# logic.py
import re

def format_pakistan_number(number):
    """
    Cleans and converts numbers to +923xxxxxxxxx format.
    Handles: 03001234567, 923001234567, 3001234567, etc.
    """
    # Remove all non-numeric characters (spaces, dashes, brackets)
    clean_num = re.sub(r'\D', '', str(number))
    
    # 1. Handle 03xxxxxxxxx (11 digits)
    if clean_num.startswith('03') and len(clean_num) == 11:
        return "+92" + clean_num[1:]
    
    # 2. Handle 923xxxxxxxxx (12 digits)
    elif clean_num.startswith('923') and len(clean_num) == 12:
        return "+" + clean_num
    
    # 3. Handle 3xxxxxxxxx (10 digits - no leading zero)
    elif clean_num.startswith('3') and len(clean_num) == 10:
        return "+92" + clean_num
        
    # Return None if it doesn't match Pakistani mobile format
    return None
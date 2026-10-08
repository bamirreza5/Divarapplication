"""Normalize Persian/Arabic numbers without an extra dependency."""
DIGIT_TABLE = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")

def normalize_digits(value):
    return str(value).translate(DIGIT_TABLE).strip()

def normalize_phone(value):
    return normalize_digits(value).replace(" ", "").replace("-", "")

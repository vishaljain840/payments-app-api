import pandas as pd
import numpy as np
from datetime import datetime

# Load the CSV file
df = pd.read_csv('payment_information.csv')

# Normalize the data (ensure correct types and handle missing values)
# Convert date columns to datetime format
df['payee_added_date_utc'] = pd.to_datetime(df['payee_added_date_utc'], errors='coerce')
df['payee_due_date'] = pd.to_datetime(df['payee_due_date'], errors='coerce')

# Convert numeric columns to float, handle NaNs with 0 or a default value
df['discount_percent'] = pd.to_numeric(df['discount_percent'], errors='coerce').fillna(0.0)
df['tax_percent'] = pd.to_numeric(df['tax_percent'], errors='coerce').fillna(0.0)
df['due_amount'] = pd.to_numeric(df['due_amount'], errors='coerce')

# Ensure that mandatory fields have no missing values
mandatory_fields = ['payee_address_line_1', 'payee_city', 'payee_country', 'payee_postal_code', 'payee_phone_number', 'payee_email', 'currency']
df = df.dropna(subset=mandatory_fields)  # Remove rows with missing mandatory fields

# Optional: Clean up other columns if needed
df['payee_phone_number'] = df['payee_phone_number'].apply(lambda x: str(x).strip() if isinstance(x, str) else x)  # Ensure phone numbers are strings
df['payee_email'] = df['payee_email'].apply(lambda x: str(x).strip() if isinstance(x, str) else x)  # Ensure emails are strings

# Save the normalized data back to a new CSV
df.to_csv('normalized_payment_information.csv', index=False)

print("CSV normalization complete!")

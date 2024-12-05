import pandas as pd
from pymongo import MongoClient

# Connect to MongoDB (replace the connection string with your local or cloud MongoDB connection)
client = MongoClient("mongodb://localhost:27017")  # For local MongoDB
db = client["payment_database"]  # Database name
collection = db["payments"]  # Collection name

# Load the normalized CSV file
normalized_data = pd.read_csv("normalized_payment_information.csv")

# Convert the dataframe to a list of dictionaries
data_dict = normalized_data.to_dict(orient="records")

# Insert data into MongoDB collection
collection.insert_many(data_dict)

print(f"{len(data_dict)} records inserted into MongoDB!")

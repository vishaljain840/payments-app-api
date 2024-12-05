from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.responses import FileResponse
from pymongo import MongoClient
from bson import ObjectId
import os
import shutil
from typing import List, Optional
from datetime import datetime

app = FastAPI()

# MongoDB connection (ensure MongoDB is running)
client = MongoClient("mongodb://localhost:27017")
db = client["payments_database"]  # Replace with your actual database name
collection = db["payments"]

# Path to save files locally (optional, just for temporary use)
UPLOAD_FOLDER = "./uploads"

# Ensure upload folder exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# Helper function to check file type (PDF, PNG, JPG)
def allowed_file(filename: str) -> bool:
    return filename.endswith((".pdf", ".png", ".jpg"))


@app.get("/")
async def read_root():
    return {"message": "Welcome to the Payments API"}


# Create payment route
@app.post("/create_payment")
async def create_payment(payment_data: dict):
    # Logic for creating payments (store them in MongoDB)
    payment_id = collection.insert_one(payment_data).inserted_id
    return {"payment_id": str(payment_id)}


# Upload evidence file when payment status is updated to completed
@app.post("/upload_evidence/{payment_id}")
async def upload_evidence(payment_id: str, file: UploadFile = File(...)):
    # Check if the payment exists in the database
    payment = collection.find_one({"_id": ObjectId(payment_id)})
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")

    # Ensure the payment status is 'completed'
    if payment["payee_payment_status"] != "completed":
        raise HTTPException(
            status_code=400,
            detail="Payment must be marked as completed to upload evidence",
        )

    # Ensure the file type is valid
    if not allowed_file(file.filename):
        raise HTTPException(
            status_code=400, detail="Invalid file type. Only PDF, PNG, JPG are allowed"
        )

    # Save the file to disk or MongoDB
    file_path = os.path.join(UPLOAD_FOLDER, file.filename)
    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    # Optionally: You can also store the file in MongoDB GridFS instead of the local filesystem.
    # In this example, we're saving the file locally.

    # Save the file path (or file metadata) in MongoDB associated with the payment
    collection.update_one(
        {"_id": ObjectId(payment_id)}, {"$set": {"evidence_file_path": file_path}}
    )

    return {"message": "Evidence file uploaded successfully", "file_path": file_path}


# Provide the download link for the uploaded evidence file
@app.get("/download_evidence/{payment_id}")
async def download_evidence(payment_id: str):
    # Retrieve the payment and file path from MongoDB
    payment = collection.find_one({"_id": ObjectId(payment_id)})
    if not payment or "evidence_file_path" not in payment:
        raise HTTPException(status_code=404, detail="Evidence file not found")

    # Return the file to be downloaded
    file_path = payment["evidence_file_path"]
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Evidence file not found on server")

    return FileResponse(file_path)

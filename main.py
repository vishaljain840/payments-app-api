from fastapi import FastAPI, HTTPException, Query, File, UploadFile
from pydantic import BaseModel
from typing import List, Optional
from pymongo import MongoClient
from datetime import datetime
from bson import ObjectId
import os
import shutil
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200"],  # Allow requests from localhost:4200
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods (GET, POST, etc.)
    allow_headers=["*"],  # Allow all headers
)
# username = quote_plus("vishaljain840")  # replace with actual username
# password = "Archana@709"  # replace with actual password
# encoded_password = quote(password)
# MongoDB connection (ensure MongoDB is running)
client = MongoClient(
    "mongodb+srv://vishaljain840:1234@cluster0.bz0qc.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
)

# Correctly formatted connection string using f-string
# connection_string = f"mongodb+srv://vishaljain840:<{password}>@cluster0.bz0qc.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

# # MongoDB connection
# client = MongoClient(connection_string)
db = client["payments_database"]  # Replace with your actual database name
# collection = db["payments"]
payments_collection = db.payments

# Path to save files locally (optional, just for temporary use)
# UPLOAD_FOLDER = "./uploads"

# # Ensure upload folder exists
# os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# # Helper function to check file type (PDF, PNG, JPG)
# def allowed_file(filename: str) -> bool:
#     return filename.endswith((".pdf", ".png", ".jpg"))


class Payment(BaseModel):
    payee_first_name: str
    payee_last_name: str
    payee_payment_status: str
    payee_added_date_utc: str
    payee_due_date: str
    payee_address_line_1: str
    payee_address_line_2: Optional[str] = None
    payee_city: str
    payee_country: str
    payee_province_or_state: str
    payee_postal_code: str
    payee_phone_number: str
    payee_email: str
    currency: str
    discount_percent: float
    tax_percent: float
    due_amount: float
    evidence_file_path: Optional[str] = None


# Utility functions
def calculate_total_due(payment: dict) -> float:
    discount = payment["discount_percent"] / 100 * payment["due_amount"]
    tax = payment["tax_percent"] / 100 * payment["due_amount"]
    return payment["due_amount"] - discount + tax


def update_payment_status(payment: dict) -> str:
    due_date = datetime.strptime(payment["payee_due_date"], "%Y-%m-%dT%H:%M:%S")
    today = datetime.utcnow()
    if due_date.date() == today.date():
        return "due_now"
    elif due_date < today:
        return "overdue"
    return payment["payee_payment_status"]


# Endpoints
@app.get("/get_payments")
async def get_payments(skip: int = 0, limit: int = 10, search: Optional[str] = None):
    filters = {}
    if search:
        filters = {
            "$or": [
                {"payee_first_name": {"$regex": search, "$options": "i"}},
                {"payee_last_name": {"$regex": search, "$options": "i"}},
                {"payee_email": {"$regex": search, "$options": "i"}},
            ]
        }

    payments = payments_collection.find(filters).skip(skip).limit(limit)
    result = []

    for payment in payments:
        payment["total_due"] = calculate_total_due(payment)
        payment["payee_payment_status"] = update_payment_status(payment)
        result.append(payment)

    return result


@app.post("/update_payment/{payment_id}")
async def update_payment(payment_id: str, payment: Payment):
    result = payments_collection.update_one(
        {"_id": ObjectId(payment_id)}, {"$set": payment.dict(exclude_unset=True)}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Payment not found")
    return {"message": "Payment updated successfully"}


@app.delete("/delete_payment/{payment_id}")
async def delete_payment(payment_id: str):
    result = payments_collection.delete_one({"_id": ObjectId(payment_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Payment not found")
    return {"message": "Payment deleted successfully"}


@app.post("/create_payment")
async def create_payment(payment: Payment):
    payment_dict = payment.dict()
    payment_dict["payee_added_date_utc"] = datetime.utcnow().isoformat()
    payment_dict["payee_payment_status"] = update_payment_status(payment_dict)
    result = payments_collection.insert_one(payment_dict)
    return {"payment_id": str(result.inserted_id)}


@app.post("/upload_evidence/{payment_id}")
async def upload_evidence(payment_id: str, file: UploadFile = File(...)):
    file_extension = file.filename.split(".")[-1].lower()
    if file_extension not in ["pdf", "png", "jpg"]:
        raise HTTPException(status_code=400, detail="Invalid file type")

    file_path = f"./uploads/{payment_id}_{file.filename}"
    os.makedirs(os.path.dirname(file_path), exist_ok=True)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    result = payments_collection.update_one(
        {"_id": ObjectId(payment_id)},
        {
            "$set": {
                "evidence_file_path": file_path,
                "payee_payment_status": "completed",
            }
        },
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Payment not found")

    return {"message": "Evidence uploaded successfully"}


@app.get("/download_evidence/{payment_id}")
async def download_evidence(payment_id: str):
    payment = payments_collection.find_one({"_id": ObjectId(payment_id)})
    if not payment or not payment.get("evidence_file_path"):
        raise HTTPException(status_code=404, detail="Evidence not found")

    file_path = payment["evidence_file_path"]
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(file_path)


# Run the application
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)

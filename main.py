from fastapi import FastAPI, HTTPException, Query
import firebase_admin
from firebase_admin import credentials, firestore
import random
import string
from datetime import datetime, timedelta
import json
import os
from fastapi.middleware.cors import CORSMiddleware


# 로컬용 Firebase 초기화
# cred = credentials.Certificate("./firekeys/admin.json")
# firebase_admin.initialize_app(cred)
# db = firestore.client()

# 배포용 Firebase 초기화
firebase_credentials = json.loads(os.getenv("FIREBASE_CREDENTIALS"))
cred = credentials.Certificate(firebase_credentials)
firebase_admin.initialize_app(cred)
db = firestore.client()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 모든 도메인 허용 (보안이 필요하면 특정 도메인만 허용)
    allow_credentials=True,
    allow_methods=["*"],  # 모든 HTTP 메서드 허용
    allow_headers=["*"],  # 모든 헤더 허용
)

# 시리얼키 난수 생성
def generate_serial_key(prefix: str) -> str:
    """랜덤 16자리 시리얼키 생성 (Mxxxx-xxxx-xxxx-xxxx / Yxxxx-xxxx-xxxx-xxxx)"""
    key = ''.join(random.choices(string.ascii_uppercase + string.digits, k=15))
    return f"{prefix}{key[:3]}-{key[3:7]}-{key[7:11]}-{key[11:]}"

# 데이터베이스 생성
def create_serial_key(prefix: str, days: int, customer: str):
    """시리얼키 생성 및 Firebase 저장"""
    serial_key = generate_serial_key(prefix)
    created_at = datetime.utcnow()
    expires_at = created_at + timedelta(days=days)

    data = {
        "serial_key": serial_key,
        "customer": customer,
        "create": created_at.strftime("%Y-%m-%d"),
        "end": expires_at.strftime("%Y-%m-%d")
    }

    # Firebase에 저장
    db.collection("serial_keys").document(serial_key).set(data)

    return data

# 30일 시리얼키
@app.post("/create/m")
def create_m_key(customer: str):
    """M으로 시작하는 16자리 키 생성 (30일 유효)"""
    return create_serial_key("M", 30, customer)

# 365일 시리얼키
@app.post("/create/y")
def create_y_key(customer: str):
    """Y로 시작하는 16자리 키 생성 (365일 유효)"""
    return create_serial_key("Y", 365, customer)

# 모든 데이터 조회
@app.get("/inquiry")
def list_keys():
    """저장된 시리얼키 목록 조회"""
    keys_ref = db.collection("serial_keys").stream()
    keys = [{**key.to_dict()} for key in keys_ref]
    return keys

# 모든 시리얼키 조회
@app.get("/inquiry/serial_key")
def list_serial_keys():
    """시리얼키만 조회"""
    keys_ref = db.collection("serial_keys").stream()
    keys = [{"serial_key": key.id} for key in keys_ref]
    return keys

# 모든 생성일 조회
@app.get("/inquiry/create")
def list_create():
    """생성일만 조회"""
    keys_ref = db.collection("serial_keys").stream()
    keys = [{"create": key.to_dict().get("create")} for key in keys_ref]
    return keys

# 모든 종료일 조회
@app.get("/inquiry/end")
def list_end():
    """만료일만 조회"""
    keys_ref = db.collection("serial_keys").stream()
    keys = [{"end": key.to_dict().get("end")} for key in keys_ref]
    return keys

# 모든 업체 조회
@app.get("/inquiry/customer")
def list_customers():
    """고객명만 조회"""
    keys_ref = db.collection("serial_keys").stream()
    keys = [{"customer": key.to_dict().get("customer")} for key in keys_ref]
    return keys

# 키워드 조회
@app.get("/search")
def search_keys(keyword: str):
    """키워드가 포함된 시리얼키 데이터 검색"""
    keys_ref = db.collection("serial_keys").stream()
    results = []
    for key in keys_ref:
        key_data = key.to_dict()
        if any(keyword.lower() in str(value).lower() for value in key_data.values()):
            results.append({"serial_key": key.id, **key_data})
    return results

# 시리얼키로 업체 조회
@app.get("/validate_serial")
def validate_serial(serial: str = Query(..., description="검증할 시리얼키 입력")):
    """정확한 형식의 시리얼키 검색"""
    keys_ref = db.collection("serial_keys").where("serial_key", "==", serial).stream()
    results = [{"serial_key": key.id, **key.to_dict()} for key in keys_ref]
    if not results:
        raise HTTPException(status_code=404, detail="시리얼키가 유효하지 않습니다.")
    return results

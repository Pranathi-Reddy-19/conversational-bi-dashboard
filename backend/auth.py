from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
import yaml
from yaml.loader import SafeLoader
import bcrypt
import jwt
from datetime import datetime, timedelta

router = APIRouter()

CONFIG_FILE = "config.yaml"
SECRET_KEY = "your-very-secret-key-change-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7 # 7 days

def get_config():
    with open(CONFIG_FILE, 'r', encoding='utf-8') as file:
        return yaml.load(file, Loader=SafeLoader)

def save_config(config):
    with open(CONFIG_FILE, 'w', encoding='utf-8') as file:
        yaml.dump(config, file, default_flow_style=False)

class LoginData(BaseModel):
    username: str
    password: str

class RegisterData(BaseModel):
    username: str
    password: str

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

@router.post("/login")
def login(data: LoginData):
    config = get_config()
    users = config.get('credentials', {}).get('usernames', {})
    
    if data.username not in users:
        raise HTTPException(status_code=401, detail="Invalid username or password")
        
    stored_hash = users[data.username]['password']
    
    # Check password
    if not bcrypt.checkpw(data.password.encode('utf-8'), stored_hash.encode('utf-8')):
         raise HTTPException(status_code=401, detail="Invalid username or password")
         
    # Generate token
    token = create_access_token(data={"sub": data.username})
    return {"access_token": token, "token_type": "bearer", "username": data.username}

@router.post("/register")
def register(data: RegisterData):
    config = get_config()
    
    if 'usernames' not in config.get('credentials', {}):
        if 'credentials' not in config:
            config['credentials'] = {}
        config['credentials']['usernames'] = {}
        
    users = config['credentials']['usernames']
    
    if data.username in users:
        raise HTTPException(status_code=400, detail="Username already taken")
        
    hashed_password = bcrypt.hashpw(data.password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    users[data.username] = {
        "name": data.username,
        "email": f"{data.username}@easybi.com",
        "password": hashed_password
    }
    
    save_config(config)
    return {"message": "User registered successfully"}

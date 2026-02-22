from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt
import bcrypt
import json
import os
import uuid

from fastapi import Depends, HTTPException, status, Cookie
from fastapi.security import OAuth2PasswordBearer
from backend.app.core.config import settings
from backend.app.models.user import User, UserInDB, TokenData

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login", auto_error=False)

# In-memory user store (simulating DB)
# Key: email
fake_users_db = {}
USERS_FILE = "users.json"

def verify_password(plain_password, hashed_password):
    # bcrypt requires bytes
    if isinstance(hashed_password, str):
        hashed_password = hashed_password.encode('utf-8')
    if isinstance(plain_password, str):
        plain_password = plain_password.encode('utf-8')

    return bcrypt.checkpw(plain_password, hashed_password)

def get_password_hash(password):
    if isinstance(password, str):
        password = password.encode('utf-8')
    return bcrypt.hashpw(password, bcrypt.gensalt()).decode('utf-8')

def save_users():
    try:
        with open(USERS_FILE, "w") as f:
            # Convert UserInDB objects to dicts
            data = {email: u.model_dump() for email, u in fake_users_db.items()}
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"Error saving users: {e}")

def init_admin_user():
    """Seeds the admin user from env vars."""
    if settings.ADMIN_EMAIL not in fake_users_db:
        admin_user = UserInDB(
            id=str(uuid.uuid4()),
            email=settings.ADMIN_EMAIL,
            role="admin",
            allowed_namespaces=[], # Admin implicitly has access to everything, handled in logic
            theme_pref="minimal",
            hashed_password=get_password_hash(settings.ADMIN_PASSWORD)
        )
        fake_users_db[settings.ADMIN_EMAIL] = admin_user
        save_users()

def load_users():
    global fake_users_db
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, "r") as f:
                data = json.load(f)
                # Convert dicts back to UserInDB objects
                fake_users_db = {email: UserInDB(**u) for email, u in data.items()}
        except Exception as e:
            print(f"Error loading users: {e}")
            fake_users_db = {}

    # Ensure admin exists
    init_admin_user()

def get_user(email: str):
    return fake_users_db.get(email)

def authenticate_user(email: str, password: str):
    user = get_user(email)
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

async def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    access_token: Optional[str] = Cookie(None)
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    final_token = token
    if not final_token and access_token:
        if access_token.startswith("Bearer "):
            final_token = access_token.split(" ")[1]
        else:
            final_token = access_token

    if not final_token:
        raise credentials_exception

    try:
        payload = jwt.decode(final_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError:
        raise credentials_exception
    user = get_user(email=token_data.username)
    if user is None:
        raise credentials_exception
    return user

async def get_current_active_user(current_user: User = Depends(get_current_user)):
    return current_user

# Initialize/Load users on import
load_users()

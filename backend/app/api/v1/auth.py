from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from uuid import uuid4
from app.dependencies import get_user_repository, get_current_user
from app.infrastructure.database.repositories import UserRepository
from app.infrastructure.database.tables import UserTable
from app.services.auth_service import hash_password, verify_password, create_access_token

router = APIRouter()

class UserAuthRequest(BaseModel):
    email: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class UserResponse(BaseModel):
    id: str
    email: str

@router.post("/signup", response_model=TokenResponse)
async def signup(
    req: UserAuthRequest,
    user_repo: UserRepository = Depends(get_user_repository)
):
    email = req.email.strip()
    password = req.password
    
    if not email or not password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email and password are required"
        )
        
    # Check if user already exists
    existing_user = await user_repo.get_by_email(email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
        
    # Create new user
    user_id = str(uuid4())
    hashed = hash_password(password)
    await user_repo.save(id=user_id, email=email, hashed_password=hashed)
    
    # Generate token
    token = create_access_token(data={"sub": user_id})
    return TokenResponse(access_token=token)

@router.post("/login", response_model=TokenResponse)
async def login(
    req: UserAuthRequest,
    user_repo: UserRepository = Depends(get_user_repository)
):
    email = req.email.strip()
    password = req.password
    
    if not email or not password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email and password are required"
        )
        
    user = await user_repo.get_by_email(email)
    if not user or not verify_password(password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
        
    # Generate token
    token = create_access_token(data={"sub": user.id})
    return TokenResponse(access_token=token)

@router.get("/me", response_model=UserResponse)
async def get_me(current_user: UserTable = Depends(get_current_user)):
    return UserResponse(id=current_user.id, email=current_user.email)

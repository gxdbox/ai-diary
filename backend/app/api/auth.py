"""
用户认证 API 路由

提供注册、登录、获取当前用户信息三个端点。
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, EmailStr, Field
from typing import Optional

from app.db.database import get_db, User
from app.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    get_current_user,
)

router = APIRouter()


# ============ 请求/响应模型 ============

class RegisterRequest(BaseModel):
    """注册请求"""
    email: EmailStr = Field(..., description="邮箱")
    password: str = Field(..., min_length=6, max_length=128, description="密码（至少6位）")
    nickname: Optional[str] = Field(None, max_length=50, description="昵称")


class UserResponse(BaseModel):
    """用户信息响应"""
    id: int
    email: str
    nickname: Optional[str] = None
    avatar_color: str

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    """登录令牌响应"""
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


# ============ 路由 ============

@router.post("/register", response_model=TokenResponse)
async def register(
    request: RegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    用户注册

    1. 检查邮箱是否已注册
    2. 哈希密码并创建用户
    3. 签发 JWT token，返回令牌 + 用户信息
    """
    # 检查邮箱是否已存在
    result = await db.execute(select(User).where(User.email == request.email))
    if result.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该邮箱已被注册",
        )

    # 创建用户
    user = User(
        email=request.email,
        hashed_password=get_password_hash(request.password),
        nickname=request.nickname or request.email.split("@")[0],
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    # 签发 token
    token = create_access_token(data={"sub": str(user.id)})

    return TokenResponse(
        access_token=token,
        user=UserResponse(
            id=user.id,
            email=user.email,
            nickname=user.nickname,
            avatar_color=user.avatar_color,
        ),
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    """
    用户登录（OAuth2 密码流）

    客户端以 application/x-www-form-urlencoded 提交：
    - username: 邮箱
    - password: 密码

    返回 JWT access_token + 用户信息
    """
    # 查询用户
    result = await db.execute(select(User).where(User.email == form_data.username))
    user = result.scalar_one_or_none()

    # 验证用户和密码
    if user is None or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="邮箱或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 签发 token
    token = create_access_token(data={"sub": str(user.id)})

    return TokenResponse(
        access_token=token,
        user=UserResponse(
            id=user.id,
            email=user.email,
            nickname=user.nickname,
            avatar_color=user.avatar_color,
        ),
    )


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """获取当前登录用户信息"""
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        nickname=current_user.nickname,
        avatar_color=current_user.avatar_color,
    )

from datetime import datetime
from sqlalchemy import BigInteger, Boolean, DateTime, Float, Integer, String, Text, ForeignKey, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from typing import List, Optional


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)  # Telegram ID
    username: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    first_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_blocked: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    
    # Relationships
    orders: Mapped[List["Order"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class Order(Base):
    __tablename__ = "orders"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"))
    target_price: Mapped[float] = mapped_column(Float, nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    is_2fa: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String(50), default="active")  # active, completed, cancelled
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Relationships
    user: Mapped["User"] = relationship(back_populates="orders")
    purchases: Mapped[List["Purchase"]] = relationship(back_populates="order", cascade="all, delete-orphan")


class Purchase(Base):
    __tablename__ = "purchases"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(Integer, ForeignKey("orders.id", ondelete="CASCADE"))
    pack_id: Mapped[str] = mapped_column(String(255), unique=True)
    accounts_count: Mapped[int] = mapped_column(Integer)
    price_paid: Mapped[float] = mapped_column(Float)
    total_price: Mapped[float] = mapped_column(Float)
    is_2fa: Mapped[bool] = mapped_column(Boolean)
    purchase_date: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    
    # Relationships
    order: Mapped["Order"] = relationship(back_populates="purchases")
    accounts: Mapped[List["Account"]] = relationship(back_populates="purchase", cascade="all, delete-orphan")


class Account(Base):
    __tablename__ = "accounts"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    purchase_id: Mapped[int] = mapped_column(Integer, ForeignKey("purchases.id", ondelete="CASCADE"))
    email: Mapped[str] = mapped_column(String(255))
    password: Mapped[str] = mapped_column(String(255))
    recovery_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    recovery_email_messages_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    authenticator_token_2fa: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    app_password: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    messages_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="available")  # available, used
    
    # Relationships
    purchase: Mapped["Purchase"] = relationship(back_populates="accounts")


class PriceHistory(Base):
    __tablename__ = "price_history"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    price_no_2fa: Mapped[float] = mapped_column(Float)
    price_2fa: Mapped[float] = mapped_column(Float)
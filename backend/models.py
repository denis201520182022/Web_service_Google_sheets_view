"""
Модели базы данных
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from backend.database import Base


class User(Base):
    """Пользователи системы"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    is_admin = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Связи
    spreadsheets = relationship("UserSpreadsheet", back_populates="user", cascade="all, delete-orphan")
    locked_ranges = relationship("LockedRange", back_populates="user", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<User {self.username} (admin={self.is_admin})>"


class UserSpreadsheet(Base):
    """История таблиц пользователя"""
    __tablename__ = "user_spreadsheets"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    spreadsheet_id = Column(String(255), nullable=False, index=True)
    spreadsheet_title = Column(String(255))
    spreadsheet_url = Column(Text)
    last_accessed = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    access_count = Column(Integer, default=1)
    is_favorite = Column(Boolean, default=False)
    
    # Связи
    user = relationship("User", back_populates="spreadsheets")
    
    def __repr__(self):
        return f"<UserSpreadsheet {self.spreadsheet_title} by user_id={self.user_id}>"


class LockedRange(Base):
    """Заблокированные диапазоны ячеек (только для админов)"""
    __tablename__ = "locked_ranges"
    
    id = Column(Integer, primary_key=True, index=True)
    spreadsheet_id = Column(String(255), nullable=False, index=True)
    sheet_name = Column(String(255), nullable=False)
    range_notation = Column(String(50), nullable=False)  # Например: A1:C10
    locked_by = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    reason = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Связи
    user = relationship("User", back_populates="locked_ranges")
    
    def __repr__(self):
        return f"<LockedRange {self.sheet_name}!{self.range_notation}>"


class AuditLog(Base):
    """Логи действий пользователей"""
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    username = Column(String(50))
    action = Column(String(100), nullable=False, index=True)  # login, update_cell, lock_range, etc.
    spreadsheet_id = Column(String(255), nullable=True)
    sheet_name = Column(String(255), nullable=True)
    details = Column(JSON, nullable=True)  # Дополнительные данные
    ip_address = Column(String(45), nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    def __repr__(self):
        return f"<AuditLog {self.action} by {self.username} at {self.timestamp}>"
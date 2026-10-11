from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, Boolean, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    accounts: Mapped[list["Account"]] = relationship(back_populates="user")
    policies: Mapped[list["Policy"]] = relationship(back_populates="user")
    privacy_actions: Mapped[list["PrivacyAction"]] = relationship(
        back_populates="user"
    )


class Service(Base):
    __tablename__ = "services"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(150), unique=True, nullable=False)
    website: Mapped[str | None] = mapped_column(String(500), nullable=True)
    purpose: Mapped[str | None] = mapped_column(Text, nullable=True)

    accounts: Mapped[list["Account"]] = relationship(back_populates="service")


class Account(Base):
    __tablename__ = "accounts"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    service_id: Mapped[int] = mapped_column(ForeignKey("services.id"), nullable=False)
    last_activity: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    status: Mapped[str] = mapped_column(
        String(30), default="UNKNOWN", nullable=False
    )
    retention_info: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped["User"] = relationship(back_populates="accounts")
    service: Mapped["Service"] = relationship(back_populates="accounts")
    data_records: Mapped[list["DataRecord"]] = relationship(
        back_populates="account", cascade="all, delete-orphan"
    )
    privacy_actions: Mapped[list["PrivacyAction"]] = relationship(
        back_populates="account"
    )


class DataRecord(Base):
    __tablename__ = "data_records"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    account_id: Mapped[int] = mapped_column(
        ForeignKey("accounts.id"), nullable=False
    )
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    account: Mapped["Account"] = relationship(back_populates="data_records")


class Policy(Base):
    __tablename__ = "policies"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    policy_type: Mapped[str] = mapped_column(String(50), nullable=False)
    policy_text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped["User"] = relationship(back_populates="policies")


class PrivacyAction(Base):
    __tablename__ = "privacy_actions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    account_id: Mapped[int] = mapped_column(
        ForeignKey("accounts.id"), nullable=False
    )

    action_type: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)

    status: Mapped[str] = mapped_column(
        String(30), default="PENDING", nullable=False
    )
    requires_approval: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    user: Mapped["User"] = relationship(back_populates="privacy_actions")
    account: Mapped["Account"] = relationship(back_populates="privacy_actions")
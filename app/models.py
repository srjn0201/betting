import enum
from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    ForeignKey,
    DateTime,
    Enum as SQLAlchemyEnum,
    Boolean,
    JSON as JSONB
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .database import Base


class Role(Base):
    __tablename__ = "roles"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    
    users = relationship("User", back_populates="role")

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=False)
    parent_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    role = relationship("Role", back_populates="users")
    parent = relationship("User", remote_side=[id], back_populates="children")
    children = relationship("User", back_populates="parent")
    
    sent_transactions = relationship("Transaction", foreign_keys="[Transaction.sender_id]", back_populates="sender")
    received_transactions = relationship("Transaction", foreign_keys="[Transaction.recipient_id]", back_populates="recipient")

    bets = relationship("Bet", back_populates="user")




class Transaction(Base):
    __tablename__ = "transactions"
    id = Column(Integer, primary_key=True, index=True)
    sender_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # Null for system deposits
    recipient_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    amount = Column(Float, nullable=False)
    transaction_type = Column(String, nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

    sender = relationship("User", foreign_keys=[sender_id], back_populates="sent_transactions")
    recipient = relationship("User", foreign_keys=[recipient_id], back_populates="received_transactions")


# --- Match & Game Data Models ---

class Team(Base):
    __tablename__ = "teams"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    short_code = Column(String(4), unique=True, nullable=False)
    logo_url = Column(String, nullable=True)

    players = relationship("Player", back_populates="team")

class Player(Base):
    __tablename__ = "players"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    role = Column(String, nullable=False) # e.g., Batsman, Bowler, All-rounder
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)

    team = relationship("Team", back_populates="players")

class Fixture(Base):
    __tablename__ = "fixtures"
    id = Column(Integer, primary_key=True, index=True)
    team1_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    team2_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    match_date = Column(DateTime(timezone=True), nullable=False)
    status = Column(String, nullable=False) # e.g., Upcoming, Live, Finished

    team1 = relationship("Team", foreign_keys=[team1_id])
    team2 = relationship("Team", foreign_keys=[team2_id])

class BallByBallEvent(Base):
    __tablename__ = "ball_by_ball_events"
    id = Column(Integer, primary_key=True, index=True)
    fixture_id = Column(Integer, ForeignKey("fixtures.id"), nullable=False)
    inning = Column(Integer, nullable=False)
    over = Column(Integer, nullable=False)
    ball = Column(Integer, nullable=False)
    batsman_id = Column(Integer, ForeignKey("players.id"), nullable=False)
    bowler_id = Column(Integer, ForeignKey("players.id"), nullable=False)
    runs_scored = Column(Integer, nullable=False)
    is_wicket = Column(Boolean, default=False)
    commentary_text = Column(String, nullable=False)

    fixture = relationship("Fixture")
    batsman = relationship("Player", foreign_keys=[batsman_id])
    bowler = relationship("Player", foreign_keys=[bowler_id])

class OddsSnapshot(Base):
    __tablename__ = "odds_snapshots"
    id = Column(Integer, primary_key=True, index=True)
    ball_by_ball_event_id = Column(Integer, ForeignKey("ball_by_ball_events.id"), nullable=False)
    odds_data = Column(JSONB, nullable=False)

    event = relationship("BallByBallEvent")


class BetStatus(enum.Enum):
    ACTIVE = "ACTIVE"
    WON = "WON"
    LOST = "LOST"


class Bet(Base):
    __tablename__ = "bets"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    fixture_id = Column(Integer, nullable=False)
    market_name = Column(String, nullable=False)
    odds = Column(Float, nullable=False)
    stake = Column(Float, nullable=False)
    status = Column(SQLAlchemyEnum(BetStatus), default=BetStatus.ACTIVE, nullable=False)

    user = relationship("User", back_populates="bets")


class TokenBlocklist(Base):
    __tablename__ = "token_blocklist"
    id = Column(Integer, primary_key=True, index=True)
    jti = Column(String, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

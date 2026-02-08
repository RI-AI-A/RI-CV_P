"""SQLAlchemy ORM models for retail intelligence system."""
from sqlalchemy import (
    Column, String, Integer, Float, DateTime, ForeignKey, 
    Enum, Text, Index, TIMESTAMP, Boolean
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
import uuid

from db.base import Base


class ActionType(str, enum.Enum):
    """Customer action types."""
    PASSED = "passed"
    ENTERED = "entered"


class Customer(Base):
    """Customer tracking table with anonymized UUIDs."""
    __tablename__ = "customers"
    
    customer_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Relationships
    movements = relationship("CustomerBranchMovement", back_populates="customer")


class CustomerBranchMovement(Base):
    """Customer movement events with enter/exit tracking."""
    __tablename__ = "customer_branch_movement"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.customer_id"), nullable=False)
    branch_id = Column(String(100), ForeignKey("branches.id"), nullable=False)
    enter_time = Column(TIMESTAMP(timezone=True), nullable=False)
    exit_time = Column(TIMESTAMP(timezone=True), nullable=True)
    action_type = Column(Enum(ActionType), nullable=False)
    
    # Relationships
    customer = relationship("Customer", back_populates="movements")
    branch = relationship("Branch", back_populates="movements")
    
    # Indexes for time-based queries
    __table_args__ = (
        Index("ix_customer_branch_movement_enter_time", "enter_time"),
        Index("ix_customer_branch_movement_exit_time", "exit_time"),
        Index("ix_customer_branch_movement_branch_id_enter_time", "branch_id", "enter_time"),
    )


class Branch(Base):
    """Branch information and metadata."""
    __tablename__ = "branches"
    
    id = Column(String(100), primary_key=True)
    name = Column(String(200), nullable=False)
    capacity = Column(Integer, nullable=False)
    peak_time = Column(String(10), nullable=True)  # Format: "HH:MM"
    neighbors = Column(JSONB, nullable=True)  # List of neighboring branch IDs
    state = Column(String(50), nullable=True)  # e.g., "active", "maintenance"
    expiry = Column(DateTime, nullable=True)
    restocking_schedule = Column(String(200), nullable=True)
    
    # Relationships
    movements = relationship("CustomerBranchMovement", back_populates="branch")
    tasks = relationship("Task", back_populates="branch")
    promotions = relationship("Promotion", back_populates="branch")
    kpis = relationship("BranchKPITimeseries", back_populates="branch")


class Employee(Base):
    """Employee information."""
    __tablename__ = "employees"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False)
    position = Column(String(100), nullable=True)
    email = Column(String(200), nullable=True)
    phone = Column(String(50), nullable=True)
    
    # Relationships
    tasks = relationship("Task", back_populates="employee")


class Task(Base):
    """Task management for employees."""
    __tablename__ = "tasks"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    task = Column(Text, nullable=False)
    time = Column(DateTime, nullable=False)
    state = Column(String(50), nullable=False)  # e.g., "pending", "in_progress", "completed"
    branch_id = Column(String(100), ForeignKey("branches.id"), nullable=False)
    note = Column(Text, nullable=True)
    
    # Relationships
    employee = relationship("Employee", back_populates="tasks")
    branch = relationship("Branch", back_populates="tasks")
    
    # Indexes
    __table_args__ = (
        Index("ix_tasks_branch_id", "branch_id"),
        Index("ix_tasks_employee_id", "employee_id"),
        Index("ix_tasks_time", "time"),
    )


class Event(Base):
    """Events with location and repetition support."""
    __tablename__ = "events"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=True)
    type = Column(String(100), nullable=False)  # e.g., "sale", "holiday", "maintenance"
    description = Column(Text, nullable=True)
    location = Column(JSONB, nullable=True)  # Flexible location data
    repetition = Column(String(50), nullable=True)  # e.g., "daily", "weekly", "monthly"
    global_event = Column(Boolean, default=False)
    
    # Indexes
    __table_args__ = (
        Index("ix_events_start_time", "start_time"),
        Index("ix_events_type", "type"),
    )


class Promotion(Base):
    """Promotions for branches and items."""
    __tablename__ = "promotions"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    branch_id = Column(String(100), ForeignKey("branches.id"), nullable=True)  # Null for global promotions
    item_name = Column(String(200), nullable=True)
    promotion_type = Column(String(100), nullable=False)  # e.g., "percentage", "fixed_amount", "bogo"
    discount_value = Column(Float, nullable=False)
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    
    # Relationships
    branch = relationship("Branch", back_populates="promotions")
    
    # Indexes
    __table_args__ = (
        Index("ix_promotions_branch_id", "branch_id"),
        Index("ix_promotions_start_date", "start_date"),
    )


class BranchKPITimeseries(Base):
    """Computed KPI metrics for branches over time windows."""
    __tablename__ = "branch_kpi_timeseries"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    branch_id = Column(String(100), ForeignKey("branches.id"), nullable=False)
    time_window_start = Column(TIMESTAMP(timezone=True), nullable=False)
    time_window_end = Column(TIMESTAMP(timezone=True), nullable=False)
    
    # KPI Metrics
    traffic_index = Column(Float, nullable=True)
    conversion_proxy = Column(Float, nullable=True)
    congestion_level = Column(Float, nullable=True)
    growth_momentum = Column(Float, nullable=True)
    utilization_ratio = Column(Float, nullable=True)
    staffing_adequacy_index = Column(Float, nullable=True)
    bottleneck_score = Column(Float, nullable=True)
    
    created_at = Column(TIMESTAMP(timezone=True), default=datetime.utcnow, nullable=False)
    
    # Relationships
    branch = relationship("Branch", back_populates="kpis")
    
    # Indexes for time-based queries
    __table_args__ = (
        Index("ix_branch_kpi_timeseries_branch_id", "branch_id"),
        Index("ix_branch_kpi_timeseries_time_window_start", "time_window_start"),
        Index("ix_branch_kpi_timeseries_branch_id_time_window", "branch_id", "time_window_start"),
    )

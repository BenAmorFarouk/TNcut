"""
SQLAlchemy models for TNCut application.
Defines the database schema for devices, logs, history, and settings.
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime,
    ForeignKey, Text, BigInteger, Index, UniqueConstraint
)
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.sql import func

# Create base class for declarative models
Base = declarative_base()


class Device(Base):
    """Model representing a network device."""
    __tablename__ = 'devices'

    id = Column(Integer, primary_key=True, index=True)
    ip_address = Column(String(45), nullable=False, index=True)  # IPv6 compatible
    mac_address = Column(String(17), nullable=True, index=True)  # MAC address format
    hostname = Column(String(255), nullable=True)
    vendor = Column(String(255), nullable=True)
    device_type = Column(String(50), nullable=True)  # PC, Server, Phone, Router, IoT, VM
    is_online = Column(Boolean, default=False, index=True)
    response_time = Column(Integer, nullable=True)  # milliseconds
    last_seen = Column(DateTime, default=func.now(), onupdate=func.now())
    first_seen = Column(DateTime, default=func.now())

    # Additional fields for extended information
    os_info = Column(String(255), nullable=True)
    open_ports = Column(Text, nullable=True)  # JSON string of port list
    notes = Column(Text, nullable=True)

    # Relationships
    traffic_logs = relationship("TrafficLog", back_populates="device", cascade="all, delete-orphan")
    history_records = relationship("DeviceHistory", back_populates="device", cascade="all, delete-orphan")

    # Constraints
    __table_args__ = (
        UniqueConstraint('ip_address', name='uq_device_ip'),
        Index('idx_device_last_seen', 'last_seen'),
        Index('idx_device_hostname', 'hostname'),
    )

    def __repr__(self) -> str:
        return f"<Device(ip='{self.ip_address}', mac='{self.mac_address}', hostname='{self.hostname}', online={self.is_online})>"

    def to_dict(self) -> dict:
        """Convert model instance to dictionary."""
        return {
            'id': self.id,
            'ip_address': self.ip_address,
            'mac_address': self.mac_address,
            'hostname': self.hostname,
            'vendor': self.vendor,
            'device_type': self.device_type,
            'is_online': self.is_online,
            'response_time': self.response_time,
            'last_seen': self.last_seen.isoformat() if self.last_seen else None,
            'first_seen': self.first_seen.isoformat() if self.first_seen else None,
            'os_info': self.os_info,
            'open_ports': self.open_ports,
            'notes': self.notes
        }


class TrafficLog(Base):
    """Model for recording network traffic statistics."""
    __tablename__ = 'traffic_logs'

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(Integer, ForeignKey('devices.id'), nullable=False, index=True)
    timestamp = Column(DateTime, default=func.now(), index=True)
    bytes_sent = Column(BigInteger, default=0)
    bytes_received = Column(BigInteger, default=0)
    packets_sent = Column(Integer, default=0)
    packets_received = Column(Integer, default=0)

    # Relationship
    device = relationship("Device", back_populates="traffic_logs")

    # Indexes
    __table_args__ = (
        Index('idx_traffic_device_time', 'device_id', 'timestamp'),
        Index('idx_traffic_time', 'timestamp'),
    )

    def __repr__(self) -> str:
        return f"<TrafficLog(device_id={self.device_id}, time='{self.timestamp}', sent={self.bytes_sent}, recv={self.bytes_received})>"

    def to_dict(self) -> dict:
        """Convert model instance to dictionary."""
        return {
            'id': self.id,
            'device_id': self.device_id,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'bytes_sent': self.bytes_sent,
            'bytes_received': self.bytes_received,
            'packets_sent': self.packets_sent,
            'packets_received': self.packets_received
        }


class DeviceHistory(Base):
    """Model for storing historical device information."""
    __tablename__ = 'device_history'

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(Integer, ForeignKey('devices.id'), nullable=False, index=True)
    timestamp = Column(DateTime, default=func.now(), index=True)
    event_type = Column(String(50), nullable=False, index=True)  # joined, left, ip_changed, etc.
    description = Column(Text, nullable=True)
    old_value = Column(Text, nullable=True)  # JSON string of previous state
    new_value = Column(Text, nullable=True)  # JSON string of new state

    # Relationship
    device = relationship("Device", back_populates="history_records")

    # Indexes
    __table_args__ = (
        Index('idx_history_device_time', 'device_id', 'timestamp'),
        Index('idx_history_event_time', 'event_type', 'timestamp'),
    )

    def __repr__(self) -> str:
        return f"<DeviceHistory(device_id={self.device_id}, time='{self.timestamp}', event='{self.event_type}')>"

    def to_dict(self) -> dict:
        """Convert model instance to dictionary."""
        return {
            'id': self.id,
            'device_id': self.device_id,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'event_type': self.event_type,
            'description': self.description,
            'old_value': self.old_value,
            'new_value': self.new_value
        }


class ApplicationLog(Base):
    """Model for storing application logs."""
    __tablename__ = 'application_logs'

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=func.now(), index=True)
    level = Column(String(20), nullable=False, index=True)  # DEBUG, INFO, WARNING, ERROR, CRITICAL
    logger_name = Column(String(255), nullable=True, index=True)
    message = Column(Text, nullable=False)
    module = Column(String(255), nullable=True)
    function = Column(String(255), nullable=True)
    line_number = Column(Integer, nullable=True)

    # Indexes
    __table_args__ = (
        Index('idx_app_log_time', 'timestamp'),
        Index('idx_app_log_level', 'level'),
        Index('idx_app_log_logger', 'logger_name'),
    )

    def __repr__(self) -> str:
        return f"<ApplicationLog(time='{self.timestamp}', level='{self.level}', message='{self.message[:50]}...')>"

    def to_dict(self) -> dict:
        """Convert model instance to dictionary."""
        return {
            'id': self.id,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'level': self.level,
            'logger_name': self.logger_name,
            'message': self.message,
            'module': self.module,
            'function': self.function,
            'line_number': self.line_number
        }


class Settings(Base):
    """Model for storing application settings."""
    __tablename__ = 'application_settings'

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(255), nullable=False, unique=True, index=True)
    value = Column(Text, nullable=True)  # JSON string for complex values
    description = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    def __repr__(self) -> str:
        return f"<Settings(key='{self.key}', value='{self.value}')>"

    def to_dict(self) -> dict:
        """Convert model instance to dictionary."""
        return {
            'id': self.id,
            'key': self.key,
            'value': self.value,
            'description': self.description,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
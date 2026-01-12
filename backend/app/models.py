# =============================================================================
# LogisFlow SQLAlchemy Models
# =============================================================================

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, BigInteger, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class Company(Base):
    """고객사 모델"""
    __tablename__ = "companies"
    
    company_id = Column(Integer, primary_key=True, index=True)
    company_name = Column(String(100), nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    
    # 관계
    shipments = relationship("Shipment", back_populates="company")


class Warehouse(Base):
    """창고 모델"""
    __tablename__ = "warehouses"
    
    warehouse_id = Column(Integer, primary_key=True, index=True)
    warehouse_name = Column(String(100), nullable=False)
    address = Column(String(255))
    created_at = Column(DateTime, server_default=func.now())


class Product(Base):
    """상품 모델"""
    __tablename__ = "products"
    
    product_id = Column(Integer, primary_key=True, index=True)
    product_name = Column(String(100), nullable=False)
    created_at = Column(DateTime, server_default=func.now())


class Shipment(Base):
    """화물 모델 (비정규화 컬럼 포함)"""
    __tablename__ = "shipments"
    
    shipment_id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.company_id"))
    origin_warehouse_id = Column(Integer, ForeignKey("warehouses.warehouse_id"))
    destination_warehouse_id = Column(Integer, ForeignKey("warehouses.warehouse_id"))
    created_at = Column(DateTime, server_default=func.now())
    
    # ★ 비정규화 컬럼
    current_status = Column(String(50), default="PENDING")
    last_updated_at = Column(DateTime, server_default=func.now())
    origin_warehouse_name = Column(String(100))
    destination_warehouse_name = Column(String(100))
    
    # 관계
    company = relationship("Company", back_populates="shipments")
    updates = relationship("ShipmentUpdate", back_populates="shipment", order_by="ShipmentUpdate.timestamp.desc()")


class ShipmentUpdate(Base):
    """상태 변경 로그 모델 (파티션 테이블)"""
    __tablename__ = "shipment_updates"
    
    update_id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    shipment_id = Column(Integer, ForeignKey("shipments.shipment_id"), nullable=False)
    status_code = Column(String(50), nullable=False)
    notes = Column(String(255))
    timestamp = Column(DateTime, nullable=False, server_default=func.now(), primary_key=True)
    
    # 관계
    shipment = relationship("Shipment", back_populates="updates")

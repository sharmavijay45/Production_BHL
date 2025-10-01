"""
BHIV Core Logistics Microservice
===============================

Handles supply chain management, inventory tracking, and logistics operations.

Features:
- Inventory management
- Supply chain tracking
- Warehouse operations
- Shipping and delivery
- Vendor management
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from fastapi import HTTPException, Depends, Query
from pydantic import BaseModel, Field
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from modules.shared.base_service import BaseService
from security.auth import get_current_user
from security.rbac import require_permission, Permission
from security.audit import audit_log

logger = logging.getLogger(__name__)

# Pydantic Models
class InventoryItem(BaseModel):
    """Inventory item model"""
    id: Optional[str] = None
    sku: str = Field(..., description="Stock Keeping Unit")
    name: str = Field(..., description="Item name")
    description: Optional[str] = None
    category: str = Field(..., description="Item category")
    quantity: int = Field(..., ge=0, description="Current stock quantity")
    unit_price: float = Field(..., ge=0, description="Price per unit")
    supplier_id: Optional[str] = None
    warehouse_location: Optional[str] = None
    reorder_level: int = Field(default=10, ge=0, description="Minimum stock level")
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class InventoryUpdate(BaseModel):
    """Inventory update model"""
    quantity: Optional[int] = Field(None, ge=0)
    unit_price: Optional[float] = Field(None, ge=0)
    warehouse_location: Optional[str] = None
    reorder_level: Optional[int] = Field(None, ge=0)

class Supplier(BaseModel):
    """Supplier model"""
    id: Optional[str] = None
    name: str = Field(..., description="Supplier name")
    contact_email: str = Field(..., description="Contact email")
    contact_phone: Optional[str] = None
    address: Optional[str] = None
    rating: float = Field(default=5.0, ge=1.0, le=5.0)
    active: bool = Field(default=True)
    created_at: Optional[datetime] = None

class ShipmentOrder(BaseModel):
    """Shipment order model"""
    id: Optional[str] = None
    customer_id: str = Field(..., description="Customer ID")
    items: List[Dict] = Field(..., description="List of items with quantities")
    shipping_address: str = Field(..., description="Delivery address")
    status: str = Field(default="pending", description="Order status")
    tracking_number: Optional[str] = None
    estimated_delivery: Optional[datetime] = None
    created_at: Optional[datetime] = None

class LogisticsService(BaseService):
    """Logistics microservice"""
    
    def __init__(self):
        super().__init__(
            service_name="Logistics",
            service_version="1.0.0",
            port=8001
        )
        
        # In-memory storage (replace with database in production)
        self.inventory: Dict[str, InventoryItem] = {}
        self.suppliers: Dict[str, Supplier] = {}
        self.shipments: Dict[str, ShipmentOrder] = {}
        
        self._setup_routes()
        self._initialize_sample_data()
    
    def _get_service_capabilities(self) -> List[str]:
        """Get logistics service capabilities"""
        return super()._get_service_capabilities() + [
            "inventory_management",
            "supplier_management", 
            "shipment_tracking",
            "warehouse_operations",
            "supply_chain_analytics"
        ]
    
    def _get_service_dependencies(self) -> List[str]:
        """Get service dependencies"""
        return ["crm_service", "integrations_service"]
    
    def _setup_routes(self):
        """Setup logistics-specific routes"""
        
        # Inventory Management Routes
        @self.app.get("/inventory", tags=["logistics"])
        async def list_inventory(
            category: Optional[str] = Query(None, description="Filter by category"),
            low_stock: bool = Query(False, description="Show only low stock items"),
            current_user: dict = Depends(get_current_user)
        ):
            """List inventory items"""
            if not require_permission(current_user, Permission.LOGISTICS_READ):
                raise HTTPException(status_code=403, detail="Logistics read permission required")
            
            items = list(self.inventory.values())
            
            # Apply filters
            if category:
                items = [item for item in items if item.category.lower() == category.lower()]
            
            if low_stock:
                items = [item for item in items if item.quantity <= item.reorder_level]
            
            await audit_log(
                action="inventory_list",
                resource="inventory",
                user_id=current_user.get("user_id"),
                details={"filter_category": category, "low_stock_filter": low_stock}
            )
            
            return {
                "items": items,
                "total_count": len(items),
                "low_stock_count": len([i for i in self.inventory.values() if i.quantity <= i.reorder_level])
            }
        
        @self.app.post("/inventory", tags=["logistics"])
        async def create_inventory_item(
            item: InventoryItem,
            current_user: dict = Depends(get_current_user)
        ):
            """Create new inventory item"""
            if not require_permission(current_user, Permission.LOGISTICS_WRITE):
                raise HTTPException(status_code=403, detail="Logistics write permission required")
            
            # Generate ID and timestamps
            item.id = f"inv_{len(self.inventory) + 1:06d}"
            item.created_at = datetime.now()
            item.updated_at = datetime.now()
            
            self.inventory[item.id] = item
            
            await audit_log(
                action="inventory_create",
                resource="inventory",
                user_id=current_user.get("user_id"),
                details={"item_id": item.id, "sku": item.sku, "quantity": item.quantity}
            )
            
            return {"success": True, "item": item}
        
        @self.app.get("/inventory/{item_id}", tags=["logistics"])
        async def get_inventory_item(
            item_id: str,
            current_user: dict = Depends(get_current_user)
        ):
            """Get specific inventory item"""
            if not require_permission(current_user, Permission.LOGISTICS_READ):
                raise HTTPException(status_code=403, detail="Logistics read permission required")
            
            if item_id not in self.inventory:
                raise HTTPException(status_code=404, detail="Item not found")
            
            return {"item": self.inventory[item_id]}
        
        @self.app.put("/inventory/{item_id}", tags=["logistics"])
        async def update_inventory_item(
            item_id: str,
            update: InventoryUpdate,
            current_user: dict = Depends(get_current_user)
        ):
            """Update inventory item"""
            if not require_permission(current_user, Permission.LOGISTICS_WRITE):
                raise HTTPException(status_code=403, detail="Logistics write permission required")
            
            if item_id not in self.inventory:
                raise HTTPException(status_code=404, detail="Item not found")
            
            item = self.inventory[item_id]
            
            # Update fields
            if update.quantity is not None:
                item.quantity = update.quantity
            if update.unit_price is not None:
                item.unit_price = update.unit_price
            if update.warehouse_location is not None:
                item.warehouse_location = update.warehouse_location
            if update.reorder_level is not None:
                item.reorder_level = update.reorder_level
            
            item.updated_at = datetime.now()
            
            await audit_log(
                action="inventory_update",
                resource="inventory",
                user_id=current_user.get("user_id"),
                details={"item_id": item_id, "updates": update.dict(exclude_unset=True)}
            )
            
            return {"success": True, "item": item}
        
        # Supplier Management Routes
        @self.app.get("/suppliers", tags=["logistics"])
        async def list_suppliers(
            active_only: bool = Query(True, description="Show only active suppliers"),
            current_user: dict = Depends(get_current_user)
        ):
            """List suppliers"""
            if not require_permission(current_user, Permission.LOGISTICS_READ):
                raise HTTPException(status_code=403, detail="Logistics read permission required")
            
            suppliers = list(self.suppliers.values())
            
            if active_only:
                suppliers = [s for s in suppliers if s.active]
            
            return {"suppliers": suppliers, "count": len(suppliers)}
        
        @self.app.post("/suppliers", tags=["logistics"])
        async def create_supplier(
            supplier: Supplier,
            current_user: dict = Depends(get_current_user)
        ):
            """Create new supplier"""
            if not require_permission(current_user, Permission.LOGISTICS_WRITE):
                raise HTTPException(status_code=403, detail="Logistics write permission required")
            
            supplier.id = f"sup_{len(self.suppliers) + 1:06d}"
            supplier.created_at = datetime.now()
            
            self.suppliers[supplier.id] = supplier
            
            await audit_log(
                action="supplier_create",
                resource="suppliers",
                user_id=current_user.get("user_id"),
                details={"supplier_id": supplier.id, "name": supplier.name}
            )
            
            return {"success": True, "supplier": supplier}
        
        # Shipment Management Routes
        @self.app.get("/shipments", tags=["logistics"])
        async def list_shipments(
            status: Optional[str] = Query(None, description="Filter by status"),
            current_user: dict = Depends(get_current_user)
        ):
            """List shipment orders"""
            if not require_permission(current_user, Permission.LOGISTICS_READ):
                raise HTTPException(status_code=403, detail="Logistics read permission required")
            
            shipments = list(self.shipments.values())
            
            if status:
                shipments = [s for s in shipments if s.status.lower() == status.lower()]
            
            return {"shipments": shipments, "count": len(shipments)}
        
        @self.app.post("/shipments", tags=["logistics"])
        async def create_shipment(
            shipment: ShipmentOrder,
            current_user: dict = Depends(get_current_user)
        ):
            """Create new shipment order"""
            if not require_permission(current_user, Permission.LOGISTICS_WRITE):
                raise HTTPException(status_code=403, detail="Logistics write permission required")
            
            shipment.id = f"ship_{len(self.shipments) + 1:06d}"
            shipment.created_at = datetime.now()
            shipment.tracking_number = f"TRK{shipment.id.upper()}"
            shipment.estimated_delivery = datetime.now() + timedelta(days=3)
            
            # Check inventory availability
            for item in shipment.items:
                item_id = item.get("item_id")
                quantity = item.get("quantity", 0)
                
                if item_id in self.inventory:
                    if self.inventory[item_id].quantity < quantity:
                        raise HTTPException(
                            status_code=400, 
                            detail=f"Insufficient inventory for item {item_id}"
                        )
                    
                    # Reserve inventory
                    self.inventory[item_id].quantity -= quantity
                    self.inventory[item_id].updated_at = datetime.now()
            
            self.shipments[shipment.id] = shipment
            
            await audit_log(
                action="shipment_create",
                resource="shipments",
                user_id=current_user.get("user_id"),
                details={
                    "shipment_id": shipment.id,
                    "customer_id": shipment.customer_id,
                    "items_count": len(shipment.items)
                }
            )
            
            return {"success": True, "shipment": shipment}
        
        @self.app.get("/shipments/{shipment_id}/track", tags=["logistics"])
        async def track_shipment(
            shipment_id: str,
            current_user: dict = Depends(get_current_user)
        ):
            """Track shipment status"""
            if not require_permission(current_user, Permission.LOGISTICS_READ):
                raise HTTPException(status_code=403, detail="Logistics read permission required")
            
            if shipment_id not in self.shipments:
                raise HTTPException(status_code=404, detail="Shipment not found")
            
            shipment = self.shipments[shipment_id]
            
            # Mock tracking events
            tracking_events = [
                {
                    "timestamp": shipment.created_at.isoformat(),
                    "status": "Order Created",
                    "location": "Warehouse",
                    "description": "Order has been created and is being prepared"
                },
                {
                    "timestamp": (shipment.created_at + timedelta(hours=2)).isoformat(),
                    "status": "In Transit",
                    "location": "Distribution Center",
                    "description": "Package is in transit to destination"
                }
            ]
            
            return {
                "shipment": shipment,
                "tracking_events": tracking_events,
                "current_status": shipment.status
            }
        
        # Analytics Routes
        @self.app.get("/analytics/inventory", tags=["logistics"])
        async def inventory_analytics(
            current_user: dict = Depends(get_current_user)
        ):
            """Get inventory analytics"""
            if not require_permission(current_user, Permission.LOGISTICS_READ):
                raise HTTPException(status_code=403, detail="Logistics read permission required")
            
            total_items = len(self.inventory)
            low_stock_items = len([i for i in self.inventory.values() if i.quantity <= i.reorder_level])
            total_value = sum(item.quantity * item.unit_price for item in self.inventory.values())
            
            categories = {}
            for item in self.inventory.values():
                if item.category not in categories:
                    categories[item.category] = {"count": 0, "value": 0}
                categories[item.category]["count"] += 1
                categories[item.category]["value"] += item.quantity * item.unit_price
            
            return {
                "summary": {
                    "total_items": total_items,
                    "low_stock_items": low_stock_items,
                    "total_inventory_value": total_value,
                    "categories_count": len(categories)
                },
                "by_category": categories,
                "alerts": {
                    "low_stock_alert": low_stock_items > 0,
                    "low_stock_items": [
                        {"id": item.id, "sku": item.sku, "quantity": item.quantity}
                        for item in self.inventory.values() 
                        if item.quantity <= item.reorder_level
                    ]
                }
            }
    
    def _initialize_sample_data(self):
        """Initialize with sample data"""
        # Sample inventory items
        sample_items = [
            InventoryItem(
                id="inv_000001",
                sku="LAPTOP-001",
                name="Business Laptop",
                description="High-performance business laptop",
                category="Electronics",
                quantity=25,
                unit_price=1200.00,
                warehouse_location="A1-B2",
                reorder_level=5,
                created_at=datetime.now()
            ),
            InventoryItem(
                id="inv_000002", 
                sku="CHAIR-001",
                name="Office Chair",
                description="Ergonomic office chair",
                category="Furniture",
                quantity=8,
                unit_price=300.00,
                warehouse_location="B2-C1",
                reorder_level=10,
                created_at=datetime.now()
            )
        ]
        
        for item in sample_items:
            self.inventory[item.id] = item
        
        # Sample suppliers
        sample_suppliers = [
            Supplier(
                id="sup_000001",
                name="TechCorp Solutions",
                contact_email="orders@techcorp.com",
                contact_phone="+1-555-0123",
                address="123 Tech Street, Silicon Valley, CA",
                rating=4.5,
                created_at=datetime.now()
            )
        ]
        
        for supplier in sample_suppliers:
            self.suppliers[supplier.id] = supplier
        
        logger.info("✅ Logistics service initialized with sample data")

# Create service instance
logistics_service = LogisticsService()

if __name__ == "__main__":
    logistics_service.run(debug=True)

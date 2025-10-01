"""
BHIV Core CRM Microservice
=========================

Customer Relationship Management service handling:
- Customer profiles and data
- Lead management
- Sales pipeline
- Customer interactions
- Support tickets
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from fastapi import HTTPException, Depends, Query
from pydantic import BaseModel, Field, EmailStr
from enum import Enum
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from modules.shared.base_service import BaseService
from security.auth import get_current_user
from security.rbac import require_permission, Permission
from security.audit import audit_log

logger = logging.getLogger(__name__)

# Enums
class CustomerStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"

class LeadStatus(str, Enum):
    NEW = "new"
    QUALIFIED = "qualified"
    PROPOSAL = "proposal"
    NEGOTIATION = "negotiation"
    CLOSED_WON = "closed_won"
    CLOSED_LOST = "closed_lost"

class TicketPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class TicketStatus(str, Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"

# Pydantic Models
class Customer(BaseModel):
    """Customer model"""
    id: Optional[str] = None
    first_name: str = Field(..., description="Customer first name")
    last_name: str = Field(..., description="Customer last name")
    email: EmailStr = Field(..., description="Customer email")
    phone: Optional[str] = None
    company: Optional[str] = None
    address: Optional[str] = None
    status: CustomerStatus = Field(default=CustomerStatus.ACTIVE)
    tags: List[str] = Field(default_factory=list)
    notes: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    last_contact: Optional[datetime] = None

class CustomerUpdate(BaseModel):
    """Customer update model"""
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    company: Optional[str] = None
    address: Optional[str] = None
    status: Optional[CustomerStatus] = None
    tags: Optional[List[str]] = None
    notes: Optional[str] = None

class Lead(BaseModel):
    """Sales lead model"""
    id: Optional[str] = None
    first_name: str = Field(..., description="Lead first name")
    last_name: str = Field(..., description="Lead last name")
    email: EmailStr = Field(..., description="Lead email")
    phone: Optional[str] = None
    company: Optional[str] = None
    source: str = Field(..., description="Lead source (website, referral, etc.)")
    status: LeadStatus = Field(default=LeadStatus.NEW)
    estimated_value: Optional[float] = Field(None, ge=0)
    probability: int = Field(default=10, ge=0, le=100, description="Probability percentage")
    assigned_to: Optional[str] = None
    notes: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class SupportTicket(BaseModel):
    """Support ticket model"""
    id: Optional[str] = None
    customer_id: str = Field(..., description="Customer ID")
    title: str = Field(..., description="Ticket title")
    description: str = Field(..., description="Issue description")
    priority: TicketPriority = Field(default=TicketPriority.MEDIUM)
    status: TicketStatus = Field(default=TicketStatus.OPEN)
    category: str = Field(..., description="Issue category")
    assigned_to: Optional[str] = None
    resolution: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None

class Interaction(BaseModel):
    """Customer interaction model"""
    id: Optional[str] = None
    customer_id: str = Field(..., description="Customer ID")
    interaction_type: str = Field(..., description="Type of interaction")
    subject: str = Field(..., description="Interaction subject")
    notes: str = Field(..., description="Interaction notes")
    user_id: str = Field(..., description="User who logged the interaction")
    created_at: Optional[datetime] = None

class CRMService(BaseService):
    """CRM microservice"""
    
    def __init__(self):
        super().__init__(
            service_name="CRM",
            service_version="1.0.0",
            port=8002
        )
        
        # In-memory storage (replace with database in production)
        self.customers: Dict[str, Customer] = {}
        self.leads: Dict[str, Lead] = {}
        self.tickets: Dict[str, SupportTicket] = {}
        self.interactions: Dict[str, Interaction] = {}
        
        self._setup_routes()
        self._initialize_sample_data()
    
    def _get_service_capabilities(self) -> List[str]:
        """Get CRM service capabilities"""
        return super()._get_service_capabilities() + [
            "customer_management",
            "lead_management",
            "sales_pipeline",
            "support_tickets",
            "customer_interactions",
            "crm_analytics"
        ]
    
    def _get_service_dependencies(self) -> List[str]:
        """Get service dependencies"""
        return ["integrations_service", "agent_orchestration_service"]
    
    def _setup_routes(self):
        """Setup CRM-specific routes"""
        
        # Customer Management Routes
        @self.app.get("/customers", tags=["crm"])
        async def list_customers(
            status: Optional[CustomerStatus] = Query(None, description="Filter by status"),
            search: Optional[str] = Query(None, description="Search by name or email"),
            current_user: dict = Depends(get_current_user)
        ):
            """List customers"""
            if not require_permission(current_user, Permission.CRM_READ):
                raise HTTPException(status_code=403, detail="CRM read permission required")
            
            customers = list(self.customers.values())
            
            # Apply filters
            if status:
                customers = [c for c in customers if c.status == status]
            
            if search:
                search_lower = search.lower()
                customers = [
                    c for c in customers 
                    if search_lower in c.first_name.lower() or 
                       search_lower in c.last_name.lower() or
                       search_lower in c.email.lower()
                ]
            
            await audit_log(
                action="customers_list",
                resource="customers",
                user_id=current_user.get("user_id"),
                details={"filter_status": status, "search_term": search}
            )
            
            return {
                "customers": customers,
                "total_count": len(customers),
                "active_count": len([c for c in self.customers.values() if c.status == CustomerStatus.ACTIVE])
            }
        
        @self.app.post("/customers", tags=["crm"])
        async def create_customer(
            customer: Customer,
            current_user: dict = Depends(get_current_user)
        ):
            """Create new customer"""
            if not require_permission(current_user, Permission.CRM_WRITE):
                raise HTTPException(status_code=403, detail="CRM write permission required")
            
            # Check for duplicate email
            for existing in self.customers.values():
                if existing.email == customer.email:
                    raise HTTPException(status_code=400, detail="Customer with this email already exists")
            
            customer.id = f"cust_{len(self.customers) + 1:06d}"
            customer.created_at = datetime.now()
            customer.updated_at = datetime.now()
            
            self.customers[customer.id] = customer
            
            await audit_log(
                action="customer_create",
                resource="customers",
                user_id=current_user.get("user_id"),
                details={"customer_id": customer.id, "email": customer.email}
            )
            
            return {"success": True, "customer": customer}
        
        @self.app.get("/customers/{customer_id}", tags=["crm"])
        async def get_customer(
            customer_id: str,
            current_user: dict = Depends(get_current_user)
        ):
            """Get specific customer"""
            if not require_permission(current_user, Permission.CRM_READ):
                raise HTTPException(status_code=403, detail="CRM read permission required")
            
            if customer_id not in self.customers:
                raise HTTPException(status_code=404, detail="Customer not found")
            
            customer = self.customers[customer_id]
            
            # Get related data
            customer_interactions = [i for i in self.interactions.values() if i.customer_id == customer_id]
            customer_tickets = [t for t in self.tickets.values() if t.customer_id == customer_id]
            
            return {
                "customer": customer,
                "interactions": customer_interactions,
                "support_tickets": customer_tickets,
                "summary": {
                    "total_interactions": len(customer_interactions),
                    "open_tickets": len([t for t in customer_tickets if t.status in [TicketStatus.OPEN, TicketStatus.IN_PROGRESS]])
                }
            }
        
        @self.app.put("/customers/{customer_id}", tags=["crm"])
        async def update_customer(
            customer_id: str,
            update: CustomerUpdate,
            current_user: dict = Depends(get_current_user)
        ):
            """Update customer"""
            if not require_permission(current_user, Permission.CRM_WRITE):
                raise HTTPException(status_code=403, detail="CRM write permission required")
            
            if customer_id not in self.customers:
                raise HTTPException(status_code=404, detail="Customer not found")
            
            customer = self.customers[customer_id]
            
            # Update fields
            update_data = update.dict(exclude_unset=True)
            for field, value in update_data.items():
                setattr(customer, field, value)
            
            customer.updated_at = datetime.now()
            
            await audit_log(
                action="customer_update",
                resource="customers",
                user_id=current_user.get("user_id"),
                details={"customer_id": customer_id, "updates": update_data}
            )
            
            return {"success": True, "customer": customer}
        
        # Lead Management Routes
        @self.app.get("/leads", tags=["crm"])
        async def list_leads(
            status: Optional[LeadStatus] = Query(None, description="Filter by status"),
            assigned_to: Optional[str] = Query(None, description="Filter by assigned user"),
            current_user: dict = Depends(get_current_user)
        ):
            """List sales leads"""
            if not require_permission(current_user, Permission.SALES_READ):
                raise HTTPException(status_code=403, detail="Sales read permission required")
            
            leads = list(self.leads.values())
            
            if status:
                leads = [l for l in leads if l.status == status]
            
            if assigned_to:
                leads = [l for l in leads if l.assigned_to == assigned_to]
            
            return {
                "leads": leads,
                "total_count": len(leads),
                "pipeline_value": sum(l.estimated_value or 0 for l in leads if l.status not in [LeadStatus.CLOSED_LOST])
            }
        
        @self.app.post("/leads", tags=["crm"])
        async def create_lead(
            lead: Lead,
            current_user: dict = Depends(get_current_user)
        ):
            """Create new lead"""
            if not require_permission(current_user, Permission.SALES_WRITE):
                raise HTTPException(status_code=403, detail="Sales write permission required")
            
            lead.id = f"lead_{len(self.leads) + 1:06d}"
            lead.created_at = datetime.now()
            lead.updated_at = datetime.now()
            
            self.leads[lead.id] = lead
            
            await audit_log(
                action="lead_create",
                resource="leads",
                user_id=current_user.get("user_id"),
                details={"lead_id": lead.id, "email": lead.email, "source": lead.source}
            )
            
            return {"success": True, "lead": lead}
        
        @self.app.put("/leads/{lead_id}/convert", tags=["crm"])
        async def convert_lead_to_customer(
            lead_id: str,
            current_user: dict = Depends(get_current_user)
        ):
            """Convert lead to customer"""
            if not require_permission(current_user, Permission.SALES_WRITE):
                raise HTTPException(status_code=403, detail="Sales write permission required")
            
            if lead_id not in self.leads:
                raise HTTPException(status_code=404, detail="Lead not found")
            
            lead = self.leads[lead_id]
            
            # Create customer from lead
            customer = Customer(
                first_name=lead.first_name,
                last_name=lead.last_name,
                email=lead.email,
                phone=lead.phone,
                company=lead.company,
                notes=f"Converted from lead {lead_id}. {lead.notes or ''}"
            )
            
            customer.id = f"cust_{len(self.customers) + 1:06d}"
            customer.created_at = datetime.now()
            customer.updated_at = datetime.now()
            
            self.customers[customer.id] = customer
            
            # Update lead status
            lead.status = LeadStatus.CLOSED_WON
            lead.updated_at = datetime.now()
            
            await audit_log(
                action="lead_convert",
                resource="leads",
                user_id=current_user.get("user_id"),
                details={"lead_id": lead_id, "customer_id": customer.id}
            )
            
            return {"success": True, "customer": customer, "lead": lead}
        
        # Support Ticket Routes
        @self.app.get("/tickets", tags=["crm"])
        async def list_tickets(
            status: Optional[TicketStatus] = Query(None, description="Filter by status"),
            priority: Optional[TicketPriority] = Query(None, description="Filter by priority"),
            customer_id: Optional[str] = Query(None, description="Filter by customer"),
            current_user: dict = Depends(get_current_user)
        ):
            """List support tickets"""
            if not require_permission(current_user, Permission.SUPPORT_READ):
                raise HTTPException(status_code=403, detail="Support read permission required")
            
            tickets = list(self.tickets.values())
            
            if status:
                tickets = [t for t in tickets if t.status == status]
            
            if priority:
                tickets = [t for t in tickets if t.priority == priority]
            
            if customer_id:
                tickets = [t for t in tickets if t.customer_id == customer_id]
            
            return {
                "tickets": tickets,
                "total_count": len(tickets),
                "open_count": len([t for t in self.tickets.values() if t.status in [TicketStatus.OPEN, TicketStatus.IN_PROGRESS]]),
                "critical_count": len([t for t in self.tickets.values() if t.priority == TicketPriority.CRITICAL])
            }
        
        @self.app.post("/tickets", tags=["crm"])
        async def create_ticket(
            ticket: SupportTicket,
            current_user: dict = Depends(get_current_user)
        ):
            """Create support ticket"""
            if not require_permission(current_user, Permission.SUPPORT_WRITE):
                raise HTTPException(status_code=403, detail="Support write permission required")
            
            # Verify customer exists
            if ticket.customer_id not in self.customers:
                raise HTTPException(status_code=400, detail="Customer not found")
            
            ticket.id = f"tick_{len(self.tickets) + 1:06d}"
            ticket.created_at = datetime.now()
            ticket.updated_at = datetime.now()
            
            self.tickets[ticket.id] = ticket
            
            await audit_log(
                action="ticket_create",
                resource="tickets",
                user_id=current_user.get("user_id"),
                details={"ticket_id": ticket.id, "customer_id": ticket.customer_id, "priority": ticket.priority}
            )
            
            return {"success": True, "ticket": ticket}
        
        # Customer Interaction Routes
        @self.app.post("/interactions", tags=["crm"])
        async def log_interaction(
            interaction: Interaction,
            current_user: dict = Depends(get_current_user)
        ):
            """Log customer interaction"""
            if not require_permission(current_user, Permission.CRM_WRITE):
                raise HTTPException(status_code=403, detail="CRM write permission required")
            
            # Verify customer exists
            if interaction.customer_id not in self.customers:
                raise HTTPException(status_code=400, detail="Customer not found")
            
            interaction.id = f"int_{len(self.interactions) + 1:06d}"
            interaction.user_id = current_user.get("user_id")
            interaction.created_at = datetime.now()
            
            self.interactions[interaction.id] = interaction
            
            # Update customer last contact
            self.customers[interaction.customer_id].last_contact = datetime.now()
            
            await audit_log(
                action="interaction_log",
                resource="interactions",
                user_id=current_user.get("user_id"),
                details={"interaction_id": interaction.id, "customer_id": interaction.customer_id}
            )
            
            return {"success": True, "interaction": interaction}
        
        # Analytics Routes
        @self.app.get("/analytics/dashboard", tags=["crm"])
        async def crm_dashboard(
            current_user: dict = Depends(get_current_user)
        ):
            """Get CRM analytics dashboard"""
            if not require_permission(current_user, Permission.CRM_READ):
                raise HTTPException(status_code=403, detail="CRM read permission required")
            
            # Customer metrics
            total_customers = len(self.customers)
            active_customers = len([c for c in self.customers.values() if c.status == CustomerStatus.ACTIVE])
            
            # Lead metrics
            total_leads = len(self.leads)
            qualified_leads = len([l for l in self.leads.values() if l.status == LeadStatus.QUALIFIED])
            pipeline_value = sum(l.estimated_value or 0 for l in self.leads.values() if l.status not in [LeadStatus.CLOSED_LOST])
            
            # Support metrics
            total_tickets = len(self.tickets)
            open_tickets = len([t for t in self.tickets.values() if t.status in [TicketStatus.OPEN, TicketStatus.IN_PROGRESS]])
            critical_tickets = len([t for t in self.tickets.values() if t.priority == TicketPriority.CRITICAL])
            
            return {
                "customers": {
                    "total": total_customers,
                    "active": active_customers,
                    "inactive": total_customers - active_customers
                },
                "leads": {
                    "total": total_leads,
                    "qualified": qualified_leads,
                    "pipeline_value": pipeline_value
                },
                "support": {
                    "total_tickets": total_tickets,
                    "open_tickets": open_tickets,
                    "critical_tickets": critical_tickets
                },
                "recent_activity": {
                    "new_customers_today": len([
                        c for c in self.customers.values() 
                        if c.created_at and c.created_at.date() == datetime.now().date()
                    ]),
                    "new_leads_today": len([
                        l for l in self.leads.values()
                        if l.created_at and l.created_at.date() == datetime.now().date()
                    ])
                }
            }
    
    def _initialize_sample_data(self):
        """Initialize with sample data"""
        # Sample customers
        sample_customers = [
            Customer(
                id="cust_000001",
                first_name="John",
                last_name="Doe",
                email="john.doe@example.com",
                phone="+1-555-0101",
                company="Acme Corp",
                address="123 Business St, City, State 12345",
                status=CustomerStatus.ACTIVE,
                tags=["enterprise", "priority"],
                created_at=datetime.now() - timedelta(days=30),
                updated_at=datetime.now()
            ),
            Customer(
                id="cust_000002",
                first_name="Jane",
                last_name="Smith",
                email="jane.smith@techstart.com",
                phone="+1-555-0102",
                company="TechStart Inc",
                status=CustomerStatus.ACTIVE,
                tags=["startup"],
                created_at=datetime.now() - timedelta(days=15),
                updated_at=datetime.now()
            )
        ]
        
        for customer in sample_customers:
            self.customers[customer.id] = customer
        
        # Sample leads
        sample_leads = [
            Lead(
                id="lead_000001",
                first_name="Bob",
                last_name="Johnson",
                email="bob.johnson@prospect.com",
                company="Prospect LLC",
                source="website",
                status=LeadStatus.QUALIFIED,
                estimated_value=50000.0,
                probability=75,
                created_at=datetime.now() - timedelta(days=5)
            )
        ]
        
        for lead in sample_leads:
            self.leads[lead.id] = lead
        
        logger.info("✅ CRM service initialized with sample data")

# Create service instance
crm_service = CRMService()

if __name__ == "__main__":
    crm_service.run(debug=True)

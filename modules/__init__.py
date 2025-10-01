"""
BHIV Core Modular Architecture
=============================

Microservices-based architecture with independent deployable modules:

1. Logistics Service - Supply chain and inventory management
2. CRM Service - Customer relationship management  
3. Agent Orchestration Service - AI agent coordination
4. LLM Query Service - Language model interactions
5. Integrations Service - External API integrations

Each module is independently deployable with its own:
- FastAPI application
- OpenAPI specification
- Database schema
- Security configuration
- Docker container
"""

__version__ = "2.0.0"
__author__ = "BHIV Core Team"

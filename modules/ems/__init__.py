"""
EMS (Employee Management System) Integration Module
==================================================

Provides integration with Employee Management System for:
- Activity log routing
- AIMS (Alert and Incident Management System) submissions
- Employee alerts and notifications
- Compliance tracking
"""

from .ems_service import EMSService
from .aims_client import AIMSClient
from .employee_alerts import EmployeeAlertManager
from .activity_logger import ActivityLogger

__all__ = [
    'EMSService',
    'AIMSClient', 
    'EmployeeAlertManager',
    'ActivityLogger'
]

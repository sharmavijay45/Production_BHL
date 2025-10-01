"""
BHIV Core Security - Simple Audit Logging
========================================

Simple audit logging for all system activities.
"""

import uuid
import json
from datetime import datetime
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

def audit_log(action: str, user: str = "system", resource: str = "", details: Dict[str, Any] = None):
    """Simple audit logging function"""
    try:
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "user": user,
            "resource": resource,
            "details": details or {},
            "audit_id": str(uuid.uuid4())
        }
        
        logger.info(f"🔍 AUDIT: {action} by {user} on {resource}")
        logger.debug(f"Audit details: {json.dumps(log_entry, indent=2)}")
        
        return log_entry
        
    except Exception as e:
        logger.error(f"❌ Audit logging failed: {e}")
        return None

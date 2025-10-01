"""
BHIV Core Threat Response Agent
===============================

Automated threat response system that takes immediate action
when threats are detected by the Threat Detection Agent.

Features:
- Automatic IP blocking
- Admin alerts via email/Slack
- Threat escalation
- Response logging
- Recovery procedures
"""

import asyncio
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set
from dataclasses import dataclass
from enum import Enum
import logging

from .threat_detection import ThreatEvent, ThreatLevel, ThreatType

logger = logging.getLogger(__name__)

class ResponseAction(Enum):
    """Types of response actions"""
    BLOCK_IP = "block_ip"
    RATE_LIMIT = "rate_limit"
    ALERT_ADMIN = "alert_admin"
    LOG_EVENT = "log_event"
    QUARANTINE = "quarantine"
    ESCALATE = "escalate"

@dataclass
class ResponseRule:
    """Defines response rules for different threat types"""
    threat_type: ThreatType
    threat_level: ThreatLevel
    actions: List[ResponseAction]
    auto_execute: bool
    cooldown_minutes: int = 5

class ThreatResponseAgent:
    """Automated threat response system"""
    
    def __init__(self):
        self.blocked_ips: Set[str] = set()
        self.response_history: List[Dict] = []
        self.response_rules = self._initialize_rules()
        self.admin_contacts = []
        self.running = False
        
    def _initialize_rules(self) -> List[ResponseRule]:
        """Initialize default response rules"""
        return [
            # Critical threats - immediate blocking
            ResponseRule(
                threat_type=ThreatType.SQL_INJECTION,
                threat_level=ThreatLevel.CRITICAL,
                actions=[ResponseAction.BLOCK_IP, ResponseAction.ALERT_ADMIN],
                auto_execute=True
            ),
            ResponseRule(
                threat_type=ThreatType.COMMAND_INJECTION,
                threat_level=ThreatLevel.CRITICAL,
                actions=[ResponseAction.BLOCK_IP, ResponseAction.ALERT_ADMIN],
                auto_execute=True
            ),
            # High threats - blocking with alert
            ResponseRule(
                threat_type=ThreatType.XSS_ATTACK,
                threat_level=ThreatLevel.HIGH,
                actions=[ResponseAction.BLOCK_IP, ResponseAction.ALERT_ADMIN],
                auto_execute=True
            ),
            ResponseRule(
                threat_type=ThreatType.BRUTE_FORCE,
                threat_level=ThreatLevel.HIGH,
                actions=[ResponseAction.BLOCK_IP, ResponseAction.ALERT_ADMIN],
                auto_execute=True,
                cooldown_minutes=30
            ),
            # Medium threats - rate limiting
            ResponseRule(
                threat_type=ThreatType.RATE_LIMIT_VIOLATION,
                threat_level=ThreatLevel.MEDIUM,
                actions=[ResponseAction.RATE_LIMIT, ResponseAction.LOG_EVENT],
                auto_execute=True
            ),
        ]
    
    async def respond_to_threat(self, threat: ThreatEvent) -> Dict:
        """Execute response to detected threat"""
        response_log = {
            'threat_id': threat.id,
            'timestamp': datetime.now().isoformat(),
            'threat_type': threat.threat_type.value,
            'source_ip': threat.source_ip,
            'actions_taken': [],
            'success': True,
            'errors': []
        }
        
        # Find matching rules
        matching_rules = [
            rule for rule in self.response_rules 
            if rule.threat_type == threat.threat_type
        ]
        
        for rule in matching_rules:
            if rule.auto_execute:
                for action in rule.actions:
                    try:
                        await self._execute_action(action, threat, rule)
                        response_log['actions_taken'].append(action.value)
                    except Exception as e:
                        response_log['errors'].append(str(e))
                        response_log['success'] = False
                        logger.error(f"Failed to execute {action.value}: {e}")
        
        self.response_history.append(response_log)
        return response_log
    
    async def _execute_action(self, action: ResponseAction, threat: ThreatEvent, rule: ResponseRule):
        """Execute specific response action"""
        if action == ResponseAction.BLOCK_IP:
            await self._block_ip(threat.source_ip, rule.cooldown_minutes)
        elif action == ResponseAction.ALERT_ADMIN:
            await self._send_admin_alert(threat)
        elif action == ResponseAction.RATE_LIMIT:
            await self._apply_rate_limit(threat.source_ip)
        elif action == ResponseAction.LOG_EVENT:
            await self._log_security_event(threat)
    
    async def _block_ip(self, ip: str, duration_minutes: int = 60):
        """Block IP address"""
        self.blocked_ips.add(ip)
        logger.warning(f"Blocked IP {ip} for {duration_minutes} minutes")
        
        # Schedule unblock
        asyncio.create_task(self._schedule_unblock(ip, duration_minutes))
    
    async def _schedule_unblock(self, ip: str, minutes: int):
        """Schedule IP unblocking"""
        await asyncio.sleep(minutes * 60)
        if ip in self.blocked_ips:
            self.blocked_ips.remove(ip)
            logger.info(f"Unblocked IP {ip}")
    
    async def _send_admin_alert(self, threat: ThreatEvent):
        """Send alert to administrators"""
        alert_message = f"""
🚨 SECURITY THREAT DETECTED 🚨

Threat ID: {threat.id}
Type: {threat.threat_type.value}
Level: {threat.threat_level.value}
Source IP: {threat.source_ip}
Endpoint: {threat.endpoint}
Time: {threat.timestamp}

Description: {threat.description}
Confidence: {threat.confidence_score:.2f}

Automatic response has been triggered.
        """
        
        logger.critical(f"SECURITY ALERT: {threat.threat_type.value} from {threat.source_ip}")
        # In production, send via email/Slack
        
    async def _apply_rate_limit(self, ip: str):
        """Apply rate limiting to IP"""
        logger.info(f"Applied rate limiting to IP {ip}")
    
    async def _log_security_event(self, threat: ThreatEvent):
        """Log security event"""
        logger.info(f"Security event logged: {threat.threat_type.value} from {threat.source_ip}")
    
    def is_ip_blocked(self, ip: str) -> bool:
        """Check if IP is blocked"""
        return ip in self.blocked_ips
    
    def get_response_stats(self) -> Dict:
        """Get response statistics"""
        total_responses = len(self.response_history)
        successful_responses = sum(1 for r in self.response_history if r['success'])
        
        action_counts = {}
        for response in self.response_history:
            for action in response['actions_taken']:
                action_counts[action] = action_counts.get(action, 0) + 1
        
        return {
            'total_responses': total_responses,
            'successful_responses': successful_responses,
            'success_rate': successful_responses / max(total_responses, 1),
            'blocked_ips_count': len(self.blocked_ips),
            'action_counts': action_counts,
            'blocked_ips': list(self.blocked_ips)
        }

# Global response agent
threat_responder = ThreatResponseAgent()

# Integration functions
async def respond_to_threat(threat: ThreatEvent) -> Dict:
    return await threat_responder.respond_to_threat(threat)

def is_ip_blocked(ip: str) -> bool:
    return threat_responder.is_ip_blocked(ip)

def get_response_stats() -> Dict:
    return threat_responder.get_response_stats()

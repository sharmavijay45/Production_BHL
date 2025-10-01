"""
BHIV Core Proactive Monitoring Agent
===================================

Real-time threat monitoring and analysis system that integrates
threat detection and response agents for comprehensive security.

Features:
- Real-time threat monitoring
- Automated threat analysis
- Intelligent response coordination
- Security metrics collection
- Alert management
"""

import asyncio
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass
import logging

from .threat_detection import ThreatDetectionAgent, ThreatEvent, ThreatLevel
from .threat_response import ThreatResponseAgent, ResponseAction

logger = logging.getLogger(__name__)

@dataclass
class SecurityMetrics:
    """Security monitoring metrics"""
    timestamp: datetime
    total_requests: int
    threats_detected: int
    threats_blocked: int
    unique_ips: int
    blocked_ips: int
    response_time_ms: float
    system_health: str

class ProactiveMonitor:
    """Proactive security monitoring system"""
    
    def __init__(self):
        self.detection_agent = ThreatDetectionAgent()
        self.response_agent = ThreatResponseAgent()
        self.monitoring_active = False
        self.metrics_history: List[SecurityMetrics] = []
        self.alert_thresholds = {
            'threat_rate_per_minute': 10,
            'blocked_ips_threshold': 50,
            'response_time_threshold_ms': 1000
        }
    
    async def start_monitoring(self):
        """Start proactive monitoring"""
        self.monitoring_active = True
        self.detection_agent.start_monitoring()
        
        logger.info("🛡️ Proactive Security Monitor started")
        
        # Start monitoring tasks
        asyncio.create_task(self._monitor_threats())
        asyncio.create_task(self._collect_metrics())
        asyncio.create_task(self._health_check())
    
    async def stop_monitoring(self):
        """Stop proactive monitoring"""
        self.monitoring_active = False
        self.detection_agent.stop_monitoring()
        logger.info("🛡️ Proactive Security Monitor stopped")
    
    async def _monitor_threats(self):
        """Continuously monitor for threats"""
        while self.monitoring_active:
            try:
                # Check for DDoS attacks
                ddos_threats = self.detection_agent.detect_ddos()
                for threat in ddos_threats:
                    await self._handle_threat(threat)
                
                # Monitor recent threats for patterns
                recent_threats = self.detection_agent.get_recent_threats(50)
                await self._analyze_threat_patterns(recent_threats)
                
                await asyncio.sleep(10)  # Check every 10 seconds
                
            except Exception as e:
                logger.error(f"Error in threat monitoring: {e}")
                await asyncio.sleep(30)
    
    async def _collect_metrics(self):
        """Collect security metrics"""
        while self.monitoring_active:
            try:
                start_time = time.time()
                
                # Collect current metrics
                threat_summary = self.detection_agent.get_threat_summary(hours=1)
                response_stats = self.response_agent.get_response_stats()
                
                metrics = SecurityMetrics(
                    timestamp=datetime.now(),
                    total_requests=sum(self.detection_agent.ip_tracker.get_request_rate(ip) 
                                     for ip in self.detection_agent.ip_tracker.ip_requests.keys()),
                    threats_detected=threat_summary.get('total_threats', 0),
                    threats_blocked=response_stats.get('successful_responses', 0),
                    unique_ips=len(self.detection_agent.ip_tracker.ip_requests),
                    blocked_ips=response_stats.get('blocked_ips_count', 0),
                    response_time_ms=(time.time() - start_time) * 1000,
                    system_health=self._calculate_system_health()
                )
                
                self.metrics_history.append(metrics)
                
                # Keep only last 24 hours of metrics
                cutoff = datetime.now() - timedelta(hours=24)
                self.metrics_history = [m for m in self.metrics_history if m.timestamp > cutoff]
                
                await asyncio.sleep(60)  # Collect every minute
                
            except Exception as e:
                logger.error(f"Error collecting metrics: {e}")
                await asyncio.sleep(60)
    
    async def _health_check(self):
        """Perform system health checks"""
        while self.monitoring_active:
            try:
                # Check alert thresholds
                if self.metrics_history:
                    latest = self.metrics_history[-1]
                    
                    # Check threat rate
                    recent_metrics = [m for m in self.metrics_history 
                                    if m.timestamp > datetime.now() - timedelta(minutes=5)]
                    
                    if recent_metrics:
                        avg_threats = sum(m.threats_detected for m in recent_metrics) / len(recent_metrics)
                        if avg_threats > self.alert_thresholds['threat_rate_per_minute']:
                            await self._send_health_alert("High threat detection rate", 
                                                        f"Average: {avg_threats:.1f} threats/min")
                    
                    # Check blocked IPs
                    if latest.blocked_ips > self.alert_thresholds['blocked_ips_threshold']:
                        await self._send_health_alert("High number of blocked IPs", 
                                                    f"Currently blocked: {latest.blocked_ips}")
                
                await asyncio.sleep(300)  # Check every 5 minutes
                
            except Exception as e:
                logger.error(f"Error in health check: {e}")
                await asyncio.sleep(300)
    
    async def _handle_threat(self, threat: ThreatEvent):
        """Handle detected threat"""
        logger.warning(f"🚨 Threat detected: {threat.threat_type.value} from {threat.source_ip}")
        
        # Execute automated response
        response_result = await self.response_agent.respond_to_threat(threat)
        
        # Log the response
        logger.info(f"✅ Response executed for threat {threat.id}: {response_result['actions_taken']}")
    
    async def _analyze_threat_patterns(self, recent_threats: List[Dict]):
        """Analyze patterns in recent threats"""
        if len(recent_threats) < 5:
            return
        
        # Analyze IP patterns
        ip_counts = {}
        for threat_dict in recent_threats:
            ip = threat_dict.get('source_ip')
            ip_counts[ip] = ip_counts.get(ip, 0) + 1
        
        # Check for coordinated attacks
        suspicious_ips = [ip for ip, count in ip_counts.items() if count >= 3]
        for ip in suspicious_ips:
            if ip not in self.response_agent.blocked_ips:
                logger.warning(f"🔍 Suspicious IP pattern detected: {ip} ({ip_counts[ip]} threats)")
                # Could trigger additional investigation or blocking
    
    def _calculate_system_health(self) -> str:
        """Calculate overall system health"""
        if not self.metrics_history:
            return "unknown"
        
        recent_metrics = [m for m in self.metrics_history 
                         if m.timestamp > datetime.now() - timedelta(minutes=10)]
        
        if not recent_metrics:
            return "unknown"
        
        # Calculate health score based on various factors
        avg_response_time = sum(m.response_time_ms for m in recent_metrics) / len(recent_metrics)
        total_threats = sum(m.threats_detected for m in recent_metrics)
        total_blocked = sum(m.threats_blocked for m in recent_metrics)
        
        health_score = 100
        
        # Penalize high response times
        if avg_response_time > 1000:
            health_score -= 20
        elif avg_response_time > 500:
            health_score -= 10
        
        # Penalize high threat rates
        if total_threats > 50:
            health_score -= 30
        elif total_threats > 20:
            health_score -= 15
        
        # Reward successful blocking
        if total_threats > 0:
            block_rate = total_blocked / total_threats
            if block_rate > 0.9:
                health_score += 10
            elif block_rate < 0.5:
                health_score -= 20
        
        if health_score >= 90:
            return "excellent"
        elif health_score >= 75:
            return "good"
        elif health_score >= 50:
            return "fair"
        else:
            return "poor"
    
    async def _send_health_alert(self, alert_type: str, details: str):
        """Send system health alert"""
        logger.critical(f"🚨 HEALTH ALERT: {alert_type} - {details}")
        # In production, send to monitoring systems
    
    def get_security_dashboard(self) -> Dict:
        """Get comprehensive security dashboard data"""
        if not self.metrics_history:
            return {"status": "no_data"}
        
        latest = self.metrics_history[-1]
        
        # Calculate trends
        hour_ago = datetime.now() - timedelta(hours=1)
        recent_metrics = [m for m in self.metrics_history if m.timestamp > hour_ago]
        
        threat_trend = []
        response_trend = []
        for m in recent_metrics[-12:]:  # Last 12 data points
            threat_trend.append(m.threats_detected)
            response_trend.append(m.threats_blocked)
        
        return {
            "status": "active",
            "timestamp": latest.timestamp.isoformat(),
            "current_metrics": {
                "total_requests": latest.total_requests,
                "threats_detected": latest.threats_detected,
                "threats_blocked": latest.threats_blocked,
                "unique_ips": latest.unique_ips,
                "blocked_ips": latest.blocked_ips,
                "response_time_ms": latest.response_time_ms,
                "system_health": latest.system_health
            },
            "trends": {
                "threat_detection": threat_trend,
                "threat_response": response_trend
            },
            "alerts": {
                "high_threat_rate": latest.threats_detected > self.alert_thresholds['threat_rate_per_minute'],
                "high_blocked_ips": latest.blocked_ips > self.alert_thresholds['blocked_ips_threshold'],
                "slow_response": latest.response_time_ms > self.alert_thresholds['response_time_threshold_ms']
            },
            "agent_status": {
                "detection_agent": self.detection_agent.running,
                "response_agent": self.response_agent.running,
                "monitor_active": self.monitoring_active
            }
        }
    
    async def process_request(self, ip: str, method: str, endpoint: str, 
                            headers: Dict[str, str], payload: Optional[str] = None) -> bool:
        """Process incoming request through security pipeline"""
        # Check if IP is blocked
        if self.response_agent.is_ip_blocked(ip):
            logger.warning(f"🚫 Blocked request from {ip}")
            return False
        
        # Analyze for threats
        threats = self.detection_agent.analyze_request(ip, method, endpoint, headers, payload)
        
        # Handle any detected threats
        for threat in threats:
            await self._handle_threat(threat)
            
            # If critical threat, block immediately
            if threat.threat_level == ThreatLevel.CRITICAL:
                return False
        
        return True

# Global monitor instance
security_monitor = ProactiveMonitor()

# Integration functions
async def start_security_monitoring():
    """Start security monitoring"""
    await security_monitor.start_monitoring()

async def stop_security_monitoring():
    """Stop security monitoring"""
    await security_monitor.stop_monitoring()

async def process_request(ip: str, method: str, endpoint: str, 
                         headers: Dict[str, str], payload: Optional[str] = None) -> bool:
    """Process request through security pipeline"""
    return await security_monitor.process_request(ip, method, endpoint, headers, payload)

def get_security_dashboard() -> Dict:
    """Get security dashboard data"""
    return security_monitor.get_security_dashboard()

if __name__ == "__main__":
    # Example usage
    async def main():
        await start_security_monitoring()
        
        # Simulate some requests
        await process_request("192.168.1.100", "POST", "/api/login", 
                            {"User-Agent": "Mozilla/5.0"}, "username=admin&password=test")
        
        # Get dashboard
        dashboard = get_security_dashboard()
        print(json.dumps(dashboard, indent=2))
        
        await stop_security_monitoring()
    
    asyncio.run(main())

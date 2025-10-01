"""
BHIV Core Observability - Alerting System
========================================

Comprehensive alerting system for BHIV Core with multiple notification channels.
Integrates with Slack, email, and webhook notifications.
"""

import asyncio
import json
import logging
import smtplib
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import aiohttp
import ssl

logger = logging.getLogger(__name__)

class AlertSeverity(Enum):
    """Alert severity levels"""
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"

class AlertStatus(Enum):
    """Alert status"""
    FIRING = "firing"
    RESOLVED = "resolved"

@dataclass
class Alert:
    """Alert data structure"""
    name: str
    severity: AlertSeverity
    status: AlertStatus
    message: str
    service: str
    timestamp: datetime
    labels: Dict[str, str]
    annotations: Dict[str, str]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert alert to dictionary"""
        return {
            **asdict(self),
            'severity': self.severity.value,
            'status': self.status.value,
            'timestamp': self.timestamp.isoformat()
        }

class AlertManager:
    """BHIV Core alert manager"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.active_alerts: Dict[str, Alert] = {}
        self.alert_history: List[Alert] = []
        self.notification_channels = []
        
        self._setup_notification_channels()
    
    def _setup_notification_channels(self):
        """Setup notification channels"""
        if self.config.get('slack', {}).get('enabled'):
            self.notification_channels.append(SlackNotifier(self.config['slack']))
        
        if self.config.get('email', {}).get('enabled'):
            self.notification_channels.append(EmailNotifier(self.config['email']))
        
        if self.config.get('webhook', {}).get('enabled'):
            self.notification_channels.append(WebhookNotifier(self.config['webhook']))
        
        logger.info(f"✅ Setup {len(self.notification_channels)} notification channels")
    
    async def send_alert(self, alert: Alert):
        """Send alert through all configured channels"""
        try:
            # Store alert
            alert_key = f"{alert.service}:{alert.name}"
            
            if alert.status == AlertStatus.FIRING:
                self.active_alerts[alert_key] = alert
            elif alert.status == AlertStatus.RESOLVED:
                self.active_alerts.pop(alert_key, None)
            
            self.alert_history.append(alert)
            
            # Send notifications
            tasks = []
            for channel in self.notification_channels:
                if self._should_notify(channel, alert):
                    tasks.append(channel.send_notification(alert))
            
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
            
            logger.info(f"📢 Alert sent: {alert.name} - {alert.severity.value}")
            
        except Exception as e:
            logger.error(f"❌ Failed to send alert: {e}")
    
    def _should_notify(self, channel, alert: Alert) -> bool:
        """Check if channel should be notified for this alert"""
        channel_config = getattr(channel, 'config', {})
        min_severity = channel_config.get('min_severity', 'info')
        
        severity_levels = {'info': 0, 'warning': 1, 'critical': 2}
        return severity_levels.get(alert.severity.value, 0) >= severity_levels.get(min_severity, 0)
    
    def get_active_alerts(self) -> List[Alert]:
        """Get all active alerts"""
        return list(self.active_alerts.values())
    
    def get_alert_history(self, hours: int = 24) -> List[Alert]:
        """Get alert history for specified hours"""
        cutoff = datetime.now() - timedelta(hours=hours)
        return [alert for alert in self.alert_history if alert.timestamp >= cutoff]

class SlackNotifier:
    """Slack notification channel"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.webhook_url = config.get('webhook_url')
        self.channel = config.get('channel', '#alerts')
        self.username = config.get('username', 'BHIV Core')
    
    async def send_notification(self, alert: Alert):
        """Send Slack notification"""
        try:
            color = self._get_color(alert.severity)
            emoji = self._get_emoji(alert.severity, alert.status)
            
            payload = {
                "channel": self.channel,
                "username": self.username,
                "attachments": [{
                    "color": color,
                    "title": f"{emoji} {alert.name}",
                    "text": alert.message,
                    "fields": [
                        {"title": "Service", "value": alert.service, "short": True},
                        {"title": "Severity", "value": alert.severity.value.upper(), "short": True},
                        {"title": "Status", "value": alert.status.value.upper(), "short": True},
                        {"title": "Time", "value": alert.timestamp.strftime("%Y-%m-%d %H:%M:%S"), "short": True}
                    ],
                    "footer": "BHIV Core Monitoring",
                    "ts": int(alert.timestamp.timestamp())
                }]
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(self.webhook_url, json=payload) as response:
                    if response.status == 200:
                        logger.info("✅ Slack notification sent")
                    else:
                        logger.error(f"❌ Slack notification failed: {response.status}")
        
        except Exception as e:
            logger.error(f"❌ Slack notification error: {e}")
    
    def _get_color(self, severity: AlertSeverity) -> str:
        """Get color for alert severity"""
        colors = {
            AlertSeverity.CRITICAL: "danger",
            AlertSeverity.WARNING: "warning",
            AlertSeverity.INFO: "good"
        }
        return colors.get(severity, "good")
    
    def _get_emoji(self, severity: AlertSeverity, status: AlertStatus) -> str:
        """Get emoji for alert"""
        if status == AlertStatus.RESOLVED:
            return "✅"
        
        emojis = {
            AlertSeverity.CRITICAL: "🚨",
            AlertSeverity.WARNING: "⚠️",
            AlertSeverity.INFO: "ℹ️"
        }
        return emojis.get(severity, "📢")

class EmailNotifier:
    """Email notification channel"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.smtp_server = config.get('smtp_server')
        self.smtp_port = config.get('smtp_port', 587)
        self.username = config.get('username')
        self.password = config.get('password')
        self.from_email = config.get('from_email')
        self.to_emails = config.get('to_emails', [])
    
    async def send_notification(self, alert: Alert):
        """Send email notification"""
        try:
            subject = f"[BHIV Core] {alert.severity.value.upper()}: {alert.name}"
            
            html_body = self._create_html_body(alert)
            text_body = self._create_text_body(alert)
            
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.from_email
            msg['To'] = ', '.join(self.to_emails)
            
            msg.attach(MIMEText(text_body, 'plain'))
            msg.attach(MIMEText(html_body, 'html'))
            
            # Send email in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._send_email, msg)
            
            logger.info("✅ Email notification sent")
            
        except Exception as e:
            logger.error(f"❌ Email notification error: {e}")
    
    def _send_email(self, msg):
        """Send email synchronously"""
        context = ssl.create_default_context()
        with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
            server.starttls(context=context)
            server.login(self.username, self.password)
            server.send_message(msg)
    
    def _create_html_body(self, alert: Alert) -> str:
        """Create HTML email body"""
        status_color = "#dc3545" if alert.severity == AlertSeverity.CRITICAL else "#ffc107" if alert.severity == AlertSeverity.WARNING else "#28a745"
        
        return f"""
        <html>
        <body style="font-family: Arial, sans-serif;">
            <div style="background-color: {status_color}; color: white; padding: 20px; border-radius: 5px;">
                <h2>🚨 BHIV Core Alert</h2>
                <h3>{alert.name}</h3>
            </div>
            
            <div style="padding: 20px;">
                <p><strong>Message:</strong> {alert.message}</p>
                <p><strong>Service:</strong> {alert.service}</p>
                <p><strong>Severity:</strong> {alert.severity.value.upper()}</p>
                <p><strong>Status:</strong> {alert.status.value.upper()}</p>
                <p><strong>Time:</strong> {alert.timestamp.strftime("%Y-%m-%d %H:%M:%S UTC")}</p>
                
                <h4>Labels:</h4>
                <ul>
                    {"".join(f"<li><strong>{k}:</strong> {v}</li>" for k, v in alert.labels.items())}
                </ul>
                
                <h4>Annotations:</h4>
                <ul>
                    {"".join(f"<li><strong>{k}:</strong> {v}</li>" for k, v in alert.annotations.items())}
                </ul>
            </div>
            
            <div style="background-color: #f8f9fa; padding: 10px; border-radius: 5px; margin-top: 20px;">
                <small>This alert was generated by BHIV Core Monitoring System</small>
            </div>
        </body>
        </html>
        """
    
    def _create_text_body(self, alert: Alert) -> str:
        """Create plain text email body"""
        return f"""
BHIV Core Alert: {alert.name}

Message: {alert.message}
Service: {alert.service}
Severity: {alert.severity.value.upper()}
Status: {alert.status.value.upper()}
Time: {alert.timestamp.strftime("%Y-%m-%d %H:%M:%S UTC")}

Labels:
{chr(10).join(f"  {k}: {v}" for k, v in alert.labels.items())}

Annotations:
{chr(10).join(f"  {k}: {v}" for k, v in alert.annotations.items())}

---
This alert was generated by BHIV Core Monitoring System
        """

class WebhookNotifier:
    """Generic webhook notification channel"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.webhook_url = config.get('url')
        self.headers = config.get('headers', {})
    
    async def send_notification(self, alert: Alert):
        """Send webhook notification"""
        try:
            payload = {
                "alert": alert.to_dict(),
                "timestamp": datetime.now().isoformat(),
                "source": "bhiv-core"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.webhook_url, 
                    json=payload, 
                    headers=self.headers
                ) as response:
                    if response.status == 200:
                        logger.info("✅ Webhook notification sent")
                    else:
                        logger.error(f"❌ Webhook notification failed: {response.status}")
        
        except Exception as e:
            logger.error(f"❌ Webhook notification error: {e}")

# Global alert manager instance
_alert_manager: Optional[AlertManager] = None

def init_alerting(config: Dict[str, Any]) -> AlertManager:
    """Initialize alerting system"""
    global _alert_manager
    _alert_manager = AlertManager(config)
    return _alert_manager

def get_alert_manager() -> Optional[AlertManager]:
    """Get global alert manager"""
    return _alert_manager

async def send_alert(name: str, severity: AlertSeverity, message: str, 
                    service: str, labels: Dict[str, str] = None, 
                    annotations: Dict[str, str] = None):
    """Send an alert"""
    if _alert_manager:
        alert = Alert(
            name=name,
            severity=severity,
            status=AlertStatus.FIRING,
            message=message,
            service=service,
            timestamp=datetime.now(),
            labels=labels or {},
            annotations=annotations or {}
        )
        await _alert_manager.send_alert(alert)

async def resolve_alert(name: str, service: str, message: str = "Alert resolved"):
    """Resolve an alert"""
    if _alert_manager:
        alert = Alert(
            name=name,
            severity=AlertSeverity.INFO,
            status=AlertStatus.RESOLVED,
            message=message,
            service=service,
            timestamp=datetime.now(),
            labels={},
            annotations={}
        )
        await _alert_manager.send_alert(alert)

# Convenience functions for common alerts
async def alert_service_down(service: str):
    """Alert when service is down"""
    await send_alert(
        name="ServiceDown",
        severity=AlertSeverity.CRITICAL,
        message=f"Service {service} is not responding",
        service=service,
        labels={"alert_type": "availability"}
    )

async def alert_high_error_rate(service: str, error_rate: float):
    """Alert for high error rate"""
    await send_alert(
        name="HighErrorRate",
        severity=AlertSeverity.WARNING,
        message=f"High error rate detected: {error_rate:.2%}",
        service=service,
        labels={"alert_type": "performance"},
        annotations={"error_rate": str(error_rate)}
    )

async def alert_threat_detected(threat_type: str, severity: str, details: str):
    """Alert for threat detection"""
    alert_severity = AlertSeverity.CRITICAL if severity == "high" else AlertSeverity.WARNING
    await send_alert(
        name="ThreatDetected",
        severity=alert_severity,
        message=f"Security threat detected: {threat_type}",
        service="security",
        labels={"alert_type": "security", "threat_type": threat_type},
        annotations={"details": details, "threat_severity": severity}
    )

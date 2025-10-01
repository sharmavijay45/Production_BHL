"""
BHIV Core Threat Detection Agent
===============================

Intelligent threat detection system that monitors API traffic,
detects attack patterns, and identifies security threats in real-time.

Features:
- SQL injection detection
- XSS attack detection
- Brute force attack monitoring
- Anomaly detection
- Rate limiting violations
- Suspicious payload analysis
- IP reputation checking
"""

import re
import json
import time
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
from enum import Enum
import ipaddress
import hashlib
import statistics

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ThreatLevel(Enum):
    """Threat severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class ThreatType(Enum):
    """Types of detected threats"""
    SQL_INJECTION = "sql_injection"
    XSS_ATTACK = "xss_attack"
    BRUTE_FORCE = "brute_force"
    RATE_LIMIT_VIOLATION = "rate_limit_violation"
    SUSPICIOUS_PAYLOAD = "suspicious_payload"
    ANOMALOUS_BEHAVIOR = "anomalous_behavior"
    MALICIOUS_IP = "malicious_ip"
    DIRECTORY_TRAVERSAL = "directory_traversal"
    COMMAND_INJECTION = "command_injection"
    DDOS_ATTEMPT = "ddos_attempt"

@dataclass
class ThreatEvent:
    """Represents a detected threat event"""
    id: str
    timestamp: datetime
    threat_type: ThreatType
    threat_level: ThreatLevel
    source_ip: str
    user_agent: Optional[str]
    endpoint: str
    method: str
    payload: Optional[str]
    description: str
    confidence_score: float
    metadata: Dict
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization"""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        data['threat_type'] = self.threat_type.value
        data['threat_level'] = self.threat_level.value
        return data

class ThreatPatterns:
    """Threat detection patterns and signatures"""
    
    # SQL Injection patterns
    SQL_INJECTION_PATTERNS = [
        r"(\%27)|(\')|(\-\-)|(\%23)|(#)",  # Basic SQL chars
        r"((\%3D)|(=))[^\n]*((\%27)|(\')|(\-\-)|(\%3B)|(;))",  # SQL operators
        r"\w*((\%27)|(\'))((\%6F)|o|(\%4F))((\%72)|r|(\%52))",  # 'or' variations
        r"((\%27)|(\'))union",  # UNION attacks
        r"exec(\s|\+)+(s|x)p\w+",  # Stored procedures
        r"select.*from.*information_schema",  # Information schema
        r"insert\s+into.*values",  # INSERT attacks
        r"drop\s+(table|database)",  # DROP attacks
        r"update.*set.*=",  # UPDATE attacks
        r"delete\s+from",  # DELETE attacks
        r"(sleep|benchmark|waitfor)\s*\(",  # Time-based attacks
    ]
    
    # XSS patterns
    XSS_PATTERNS = [
        r"<script[^>]*>.*?</script>",  # Script tags
        r"javascript:",  # JavaScript protocol
        r"on\w+\s*=",  # Event handlers
        r"<iframe[^>]*>",  # Iframe injection
        r"<object[^>]*>",  # Object injection
        r"<embed[^>]*>",  # Embed injection
        r"<link[^>]*>",  # Link injection
        r"<meta[^>]*>",  # Meta injection
        r"expression\s*\(",  # CSS expression
        r"vbscript:",  # VBScript protocol
    ]
    
    # Directory traversal patterns
    DIRECTORY_TRAVERSAL_PATTERNS = [
        r"\.\.\/",  # Basic traversal
        r"\.\.\\",  # Windows traversal
        r"%2e%2e%2f",  # URL encoded traversal
        r"%2e%2e%5c",  # URL encoded Windows traversal
        r"\.\.%2f",  # Mixed encoding
        r"\.\.%5c",  # Mixed encoding Windows
    ]
    
    # Command injection patterns
    COMMAND_INJECTION_PATTERNS = [
        r"[;&|`]",  # Command separators
        r"\$\([^)]*\)",  # Command substitution
        r"`[^`]*`",  # Backtick execution
        r"(nc|netcat|wget|curl|ping|nslookup)",  # Common commands
        r"(cat|type|more|less)\s+",  # File reading commands
        r"(rm|del|rmdir)\s+",  # File deletion commands
    ]
    
    # Suspicious user agents
    SUSPICIOUS_USER_AGENTS = [
        r"sqlmap",
        r"nmap",
        r"nikto",
        r"burp",
        r"w3af",
        r"acunetix",
        r"nessus",
        r"openvas",
        r"masscan",
        r"zap",
    ]

class IPTracker:
    """Tracks IP behavior and reputation"""
    
    def __init__(self):
        self.ip_requests = defaultdict(deque)  # IP -> request timestamps
        self.ip_failures = defaultdict(int)    # IP -> failure count
        self.blocked_ips = set()               # Blocked IPs
        self.suspicious_ips = set()            # Suspicious IPs
        self.whitelist_ips = set()             # Whitelisted IPs
        
        # Known malicious IP ranges (example)
        self.malicious_ranges = [
            "10.0.0.0/8",      # Private ranges often used in attacks
            "192.168.0.0/16",  # Private ranges
            "172.16.0.0/12",   # Private ranges
        ]
    
    def is_ip_suspicious(self, ip: str) -> bool:
        """Check if IP is suspicious"""
        if ip in self.whitelist_ips:
            return False
        
        if ip in self.blocked_ips or ip in self.suspicious_ips:
            return True
        
        # Check against malicious ranges
        try:
            ip_obj = ipaddress.ip_address(ip)
            for range_str in self.malicious_ranges:
                if ip_obj in ipaddress.ip_network(range_str):
                    return True
        except ValueError:
            return True  # Invalid IP is suspicious
        
        return False
    
    def track_request(self, ip: str, success: bool = True):
        """Track a request from an IP"""
        now = time.time()
        
        # Clean old requests (older than 1 hour)
        cutoff = now - 3600
        while self.ip_requests[ip] and self.ip_requests[ip][0] < cutoff:
            self.ip_requests[ip].popleft()
        
        # Add current request
        self.ip_requests[ip].append(now)
        
        # Track failures
        if not success:
            self.ip_failures[ip] += 1
    
    def get_request_rate(self, ip: str, window_seconds: int = 300) -> int:
        """Get request rate for IP in given window"""
        now = time.time()
        cutoff = now - window_seconds
        
        return sum(1 for timestamp in self.ip_requests[ip] if timestamp > cutoff)
    
    def is_rate_limited(self, ip: str, max_requests: int = 100, window_seconds: int = 300) -> bool:
        """Check if IP should be rate limited"""
        return self.get_request_rate(ip, window_seconds) > max_requests

class ThreatDetectionAgent:
    """Main threat detection agent"""
    
    def __init__(self):
        self.ip_tracker = IPTracker()
        self.threat_events = deque(maxlen=10000)  # Store recent threats
        self.detection_stats = defaultdict(int)
        self.running = False
        
        # Compile regex patterns for performance
        self.sql_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in ThreatPatterns.SQL_INJECTION_PATTERNS]
        self.xss_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in ThreatPatterns.XSS_PATTERNS]
        self.traversal_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in ThreatPatterns.DIRECTORY_TRAVERSAL_PATTERNS]
        self.command_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in ThreatPatterns.COMMAND_INJECTION_PATTERNS]
        self.ua_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in ThreatPatterns.SUSPICIOUS_USER_AGENTS]
    
    def generate_threat_id(self, threat_type: ThreatType, source_ip: str) -> str:
        """Generate unique threat ID"""
        timestamp = str(int(time.time()))
        data = f"{threat_type.value}:{source_ip}:{timestamp}"
        return hashlib.md5(data.encode()).hexdigest()[:16]
    
    def analyze_request(self, 
                       ip: str, 
                       method: str, 
                       endpoint: str, 
                       headers: Dict[str, str], 
                       payload: Optional[str] = None) -> List[ThreatEvent]:
        """Analyze incoming request for threats"""
        threats = []
        user_agent = headers.get('User-Agent', '')
        
        # Track the request
        self.ip_tracker.track_request(ip)
        
        # Check IP reputation
        if self.ip_tracker.is_ip_suspicious(ip):
            threat = ThreatEvent(
                id=self.generate_threat_id(ThreatType.MALICIOUS_IP, ip),
                timestamp=datetime.now(),
                threat_type=ThreatType.MALICIOUS_IP,
                threat_level=ThreatLevel.HIGH,
                source_ip=ip,
                user_agent=user_agent,
                endpoint=endpoint,
                method=method,
                payload=payload,
                description=f"Request from suspicious IP: {ip}",
                confidence_score=0.8,
                metadata={'ip_reputation': 'suspicious'}
            )
            threats.append(threat)
        
        # Check rate limiting
        if self.ip_tracker.is_rate_limited(ip):
            threat = ThreatEvent(
                id=self.generate_threat_id(ThreatType.RATE_LIMIT_VIOLATION, ip),
                timestamp=datetime.now(),
                threat_type=ThreatType.RATE_LIMIT_VIOLATION,
                threat_level=ThreatLevel.MEDIUM,
                source_ip=ip,
                user_agent=user_agent,
                endpoint=endpoint,
                method=method,
                payload=payload,
                description=f"Rate limit exceeded from IP: {ip}",
                confidence_score=0.9,
                metadata={'request_rate': self.ip_tracker.get_request_rate(ip)}
            )
            threats.append(threat)
        
        # Check user agent
        for pattern in self.ua_patterns:
            if pattern.search(user_agent):
                threat = ThreatEvent(
                    id=self.generate_threat_id(ThreatType.SUSPICIOUS_PAYLOAD, ip),
                    timestamp=datetime.now(),
                    threat_type=ThreatType.SUSPICIOUS_PAYLOAD,
                    threat_level=ThreatLevel.MEDIUM,
                    source_ip=ip,
                    user_agent=user_agent,
                    endpoint=endpoint,
                    method=method,
                    payload=payload,
                    description=f"Suspicious user agent detected: {user_agent}",
                    confidence_score=0.7,
                    metadata={'pattern_matched': pattern.pattern}
                )
                threats.append(threat)
                break
        
        # Analyze payload if present
        if payload:
            threats.extend(self._analyze_payload(ip, method, endpoint, user_agent, payload))
        
        # Analyze URL/endpoint
        threats.extend(self._analyze_endpoint(ip, method, endpoint, user_agent))
        
        # Store detected threats
        for threat in threats:
            self.threat_events.append(threat)
            self.detection_stats[threat.threat_type.value] += 1
        
        return threats
    
    def _analyze_payload(self, ip: str, method: str, endpoint: str, user_agent: str, payload: str) -> List[ThreatEvent]:
        """Analyze request payload for threats"""
        threats = []
        
        # SQL Injection detection
        for pattern in self.sql_patterns:
            if pattern.search(payload):
                threat = ThreatEvent(
                    id=self.generate_threat_id(ThreatType.SQL_INJECTION, ip),
                    timestamp=datetime.now(),
                    threat_type=ThreatType.SQL_INJECTION,
                    threat_level=ThreatLevel.HIGH,
                    source_ip=ip,
                    user_agent=user_agent,
                    endpoint=endpoint,
                    method=method,
                    payload=payload[:500],  # Truncate for storage
                    description=f"SQL injection attempt detected in payload",
                    confidence_score=0.85,
                    metadata={
                        'pattern_matched': pattern.pattern,
                        'payload_length': len(payload)
                    }
                )
                threats.append(threat)
                break
        
        # XSS detection
        for pattern in self.xss_patterns:
            if pattern.search(payload):
                threat = ThreatEvent(
                    id=self.generate_threat_id(ThreatType.XSS_ATTACK, ip),
                    timestamp=datetime.now(),
                    threat_type=ThreatType.XSS_ATTACK,
                    threat_level=ThreatLevel.HIGH,
                    source_ip=ip,
                    user_agent=user_agent,
                    endpoint=endpoint,
                    method=method,
                    payload=payload[:500],
                    description=f"XSS attack attempt detected in payload",
                    confidence_score=0.8,
                    metadata={
                        'pattern_matched': pattern.pattern,
                        'payload_length': len(payload)
                    }
                )
                threats.append(threat)
                break
        
        # Command injection detection
        for pattern in self.command_patterns:
            if pattern.search(payload):
                threat = ThreatEvent(
                    id=self.generate_threat_id(ThreatType.COMMAND_INJECTION, ip),
                    timestamp=datetime.now(),
                    threat_type=ThreatType.COMMAND_INJECTION,
                    threat_level=ThreatLevel.CRITICAL,
                    source_ip=ip,
                    user_agent=user_agent,
                    endpoint=endpoint,
                    method=method,
                    payload=payload[:500],
                    description=f"Command injection attempt detected in payload",
                    confidence_score=0.9,
                    metadata={
                        'pattern_matched': pattern.pattern,
                        'payload_length': len(payload)
                    }
                )
                threats.append(threat)
                break
        
        return threats
    
    def _analyze_endpoint(self, ip: str, method: str, endpoint: str, user_agent: str) -> List[ThreatEvent]:
        """Analyze endpoint/URL for threats"""
        threats = []
        
        # Directory traversal detection
        for pattern in self.traversal_patterns:
            if pattern.search(endpoint):
                threat = ThreatEvent(
                    id=self.generate_threat_id(ThreatType.DIRECTORY_TRAVERSAL, ip),
                    timestamp=datetime.now(),
                    threat_type=ThreatType.DIRECTORY_TRAVERSAL,
                    threat_level=ThreatLevel.HIGH,
                    source_ip=ip,
                    user_agent=user_agent,
                    endpoint=endpoint,
                    method=method,
                    payload=None,
                    description=f"Directory traversal attempt detected in URL",
                    confidence_score=0.85,
                    metadata={
                        'pattern_matched': pattern.pattern,
                        'endpoint': endpoint
                    }
                )
                threats.append(threat)
                break
        
        return threats
    
    def detect_brute_force(self, ip: str, endpoint: str, success: bool) -> Optional[ThreatEvent]:
        """Detect brute force attacks"""
        # Track failed attempts
        if not success:
            self.ip_tracker.ip_failures[ip] += 1
            
            # Check if threshold exceeded
            if self.ip_tracker.ip_failures[ip] >= 5:  # 5 failed attempts
                return ThreatEvent(
                    id=self.generate_threat_id(ThreatType.BRUTE_FORCE, ip),
                    timestamp=datetime.now(),
                    threat_type=ThreatType.BRUTE_FORCE,
                    threat_level=ThreatLevel.HIGH,
                    source_ip=ip,
                    user_agent=None,
                    endpoint=endpoint,
                    method="POST",
                    payload=None,
                    description=f"Brute force attack detected from IP: {ip}",
                    confidence_score=0.9,
                    metadata={
                        'failed_attempts': self.ip_tracker.ip_failures[ip],
                        'endpoint': endpoint
                    }
                )
        else:
            # Reset counter on success
            self.ip_tracker.ip_failures[ip] = 0
        
        return None
    
    def detect_ddos(self, time_window: int = 60) -> List[ThreatEvent]:
        """Detect potential DDoS attacks"""
        threats = []
        now = time.time()
        cutoff = now - time_window
        
        # Count requests per IP in time window
        ip_counts = defaultdict(int)
        for ip, timestamps in self.ip_tracker.ip_requests.items():
            count = sum(1 for ts in timestamps if ts > cutoff)
            ip_counts[ip] = count
        
        # Detect anomalous request rates
        if ip_counts:
            rates = list(ip_counts.values())
            if len(rates) > 1:
                mean_rate = statistics.mean(rates)
                stdev_rate = statistics.stdev(rates) if len(rates) > 1 else 0
                
                for ip, count in ip_counts.items():
                    if count > mean_rate + (3 * stdev_rate) and count > 100:  # 3 sigma rule
                        threat = ThreatEvent(
                            id=self.generate_threat_id(ThreatType.DDOS_ATTEMPT, ip),
                            timestamp=datetime.now(),
                            threat_type=ThreatType.DDOS_ATTEMPT,
                            threat_level=ThreatLevel.CRITICAL,
                            source_ip=ip,
                            user_agent=None,
                            endpoint="*",
                            method="*",
                            payload=None,
                            description=f"Potential DDoS attack from IP: {ip}",
                            confidence_score=0.8,
                            metadata={
                                'request_count': count,
                                'time_window': time_window,
                                'mean_rate': mean_rate,
                                'threshold': mean_rate + (3 * stdev_rate)
                            }
                        )
                        threats.append(threat)
        
        return threats
    
    def get_threat_summary(self, hours: int = 24) -> Dict:
        """Get threat detection summary"""
        cutoff = datetime.now() - timedelta(hours=hours)
        recent_threats = [t for t in self.threat_events if t.timestamp > cutoff]
        
        summary = {
            'total_threats': len(recent_threats),
            'threat_types': defaultdict(int),
            'threat_levels': defaultdict(int),
            'top_source_ips': defaultdict(int),
            'top_endpoints': defaultdict(int),
            'detection_rate': len(recent_threats) / max(hours, 1),
            'time_window': f"{hours} hours"
        }
        
        for threat in recent_threats:
            summary['threat_types'][threat.threat_type.value] += 1
            summary['threat_levels'][threat.threat_level.value] += 1
            summary['top_source_ips'][threat.source_ip] += 1
            summary['top_endpoints'][threat.endpoint] += 1
        
        # Convert to regular dicts and sort
        summary['threat_types'] = dict(summary['threat_types'])
        summary['threat_levels'] = dict(summary['threat_levels'])
        summary['top_source_ips'] = dict(sorted(summary['top_source_ips'].items(), key=lambda x: x[1], reverse=True)[:10])
        summary['top_endpoints'] = dict(sorted(summary['top_endpoints'].items(), key=lambda x: x[1], reverse=True)[:10])
        
        return summary
    
    def get_recent_threats(self, limit: int = 100) -> List[Dict]:
        """Get recent threat events"""
        recent = list(self.threat_events)[-limit:]
        return [threat.to_dict() for threat in reversed(recent)]
    
    def start_monitoring(self):
        """Start the threat detection monitoring"""
        self.running = True
        logger.info("Threat Detection Agent started")
    
    def stop_monitoring(self):
        """Stop the threat detection monitoring"""
        self.running = False
        logger.info("Threat Detection Agent stopped")

# Global threat detection agent instance
threat_detector = ThreatDetectionAgent()

# Convenience functions for integration
def analyze_request(ip: str, method: str, endpoint: str, headers: Dict[str, str], payload: Optional[str] = None) -> List[ThreatEvent]:
    """Analyze a request for threats"""
    return threat_detector.analyze_request(ip, method, endpoint, headers, payload)

def detect_brute_force(ip: str, endpoint: str, success: bool) -> Optional[ThreatEvent]:
    """Detect brute force attacks"""
    return threat_detector.detect_brute_force(ip, endpoint, success)

def get_threat_summary(hours: int = 24) -> Dict:
    """Get threat detection summary"""
    return threat_detector.get_threat_summary(hours)

def get_recent_threats(limit: int = 100) -> List[Dict]:
    """Get recent threat events"""
    return threat_detector.get_recent_threats(limit)

def start_threat_detection():
    """Start threat detection"""
    threat_detector.start_monitoring()

def stop_threat_detection():
    """Stop threat detection"""
    threat_detector.stop_monitoring()

if __name__ == "__main__":
    # Example usage
    agent = ThreatDetectionAgent()
    agent.start_monitoring()
    
    # Test SQL injection detection
    threats = agent.analyze_request(
        ip="192.168.1.100",
        method="POST",
        endpoint="/api/query",
        headers={"User-Agent": "Mozilla/5.0"},
        payload="SELECT * FROM users WHERE id = '1' OR '1'='1'"
    )
    
    for threat in threats:
        print(f"Threat detected: {threat.threat_type.value} - {threat.description}")
    
    # Get summary
    summary = agent.get_threat_summary()
    print(f"Threat summary: {json.dumps(summary, indent=2)}")

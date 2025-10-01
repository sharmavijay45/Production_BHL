#!/usr/bin/env python3
"""
BHIV Core Day 3 Setup Script
============================

Quick setup script for threat mitigation agents and security monitoring.
"""

import os
import sys
import subprocess
import asyncio
from pathlib import Path

def print_banner():
    """Print setup banner"""
    banner = """
🛡️ BHIV CORE DAY 3: THREAT MITIGATION SETUP
==========================================
Intelligent threat detection and response system setup.
    """
    print(banner)

def install_dependencies():
    """Install threat mitigation dependencies"""
    print("📦 Installing threat mitigation dependencies...")
    
    try:
        subprocess.run([
            sys.executable, "-m", "pip", "install", "-r", "requirements-threats.txt"
        ], check=True, capture_output=True)
        print("✅ Dependencies installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install dependencies: {e}")
        return False

def create_agents_directory():
    """Create agents directory if it doesn't exist"""
    agents_dir = Path("agents")
    if not agents_dir.exists():
        agents_dir.mkdir()
        print("📁 Created agents/ directory")
    
    # Create __init__.py
    init_file = agents_dir / "__init__.py"
    if not init_file.exists():
        init_file.write_text('"""BHIV Core Security Agents"""\n')
        print("📄 Created agents/__init__.py")

async def test_threat_system():
    """Test the threat mitigation system"""
    print("\n🧪 Testing threat mitigation system...")
    
    try:
        # Import and test basic functionality
        from agents.threat_detection import ThreatDetectionAgent
        from agents.threat_response import ThreatResponseAgent
        from agents.proactive_monitor import ProactiveMonitor
        
        # Quick functionality test
        detector = ThreatDetectionAgent()
        responder = ThreatResponseAgent()
        monitor = ProactiveMonitor()
        
        # Test SQL injection detection
        threats = detector.analyze_request(
            ip="127.0.0.1",
            method="POST",
            endpoint="/test",
            headers={"User-Agent": "TestAgent"},
            payload="SELECT * FROM users WHERE id = '1' OR '1'='1'"
        )
        
        if threats:
            print("✅ Threat detection working")
        else:
            print("⚠️ Threat detection may need tuning")
        
        # Test response system
        stats = responder.get_response_stats()
        print(f"✅ Response system initialized: {len(stats)} stats available")
        
        # Test monitoring
        dashboard = monitor.get_security_dashboard()
        print(f"✅ Monitoring system ready: {dashboard.get('status', 'unknown')}")
        
        return True
        
    except Exception as e:
        print(f"❌ Testing failed: {e}")
        return False

def print_usage_guide():
    """Print usage guide"""
    guide = """
🚀 THREAT MITIGATION SYSTEM READY!

📋 Quick Start Guide:

1️⃣ Start Secure Service with Threat Protection:
   python secure_service_with_threats.py

2️⃣ Run Comprehensive Tests:
   python test_threat_mitigation.py

3️⃣ Access Security Dashboard:
   GET http://localhost:8080/security/dashboard
   (Requires admin authentication)

4️⃣ Monitor Threats in Real-time:
   GET http://localhost:8080/security/threats

🔧 Key Features Enabled:

✅ SQL Injection Detection (11 patterns)
✅ XSS Attack Detection (10 patterns)  
✅ Brute Force Protection (5 failed attempts)
✅ Rate Limiting (100 requests/5min)
✅ DDoS Detection (anomaly analysis)
✅ Automatic IP Blocking
✅ Admin Alert System
✅ Real-time Security Dashboard

🛡️ Threat Types Detected:
- SQL Injection & Command Injection
- Cross-Site Scripting (XSS)
- Directory Traversal
- Brute Force Attacks
- Rate Limit Violations
- DDoS Attempts
- Suspicious User Agents
- Malicious IP Addresses

📊 Security Endpoints:
- /security/dashboard - Real-time security metrics
- /security/threats - Threat intelligence feed
- /security/responses - Response statistics
- /security/block-ip - Manual IP blocking
- /security/unblock-ip - Manual IP unblocking

⚠️ Production Notes:
- Change default JWT secrets
- Configure email/Slack alerts
- Tune detection thresholds
- Setup persistent threat storage
- Configure SSL certificates

🎯 Next: Day 4-5 Modularity
Ready to split into microservices with OpenAPI contracts!
    """
    print(guide)

async def main():
    """Main setup function"""
    print_banner()
    
    # Install dependencies
    if not install_dependencies():
        print("❌ Setup failed - could not install dependencies")
        return 1
    
    # Create directory structure
    create_agents_directory()
    
    # Test the system
    if await test_threat_system():
        print("\n✅ All systems operational!")
    else:
        print("\n⚠️ Some components may need attention")
    
    # Print usage guide
    print_usage_guide()
    
    return 0

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)

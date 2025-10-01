#!/usr/bin/env python3
"""
BHIV Core Microservices Setup Script
===================================

Automated setup and management for the modular microservices architecture.
"""

import os
import sys
import subprocess
import time
import requests
import json
from pathlib import Path
from datetime import datetime

def print_banner():
    """Print setup banner"""
    banner = """
🏗️ BHIV CORE MICROSERVICES SETUP
=================================
Modular architecture deployment and management system.
    """
    print(banner)

def install_dependencies():
    """Install microservices dependencies"""
    print("📦 Installing microservices dependencies...")
    
    requirements_files = [
        "requirements-security.txt",
        "requirements-threats.txt"
    ]
    
    for req_file in requirements_files:
        if os.path.exists(req_file):
            try:
                subprocess.run([
                    sys.executable, "-m", "pip", "install", "-r", req_file
                ], check=True, capture_output=True)
                print(f"✅ Installed dependencies from {req_file}")
            except subprocess.CalledProcessError as e:
                print(f"⚠️ Warning: Failed to install {req_file}: {e}")
    
    # Install additional microservices dependencies
    additional_deps = [
        "httpx>=0.25.0",
        "aiohttp>=3.8.0",
        "prometheus-client>=0.17.0"
    ]
    
    for dep in additional_deps:
        try:
            subprocess.run([
                sys.executable, "-m", "pip", "install", dep
            ], check=True, capture_output=True)
        except:
            print(f"⚠️ Warning: Failed to install {dep}")
    
    print("✅ Dependencies installation completed")

def create_directory_structure():
    """Create microservices directory structure"""
    print("📁 Creating directory structure...")
    
    directories = [
        "modules",
        "modules/shared",
        "modules/logistics", 
        "modules/crm",
        "modules/agent_orchestration",
        "modules/llm_query",
        "modules/integrations",
        "api_gateway",
        "logs",
        "config"
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
    
    print("✅ Directory structure created")

def start_service(service_name, port, script_path):
    """Start a microservice"""
    print(f"🚀 Starting {service_name} service on port {port}...")
    
    try:
        # Start service in background
        process = subprocess.Popen([
            sys.executable, script_path
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Wait for service to start
        time.sleep(3)
        
        # Check if service is responding
        try:
            response = requests.get(f"http://localhost:{port}/health", timeout=5)
            if response.status_code == 200:
                print(f"✅ {service_name} service started successfully")
                return process
            else:
                print(f"❌ {service_name} service health check failed")
                process.terminate()
                return None
        except requests.exceptions.RequestException:
            print(f"❌ {service_name} service not responding")
            process.terminate()
            return None
            
    except Exception as e:
        print(f"❌ Failed to start {service_name}: {e}")
        return None

def check_service_health(service_name, port):
    """Check if service is healthy"""
    try:
        response = requests.get(f"http://localhost:{port}/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            status = data.get("status", "unknown")
            print(f"✅ {service_name}: {status}")
            return True
        else:
            print(f"❌ {service_name}: HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ {service_name}: {str(e)}")
        return False

def start_all_services():
    """Start all microservices in correct order"""
    print("\n🚀 Starting all microservices...")
    
    services = [
        ("Integrations", 8005, "modules/integrations/service.py"),
        ("LLM Query", 8004, "modules/llm_query/service.py"),
        ("Logistics", 8001, "modules/logistics/service.py"),
        ("CRM", 8002, "modules/crm/service.py"),
        ("Agent Orchestration", 8003, "modules/agent_orchestration/service.py"),
        ("API Gateway", 8000, "api_gateway/gateway.py")
    ]
    
    processes = {}
    
    for service_name, port, script_path in services:
        if os.path.exists(script_path):
            process = start_service(service_name, port, script_path)
            if process:
                processes[service_name] = {"process": process, "port": port}
        else:
            print(f"⚠️ {service_name} script not found: {script_path}")
    
    return processes

def check_all_services():
    """Check health of all services"""
    print("\n🏥 Checking service health...")
    
    services = [
        ("Integrations", 8005),
        ("LLM Query", 8004),
        ("Logistics", 8001),
        ("CRM", 8002),
        ("Agent Orchestration", 8003),
        ("API Gateway", 8000)
    ]
    
    healthy_services = 0
    
    for service_name, port in services:
        if check_service_health(service_name, port):
            healthy_services += 1
    
    print(f"\n📊 Services Status: {healthy_services}/{len(services)} healthy")
    return healthy_services

def test_gateway_routing():
    """Test API Gateway routing"""
    print("\n🌐 Testing API Gateway routing...")
    
    routes = [
        ("logistics", "/inventory"),
        ("crm", "/customers"),
        ("agents", "/agents"),
        ("llm", "/models"),
        ("integrations", "/integrations")
    ]
    
    successful_routes = 0
    
    for service, endpoint in routes:
        try:
            response = requests.get(
                f"http://localhost:8000/api/{service}{endpoint}",
                timeout=5
            )
            
            if response.status_code in [200, 403]:  # 403 = auth required (OK)
                print(f"✅ Gateway → {service}: HTTP {response.status_code}")
                successful_routes += 1
            else:
                print(f"❌ Gateway → {service}: HTTP {response.status_code}")
                
        except Exception as e:
            print(f"❌ Gateway → {service}: {str(e)}")
    
    print(f"\n📊 Gateway Routing: {successful_routes}/{len(routes)} successful")
    return successful_routes

def generate_service_map():
    """Generate service discovery map"""
    print("\n📋 Generating service map...")
    
    try:
        response = requests.get("http://localhost:8000/services", timeout=5)
        if response.status_code == 200:
            services_data = response.json()
            print("✅ Service discovery working")
            
            print("\n🗺️ Service Map:")
            for service_name, config in services_data.get("services", {}).items():
                print(f"  - {service_name}: http://{config['host']}:{config['port']}")
            
            return True
        else:
            print("❌ Service discovery failed")
            return False
            
    except Exception as e:
        print(f"❌ Service discovery error: {e}")
        return False

def run_integration_tests():
    """Run integration tests"""
    print("\n🧪 Running integration tests...")
    
    try:
        result = subprocess.run([
            sys.executable, "test_modular_system.py"
        ], capture_output=True, text=True, timeout=300)
        
        if result.returncode == 0:
            print("✅ Integration tests passed")
            return True
        else:
            print("❌ Integration tests failed")
            print(result.stdout)
            return False
            
    except subprocess.TimeoutExpired:
        print("⏰ Integration tests timed out")
        return False
    except Exception as e:
        print(f"❌ Integration test error: {e}")
        return False

def print_usage_guide():
    """Print usage guide"""
    guide = """
🎉 MICROSERVICES ARCHITECTURE READY!

📋 Service Endpoints:

🌐 API Gateway (Recommended Entry Point):
   http://localhost:8000
   - Unified access to all services
   - Authentication and rate limiting
   - Load balancing and routing

📦 Individual Services:
   - Logistics:           http://localhost:8001
   - CRM:                 http://localhost:8002  
   - Agent Orchestration: http://localhost:8003
   - LLM Query:           http://localhost:8004
   - Integrations:        http://localhost:8005

📚 API Documentation:
   - Gateway Docs:    http://localhost:8000/docs
   - Logistics Docs:  http://localhost:8001/docs
   - CRM Docs:        http://localhost:8002/docs
   - Agents Docs:     http://localhost:8003/docs
   - LLM Docs:        http://localhost:8004/docs
   - Integrations:    http://localhost:8005/docs

🔧 Example API Calls:

# Through API Gateway (Recommended)
curl http://localhost:8000/api/logistics/inventory
curl http://localhost:8000/api/crm/customers
curl http://localhost:8000/api/agents/agents
curl http://localhost:8000/api/llm/models

# Health Checks
curl http://localhost:8000/health          # Gateway health
curl http://localhost:8000/services        # Service discovery

# Batch Requests
curl -X POST http://localhost:8000/api/batch \\
  -H "Content-Type: application/json" \\
  -d '{"requests": [{"service": "logistics", "path": "inventory"}]}'

🛡️ Security:
- All services require JWT authentication
- Use /auth/login to get access token
- Include token in Authorization header

🎯 Next Steps:
1. Day 6: Docker containerization
2. Day 6: Kubernetes deployment  
3. Day 6: CI/CD pipeline setup
4. Day 7-8: Observability (Prometheus + Grafana)

📊 Architecture Benefits:
✅ Independent service deployment
✅ Horizontal scaling capability
✅ Technology stack flexibility
✅ Fault isolation
✅ Team autonomy
✅ Continuous delivery ready
    """
    print(guide)

def main():
    """Main setup function"""
    print_banner()
    
    # Setup phase
    install_dependencies()
    create_directory_structure()
    
    # Check if service files exist
    required_files = [
        "modules/logistics/service.py",
        "modules/crm/service.py", 
        "modules/agent_orchestration/service.py",
        "modules/llm_query/service.py",
        "modules/integrations/service.py",
        "api_gateway/gateway.py"
    ]
    
    missing_files = [f for f in required_files if not os.path.exists(f)]
    if missing_files:
        print(f"\n❌ Missing service files: {missing_files}")
        print("Please ensure all microservice files are created first.")
        return 1
    
    # Start services
    processes = start_all_services()
    
    if len(processes) < 3:
        print("\n❌ Insufficient services started. Check for errors above.")
        return 1
    
    # Wait for services to initialize
    print("\n⏳ Waiting for services to initialize...")
    time.sleep(5)
    
    # Health checks
    healthy_count = check_all_services()
    
    # Test gateway
    if "API Gateway" in processes:
        routing_success = test_gateway_routing()
        generate_service_map()
    
    # Integration tests (optional)
    print("\n🤔 Run integration tests? (y/n): ", end="")
    if input().lower().startswith('y'):
        run_integration_tests()
    
    # Summary
    print("\n" + "=" * 50)
    print("🎯 MICROSERVICES SETUP SUMMARY")
    print("=" * 50)
    print(f"Services Started: {len(processes)}/6")
    print(f"Services Healthy: {healthy_count}/6")
    
    if healthy_count >= 4:
        print("\n✅ MICROSERVICES ARCHITECTURE: OPERATIONAL")
        print_usage_guide()
        
        # Keep services running
        print("\n🔄 Services are running. Press Ctrl+C to stop all services.")
        try:
            while True:
                time.sleep(10)
                # Periodic health check
                alive_count = sum(1 for p in processes.values() if p["process"].poll() is None)
                if alive_count < len(processes):
                    print(f"⚠️ Warning: {len(processes) - alive_count} services stopped")
        except KeyboardInterrupt:
            print("\n🛑 Stopping all services...")
            for service_name, service_info in processes.items():
                try:
                    service_info["process"].terminate()
                    service_info["process"].wait(timeout=5)
                    print(f"✅ Stopped {service_name}")
                except:
                    print(f"⚠️ Force killing {service_name}")
                    service_info["process"].kill()
    else:
        print("\n⚠️ MICROSERVICES ARCHITECTURE: NEEDS ATTENTION")
        return 1
    
    return 0

if __name__ == "__main__":
    exit_code = main()
    exit(exit_code)

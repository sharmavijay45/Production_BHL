#!/usr/bin/env python3
"""
Complete Production Mode Setup Script
====================================
"""

import os
import sys
import subprocess
from dotenv import load_dotenv

load_dotenv()

def install_missing_dependencies():
    """Install missing dependencies for production mode"""
    
    print("🔧 Installing missing dependencies...")
    
    missing_packages = [
        "opentelemetry-instrumentation-redis",
        "redis"  # Add redis package itself
    ]
    
    for package in missing_packages:
        try:
            print(f"📦 Installing {package}...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])
            print(f"✅ {package} installed successfully")
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to install {package}: {e}")
            return False
    
    return True

def test_production_imports():
    """Test if all production imports work"""
    
    print("\n🧪 Testing production imports...")
    
    try:
        from integration.agent_integration import get_agent_registry
        print("✅ integration.agent_integration - OK")
    except ImportError as e:
        print(f"❌ integration.agent_integration - FAILED: {e}")
        return False
    
    try:
        from security.auth import verify_token, create_access_token
        print("✅ security.auth - OK")
    except ImportError as e:
        print(f"❌ security.auth - FAILED: {e}")
        return False
    
    try:
        from observability.metrics import init_metrics, get_metrics
        print("✅ observability.metrics - OK")
    except ImportError as e:
        print(f"❌ observability.metrics - FAILED: {e}")
        return False
    
    try:
        from observability.tracing import init_tracing
        print("✅ observability.tracing - OK")
    except ImportError as e:
        print(f"❌ observability.tracing - FAILED: {e}")
        return False
    
    try:
        from observability.alerting import init_alerting
        print("✅ observability.alerting - OK")
    except ImportError as e:
        print(f"❌ observability.alerting - FAILED: {e}")
        return False
    
    return True

def verify_environment():
    """Verify environment configuration"""
    
    print("\n🔍 Verifying environment configuration...")
    
    # Check PRODUCTION_MODE
    production_mode = os.getenv('PRODUCTION_MODE', 'false')
    print(f"📋 PRODUCTION_MODE: {production_mode}")
    
    if production_mode.lower() != 'true':
        print("⚠️ PRODUCTION_MODE is not set to 'true'")
        return False
    
    # Check RAG_API_URL
    rag_url = os.getenv('RAG_API_URL', '')
    print(f"📋 RAG_API_URL: {rag_url}")
    
    if not rag_url:
        print("⚠️ RAG_API_URL is not set")
        return False
    
    # Check Vaani endpoint
    vaani_endpoint = os.getenv('VAANI_ENDPOINT', '')
    print(f"📋 VAANI_ENDPOINT: {vaani_endpoint}")
    
    return True

def main():
    """Main setup function"""
    
    print("🚀 Production Mode Setup")
    print("=" * 50)
    
    # Step 1: Install dependencies
    if not install_missing_dependencies():
        print("❌ Failed to install dependencies")
        return False
    
    # Step 2: Verify environment
    if not verify_environment():
        print("❌ Environment configuration issues")
        return False
    
    # Step 3: Test imports
    if not test_production_imports():
        print("❌ Production imports failed")
        return False
    
    print("\n🎉 Production mode setup completed successfully!")
    print("\n📋 Next steps:")
    print("1. Start Simple API: python simple_api.py --port 8001")
    print("2. Check for: '✅ Production mode enabled with full observability'")
    print("3. Test API: curl 'http://localhost:8001/ask-vedas?query=What is dharma?'")
    print("4. View metrics: curl 'http://localhost:8001/metrics'")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

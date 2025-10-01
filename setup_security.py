#!/usr/bin/env python3
"""
BHIV Core Security Setup Script
==============================

Quick setup script for Day 1 security implementation.
"""

import os
import sys
import subprocess
import secrets
from pathlib import Path

def print_banner():
    """Print setup banner"""
    banner = """
🔒 BHIV CORE SECURITY SETUP
===========================
Production-grade security implementation setup script.
    """
    print(banner)

def check_python_version():
    """Check Python version"""
    if sys.version_info < (3, 8):
        print("❌ Python 3.8+ required")
        sys.exit(1)
    print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor} detected")

def install_dependencies():
    """Install required dependencies"""
    print("\n📦 Installing dependencies...")
    
    try:
        subprocess.run([
            sys.executable, "-m", "pip", "install", "-r", "requirements-security.txt"
        ], check=True, capture_output=True)
        print("✅ Dependencies installed successfully")
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install dependencies: {e}")
        print("Please run: pip install -r requirements-security.txt")
        return False
    
    return True

def generate_env_file():
    """Generate environment file with secure defaults"""
    print("\n🔧 Generating environment configuration...")
    
    # Generate secure JWT secret
    jwt_secret = secrets.token_urlsafe(32)
    
    env_content = f"""# BHIV Core Security Environment
# Generated on {os.popen('date').read().strip()}

# JWT Configuration
JWT_SECRET_KEY={jwt_secret}
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# Service Configuration
SECURE_SERVICE_HOST=0.0.0.0
SECURE_SERVICE_PORT=8080

# Database Configuration (UPDATE WITH YOUR VALUES)
DATABASE_URL=postgresql://username:password@localhost:5432/bhiv_core?sslmode=require

# Security Features
ENABLE_AUDIT_LOGGING=true
ENABLE_THREAT_DETECTION=true
ENABLE_RATE_LIMITING=true

# Development Settings (CHANGE IN PRODUCTION)
ENVIRONMENT=development
DEBUG=false
"""
    
    with open(".env", "w") as f:
        f.write(env_content)
    
    print("✅ Environment file created (.env)")
    print("⚠️  Please update DATABASE_URL with your PostgreSQL credentials")

def check_database():
    """Check database connectivity"""
    print("\n🗄️ Checking database setup...")
    
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("⚠️  DATABASE_URL not set. Please configure your PostgreSQL database.")
        print("   Example: postgresql://user:pass@localhost:5432/bhiv_core")
        return False
    
    try:
        # Try to import and test database connection
        from security.database import db_manager
        if db_manager.test_connection():
            print("✅ Database connection successful")
            return True
        else:
            print("❌ Database connection failed")
            return False
    except Exception as e:
        print(f"⚠️  Database check failed: {e}")
        print("   Please ensure PostgreSQL is running and DATABASE_URL is correct")
        return False

def run_migration():
    """Run database migration"""
    print("\n🔄 Running database migration...")
    
    try:
        subprocess.run([sys.executable, "migrate_to_secure.py"], check=True)
        print("✅ Migration completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Migration failed: {e}")
        return False

def run_tests():
    """Run security tests"""
    print("\n🧪 Running security tests...")
    
    try:
        # Start service in background for testing
        print("Starting secure service for testing...")
        service_process = subprocess.Popen([
            sys.executable, "secure_uniguru_service.py"
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Wait a moment for service to start
        import time
        time.sleep(3)
        
        # Run tests
        result = subprocess.run([
            sys.executable, "test_security_implementation.py"
        ], capture_output=True, text=True)
        
        # Stop service
        service_process.terminate()
        service_process.wait()
        
        if result.returncode == 0:
            print("✅ Security tests passed")
            return True
        else:
            print(f"⚠️  Some tests failed: {result.stdout}")
            return False
            
    except Exception as e:
        print(f"❌ Test execution failed: {e}")
        return False

def print_next_steps():
    """Print next steps"""
    next_steps = """
🎉 BHIV CORE SECURITY SETUP COMPLETE!

🚀 Next Steps:
1. Update DATABASE_URL in .env file with your PostgreSQL credentials
2. Start the secure service: python secure_uniguru_service.py
3. Test the API endpoints using the Postman collection
4. Change default passwords in production
5. Configure SSL/TLS certificates for HTTPS

📚 Documentation:
- API Documentation: API_DOCUMENTATION.md
- Day 1 Summary: DAY1_COMPLETION_SUMMARY.md
- Security Guide: security/ module

🔑 Default Login:
- Username: admin
- Password: SecureAdmin123!
- Endpoint: POST /auth/login

⚠️  SECURITY REMINDERS:
- Change all default passwords
- Update JWT_SECRET_KEY for production
- Configure SSL certificates
- Review security configuration
- Setup monitoring and alerting

Ready to proceed to Day 3: Threat Mitigation Agents! 🛡️
    """
    print(next_steps)

def main():
    """Main setup function"""
    print_banner()
    
    # Check prerequisites
    check_python_version()
    
    # Install dependencies
    if not install_dependencies():
        sys.exit(1)
    
    # Generate environment file
    generate_env_file()
    
    # Load environment
    from dotenv import load_dotenv
    load_dotenv()
    
    # Check database (optional)
    db_ok = check_database()
    
    # Run migration if database is available
    if db_ok:
        if not run_migration():
            print("⚠️  Migration failed, but you can run it manually later")
    
    # Print completion message
    print_next_steps()

if __name__ == "__main__":
    main()

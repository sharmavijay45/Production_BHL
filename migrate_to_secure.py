"""
Database Migration Script
========================

Migrates existing BHIV Core system to secure production setup.
"""

import os
import sys
import logging
from datetime import datetime
from typing import Dict, Any, List
import asyncio
import json

# Add current directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from security.database import migration_manager, DatabaseTransaction, db_manager
from security.models import User, UserRole, AuditLog, SecurityEvent, ThreatAlert
from security.auth import hash_password

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MigrationManager:
    """Handles migration from existing system to secure system"""
    
    def __init__(self):
        self.logger = logger
    
    async def run_full_migration(self):
        """Run complete migration process"""
        self.logger.info("🚀 Starting BHIV Core Security Migration...")
        
        try:
            # Step 1: Create security database tables
            await self.create_security_tables()
            
            # Step 2: Migrate existing users (if any)
            await self.migrate_existing_users()
            
            # Step 3: Create default users and roles
            await self.create_default_users()
            
            # Step 4: Initialize audit logging
            await self.initialize_audit_system()
            
            # Step 5: Setup security monitoring
            await self.setup_security_monitoring()
            
            # Step 6: Verify migration
            await self.verify_migration()
            
            self.logger.info("✅ Migration completed successfully!")
            
        except Exception as e:
            self.logger.error(f"❌ Migration failed: {e}")
            raise
    
    async def create_security_tables(self):
        """Create all security-related database tables"""
        self.logger.info("📊 Creating security database tables...")
        
        try:
            migration_manager.create_security_tables()
            self.logger.info("✅ Security tables created successfully")
        except Exception as e:
            self.logger.error(f"❌ Failed to create security tables: {e}")
            raise
    
    async def migrate_existing_users(self):
        """Migrate existing users from MongoDB to PostgreSQL"""
        self.logger.info("👥 Migrating existing users...")
        
        try:
            # Try to connect to existing MongoDB and migrate users
            from pymongo import MongoClient
            
            mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017/bhiv_core")
            client = MongoClient(mongo_uri)
            db = client.get_default_database()
            
            # Check if users collection exists
            if "users" in db.list_collection_names():
                users_collection = db.users
                existing_users = list(users_collection.find())
                
                self.logger.info(f"Found {len(existing_users)} existing users to migrate")
                
                with DatabaseTransaction() as pg_db:
                    for user_data in existing_users:
                        # Create user in PostgreSQL
                        new_user = User(
                            username=user_data.get("username", f"user_{user_data['_id']}"),
                            email=user_data.get("email", f"user_{user_data['_id']}@bhivcore.com"),
                            hashed_password=hash_password(user_data.get("password", "TempPassword123!")),
                            full_name=user_data.get("full_name", "Migrated User"),
                            role=UserRole.CUSTOMER,  # Default role for migrated users
                            is_active=user_data.get("is_active", True),
                            is_verified=user_data.get("is_verified", False)
                        )
                        
                        pg_db.add(new_user)
                    
                    pg_db.commit()
                    self.logger.info(f"✅ Migrated {len(existing_users)} users successfully")
            else:
                self.logger.info("No existing users found to migrate")
                
        except Exception as e:
            self.logger.warning(f"Could not migrate existing users: {e}")
            self.logger.info("Proceeding with fresh user setup...")
    
    async def create_default_users(self):
        """Create default system users with different roles"""
        self.logger.info("👤 Creating default users...")
        
        default_users = [
            {
                "username": "admin",
                "email": "admin@bhivcore.com",
                "password": "SecureAdmin123!",
                "full_name": "System Administrator",
                "role": UserRole.ADMIN
            },
            {
                "username": "ops_manager",
                "email": "ops@bhivcore.com", 
                "password": "SecureOps123!",
                "full_name": "Operations Manager",
                "role": UserRole.OPS
            },
            {
                "username": "sales_lead",
                "email": "sales@bhivcore.com",
                "password": "SecureSales123!",
                "full_name": "Sales Lead",
                "role": UserRole.SALES
            },
            {
                "username": "support_agent",
                "email": "support@bhivcore.com",
                "password": "SecureSupport123!",
                "full_name": "Support Agent", 
                "role": UserRole.SUPPORT
            },
            {
                "username": "demo_customer",
                "email": "customer@bhivcore.com",
                "password": "SecureCustomer123!",
                "full_name": "Demo Customer",
                "role": UserRole.CUSTOMER
            }
        ]
        
        created_count = 0
        with DatabaseTransaction() as db:
            for user_data in default_users:
                # Check if user already exists
                existing_user = db.query(User).filter(
                    (User.username == user_data["username"]) | 
                    (User.email == user_data["email"])
                ).first()
                
                if not existing_user:
                    new_user = User(
                        username=user_data["username"],
                        email=user_data["email"],
                        hashed_password=hash_password(user_data["password"]),
                        full_name=user_data["full_name"],
                        role=user_data["role"],
                        is_active=True,
                        is_verified=True
                    )
                    
                    db.add(new_user)
                    created_count += 1
                    self.logger.info(f"Created user: {user_data['username']} ({user_data['role']})")
                else:
                    self.logger.info(f"User already exists: {user_data['username']}")
            
            db.commit()
        
        self.logger.info(f"✅ Created {created_count} default users")
        
        # Log default credentials (remove in production!)
        self.logger.warning("🔑 DEFAULT CREDENTIALS (CHANGE IN PRODUCTION):")
        for user_data in default_users:
            self.logger.warning(f"   {user_data['username']}: {user_data['password']}")
    
    async def initialize_audit_system(self):
        """Initialize audit logging system"""
        self.logger.info("📋 Initializing audit logging system...")
        
        try:
            with DatabaseTransaction() as db:
                # Create initial audit log entry
                initial_audit = AuditLog(
                    action="system_migration",
                    resource="system",
                    details={
                        "migration_version": "1.0.0",
                        "timestamp": datetime.utcnow().isoformat(),
                        "status": "completed"
                    },
                    ip_address="127.0.0.1",
                    user_agent="Migration Script"
                )
                
                db.add(initial_audit)
                db.commit()
                
            self.logger.info("✅ Audit logging system initialized")
            
        except Exception as e:
            self.logger.error(f"❌ Failed to initialize audit system: {e}")
            raise
    
    async def setup_security_monitoring(self):
        """Setup initial security monitoring"""
        self.logger.info("🛡️ Setting up security monitoring...")
        
        try:
            with DatabaseTransaction() as db:
                # Create initial security event
                security_event = SecurityEvent(
                    event_type="system_initialization",
                    severity="low",
                    description="Security system initialized successfully",
                    details={
                        "migration_timestamp": datetime.utcnow().isoformat(),
                        "security_features": [
                            "JWT Authentication",
                            "RBAC Authorization", 
                            "Audit Logging",
                            "Threat Detection",
                            "Rate Limiting"
                        ]
                    }
                )
                
                db.add(security_event)
                db.commit()
                
            self.logger.info("✅ Security monitoring setup completed")
            
        except Exception as e:
            self.logger.error(f"❌ Failed to setup security monitoring: {e}")
            raise
    
    async def verify_migration(self):
        """Verify migration was successful"""
        self.logger.info("🔍 Verifying migration...")
        
        try:
            with DatabaseTransaction() as db:
                # Check users
                user_count = db.query(User).count()
                admin_count = db.query(User).filter(User.role == UserRole.ADMIN).count()
                
                # Check audit logs
                audit_count = db.query(AuditLog).count()
                
                # Check security events
                security_event_count = db.query(SecurityEvent).count()
                
                self.logger.info(f"📊 Migration Verification Results:")
                self.logger.info(f"   Users created: {user_count}")
                self.logger.info(f"   Admin users: {admin_count}")
                self.logger.info(f"   Audit log entries: {audit_count}")
                self.logger.info(f"   Security events: {security_event_count}")
                
                # Verify database connection
                db_health = db_manager.test_connection()
                if db_health:
                    self.logger.info("✅ Database connection verified")
                else:
                    raise Exception("Database connection test failed")
                
                # Verify all required tables exist
                from sqlalchemy import inspect
                inspector = inspect(db.bind)
                tables = inspector.get_table_names()
                
                required_tables = ["users", "audit_logs", "security_events", "threat_alerts"]
                missing_tables = [table for table in required_tables if table not in tables]
                
                if missing_tables:
                    raise Exception(f"Missing required tables: {missing_tables}")
                
                self.logger.info("✅ All required tables verified")
                
        except Exception as e:
            self.logger.error(f"❌ Migration verification failed: {e}")
            raise
    
    def print_migration_summary(self):
        """Print migration summary and next steps"""
        summary = """
🎉 BHIV Core Security Migration Completed Successfully!

📋 What was migrated:
   ✅ Security database tables created
   ✅ User authentication system with JWT
   ✅ Role-based access control (RBAC)
   ✅ Audit logging system
   ✅ Security monitoring setup
   ✅ Default users created

🔑 Default User Accounts Created:
   - admin@bhivcore.com (Admin)
   - ops@bhivcore.com (Operations)
   - sales@bhivcore.com (Sales)
   - support@bhivcore.com (Support)
   - customer@bhivcore.com (Customer)

⚠️  IMPORTANT SECURITY NOTES:
   1. Change all default passwords immediately in production
   2. Update JWT_SECRET_KEY in environment variables
   3. Configure SSL certificates for HTTPS
   4. Review and update security configuration
   5. Setup monitoring and alerting

🚀 Next Steps:
   1. Start the secure service: python secure_uniguru_service.py
   2. Test authentication: POST /auth/login
   3. Verify security endpoints work
   4. Configure production environment variables
   5. Setup SSL/TLS certificates

📚 Documentation:
   - API Documentation: API_DOCUMENTATION.md
   - Security Guide: Check security/ module
   - Production Setup: env.production.example

🔧 Troubleshooting:
   - Check logs for any errors
   - Verify database connectivity
   - Test JWT token generation
   - Validate RBAC permissions
        """
        
        print(summary)

async def main():
    """Main migration function"""
    migration = MigrationManager()
    
    try:
        await migration.run_full_migration()
        migration.print_migration_summary()
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    # Check if required environment variables are set
    required_env_vars = ["DATABASE_URL", "JWT_SECRET_KEY"]
    missing_vars = [var for var in required_env_vars if not os.getenv(var)]
    
    if missing_vars:
        logger.error(f"Missing required environment variables: {missing_vars}")
        logger.error("Please set up your .env file based on env.production.example")
        sys.exit(1)
    
    # Run migration
    asyncio.run(main())

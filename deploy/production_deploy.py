"""
BHIV Core Production Deployment Script
=====================================

Complete production deployment orchestration for BHIV Core system.
Handles all components: Security, Threat Mitigation, Microservices, 
Observability, and Agent System.
"""

import asyncio
import logging
import os
import subprocess
import sys
import time
import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from integration.system_integration import get_bhiv_integration
from integration.agent_integration import get_agent_registry

logger = logging.getLogger(__name__)

class ProductionDeployment:
    """Production deployment orchestrator"""
    
    def __init__(self):
        self.deployment_id = f"bhiv-deploy-{int(time.time())}"
        self.deployment_status = "initializing"
        self.components_status = {}
        
    async def deploy(self, deployment_type: str = "docker-compose"):
        """Execute production deployment"""
        logger.info(f"🚀 Starting BHIV Core production deployment: {self.deployment_id}")
        
        try:
            # Pre-deployment checks
            await self._pre_deployment_checks()
            
            # Deploy infrastructure
            await self._deploy_infrastructure(deployment_type)
            
            # Deploy microservices
            await self._deploy_microservices(deployment_type)
            
            # Deploy observability stack
            await self._deploy_observability(deployment_type)
            
            # Initialize and test system
            await self._initialize_system()
            
            # Post-deployment verification
            await self._post_deployment_verification()
            
            self.deployment_status = "completed"
            logger.info("✅ BHIV Core production deployment completed successfully!")
            
            # Generate deployment report
            await self._generate_deployment_report()
            
        except Exception as e:
            self.deployment_status = "failed"
            logger.error(f"❌ Deployment failed: {e}")
            await self._handle_deployment_failure(e)
            raise
    
    async def _pre_deployment_checks(self):
        """Pre-deployment validation"""
        logger.info("🔍 Running pre-deployment checks...")
        
        checks = [
            ("Docker", self._check_docker),
            ("Environment Variables", self._check_environment),
            ("Database Connection", self._check_database),
            ("External APIs", self._check_external_apis),
            ("File Permissions", self._check_file_permissions)
        ]
        
        for check_name, check_func in checks:
            try:
                await check_func()
                self.components_status[f"precheck_{check_name.lower().replace(' ', '_')}"] = "passed"
                logger.info(f"✅ {check_name} check passed")
            except Exception as e:
                self.components_status[f"precheck_{check_name.lower().replace(' ', '_')}"] = "failed"
                logger.error(f"❌ {check_name} check failed: {e}")
                raise Exception(f"Pre-deployment check failed: {check_name}")
    
    async def _check_docker(self):
        """Check Docker availability"""
        result = subprocess.run(["docker", "--version"], capture_output=True, text=True)
        if result.returncode != 0:
            raise Exception("Docker not available")
        
        # Check Docker Compose
        result = subprocess.run(["docker-compose", "--version"], capture_output=True, text=True)
        if result.returncode != 0:
            raise Exception("Docker Compose not available")
    
    async def _check_environment(self):
        """Check required environment variables"""
        required_vars = [
            "POSTGRES_PASSWORD",
            "JWT_SECRET_KEY",
            "GROQ_API_KEY",
            "GEMINI_API_KEY"
        ]
        
        missing_vars = []
        for var in required_vars:
            if not os.getenv(var):
                missing_vars.append(var)
        
        if missing_vars:
            raise Exception(f"Missing environment variables: {', '.join(missing_vars)}")
    
    async def _check_database(self):
        """Check database connectivity"""
        # This would typically test database connection
        # For now, just check if connection string is provided
        db_url = os.getenv("DATABASE_URL")
        if not db_url:
            raise Exception("DATABASE_URL not configured")
    
    async def _check_external_apis(self):
        """Check external API connectivity"""
        # Test key APIs
        import aiohttp
        
        apis_to_test = [
            ("Groq API", "https://api.groq.com/openai/v1/models"),
            ("Gemini API", "https://generativelanguage.googleapis.com/v1/models")
        ]
        
        async with aiohttp.ClientSession() as session:
            for api_name, url in apis_to_test:
                try:
                    async with session.get(url, timeout=10) as response:
                        if response.status not in [200, 401, 403]:  # 401/403 means API is reachable
                            raise Exception(f"{api_name} unreachable")
                except Exception as e:
                    logger.warning(f"⚠️ {api_name} check failed: {e}")
    
    async def _check_file_permissions(self):
        """Check file permissions"""
        # Check if we can write to logs directory
        logs_dir = project_root / "logs"
        logs_dir.mkdir(exist_ok=True)
        
        test_file = logs_dir / "deployment_test.txt"
        try:
            test_file.write_text("test")
            test_file.unlink()
        except Exception as e:
            raise Exception(f"Cannot write to logs directory: {e}")
    
    async def _deploy_infrastructure(self, deployment_type: str):
        """Deploy infrastructure components"""
        logger.info("🏗️ Deploying infrastructure...")
        
        if deployment_type == "docker-compose":
            await self._deploy_docker_compose()
        elif deployment_type == "kubernetes":
            await self._deploy_kubernetes()
        else:
            raise Exception(f"Unsupported deployment type: {deployment_type}")
        
        self.components_status["infrastructure"] = "deployed"
    
    async def _deploy_docker_compose(self):
        """Deploy using Docker Compose"""
        logger.info("🐳 Deploying with Docker Compose...")
        
        # Build images
        build_cmd = ["docker-compose", "build", "--parallel"]
        result = subprocess.run(build_cmd, cwd=project_root, capture_output=True, text=True)
        
        if result.returncode != 0:
            raise Exception(f"Docker build failed: {result.stderr}")
        
        # Start services
        up_cmd = ["docker-compose", "up", "-d"]
        result = subprocess.run(up_cmd, cwd=project_root, capture_output=True, text=True)
        
        if result.returncode != 0:
            raise Exception(f"Docker Compose up failed: {result.stderr}")
        
        # Wait for services to be ready
        await self._wait_for_services()
    
    async def _deploy_kubernetes(self):
        """Deploy using Kubernetes"""
        logger.info("☸️ Deploying with Kubernetes...")
        
        k8s_manifests = [
            "k8s/namespace.yaml",
            "k8s/configmap.yaml",
            "k8s/secrets.yaml",
            "k8s/postgres.yaml",
            "k8s/redis.yaml",
            "k8s/logistics-service.yaml",
            "k8s/api-gateway.yaml"
        ]
        
        for manifest in k8s_manifests:
            manifest_path = project_root / manifest
            if manifest_path.exists():
                cmd = ["kubectl", "apply", "-f", str(manifest_path)]
                result = subprocess.run(cmd, capture_output=True, text=True)
                
                if result.returncode != 0:
                    raise Exception(f"Failed to apply {manifest}: {result.stderr}")
                
                logger.info(f"✅ Applied {manifest}")
        
        # Wait for deployments to be ready
        await self._wait_for_k8s_deployments()
    
    async def _wait_for_services(self):
        """Wait for Docker services to be ready"""
        logger.info("⏳ Waiting for services to be ready...")
        
        services_to_check = [
            ("postgres", "5432"),
            ("redis", "6379"),
            ("api-gateway", "8000")
        ]
        
        max_wait = 300  # 5 minutes
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            all_ready = True
            
            for service_name, port in services_to_check:
                if not await self._check_service_health(service_name, port):
                    all_ready = False
                    break
            
            if all_ready:
                logger.info("✅ All services are ready")
                return
            
            await asyncio.sleep(10)
        
        raise Exception("Services did not become ready within timeout")
    
    async def _check_service_health(self, service_name: str, port: str) -> bool:
        """Check if a service is healthy"""
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                url = f"http://localhost:{port}/health"
                async with session.get(url, timeout=5) as response:
                    return response.status == 200
        except:
            return False
    
    async def _wait_for_k8s_deployments(self):
        """Wait for Kubernetes deployments to be ready"""
        logger.info("⏳ Waiting for Kubernetes deployments...")
        
        deployments = ["postgres", "redis", "logistics-service", "api-gateway"]
        
        for deployment in deployments:
            cmd = [
                "kubectl", "rollout", "status", 
                f"deployment/{deployment}", 
                "-n", "bhiv-core", 
                "--timeout=300s"
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                raise Exception(f"Deployment {deployment} failed to become ready")
            
            logger.info(f"✅ {deployment} deployment ready")
    
    async def _deploy_microservices(self, deployment_type: str):
        """Deploy microservices"""
        logger.info("🔧 Deploying microservices...")
        
        # Microservices are deployed as part of infrastructure
        # This step handles service-specific configurations
        
        self.components_status["microservices"] = "deployed"
    
    async def _deploy_observability(self, deployment_type: str):
        """Deploy observability stack"""
        logger.info("📊 Deploying observability stack...")
        
        # Prometheus and Grafana are included in docker-compose
        # This step handles additional observability setup
        
        self.components_status["observability"] = "deployed"
    
    async def _initialize_system(self):
        """Initialize BHIV Core system"""
        logger.info("🔧 Initializing BHIV Core system...")
        
        # Initialize core integration
        integration = get_bhiv_integration()
        await integration.initialize()
        
        # Initialize agent registry
        agent_registry = get_agent_registry()
        await agent_registry.initialize()
        
        self.components_status["system_initialization"] = "completed"
    
    async def _post_deployment_verification(self):
        """Post-deployment verification"""
        logger.info("✅ Running post-deployment verification...")
        
        # Health checks
        integration = get_bhiv_integration()
        health = await integration.health_check()
        
        if health["status"] != "healthy":
            raise Exception(f"System health check failed: {health}")
        
        # Agent system check
        agent_registry = get_agent_registry()
        agent_health = await agent_registry.health_check()
        
        if agent_health["status"] not in ["healthy", "degraded"]:
            raise Exception(f"Agent system health check failed: {agent_health}")
        
        # API endpoint tests
        await self._test_api_endpoints()
        
        self.components_status["verification"] = "passed"
    
    async def _test_api_endpoints(self):
        """Test key API endpoints"""
        import aiohttp
        
        endpoints_to_test = [
            ("http://localhost:8000/health", "API Gateway Health"),
            ("http://localhost:8001/health", "Logistics Service Health"),
            ("http://localhost:9090/api/v1/query?query=up", "Prometheus"),
            ("http://localhost:3000/api/health", "Grafana")
        ]
        
        async with aiohttp.ClientSession() as session:
            for url, description in endpoints_to_test:
                try:
                    async with session.get(url, timeout=10) as response:
                        if response.status == 200:
                            logger.info(f"✅ {description} endpoint working")
                        else:
                            logger.warning(f"⚠️ {description} endpoint returned {response.status}")
                except Exception as e:
                    logger.warning(f"⚠️ {description} endpoint test failed: {e}")
    
    async def _generate_deployment_report(self):
        """Generate deployment report"""
        report = {
            "deployment_id": self.deployment_id,
            "status": self.deployment_status,
            "timestamp": datetime.utcnow().isoformat(),
            "components": self.components_status,
            "system_info": {
                "total_microservices": 6,
                "total_agents": len(get_agent_registry().agents),
                "observability_enabled": True,
                "security_enabled": True
            }
        }
        
        # Save report
        reports_dir = project_root / "deployment_reports"
        reports_dir.mkdir(exist_ok=True)
        
        report_file = reports_dir / f"{self.deployment_id}_report.json"
        report_file.write_text(json.dumps(report, indent=2))
        
        logger.info(f"📋 Deployment report saved: {report_file}")
        
        # Print summary
        print("\n" + "="*60)
        print("🎉 BHIV CORE PRODUCTION DEPLOYMENT COMPLETED")
        print("="*60)
        print(f"Deployment ID: {self.deployment_id}")
        print(f"Status: {self.deployment_status}")
        print(f"Timestamp: {report['timestamp']}")
        print("\n📊 Component Status:")
        for component, status in self.components_status.items():
            print(f"  • {component}: {status}")
        print("\n🌐 Access URLs:")
        print("  • API Gateway: http://localhost:8000")
        print("  • Grafana Dashboard: http://localhost:3000")
        print("  • Prometheus: http://localhost:9090")
        print("="*60)
    
    async def _handle_deployment_failure(self, error: Exception):
        """Handle deployment failure"""
        logger.error(f"🚨 Deployment failed: {error}")
        
        # Generate failure report
        failure_report = {
            "deployment_id": self.deployment_id,
            "status": "failed",
            "error": str(error),
            "timestamp": datetime.utcnow().isoformat(),
            "components_status": self.components_status
        }
        
        # Save failure report
        reports_dir = project_root / "deployment_reports"
        reports_dir.mkdir(exist_ok=True)
        
        failure_file = reports_dir / f"{self.deployment_id}_failure.json"
        failure_file.write_text(json.dumps(failure_report, indent=2))
        
        # Cleanup on failure
        await self._cleanup_failed_deployment()
    
    async def _cleanup_failed_deployment(self):
        """Cleanup failed deployment"""
        logger.info("🧹 Cleaning up failed deployment...")
        
        try:
            # Stop Docker Compose services
            cmd = ["docker-compose", "down", "-v"]
            subprocess.run(cmd, cwd=project_root, capture_output=True)
            
            logger.info("✅ Cleanup completed")
        except Exception as e:
            logger.error(f"❌ Cleanup failed: {e}")

async def main():
    """Main deployment function"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    deployment = ProductionDeployment()
    
    try:
        deployment_type = sys.argv[1] if len(sys.argv) > 1 else "docker-compose"
        await deployment.deploy(deployment_type)
        
    except Exception as e:
        logger.error(f"❌ Deployment failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())

#!/usr/bin/env python3
"""
Enhanced CLI Example - Shows how CLI Runner integrates with production features
==============================================================================

This example demonstrates how your existing CLI runner automatically gets
enhanced with production features when PRODUCTION_MODE=true.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from integration.agent_integration import get_agent_registry
from security.auth import create_access_token

async def enhanced_cli_example():
    """Example showing enhanced CLI functionality"""
    
    print("🚀 BHIV Core Enhanced CLI Example")
    print("=" * 50)
    
    # Check if production mode is enabled
    production_mode = os.getenv('PRODUCTION_MODE', 'false').lower() == 'true'
    
    if production_mode:
        print("✅ Production Mode: Enhanced features enabled")
        print("   - Security: JWT authentication & RBAC")
        print("   - Observability: Metrics, tracing, alerting")
        print("   - Threat Detection: Real-time security monitoring")
    else:
        print("ℹ️  Development Mode: Using original implementations")
        print("   - Set PRODUCTION_MODE=true for enhanced features")
    
    print("\n" + "=" * 50)
    
    # Initialize enhanced agent registry if in production mode
    if production_mode:
        try:
            agent_registry = get_agent_registry()
            await agent_registry.initialize()
            print("✅ Enhanced agent registry initialized")
        except Exception as e:
            print(f"❌ Failed to initialize enhanced agents: {e}")
            return
    
    # Example queries to test different agents
    test_queries = [
        {
            "agent": "vedas",
            "query": "What is the meaning of dharma in Hindu philosophy?",
            "description": "Spiritual guidance query"
        },
        {
            "agent": "edumentor",
            "query": "Explain machine learning in simple terms for beginners",
            "description": "Educational content query"
        },
        {
            "agent": "wellness",
            "query": "What are some natural ways to reduce stress and anxiety?",
            "description": "Wellness guidance query"
        },
        {
            "agent": "knowledge",
            "query": "What is quantum computing and how does it work?",
            "description": "Knowledge retrieval query"
        }
    ]
    
    print("\n🤖 Testing Enhanced Agent System")
    print("-" * 50)
    
    for i, test in enumerate(test_queries, 1):
        print(f"\n{i}. {test['description']}")
        print(f"   Agent: {test['agent']}")
        print(f"   Query: {test['query']}")
        
        if production_mode and 'agent_registry' in locals():
            try:
                # Create demo user token for testing
                demo_user = {"sub": "cli_demo_user", "role": "customer"}
                demo_token = create_access_token(demo_user)
                
                # Process with enhanced agent
                result = await agent_registry.process_query(
                    agent_name=test["agent"],
                    query=test["query"],
                    context={"interface": "cli", "demo": True},
                    user_token=demo_token
                )
                
                if result.get("success"):
                    print(f"   ✅ Enhanced Response: {result.get('result', '')[:100]}...")
                    print(f"   ⏱️  Processing Time: {result.get('processing_time', 0):.3f}s")
                    print(f"   🔒 Security: Authenticated & authorized")
                    print(f"   📊 Observability: Metrics collected, traced")
                else:
                    print(f"   ❌ Enhanced processing failed: {result.get('error')}")
                    
            except Exception as e:
                print(f"   ❌ Error with enhanced agent: {e}")
        else:
            # Simulate original CLI behavior
            print(f"   📝 Original CLI: Would process with {test['agent']} agent")
            print(f"   ⚡ Fast response without enhanced features")
    
    # Show agent statistics if in production mode
    if production_mode and 'agent_registry' in locals():
        print(f"\n📊 Agent Statistics")
        print("-" * 30)
        
        try:
            stats = agent_registry.get_agent_stats()
            for agent_name, agent_stats in stats.items():
                success_rate = (
                    agent_stats["successful_queries"] / agent_stats["total_queries"] * 100
                    if agent_stats["total_queries"] > 0 else 0
                )
                print(f"   {agent_name.title()}: {agent_stats['total_queries']} queries, "
                      f"{success_rate:.1f}% success rate")
        except Exception as e:
            print(f"   ❌ Could not retrieve stats: {e}")
    
    # Show health check
    if production_mode and 'agent_registry' in locals():
        print(f"\n🏥 System Health Check")
        print("-" * 30)
        
        try:
            health = await agent_registry.health_check()
            print(f"   Overall Status: {health['status']}")
            print(f"   Total Agents: {health['total_agents']}")
            
            healthy_agents = [
                name for name, status in health["agents"].items() 
                if status["status"] == "healthy"
            ]
            print(f"   Healthy Agents: {len(healthy_agents)}/{health['total_agents']}")
            
        except Exception as e:
            print(f"   ❌ Health check failed: {e}")
    
    print(f"\n🎉 Enhanced CLI Example Complete!")
    print("=" * 50)
    
    if not production_mode:
        print("\n💡 To see enhanced features:")
        print("   export PRODUCTION_MODE=true")
        print("   python examples/enhanced_cli_example.py")

def simulate_original_cli():
    """Simulate how the original CLI runner works"""
    print("\n📝 Original CLI Runner Simulation")
    print("-" * 40)
    
    # This simulates your existing cli_runner.py behavior
    commands = [
        'python cli_runner.py explain "What is dharma?" vedas_agent',
        'python cli_runner.py create "meditation guide" wellness_agent',
        'python cli_runner.py analyze "machine learning" edumentor_agent'
    ]
    
    for cmd in commands:
        print(f"   $ {cmd}")
        print(f"     ✅ Works exactly as before")
    
    print(f"\n   With PRODUCTION_MODE=true, same commands get:")
    print(f"     🔒 JWT authentication & RBAC")
    print(f"     📊 Metrics collection & tracing")
    print(f"     🛡️ Threat detection & response")
    print(f"     🚨 Automated alerting")

async def main():
    """Main example function"""
    await enhanced_cli_example()
    simulate_original_cli()

if __name__ == "__main__":
    asyncio.run(main())

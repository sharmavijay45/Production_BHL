#!/usr/bin/env python3
"""
Fix RAG URLs in agent_configs.json to use environment variable
============================================================
"""

import json
import os
from dotenv import load_dotenv

load_dotenv()

def fix_rag_urls():
    """Update agent_configs.json to use RAG_API_URL from environment"""
    
    # Get RAG API URL from environment
    rag_api_url = os.getenv("RAG_API_URL", "https://61fe43d7354f.ngrok-free.app/rag").strip()
    
    print(f"🔧 Fixing RAG URLs in agent_configs.json")
    print(f"📋 Using RAG_API_URL from .env: {rag_api_url}")
    
    # Read current config
    config_path = "config/agent_configs.json"
    
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        # Count updates
        updated_count = 0
        
        # Update all agents with rag_api_url
        for agent_name, agent_config in config.items():
            if isinstance(agent_config, dict) and "rag_api_url" in agent_config:
                old_url = agent_config["rag_api_url"]
                agent_config["rag_api_url"] = rag_api_url
                updated_count += 1
                print(f"✅ Updated {agent_name}: {old_url} -> {rag_api_url}")
        
        # Write updated config
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=4)
        
        print(f"\n🎉 Successfully updated {updated_count} agents")
        print(f"📁 Config saved to: {config_path}")
        
    except Exception as e:
        print(f"❌ Error updating config: {e}")
        return False
    
    return True

if __name__ == "__main__":
    fix_rag_urls()

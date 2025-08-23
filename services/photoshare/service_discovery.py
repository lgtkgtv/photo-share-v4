#!/usr/bin/env python3
"""
Service Discovery Integration
============================

Provides service discovery capabilities using Consul and local service registry.
"""

import os
import aiohttp
import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

class ServiceDiscovery:
    """Service discovery and registration manager."""
    
    def __init__(self):
        self.consul_url = os.getenv("SERVICE_REGISTRY_URL", "http://consul:8500")
        self.service_name = "photo-share"
        self.service_id = f"{self.service_name}-{os.getenv('HOSTNAME', 'local')}"
        self.service_port = int(os.getenv("SERVICE_PORT", "8000"))
        self.service_host = os.getenv("SERVICE_HOST", "photo-share-platform")
        self.health_check_interval = 30
        
        # Local service registry as fallback
        self.local_services = {
            "photo-share": {
                "host": self.service_host,
                "port": self.service_port,
                "status": "healthy",
                "last_check": datetime.now(timezone.utc).isoformat()
            },
            "postgresql": {
                "host": "platform-db",
                "port": 5432,
                "status": "healthy",
                "last_check": datetime.now(timezone.utc).isoformat()
            },
            "redis": {
                "host": "redis-cache", 
                "port": 6379,
                "status": "healthy",
                "last_check": datetime.now(timezone.utc).isoformat()
            },
            "storage": {
                "host": "platform-storage",
                "port": 80,
                "status": "healthy",
                "last_check": datetime.now(timezone.utc).isoformat()
            },
            "prometheus": {
                "host": "platform-prometheus",
                "port": 9090,
                "status": "healthy",
                "last_check": datetime.now(timezone.utc).isoformat()
            },
            "grafana": {
                "host": "platform-grafana",
                "port": 3000,
                "status": "healthy",
                "last_check": datetime.now(timezone.utc).isoformat()
            }
        }
    
    async def register_service(self) -> bool:
        """Register this service with Consul."""
        try:
            service_definition = {
                "ID": self.service_id,
                "Name": self.service_name,
                "Tags": ["photo", "api", "platform", "database-integrated"],
                "Address": self.service_host,
                "Port": self.service_port,
                "Check": {
                    "HTTP": f"http://{self.service_host}:{self.service_port}/health",
                    "Interval": f"{self.health_check_interval}s",
                    "Timeout": "10s"
                },
                "Meta": {
                    "version": "2.1.0-database",
                    "features": "auth,storage,database",
                    "registered_at": datetime.now(timezone.utc).isoformat()
                }
            }
            
            # Try to register with Consul
            consul_registered = await self._register_with_consul(service_definition)
            
            if consul_registered:
                logger.info(f"Service {self.service_id} registered with Consul")
                return True
            else:
                logger.warning("Consul registration failed, using local registry")
                self.local_services[self.service_name]["status"] = "registered_locally"
                return True
                
        except Exception as e:
            logger.error(f"Service registration failed: {e}")
            return False
    
    async def _register_with_consul(self, service_def: Dict) -> bool:
        """Register service with Consul."""
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as session:
                url = f"{self.consul_url}/v1/agent/service/register"
                async with session.put(url, json=service_def) as response:
                    return response.status == 200
        except Exception as e:
            logger.debug(f"Consul registration failed: {e}")
            return False
    
    async def deregister_service(self) -> bool:
        """Deregister this service from Consul."""
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as session:
                url = f"{self.consul_url}/v1/agent/service/deregister/{self.service_id}"
                async with session.put(url) as response:
                    success = response.status == 200
                    if success:
                        logger.info(f"Service {self.service_id} deregistered from Consul")
                    return success
        except Exception as e:
            logger.warning(f"Service deregistration failed: {e}")
            return False
    
    async def discover_service(self, service_name: str) -> Optional[Dict[str, Any]]:
        """Discover a service by name."""
        try:
            # Try Consul first
            consul_service = await self._discover_from_consul(service_name)
            if consul_service:
                return consul_service
            
            # Fallback to local registry
            return self._discover_from_local_registry(service_name)
            
        except Exception as e:
            logger.error(f"Service discovery failed for {service_name}: {e}")
            return None
    
    async def _discover_from_consul(self, service_name: str) -> Optional[Dict[str, Any]]:
        """Discover service from Consul."""
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as session:
                url = f"{self.consul_url}/v1/health/service/{service_name}?passing=true"
                async with session.get(url) as response:
                    if response.status == 200:
                        services = await response.json()
                        if services:
                            service = services[0]  # Get first healthy instance
                            return {
                                "service_id": service["Service"]["ID"],
                                "service_name": service["Service"]["Service"],
                                "host": service["Service"]["Address"],
                                "port": service["Service"]["Port"],
                                "tags": service["Service"]["Tags"],
                                "meta": service["Service"]["Meta"],
                                "status": "healthy",
                                "source": "consul"
                            }
            return None
        except Exception as e:
            logger.debug(f"Consul discovery failed for {service_name}: {e}")
            return None
    
    def _discover_from_local_registry(self, service_name: str) -> Optional[Dict[str, Any]]:
        """Discover service from local registry."""
        if service_name in self.local_services:
            service = self.local_services[service_name]
            return {
                "service_name": service_name,
                "host": service["host"],
                "port": service["port"],
                "status": service["status"],
                "last_check": service["last_check"],
                "source": "local_registry"
            }
        return None
    
    async def list_services(self) -> Dict[str, List[Dict[str, Any]]]:
        """List all discovered services."""
        try:
            consul_services = await self._list_consul_services()
            local_services = self._list_local_services()
            
            return {
                "consul_services": consul_services,
                "local_services": local_services,
                "total_consul": len(consul_services),
                "total_local": len(local_services)
            }
            
        except Exception as e:
            logger.error(f"Service listing failed: {e}")
            return {"consul_services": [], "local_services": [], "total_consul": 0, "total_local": 0}
    
    async def _list_consul_services(self) -> List[Dict[str, Any]]:
        """List services from Consul."""
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as session:
                url = f"{self.consul_url}/v1/agent/services"
                async with session.get(url) as response:
                    if response.status == 200:
                        services = await response.json()
                        return [
                            {
                                "service_id": service["ID"],
                                "service_name": service["Service"],
                                "host": service["Address"],
                                "port": service["Port"],
                                "tags": service["Tags"],
                                "meta": service.get("Meta", {}),
                                "source": "consul"
                            }
                            for service in services.values()
                        ]
            return []
        except Exception:
            return []
    
    def _list_local_services(self) -> List[Dict[str, Any]]:
        """List services from local registry."""
        return [
            {
                "service_name": name,
                "host": service["host"],
                "port": service["port"],
                "status": service["status"],
                "last_check": service["last_check"],
                "source": "local_registry"
            }
            for name, service in self.local_services.items()
        ]
    
    async def health_check_services(self) -> Dict[str, Any]:
        """Perform health checks on known services."""
        results = {}
        
        for service_name, service_info in self.local_services.items():
            try:
                if service_name == "photo-share":
                    # Skip self
                    continue
                    
                health_status = await self._check_service_health(
                    service_info["host"],
                    service_info["port"],
                    service_name
                )
                
                results[service_name] = {
                    "host": service_info["host"],
                    "port": service_info["port"],
                    "status": "healthy" if health_status else "unhealthy",
                    "checked_at": datetime.now(timezone.utc).isoformat()
                }
                
                # Update local registry
                self.local_services[service_name]["status"] = "healthy" if health_status else "unhealthy"
                self.local_services[service_name]["last_check"] = results[service_name]["checked_at"]
                
            except Exception as e:
                results[service_name] = {
                    "host": service_info["host"],
                    "port": service_info["port"],
                    "status": "error",
                    "error": str(e),
                    "checked_at": datetime.now(timezone.utc).isoformat()
                }
        
        return results
    
    async def _check_service_health(self, host: str, port: int, service_name: str) -> bool:
        """Check if a service is healthy."""
        try:
            # Define health check endpoints for different services
            health_endpoints = {
                "postgresql": None,  # Use pg_isready instead
                "redis": None,       # Use redis-cli ping instead
                "storage": "/health",
                "prometheus": "/-/healthy",
                "grafana": "/api/health"
            }
            
            if service_name in ["postgresql", "redis"]:
                # For database services, try basic TCP connection
                reader, writer = await asyncio.wait_for(
                    asyncio.open_connection(host, port), timeout=5
                )
                writer.close()
                await writer.wait_closed()
                return True
            
            # For HTTP services, check health endpoint
            endpoint = health_endpoints.get(service_name, "/health")
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as session:
                url = f"http://{host}:{port}{endpoint}"
                async with session.get(url) as response:
                    return response.status == 200
                    
        except Exception:
            return False
    
    async def get_service_url(self, service_name: str, path: str = "") -> Optional[str]:
        """Get full URL for a service."""
        service = await self.discover_service(service_name)
        if service:
            protocol = "http"  # Could be enhanced to support HTTPS
            return f"{protocol}://{service['host']}:{service['port']}{path}"
        return None
    
    async def get_discovery_status(self) -> Dict[str, Any]:
        """Get service discovery system status."""
        try:
            # Check Consul connectivity
            consul_healthy = False
            try:
                async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=3)) as session:
                    url = f"{self.consul_url}/v1/status/leader"
                    async with session.get(url) as response:
                        consul_healthy = response.status == 200
            except Exception:
                consul_healthy = False
            
            service_health = await self.health_check_services()
            
            return {
                "consul_available": consul_healthy,
                "consul_url": self.consul_url,
                "service_id": self.service_id,
                "service_name": self.service_name,
                "local_registry_services": len(self.local_services),
                "service_health_checks": service_health,
                "discovery_mode": "consul" if consul_healthy else "local_registry"
            }
            
        except Exception as e:
            logger.error(f"Discovery status check failed: {e}")
            return {
                "consul_available": False,
                "error": str(e),
                "discovery_mode": "local_registry"
            }
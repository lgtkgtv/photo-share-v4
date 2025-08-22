"""
Unit tests for service discovery components.
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
import asyncio

from service_discovery import ServiceDiscovery


class TestServiceRegistry:
    """Test ServiceRegistry class."""

    @pytest.mark.unit
    def test_init(self):
        """Test service registry initialization."""
        registry = ServiceRegistry()
        
        assert registry is not None
        assert hasattr(registry, 'services')
        assert isinstance(registry.services, dict)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_register_service(self):
        """Test service registration."""
        registry = ServiceRegistry()
        
        await registry.register_service("photo-service", "localhost", 8000, {
            "version": "1.0.0",
            "environment": "test"
        })
        
        assert "photo-service" in registry.services
        service = registry.services["photo-service"]
        assert service["host"] == "localhost"
        assert service["port"] == 8000

    @pytest.mark.unit
    @pytest.mark.asyncio  
    async def test_deregister_service(self):
        """Test service deregistration."""
        registry = ServiceRegistry()
        
        # Register then deregister
        await registry.register_service("photo-service", "localhost", 8000)
        await registry.deregister_service("photo-service")
        
        assert "photo-service" not in registry.services

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_service(self):
        """Test getting service details."""
        registry = ServiceRegistry()
        
        await registry.register_service("photo-service", "localhost", 8000, {
            "version": "1.0.0"
        })
        
        service = await registry.get_service("photo-service")
        
        assert service is not None
        assert service["host"] == "localhost"
        assert service["port"] == 8000
        assert service["metadata"]["version"] == "1.0.0"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_list_services(self):
        """Test listing all services."""
        registry = ServiceRegistry()
        
        await registry.register_service("service1", "localhost", 8000)
        await registry.register_service("service2", "localhost", 8001)
        
        services = await registry.list_services()
        
        assert len(services) == 2
        assert "service1" in services
        assert "service2" in services


class TestHealthChecker:
    """Test HealthChecker class."""

    @pytest.mark.unit
    def test_init(self):
        """Test health checker initialization."""
        checker = HealthChecker()
        
        assert checker is not None
        assert hasattr(checker, 'check_interval')

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_check_service_health_success(self):
        """Test successful health check."""
        checker = HealthChecker()
        
        # Mock successful HTTP response
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_response = Mock()
            mock_response.status = 200
            mock_get.return_value.__aenter__.return_value = mock_response
            
            is_healthy = await checker.check_service_health("localhost", 8000, "/health")
            
            assert is_healthy is True

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_check_service_health_failure(self):
        """Test failed health check."""
        checker = HealthChecker()
        
        # Mock failed HTTP response
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_response = Mock()
            mock_response.status = 500
            mock_get.return_value.__aenter__.return_value = mock_response
            
            is_healthy = await checker.check_service_health("localhost", 8000, "/health")
            
            assert is_healthy is False

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_check_service_health_exception(self):
        """Test health check with connection exception."""
        checker = HealthChecker()
        
        # Mock connection exception
        with patch('aiohttp.ClientSession.get', side_effect=Exception("Connection failed")):
            is_healthy = await checker.check_service_health("localhost", 8000, "/health")
            
            assert is_healthy is False


class TestServiceDiscovery:
    """Test ServiceDiscovery class."""

    @pytest.mark.unit
    def test_init(self):
        """Test service discovery initialization."""
        discovery = ServiceDiscovery()
        
        assert discovery is not None
        assert hasattr(discovery, 'registry')
        assert hasattr(discovery, 'health_checker')

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_register_self(self):
        """Test self service registration."""
        discovery = ServiceDiscovery()
        
        await discovery.register_self("photo-service", "localhost", 8000, {
            "version": "1.0.0",
            "health_endpoint": "/health"
        })
        
        # Should not raise exception
        assert True

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_discover_services(self):
        """Test service discovery."""
        discovery = ServiceDiscovery()
        
        # Register a service first
        await discovery.register_self("photo-service", "localhost", 8000)
        
        services = await discovery.discover_services("photo")
        
        # Should return list (might be empty if filtering doesn't match)
        assert isinstance(services, list)

    @pytest.mark.unit  
    @pytest.mark.asyncio
    async def test_get_healthy_services(self):
        """Test getting healthy services."""
        discovery = ServiceDiscovery()
        
        healthy_services = await discovery.get_healthy_services()
        
        # Should return list
        assert isinstance(healthy_services, list)


class TestConsulServiceRegistry:
    """Test ConsulServiceRegistry class."""

    @pytest.mark.unit
    def test_init(self):
        """Test consul service registry initialization."""
        with patch('consul.aio.Consul'):
            registry = ConsulServiceRegistry("localhost", 8500)
            
            assert registry is not None
            assert hasattr(registry, 'consul')

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_register_service(self):
        """Test consul service registration."""
        with patch('consul.aio.Consul') as mock_consul:
            mock_agent = Mock()
            mock_agent.service = Mock()
            mock_agent.service.register = AsyncMock()
            mock_consul.return_value.agent = mock_agent
            
            registry = ConsulServiceRegistry("localhost", 8500)
            
            await registry.register_service("photo-service", "localhost", 8000, {
                "version": "1.0.0"
            })
            
            # Should call consul register
            mock_agent.service.register.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_deregister_service(self):
        """Test consul service deregistration."""
        with patch('consul.aio.Consul') as mock_consul:
            mock_agent = Mock()
            mock_agent.service = Mock()
            mock_agent.service.deregister = AsyncMock()
            mock_consul.return_value.agent = mock_agent
            
            registry = ConsulServiceRegistry("localhost", 8500)
            
            await registry.deregister_service("photo-service")
            
            # Should call consul deregister
            mock_agent.service.deregister.assert_called_once_with("photo-service")

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_service(self):
        """Test getting service from consul."""
        with patch('consul.aio.Consul') as mock_consul:
            mock_catalog = Mock()
            mock_catalog.service = AsyncMock(return_value=(None, [{
                'ServiceName': 'photo-service',
                'ServiceAddress': 'localhost', 
                'ServicePort': 8000,
                'ServiceMeta': {'version': '1.0.0'}
            }]))
            mock_consul.return_value.catalog = mock_catalog
            
            registry = ConsulServiceRegistry("localhost", 8500)
            
            service = await registry.get_service("photo-service")
            
            assert service is not None
            assert service["name"] == "photo-service"
            assert service["host"] == "localhost"
            assert service["port"] == 8000

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_list_services(self):
        """Test listing services from consul."""
        with patch('consul.aio.Consul') as mock_consul:
            mock_catalog = Mock()
            mock_catalog.services = AsyncMock(return_value=(None, {
                'photo-service': [],
                'user-service': []
            }))
            mock_consul.return_value.catalog = mock_catalog
            
            registry = ConsulServiceRegistry("localhost", 8500)
            
            services = await registry.list_services()
            
            assert isinstance(services, list)
            assert len(services) == 2
            assert 'photo-service' in services
            assert 'user-service' in services
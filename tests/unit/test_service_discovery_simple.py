"""
Unit tests for service discovery components.
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch

from service_discovery import ServiceDiscovery


class TestServiceDiscovery:
    """Test ServiceDiscovery class."""

    @pytest.mark.unit
    def test_init(self):
        """Test service discovery initialization."""
        discovery = ServiceDiscovery()
        
        assert discovery is not None
        assert hasattr(discovery, 'consul_client')

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_register_service(self):
        """Test service registration."""
        discovery = ServiceDiscovery()
        
        # Mock consul client
        with patch.object(discovery, 'consul_client') as mock_consul:
            mock_agent = Mock()
            mock_agent.service = Mock()
            mock_agent.service.register = AsyncMock()
            mock_consul.agent = mock_agent
            
            await discovery.register_service(
                service_name="photo-service",
                host="localhost", 
                port=8000,
                health_endpoint="/health"
            )
            
            # Should call consul register
            mock_agent.service.register.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_deregister_service(self):
        """Test service deregistration."""
        discovery = ServiceDiscovery()
        
        with patch.object(discovery, 'consul_client') as mock_consul:
            mock_agent = Mock()
            mock_agent.service = Mock()
            mock_agent.service.deregister = AsyncMock()
            mock_consul.agent = mock_agent
            
            await discovery.deregister_service("photo-service")
            
            mock_agent.service.deregister.assert_called_once_with("photo-service")

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_discover_services(self):
        """Test service discovery."""
        discovery = ServiceDiscovery()
        
        with patch.object(discovery, 'consul_client') as mock_consul:
            mock_catalog = Mock()
            mock_catalog.service = AsyncMock(return_value=(None, [
                {
                    'ServiceName': 'photo-service',
                    'ServiceAddress': 'localhost',
                    'ServicePort': 8000
                }
            ]))
            mock_consul.catalog = mock_catalog
            
            services = await discovery.discover_services("photo-service")
            
            assert isinstance(services, list)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_health_check(self):
        """Test health check functionality."""
        discovery = ServiceDiscovery()
        
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_response = Mock()
            mock_response.status = 200
            mock_get.return_value.__aenter__.return_value = mock_response
            
            is_healthy = await discovery.health_check("localhost", 8000, "/health")
            
            # Should return boolean
            assert isinstance(is_healthy, bool)
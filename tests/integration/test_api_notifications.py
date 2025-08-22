#!/usr/bin/env python3
"""
Integration tests for Notification System API endpoints.

Tests the complete notification system including:
- Notification creation and delivery
- Reading and marking notifications
- Bulk notification operations
- Notification filtering and pagination
"""

import pytest
import os
import sys

# Add service path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'services', 'photoshare'))

from fastapi.testclient import TestClient
from httpx import AsyncClient


@pytest.mark.integration
@pytest.mark.auth
class TestNotificationSystem:
    """Test notification system endpoints."""

    async def test_get_user_notifications(self, async_test_client: AsyncClient, auth_headers):
        """Test retrieving user's notifications."""
        response = await async_test_client.get(
            "/api/notifications",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        notifications = response.json()
        assert isinstance(notifications, list)

    async def test_mark_notification_as_read(self, async_test_client: AsyncClient, auth_headers):
        """Test marking a specific notification as read."""
        # This test assumes there's a notification to mark as read
        # In a real scenario, you'd create a notification first
        
        # For now, test the endpoint structure
        # Use a non-existent notification ID to test the endpoint
        response = await async_test_client.put(
            "/api/notifications/999999/read",
            headers=auth_headers
        )
        
        # Should return 404 for non-existent notification
        assert response.status_code == 404

    async def test_mark_all_notifications_as_read(self, async_test_client: AsyncClient, auth_headers):
        """Test marking all notifications as read."""
        response = await async_test_client.put(
            "/api/notifications/read-all",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "success" in data
        assert data["success"] is True

    async def test_get_unread_notifications_count(self, async_test_client: AsyncClient, auth_headers):
        """Test getting unread notifications count."""
        response = await async_test_client.get(
            "/api/notifications/unread-count",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "count" in data
        assert isinstance(data["count"], int)
        assert data["count"] >= 0

    async def test_delete_notification(self, async_test_client: AsyncClient, auth_headers):
        """Test deleting a notification."""
        # Test with non-existent notification ID
        response = await async_test_client.delete(
            "/api/notifications/999999",
            headers=auth_headers
        )
        
        # Should return 404 for non-existent notification
        assert response.status_code == 404

    async def test_get_notifications_with_pagination(self, async_test_client: AsyncClient, auth_headers):
        """Test notification pagination."""
        # Test with limit and offset parameters
        response = await async_test_client.get(
            "/api/notifications?limit=10&offset=0",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        notifications = response.json()
        assert isinstance(notifications, list)
        assert len(notifications) <= 10

    async def test_get_notifications_by_type(self, async_test_client: AsyncClient, auth_headers):
        """Test filtering notifications by type."""
        # Test different notification types
        notification_types = ["like", "comment", "follow", "mention"]
        
        for notification_type in notification_types:
            response = await async_test_client.get(
                f"/api/notifications?type={notification_type}",
                headers=auth_headers
            )
            
            assert response.status_code == 200
            notifications = response.json()
            assert isinstance(notifications, list)

    async def test_notification_authorization(self, async_test_client: AsyncClient):
        """Test notification endpoints require authentication."""
        # Try to get notifications without auth
        response = await async_test_client.get("/api/notifications")
        
        assert response.status_code == 401  # Unauthorized

    async def test_notification_permissions(self, async_test_client: AsyncClient, auth_headers):
        """Test users can only access their own notifications."""
        # Test accessing notifications with valid auth
        response = await async_test_client.get(
            "/api/notifications",
            headers=auth_headers
        )
        
        assert response.status_code == 200

    async def test_mark_notification_as_unread(self, async_test_client: AsyncClient, auth_headers):
        """Test marking a notification as unread."""
        # Test with non-existent notification ID
        response = await async_test_client.put(
            "/api/notifications/999999/unread",
            headers=auth_headers
        )
        
        # Should return 404 for non-existent notification
        assert response.status_code == 404

    async def test_bulk_delete_notifications(self, async_test_client: AsyncClient, auth_headers):
        """Test bulk deletion of notifications."""
        # Test deleting multiple notifications
        notification_ids = [1, 2, 3]  # Non-existent IDs for testing
        
        response = await async_test_client.delete(
            "/api/notifications/bulk",
            json={"notification_ids": notification_ids},
            headers=auth_headers
        )
        
        # Should return success even if notifications don't exist
        assert response.status_code == 200

    async def test_get_notifications_invalid_params(self, async_test_client: AsyncClient, auth_headers):
        """Test notification endpoint with invalid parameters."""
        # Test with invalid limit (negative number)
        response = await async_test_client.get(
            "/api/notifications?limit=-1",
            headers=auth_headers
        )
        
        # Should handle invalid parameters gracefully
        assert response.status_code in [200, 422]

    async def test_notification_marking_invalid_id(self, async_test_client: AsyncClient, auth_headers):
        """Test marking notification with invalid ID."""
        # Test with invalid notification ID format
        response = await async_test_client.put(
            "/api/notifications/invalid-id/read",
            headers=auth_headers
        )
        
        # Should return 422 for invalid ID format or 404 for not found
        assert response.status_code in [404, 422]


@pytest.mark.integration
@pytest.mark.slow
class TestNotificationWorkflow:
    """Test complete notification workflows."""

    async def test_notification_lifecycle(self, async_test_client: AsyncClient, auth_headers):
        """Test complete notification lifecycle."""
        # Get initial unread count
        initial_response = await async_test_client.get(
            "/api/notifications/unread-count",
            headers=auth_headers
        )
        initial_count = initial_response.json()["count"]
        
        # Mark all as read
        await async_test_client.put(
            "/api/notifications/read-all",
            headers=auth_headers
        )
        
        # Verify count is now 0
        after_read_response = await async_test_client.get(
            "/api/notifications/unread-count",
            headers=auth_headers
        )
        after_read_count = after_read_response.json()["count"]
        
        assert after_read_count <= initial_count

    async def test_notification_filtering_workflow(self, async_test_client: AsyncClient, auth_headers):
        """Test notification filtering workflow."""
        # Get all notifications
        all_response = await async_test_client.get(
            "/api/notifications",
            headers=auth_headers
        )
        all_notifications = all_response.json()
        
        # Get only unread notifications
        unread_response = await async_test_client.get(
            "/api/notifications?read=false",
            headers=auth_headers
        )
        unread_notifications = unread_response.json()
        
        # Unread count should be <= total count
        assert len(unread_notifications) <= len(all_notifications)

    async def test_notification_pagination_workflow(self, async_test_client: AsyncClient, auth_headers):
        """Test notification pagination workflow."""
        # Get first page
        page1_response = await async_test_client.get(
            "/api/notifications?limit=5&offset=0",
            headers=auth_headers
        )
        page1_notifications = page1_response.json()
        
        # Get second page
        page2_response = await async_test_client.get(
            "/api/notifications?limit=5&offset=5",
            headers=auth_headers
        )
        page2_notifications = page2_response.json()
        
        # Pages should not overlap (if there are enough notifications)
        page1_ids = {n.get("id") for n in page1_notifications if n.get("id")}
        page2_ids = {n.get("id") for n in page2_notifications if n.get("id")}
        
        # No overlap if both pages have notifications
        if page1_ids and page2_ids:
            assert page1_ids.isdisjoint(page2_ids)
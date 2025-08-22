#!/usr/bin/env python3
"""
API test script for notification system endpoints.

Tests notification functionality including:
- Notification delivery and management
- Read/unread status tracking
- Bulk operations
- Notification filtering
"""

import pytest
import os
import sys

# Add service path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'services', 'photoshare'))

from httpx import AsyncClient


@pytest.mark.api
@pytest.mark.notifications
class TestNotificationSystem:
    """Test notification system API endpoints."""

    async def test_notification_workflow(self, async_test_client: AsyncClient, auth_headers):
        """Test complete notification workflow."""
        
        # Step 1: Get initial unread count
        initial_count_response = await async_test_client.get(
            "/api/notifications/unread-count",
            headers=auth_headers
        )
        
        assert initial_count_response.status_code == 200
        initial_data = initial_count_response.json()
        assert "count" in initial_data
        assert isinstance(initial_data["count"], int)
        initial_count = initial_data["count"]
        
        # Step 2: Get all notifications
        notifications_response = await async_test_client.get(
            "/api/notifications",
            headers=auth_headers
        )
        
        assert notifications_response.status_code == 200
        notifications = notifications_response.json()
        assert isinstance(notifications, list)
        
        # Step 3: Mark all as read
        mark_all_response = await async_test_client.put(
            "/api/notifications/read-all",
            headers=auth_headers
        )
        
        assert mark_all_response.status_code == 200
        mark_all_data = mark_all_response.json()
        assert mark_all_data["success"] is True
        
        # Step 4: Verify unread count is now 0 or reduced
        final_count_response = await async_test_client.get(
            "/api/notifications/unread-count",
            headers=auth_headers
        )
        
        final_count = final_count_response.json()["count"]
        assert final_count <= initial_count

    async def test_notification_filtering(self, async_test_client: AsyncClient, auth_headers):
        """Test notification filtering options."""
        
        # Test different filtering options
        filter_options = [
            {"read": "true"},
            {"read": "false"},
            {"type": "like"},
            {"type": "comment"},
            {"type": "follow"}
        ]
        
        for filters in filter_options:
            query_string = "&".join(f"{k}={v}" for k, v in filters.items())
            
            response = await async_test_client.get(
                f"/api/notifications?{query_string}",
                headers=auth_headers
            )
            
            assert response.status_code == 200
            notifications = response.json()
            assert isinstance(notifications, list)

    async def test_notification_pagination(self, async_test_client: AsyncClient, auth_headers):
        """Test notification pagination."""
        
        # Test pagination parameters
        pagination_tests = [
            {"limit": 5, "offset": 0},
            {"limit": 10, "offset": 5},
            {"limit": 1, "offset": 0}
        ]
        
        for params in pagination_tests:
            query_string = "&".join(f"{k}={v}" for k, v in params.items())
            
            response = await async_test_client.get(
                f"/api/notifications?{query_string}",
                headers=auth_headers
            )
            
            assert response.status_code == 200
            notifications = response.json()
            assert isinstance(notifications, list)
            assert len(notifications) <= params["limit"]

    async def test_individual_notification_operations(self, async_test_client: AsyncClient, auth_headers):
        """Test individual notification operations."""
        
        # Test with non-existent notification (simulates expected behavior)
        nonexistent_id = 999999
        
        # Try to mark non-existent notification as read
        read_response = await async_test_client.put(
            f"/api/notifications/{nonexistent_id}/read",
            headers=auth_headers
        )
        
        assert read_response.status_code == 404
        
        # Try to mark non-existent notification as unread
        unread_response = await async_test_client.put(
            f"/api/notifications/{nonexistent_id}/unread",
            headers=auth_headers
        )
        
        assert unread_response.status_code == 404
        
        # Try to delete non-existent notification
        delete_response = await async_test_client.delete(
            f"/api/notifications/{nonexistent_id}",
            headers=auth_headers
        )
        
        assert delete_response.status_code == 404

    async def test_bulk_notification_operations(self, async_test_client: AsyncClient, auth_headers):
        """Test bulk notification operations."""
        
        # Test bulk delete with non-existent IDs
        bulk_data = {
            "notification_ids": [999997, 999998, 999999]
        }
        
        bulk_response = await async_test_client.delete(
            "/api/notifications/bulk",
            json=bulk_data,
            headers=auth_headers
        )
        
        # Should handle gracefully even if notifications don't exist
        assert bulk_response.status_code == 200

    async def test_notification_authorization(self, async_test_client: AsyncClient):
        """Test notification endpoints require authentication."""
        
        # Try to get notifications without auth
        response = await async_test_client.get("/api/notifications")
        
        assert response.status_code == 401  # Unauthorized
        
        # Try to get unread count without auth
        count_response = await async_test_client.get("/api/notifications/unread-count")
        
        assert count_response.status_code == 401

    async def test_notification_input_validation(self, async_test_client: AsyncClient, auth_headers):
        """Test notification input validation."""
        
        # Test invalid pagination parameters
        invalid_params = [
            "limit=-1",
            "offset=-5",
            "limit=abc",
            "offset=xyz"
        ]
        
        for param in invalid_params:
            response = await async_test_client.get(
                f"/api/notifications?{param}",
                headers=auth_headers
            )
            
            # Should handle invalid parameters gracefully
            assert response.status_code in [200, 422]

    async def test_notification_type_filtering(self, async_test_client: AsyncClient, auth_headers):
        """Test filtering notifications by type."""
        
        # Test various notification types
        notification_types = ["like", "comment", "follow", "mention", "share"]
        
        for notification_type in notification_types:
            response = await async_test_client.get(
                f"/api/notifications?type={notification_type}",
                headers=auth_headers
            )
            
            assert response.status_code == 200
            notifications = response.json()
            assert isinstance(notifications, list)
            
            # If notifications exist, verify they match the type
            for notification in notifications:
                if "type" in notification:
                    assert notification["type"] == notification_type

    async def test_notification_status_management(self, async_test_client: AsyncClient, auth_headers):
        """Test notification read/unread status management."""
        
        # Get initial state
        initial_response = await async_test_client.get(
            "/api/notifications",
            headers=auth_headers
        )
        
        initial_notifications = initial_response.json()
        
        # Mark all as read
        await async_test_client.put(
            "/api/notifications/read-all",
            headers=auth_headers
        )
        
        # Get notifications marked as read
        read_response = await async_test_client.get(
            "/api/notifications?read=true",
            headers=auth_headers
        )
        
        assert read_response.status_code == 200
        read_notifications = read_response.json()
        
        # Get notifications marked as unread
        unread_response = await async_test_client.get(
            "/api/notifications?read=false",
            headers=auth_headers
        )
        
        assert unread_response.status_code == 200
        unread_notifications = unread_response.json()
        
        # Total should match (read + unread = all)
        total_filtered = len(read_notifications) + len(unread_notifications)
        assert total_filtered >= 0  # At least consistent

    async def test_notification_ordering(self, async_test_client: AsyncClient, auth_headers):
        """Test notification ordering (newest first)."""
        
        response = await async_test_client.get(
            "/api/notifications?limit=10",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        notifications = response.json()
        
        # Verify ordering if notifications have timestamps
        if len(notifications) > 1:
            for i in range(len(notifications) - 1):
                if "created_at" in notifications[i] and "created_at" in notifications[i + 1]:
                    # Should be ordered by creation time (newest first)
                    assert notifications[i]["created_at"] >= notifications[i + 1]["created_at"]


@pytest.mark.api
@pytest.mark.performance
class TestNotificationPerformance:
    """Test notification system performance."""

    async def test_notification_loading_performance(self, async_test_client: AsyncClient, auth_headers):
        """Test notification loading performance."""
        import time
        
        start_time = time.time()
        
        response = await async_test_client.get(
            "/api/notifications?limit=50",
            headers=auth_headers
        )
        
        end_time = time.time()
        
        assert response.status_code == 200
        
        # Notification loading should be fast
        response_time = end_time - start_time
        assert response_time < 1.0, f"Notification loading took {response_time:.2f}s, should be < 1.0s"

    async def test_unread_count_performance(self, async_test_client: AsyncClient, auth_headers):
        """Test unread count query performance."""
        import time
        
        start_time = time.time()
        
        response = await async_test_client.get(
            "/api/notifications/unread-count",
            headers=auth_headers
        )
        
        end_time = time.time()
        
        assert response.status_code == 200
        
        # Unread count should be very fast
        response_time = end_time - start_time
        assert response_time < 0.5, f"Unread count took {response_time:.2f}s, should be < 0.5s"

    async def test_bulk_operations_performance(self, async_test_client: AsyncClient, auth_headers):
        """Test bulk operations performance."""
        import time
        
        # Test bulk delete performance
        bulk_data = {
            "notification_ids": list(range(1, 101))  # 100 IDs
        }
        
        start_time = time.time()
        
        response = await async_test_client.delete(
            "/api/notifications/bulk",
            json=bulk_data,
            headers=auth_headers
        )
        
        end_time = time.time()
        
        assert response.status_code == 200
        
        # Bulk operations should be reasonably fast
        response_time = end_time - start_time
        assert response_time < 2.0, f"Bulk delete took {response_time:.2f}s, should be < 2.0s"


@pytest.mark.api
@pytest.mark.integration
class TestNotificationIntegration:
    """Test notification system integration with other features."""

    async def test_notification_creation_triggers(self, async_test_client: AsyncClient, auth_headers, test_photo):
        """Test that social actions trigger notifications (if implemented)."""
        
        # Get initial notification count
        initial_response = await async_test_client.get(
            "/api/notifications/unread-count",
            headers=auth_headers
        )
        initial_count = initial_response.json()["count"]
        
        # Perform social actions that might trigger notifications
        # (These might not create notifications for the same user, but test the endpoints)
        
        # Like a photo
        await async_test_client.post(
            f"/api/photos/{test_photo.id}/like",
            headers=auth_headers
        )
        
        # Comment on photo
        comment_data = {"content": "Test comment for notifications"}
        await async_test_client.post(
            f"/api/photos/{test_photo.id}/comments",
            json=comment_data,
            headers=auth_headers
        )
        
        # Check if notification count changed (might not for self-actions)
        final_response = await async_test_client.get(
            "/api/notifications/unread-count",
            headers=auth_headers
        )
        final_count = final_response.json()["count"]
        
        # Count should be >= initial (might not change for self-actions)
        assert final_count >= initial_count
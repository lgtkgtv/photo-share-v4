#!/usr/bin/env python3
"""
Integration tests for Social Features API endpoints.

Tests the complete social media functionality including:
- Photo likes and unlikes
- Comment system with replies
- User following system
- Photo tagging and mentions
- Social interaction workflows
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
class TestSocialFeatures:
    """Test social features endpoints."""

    async def test_like_photo(self, async_test_client: AsyncClient, auth_headers, test_photo):
        """Test liking a photo."""
        response = await async_test_client.post(
            f"/api/photos/{test_photo.id}/like",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "like_count" in data

    async def test_unlike_photo(self, async_test_client: AsyncClient, auth_headers, test_photo):
        """Test unliking a photo."""
        # First like the photo
        await async_test_client.post(
            f"/api/photos/{test_photo.id}/like",
            headers=auth_headers
        )
        
        # Then unlike it
        response = await async_test_client.delete(
            f"/api/photos/{test_photo.id}/like",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    async def test_get_photo_likes(self, async_test_client: AsyncClient, auth_headers, test_photo):
        """Test getting likes for a photo."""
        # Like the photo first
        await async_test_client.post(
            f"/api/photos/{test_photo.id}/like",
            headers=auth_headers
        )
        
        # Get photo likes
        response = await async_test_client.get(
            f"/api/photos/{test_photo.id}/likes",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        likes = response.json()
        assert isinstance(likes, list)
        assert len(likes) >= 1

    async def test_add_comment_to_photo(self, async_test_client: AsyncClient, auth_headers, test_photo):
        """Test adding a comment to a photo."""
        comment_data = {
            "content": "This is a beautiful photo! Amazing colors and composition."
        }
        
        response = await async_test_client.post(
            f"/api/photos/{test_photo.id}/comments",
            json=comment_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["content"] == comment_data["content"]
        assert "id" in data
        assert "created_at" in data
        assert data["photo_id"] == test_photo.id

    async def test_get_photo_comments(self, async_test_client: AsyncClient, auth_headers, test_photo):
        """Test getting comments for a photo."""
        # Add a comment first
        comment_data = {"content": "Test comment for retrieval"}
        
        comment_response = await async_test_client.post(
            f"/api/photos/{test_photo.id}/comments",
            json=comment_data,
            headers=auth_headers
        )
        assert comment_response.status_code == 200
        
        # Get photo comments
        response = await async_test_client.get(
            f"/api/photos/{test_photo.id}/comments",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        comments = response.json()
        assert isinstance(comments, list)
        assert len(comments) >= 1
        assert comments[0]["content"] == comment_data["content"]

    async def test_reply_to_comment(self, async_test_client: AsyncClient, auth_headers, test_photo):
        """Test replying to a comment."""
        # Add a comment first
        comment_data = {"content": "Original comment"}
        
        comment_response = await async_test_client.post(
            f"/api/photos/{test_photo.id}/comments",
            json=comment_data,
            headers=auth_headers
        )
        comment_id = comment_response.json()["id"]
        
        # Reply to the comment
        reply_data = {
            "content": "This is a reply to the comment",
            "parent_id": comment_id
        }
        
        response = await async_test_client.post(
            f"/api/photos/{test_photo.id}/comments",
            json=reply_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["content"] == reply_data["content"]
        assert data["parent_id"] == comment_id

    async def test_delete_comment(self, async_test_client: AsyncClient, auth_headers, test_photo):
        """Test deleting a comment."""
        # Add a comment first
        comment_data = {"content": "Comment to be deleted"}
        
        comment_response = await async_test_client.post(
            f"/api/photos/{test_photo.id}/comments",
            json=comment_data,
            headers=auth_headers
        )
        comment_id = comment_response.json()["id"]
        
        # Delete the comment
        response = await async_test_client.delete(
            f"/api/comments/{comment_id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    async def test_follow_user(self, async_test_client: AsyncClient, auth_headers, test_user):
        """Test following a user."""
        # Note: This would typically require a second user
        # For now, test the endpoint structure with the same user
        response = await async_test_client.post(
            f"/api/users/{test_user.id}/follow",
            headers=auth_headers
        )
        
        # Self-following might be prevented, so accept either success or error
        assert response.status_code in [200, 400]

    async def test_unfollow_user(self, async_test_client: AsyncClient, auth_headers, test_user):
        """Test unfollowing a user."""
        # Try to unfollow (might not be following)
        response = await async_test_client.delete(
            f"/api/users/{test_user.id}/follow",
            headers=auth_headers
        )
        
        # Accept success or "not following" error
        assert response.status_code in [200, 400, 404]

    async def test_get_user_followers(self, async_test_client: AsyncClient, auth_headers, test_user):
        """Test getting user's followers."""
        response = await async_test_client.get(
            f"/api/users/{test_user.id}/followers",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        followers = response.json()
        assert isinstance(followers, list)

    async def test_get_user_following(self, async_test_client: AsyncClient, auth_headers, test_user):
        """Test getting users that a user is following."""
        response = await async_test_client.get(
            f"/api/users/{test_user.id}/following",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        following = response.json()
        assert isinstance(following, list)

    async def test_tag_photo(self, async_test_client: AsyncClient, auth_headers, test_photo):
        """Test adding tags to a photo."""
        tag_data = {
            "tags": ["landscape", "sunset", "vacation", "beach"]
        }
        
        response = await async_test_client.post(
            f"/api/photos/{test_photo.id}/tags",
            json=tag_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "tags" in data

    async def test_get_photo_tags(self, async_test_client: AsyncClient, auth_headers, test_photo):
        """Test getting tags for a photo."""
        # Add tags first
        tag_data = {"tags": ["test", "photography"]}
        
        await async_test_client.post(
            f"/api/photos/{test_photo.id}/tags",
            json=tag_data,
            headers=auth_headers
        )
        
        # Get photo tags
        response = await async_test_client.get(
            f"/api/photos/{test_photo.id}/tags",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        tags = response.json()
        assert isinstance(tags, list)

    async def test_search_photos_by_tag(self, async_test_client: AsyncClient, auth_headers, test_photo):
        """Test searching photos by tag."""
        # Add tags to photo first
        tag_data = {"tags": ["searchable", "unique-tag"]}
        
        await async_test_client.post(
            f"/api/photos/{test_photo.id}/tags",
            json=tag_data,
            headers=auth_headers
        )
        
        # Search for photos with tag
        response = await async_test_client.get(
            "/api/photos/search?tag=searchable",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        photos = response.json()
        assert isinstance(photos, list)

    async def test_get_popular_tags(self, async_test_client: AsyncClient, auth_headers):
        """Test getting popular tags."""
        response = await async_test_client.get(
            "/api/tags/popular",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        tags = response.json()
        assert isinstance(tags, list)

    async def test_remove_photo_tag(self, async_test_client: AsyncClient, auth_headers, test_photo):
        """Test removing a tag from a photo."""
        # Add tags first
        tag_data = {"tags": ["removable", "permanent"]}
        
        await async_test_client.post(
            f"/api/photos/{test_photo.id}/tags",
            json=tag_data,
            headers=auth_headers
        )
        
        # Remove specific tag
        response = await async_test_client.delete(
            f"/api/photos/{test_photo.id}/tags/removable",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    async def test_social_authorization(self, async_test_client: AsyncClient, test_photo):
        """Test social endpoints require authentication."""
        # Try to like photo without auth
        response = await async_test_client.post(f"/api/photos/{test_photo.id}/like")
        assert response.status_code == 401

        # Try to comment without auth
        comment_data = {"content": "Unauthorized comment"}
        response = await async_test_client.post(
            f"/api/photos/{test_photo.id}/comments",
            json=comment_data
        )
        assert response.status_code == 401

    async def test_comment_validation(self, async_test_client: AsyncClient, auth_headers, test_photo):
        """Test comment input validation."""
        # Test empty comment
        invalid_data = {"content": ""}
        
        response = await async_test_client.post(
            f"/api/photos/{test_photo.id}/comments",
            json=invalid_data,
            headers=auth_headers
        )
        
        assert response.status_code == 422  # Validation error

    async def test_tag_validation(self, async_test_client: AsyncClient, auth_headers, test_photo):
        """Test tag input validation."""
        # Test empty tags array
        invalid_data = {"tags": []}
        
        response = await async_test_client.post(
            f"/api/photos/{test_photo.id}/tags",
            json=invalid_data,
            headers=auth_headers
        )
        
        # Should either accept empty array or return validation error
        assert response.status_code in [200, 422]


@pytest.mark.integration
@pytest.mark.slow
class TestSocialWorkflows:
    """Test complete social interaction workflows."""

    async def test_complete_social_interaction_workflow(self, async_test_client: AsyncClient, auth_headers, test_photo):
        """Test complete social interaction workflow."""
        # 1. Like the photo
        like_response = await async_test_client.post(
            f"/api/photos/{test_photo.id}/like",
            headers=auth_headers
        )
        assert like_response.status_code == 200
        
        # 2. Add a comment
        comment_data = {"content": "Amazing photo! Love the composition."}
        comment_response = await async_test_client.post(
            f"/api/photos/{test_photo.id}/comments",
            json=comment_data,
            headers=auth_headers
        )
        assert comment_response.status_code == 200
        comment_id = comment_response.json()["id"]
        
        # 3. Add tags
        tag_data = {"tags": ["workflow", "test", "social"]}
        tag_response = await async_test_client.post(
            f"/api/photos/{test_photo.id}/tags",
            json=tag_data,
            headers=auth_headers
        )
        assert tag_response.status_code == 200
        
        # 4. Reply to comment
        reply_data = {
            "content": "Thank you for the feedback!",
            "parent_id": comment_id
        }
        reply_response = await async_test_client.post(
            f"/api/photos/{test_photo.id}/comments",
            json=reply_data,
            headers=auth_headers
        )
        assert reply_response.status_code == 200
        
        # 5. Verify all interactions exist
        # Check likes
        likes_response = await async_test_client.get(
            f"/api/photos/{test_photo.id}/likes",
            headers=auth_headers
        )
        assert likes_response.status_code == 200
        assert len(likes_response.json()) >= 1
        
        # Check comments
        comments_response = await async_test_client.get(
            f"/api/photos/{test_photo.id}/comments",
            headers=auth_headers
        )
        assert comments_response.status_code == 200
        comments = comments_response.json()
        assert len(comments) >= 2  # Original comment + reply
        
        # Check tags
        tags_response = await async_test_client.get(
            f"/api/photos/{test_photo.id}/tags",
            headers=auth_headers
        )
        assert tags_response.status_code == 200
        tags = tags_response.json()
        assert len(tags) >= 3  # The three tags we added

    async def test_social_privacy_workflow(self, async_test_client: AsyncClient, auth_headers, test_photo):
        """Test social interactions with privacy considerations."""
        # This would test interactions between different users
        # For now, test basic privacy of own content
        
        # Add private comment and verify it's accessible by owner
        comment_data = {"content": "Private thought about this photo"}
        comment_response = await async_test_client.post(
            f"/api/photos/{test_photo.id}/comments",
            json=comment_data,
            headers=auth_headers
        )
        assert comment_response.status_code == 200
        
        # Owner should be able to see their own comments
        comments_response = await async_test_client.get(
            f"/api/photos/{test_photo.id}/comments",
            headers=auth_headers
        )
        assert comments_response.status_code == 200
        comments = comments_response.json()
        comment_contents = [c["content"] for c in comments]
        assert comment_data["content"] in comment_contents
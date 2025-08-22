#!/usr/bin/env python3
"""
API test script for social features endpoints.

Tests social media functionality including:
- Photo likes and interactions
- Comment system
- User following
- Photo tagging and search
- Social workflows
"""

import pytest
import os
import sys

# Add service path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'services', 'photoshare'))

from httpx import AsyncClient


@pytest.mark.api
@pytest.mark.social
class TestSocialInteractions:
    """Test social interaction endpoints."""

    async def test_like_unlike_workflow(self, async_test_client: AsyncClient, auth_headers, test_photo):
        """Test complete like/unlike workflow."""
        
        # Step 1: Like the photo
        like_response = await async_test_client.post(
            f"/api/photos/{test_photo.id}/like",
            headers=auth_headers
        )
        
        assert like_response.status_code == 200
        like_data = like_response.json()
        assert like_data["success"] is True
        assert "like_count" in like_data
        initial_like_count = like_data["like_count"]
        
        # Step 2: Verify like exists
        likes_response = await async_test_client.get(
            f"/api/photos/{test_photo.id}/likes",
            headers=auth_headers
        )
        
        assert likes_response.status_code == 200
        likes = likes_response.json()
        assert len(likes) == initial_like_count
        
        # Step 3: Unlike the photo
        unlike_response = await async_test_client.delete(
            f"/api/photos/{test_photo.id}/like",
            headers=auth_headers
        )
        
        assert unlike_response.status_code == 200
        unlike_data = unlike_response.json()
        assert unlike_data["success"] is True
        
        # Step 4: Verify like is removed
        final_likes_response = await async_test_client.get(
            f"/api/photos/{test_photo.id}/likes",
            headers=auth_headers
        )
        
        final_likes = final_likes_response.json()
        assert len(final_likes) == initial_like_count - 1

    async def test_comment_workflow(self, async_test_client: AsyncClient, auth_headers, test_photo):
        """Test complete comment workflow."""
        
        # Step 1: Add comment
        comment_data = {
            "content": "This is an amazing photo! Love the composition and lighting."
        }
        
        comment_response = await async_test_client.post(
            f"/api/photos/{test_photo.id}/comments",
            json=comment_data,
            headers=auth_headers
        )
        
        assert comment_response.status_code == 200
        comment = comment_response.json()
        assert comment["content"] == comment_data["content"]
        assert comment["photo_id"] == test_photo.id
        assert "id" in comment
        comment_id = comment["id"]
        
        # Step 2: Reply to comment
        reply_data = {
            "content": "Thank you so much! I'm glad you like it.",
            "parent_id": comment_id
        }
        
        reply_response = await async_test_client.post(
            f"/api/photos/{test_photo.id}/comments",
            json=reply_data,
            headers=auth_headers
        )
        
        assert reply_response.status_code == 200
        reply = reply_response.json()
        assert reply["content"] == reply_data["content"]
        assert reply["parent_id"] == comment_id
        
        # Step 3: Get all comments
        comments_response = await async_test_client.get(
            f"/api/photos/{test_photo.id}/comments",
            headers=auth_headers
        )
        
        assert comments_response.status_code == 200
        comments = comments_response.json()
        assert len(comments) >= 2  # Original comment + reply
        
        # Step 4: Delete comment
        delete_response = await async_test_client.delete(
            f"/api/comments/{comment_id}",
            headers=auth_headers
        )
        
        assert delete_response.status_code == 200

    async def test_tagging_workflow(self, async_test_client: AsyncClient, auth_headers, test_photo):
        """Test photo tagging workflow."""
        
        # Step 1: Add tags to photo
        tag_data = {
            "tags": ["landscape", "nature", "sunset", "photography", "beautiful"]
        }
        
        tag_response = await async_test_client.post(
            f"/api/photos/{test_photo.id}/tags",
            json=tag_data,
            headers=auth_headers
        )
        
        assert tag_response.status_code == 200
        tag_result = tag_response.json()
        assert tag_result["success"] is True
        
        # Step 2: Get photo tags
        tags_response = await async_test_client.get(
            f"/api/photos/{test_photo.id}/tags",
            headers=auth_headers
        )
        
        assert tags_response.status_code == 200
        tags = tags_response.json()
        assert len(tags) == len(tag_data["tags"])
        
        tag_names = [tag["name"] if isinstance(tag, dict) else tag for tag in tags]
        for expected_tag in tag_data["tags"]:
            assert expected_tag in tag_names
        
        # Step 3: Search photos by tag
        search_response = await async_test_client.get(
            "/api/photos/search?tag=landscape",
            headers=auth_headers
        )
        
        assert search_response.status_code == 200
        search_results = search_response.json()
        assert isinstance(search_results, list)
        
        # Our photo should be in the results
        photo_ids = [photo["id"] for photo in search_results]
        assert test_photo.id in photo_ids
        
        # Step 4: Remove specific tag
        remove_response = await async_test_client.delete(
            f"/api/photos/{test_photo.id}/tags/landscape",
            headers=auth_headers
        )
        
        assert remove_response.status_code == 200
        
        # Step 5: Verify tag is removed
        final_tags_response = await async_test_client.get(
            f"/api/photos/{test_photo.id}/tags",
            headers=auth_headers
        )
        
        final_tags = final_tags_response.json()
        final_tag_names = [tag["name"] if isinstance(tag, dict) else tag for tag in final_tags]
        assert "landscape" not in final_tag_names

    async def test_follow_workflow(self, async_test_client: AsyncClient, auth_headers, test_user):
        """Test user following workflow."""
        
        # Note: Following yourself might be prevented, so we test the API structure
        
        # Step 1: Get initial following count
        following_response = await async_test_client.get(
            f"/api/users/{test_user.id}/following",
            headers=auth_headers
        )
        
        assert following_response.status_code == 200
        initial_following = following_response.json()
        initial_count = len(initial_following)
        
        # Step 2: Get initial followers count
        followers_response = await async_test_client.get(
            f"/api/users/{test_user.id}/followers",
            headers=auth_headers
        )
        
        assert followers_response.status_code == 200
        initial_followers = followers_response.json()
        
        # Step 3: Test follow endpoint (might fail for self-follow)
        follow_response = await async_test_client.post(
            f"/api/users/{test_user.id}/follow",
            headers=auth_headers
        )
        
        # Accept either success or validation error for self-follow
        assert follow_response.status_code in [200, 400]
        
        # Step 4: Test unfollow endpoint
        unfollow_response = await async_test_client.delete(
            f"/api/users/{test_user.id}/follow",
            headers=auth_headers
        )
        
        # Accept success or "not following" error
        assert unfollow_response.status_code in [200, 400, 404]

    async def test_popular_tags(self, async_test_client: AsyncClient, auth_headers, test_photo):
        """Test popular tags endpoint."""
        
        # Add some tags to create data
        tag_data = {"tags": ["popular", "trending", "viral"]}
        
        await async_test_client.post(
            f"/api/photos/{test_photo.id}/tags",
            json=tag_data,
            headers=auth_headers
        )
        
        # Get popular tags
        response = await async_test_client.get(
            "/api/tags/popular",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        popular_tags = response.json()
        assert isinstance(popular_tags, list)
        
        # Should include our tags or be empty if no usage stats
        if popular_tags:
            assert all("name" in tag for tag in popular_tags if isinstance(tag, dict))

    async def test_search_functionality(self, async_test_client: AsyncClient, auth_headers, test_photo):
        """Test search functionality."""
        
        # Add searchable tags
        tag_data = {"tags": ["searchtest", "unique"]}
        
        await async_test_client.post(
            f"/api/photos/{test_photo.id}/tags",
            json=tag_data,
            headers=auth_headers
        )
        
        # Test tag search
        tag_search_response = await async_test_client.get(
            "/api/photos/search?tag=searchtest",
            headers=auth_headers
        )
        
        assert tag_search_response.status_code == 200
        search_results = tag_search_response.json()
        assert isinstance(search_results, list)
        
        if search_results:
            photo_ids = [photo["id"] for photo in search_results]
            assert test_photo.id in photo_ids

    async def test_unauthorized_social_actions(self, async_test_client: AsyncClient, test_photo):
        """Test social actions without authentication."""
        
        # Try to like without auth
        like_response = await async_test_client.post(
            f"/api/photos/{test_photo.id}/like"
        )
        assert like_response.status_code == 401
        
        # Try to comment without auth
        comment_data = {"content": "Unauthorized comment"}
        comment_response = await async_test_client.post(
            f"/api/photos/{test_photo.id}/comments",
            json=comment_data
        )
        assert comment_response.status_code == 401
        
        # Try to tag without auth
        tag_data = {"tags": ["unauthorized"]}
        tag_response = await async_test_client.post(
            f"/api/photos/{test_photo.id}/tags",
            json=tag_data
        )
        assert tag_response.status_code == 401

    async def test_social_validation(self, async_test_client: AsyncClient, auth_headers, test_photo):
        """Test validation of social interactions."""
        
        # Test empty comment
        empty_comment = {"content": ""}
        comment_response = await async_test_client.post(
            f"/api/photos/{test_photo.id}/comments",
            json=empty_comment,
            headers=auth_headers
        )
        assert comment_response.status_code == 422
        
        # Test empty tags
        empty_tags = {"tags": []}
        tag_response = await async_test_client.post(
            f"/api/photos/{test_photo.id}/tags",
            json=empty_tags,
            headers=auth_headers
        )
        # Should either accept empty or reject
        assert tag_response.status_code in [200, 422]

    async def test_double_like_prevention(self, async_test_client: AsyncClient, auth_headers, test_photo):
        """Test that double-liking is handled properly."""
        
        # First like
        first_like = await async_test_client.post(
            f"/api/photos/{test_photo.id}/like",
            headers=auth_headers
        )
        assert first_like.status_code == 200
        
        # Second like (should be handled gracefully)
        second_like = await async_test_client.post(
            f"/api/photos/{test_photo.id}/like",
            headers=auth_headers
        )
        # Should either succeed (idempotent) or return conflict
        assert second_like.status_code in [200, 409]

    async def test_comment_on_nonexistent_photo(self, async_test_client: AsyncClient, auth_headers):
        """Test commenting on non-existent photo."""
        
        comment_data = {"content": "Comment on missing photo"}
        
        response = await async_test_client.post(
            "/api/photos/999999/comments",
            json=comment_data,
            headers=auth_headers
        )
        
        assert response.status_code == 404

    async def test_like_nonexistent_photo(self, async_test_client: AsyncClient, auth_headers):
        """Test liking non-existent photo."""
        
        response = await async_test_client.post(
            "/api/photos/999999/like",
            headers=auth_headers
        )
        
        assert response.status_code == 404


@pytest.mark.api
@pytest.mark.performance
class TestSocialPerformance:
    """Test social features performance."""

    async def test_comments_loading_performance(self, async_test_client: AsyncClient, auth_headers, test_photo):
        """Test performance of loading comments."""
        import time
        
        start_time = time.time()
        
        response = await async_test_client.get(
            f"/api/photos/{test_photo.id}/comments",
            headers=auth_headers
        )
        
        end_time = time.time()
        
        assert response.status_code == 200
        
        # Comments should load quickly
        response_time = end_time - start_time
        assert response_time < 1.0, f"Comments took {response_time:.2f}s, should be < 1.0s"

    async def test_likes_loading_performance(self, async_test_client: AsyncClient, auth_headers, test_photo):
        """Test performance of loading likes."""
        import time
        
        start_time = time.time()
        
        response = await async_test_client.get(
            f"/api/photos/{test_photo.id}/likes",
            headers=auth_headers
        )
        
        end_time = time.time()
        
        assert response.status_code == 200
        
        # Likes should load quickly
        response_time = end_time - start_time
        assert response_time < 1.0, f"Likes took {response_time:.2f}s, should be < 1.0s"

    async def test_search_performance(self, async_test_client: AsyncClient, auth_headers):
        """Test search performance."""
        import time
        
        start_time = time.time()
        
        response = await async_test_client.get(
            "/api/photos/search?tag=test",
            headers=auth_headers
        )
        
        end_time = time.time()
        
        assert response.status_code == 200
        
        # Search should be fast
        response_time = end_time - start_time
        assert response_time < 2.0, f"Search took {response_time:.2f}s, should be < 2.0s"
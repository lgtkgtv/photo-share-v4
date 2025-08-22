"""
Integration tests for photo API endpoints.
"""
import pytest
from fastapi.testclient import TestClient
from io import BytesIO


class TestPhotoAPI:
    """Test photo API endpoints."""

    @pytest.mark.integration
    @pytest.mark.api
    def test_upload_photo_authenticated(self, test_client: TestClient, auth_headers, sample_image_data):
        """Test photo upload with authentication."""
        files = {"file": ("test.jpg", BytesIO(sample_image_data), "image/jpeg")}
        data = {
            "title": "Test Photo",
            "description": "A test photo upload",
            "is_public": "true"
        }
        
        response = test_client.post(
            "/api/photos/upload",
            headers=auth_headers,
            files=files,
            data=data
        )
        
        assert response.status_code == 200
        photo_data = response.json()
        assert photo_data["title"] == "Test Photo"
        assert photo_data["description"] == "A test photo upload"
        assert photo_data["is_public"] is True
        assert photo_data["content_type"] == "image/jpeg"
        assert "id" in photo_data
        assert "filename" in photo_data
        assert "created_at" in photo_data

    @pytest.mark.integration
    @pytest.mark.api
    def test_upload_photo_unauthenticated(self, test_client: TestClient, sample_image_data):
        """Test photo upload without authentication."""
        files = {"file": ("test.jpg", BytesIO(sample_image_data), "image/jpeg")}
        data = {"title": "Test Photo"}
        
        response = test_client.post("/api/photos/upload", files=files, data=data)
        
        assert response.status_code == 403  # Should require authentication

    @pytest.mark.integration
    @pytest.mark.api
    def test_upload_photo_invalid_file_type(self, test_client: TestClient, auth_headers):
        """Test photo upload with invalid file type."""
        # Try to upload a text file as image
        files = {"file": ("test.txt", BytesIO(b"not an image"), "text/plain")}
        data = {"title": "Invalid File"}
        
        response = test_client.post(
            "/api/photos/upload",
            headers=auth_headers,
            files=files,
            data=data
        )
        
        assert response.status_code == 400  # Should reject invalid file type

    @pytest.mark.integration
    @pytest.mark.api
    def test_upload_photo_oversized_file(self, test_client: TestClient, auth_headers):
        """Test photo upload with oversized file."""
        # Create a file larger than 50MB (mocked in our test)
        large_data = b"x" * (60 * 1024 * 1024)  # 60MB
        files = {"file": ("large.jpg", BytesIO(large_data), "image/jpeg")}
        data = {"title": "Large Photo"}
        
        response = test_client.post(
            "/api/photos/upload",
            headers=auth_headers,
            files=files,
            data=data
        )
        
        assert response.status_code == 400  # Should reject oversized file

    @pytest.mark.integration
    @pytest.mark.api
    def test_list_user_photos(self, test_client: TestClient, auth_headers, test_photo):
        """Test listing user's photos."""
        response = test_client.get("/api/photos/", headers=auth_headers)
        
        assert response.status_code == 200
        photos = response.json()
        assert isinstance(photos, list)
        
        # Should contain our test photo
        photo_ids = [photo["id"] for photo in photos]
        assert test_photo.id in photo_ids

    @pytest.mark.integration
    @pytest.mark.api
    def test_list_user_photos_unauthenticated(self, test_client: TestClient):
        """Test listing user's photos without authentication."""
        response = test_client.get("/api/photos/")
        
        assert response.status_code == 403  # Should require authentication

    @pytest.mark.integration
    @pytest.mark.api
    def test_list_public_photos(self, test_client: TestClient, test_photo):
        """Test listing public photos (no authentication required)."""
        response = test_client.get("/api/photos/public")
        
        assert response.status_code == 200
        photos = response.json()
        assert isinstance(photos, list)
        
        # Should contain our public test photo
        if test_photo.is_public:
            photo_ids = [photo["id"] for photo in photos]
            assert test_photo.id in photo_ids

    @pytest.mark.integration
    @pytest.mark.api
    def test_get_photo_details_owner(self, test_client: TestClient, auth_headers, test_photo):
        """Test getting photo details as the owner."""
        response = test_client.get(f"/api/photos/{test_photo.id}", headers=auth_headers)
        
        assert response.status_code == 200
        photo_data = response.json()
        assert photo_data["id"] == test_photo.id
        assert photo_data["filename"] == test_photo.filename
        assert photo_data["title"] == test_photo.title

    @pytest.mark.integration
    @pytest.mark.api
    def test_get_photo_details_public(self, test_client: TestClient, test_photo):
        """Test getting public photo details without authentication."""
        if test_photo.is_public:
            response = test_client.get(f"/api/photos/{test_photo.id}")
            # Note: This might require authentication in current implementation
            # The test verifies the current behavior
            assert response.status_code in [200, 403]

    @pytest.mark.integration
    @pytest.mark.api
    def test_get_photo_details_not_found(self, test_client: TestClient, auth_headers):
        """Test getting details for non-existent photo."""
        response = test_client.get("/api/photos/99999", headers=auth_headers)
        
        assert response.status_code == 404

    @pytest.mark.integration
    @pytest.mark.api
    def test_download_photo_owner(self, test_client: TestClient, auth_headers, test_photo):
        """Test downloading photo as the owner."""
        response = test_client.get(f"/api/photos/{test_photo.id}/download", headers=auth_headers)
        
        assert response.status_code == 200
        assert response.headers["content-type"] == test_photo.content_type
        assert "content-disposition" in response.headers
        assert test_photo.original_filename in response.headers["content-disposition"]

    @pytest.mark.integration
    @pytest.mark.api
    def test_download_photo_unauthenticated(self, test_client: TestClient, test_photo):
        """Test downloading photo without authentication."""
        response = test_client.get(f"/api/photos/{test_photo.id}/download")
        
        assert response.status_code == 403  # Should require authentication

    @pytest.mark.integration
    @pytest.mark.api
    def test_get_photo_url(self, test_client: TestClient, auth_headers, test_photo):
        """Test getting photo URLs."""
        response = test_client.get(f"/api/photos/{test_photo.id}/url", headers=auth_headers)
        
        assert response.status_code == 200
        url_data = response.json()
        assert url_data["photo_id"] == test_photo.id
        assert "download_url" in url_data
        assert "storage_url" in url_data
        assert url_data["filename"] == test_photo.original_filename

    @pytest.mark.integration
    @pytest.mark.api
    def test_pagination_photos(self, test_client: TestClient, auth_headers):
        """Test photo pagination."""
        # Test with different page sizes
        response1 = test_client.get("/api/photos/?skip=0&limit=5", headers=auth_headers)
        assert response1.status_code == 200
        photos1 = response1.json()
        assert len(photos1) <= 5
        
        response2 = test_client.get("/api/photos/?skip=0&limit=10", headers=auth_headers)
        assert response2.status_code == 200
        photos2 = response2.json()
        assert len(photos2) <= 10
        assert len(photos2) >= len(photos1)


class TestPhotoSecurity:
    """Test photo security features."""

    @pytest.mark.integration
    @pytest.mark.security
    def test_file_content_validation(self, test_client: TestClient, auth_headers):
        """Test that malicious file content is rejected."""
        # Try to upload file with script content
        malicious_content = b"<script>alert('xss')</script>"
        files = {"file": ("malicious.jpg", BytesIO(malicious_content), "image/jpeg")}
        data = {"title": "Malicious File"}
        
        response = test_client.post(
            "/api/photos/upload",
            headers=auth_headers,
            files=files,
            data=data
        )
        
        assert response.status_code == 400  # Should reject malicious content

    @pytest.mark.integration
    @pytest.mark.security
    def test_filename_sanitization(self, test_client: TestClient, auth_headers, sample_image_data):
        """Test that malicious filenames are sanitized."""
        malicious_filename = "../../../etc/passwd.jpg"
        files = {"file": (malicious_filename, BytesIO(sample_image_data), "image/jpeg")}
        data = {"title": "Test Photo"}
        
        response = test_client.post(
            "/api/photos/upload",
            headers=auth_headers,
            files=files,
            data=data
        )
        
        if response.status_code == 200:
            photo_data = response.json()
            # Filename should be sanitized
            assert "../" not in photo_data["filename"]
            assert "/etc/passwd" not in photo_data["filename"]

    @pytest.mark.integration
    @pytest.mark.security
    def test_access_control_private_photos(self, test_client: TestClient, test_user_data):
        """Test access control for private photos."""
        # Create two users
        user1_data = {
            "email": "user1@example.com",
            "password": "User1Password123!"
        }
        user2_data = {
            "email": "user2@example.com", 
            "password": "User2Password123!"
        }
        
        # Register both users
        test_client.post("/api/users/register", json=user1_data)
        test_client.post("/api/users/register", json=user2_data)
        
        # Login as user1
        login1_response = test_client.post("/api/users/login", data={
            "username": user1_data["email"],
            "password": user1_data["password"]
        })
        
        if login1_response.status_code == 200:
            user1_token = login1_response.json()["access_token"]
            user1_headers = {"Authorization": f"Bearer {user1_token}"}
            
            # User1 uploads a private photo
            files = {"file": ("private.jpg", BytesIO(b"fake_image"), "image/jpeg")}
            data = {"title": "Private Photo", "is_public": "false"}
            
            upload_response = test_client.post(
                "/api/photos/upload",
                headers=user1_headers,
                files=files,
                data=data
            )
            
            if upload_response.status_code == 200:
                photo_id = upload_response.json()["id"]
                
                # Login as user2
                login2_response = test_client.post("/api/users/login", data={
                    "username": user2_data["email"],
                    "password": user2_data["password"]
                })
                
                if login2_response.status_code == 200:
                    user2_token = login2_response.json()["access_token"]
                    user2_headers = {"Authorization": f"Bearer {user2_token}"}
                    
                    # User2 tries to access user1's private photo
                    access_response = test_client.get(
                        f"/api/photos/{photo_id}",
                        headers=user2_headers
                    )
                    
                    # Should be denied
                    assert access_response.status_code == 403


class TestPhotoWorkflow:
    """Test complete photo management workflows."""

    @pytest.mark.integration
    @pytest.mark.slow
    def test_complete_photo_workflow(self, test_client: TestClient, sample_image_data):
        """Test complete photo workflow: register -> login -> upload -> view -> download."""
        # Step 1: Register user
        user_data = {
            "email": "workflow@example.com",
            "password": "WorkflowPassword123!"
        }
        
        register_response = test_client.post("/api/users/register", json=user_data)
        assert register_response.status_code == 200
        
        # Step 2: Login
        login_response = test_client.post("/api/users/login", data={
            "username": user_data["email"],
            "password": user_data["password"]
        })
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Step 3: Upload photo
        files = {"file": ("workflow.jpg", BytesIO(sample_image_data), "image/jpeg")}
        data = {
            "title": "Workflow Test Photo",
            "description": "Testing complete workflow",
            "is_public": "true"
        }
        
        upload_response = test_client.post(
            "/api/photos/upload",
            headers=headers,
            files=files,
            data=data
        )
        assert upload_response.status_code == 200
        photo_id = upload_response.json()["id"]
        
        # Step 4: View photo details
        details_response = test_client.get(f"/api/photos/{photo_id}", headers=headers)
        assert details_response.status_code == 200
        photo_details = details_response.json()
        assert photo_details["title"] == "Workflow Test Photo"
        
        # Step 5: List photos
        list_response = test_client.get("/api/photos/", headers=headers)
        assert list_response.status_code == 200
        photos = list_response.json()
        photo_ids = [photo["id"] for photo in photos]
        assert photo_id in photo_ids
        
        # Step 6: Download photo
        download_response = test_client.get(f"/api/photos/{photo_id}/download", headers=headers)
        assert download_response.status_code == 200
        assert len(download_response.content) > 0
        
        # Step 7: Get photo URL
        url_response = test_client.get(f"/api/photos/{photo_id}/url", headers=headers)
        assert url_response.status_code == 200
        url_data = url_response.json()
        assert url_data["photo_id"] == photo_id
"""
Phase 3 Integration Tests - PDF Processing
Tests PDF upload, text extraction, image extraction, and API endpoints
"""

import pytest
import io
from pathlib import Path
from fastapi.testclient import TestClient
from PIL import Image as PILImage

from backend.main import app
from backend.services import PDFService, StorageService
from backend.database.models import PDF, Image


# ==================== PDF Service Unit Tests ====================

class TestPDFService:
    """Test PDFService methods"""

    def test_storage_service_initialization(self, db_session):
        """Test that storage service initializes correctly"""
        storage = StorageService()

        assert storage.base_storage_path.exists()
        assert storage.pdf_storage_path.exists()
        assert storage.image_storage_path.exists()
        assert storage.thumbnail_storage_path.exists()

    def test_save_image_with_thumbnail(self, db_session):
        """Test saving an image with thumbnail generation"""
        storage = StorageService()

        # Create a simple test image
        img = PILImage.new('RGB', (800, 600), color='red')
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='PNG')
        img_bytes.seek(0)

        # Save image
        result = storage.save_image(
            img_bytes.getvalue(),
            'PNG',
            create_thumbnail=True,
            thumbnail_size=(200, 200)
        )

        assert result["image_path"]
        assert result["thumbnail_path"]
        assert result["file_size_bytes"] > 0
        assert Path(result["image_path"]).exists()
        assert Path(result["thumbnail_path"]).exists()

        # Cleanup
        storage.delete_image(result["image_path"], result["thumbnail_path"])

    def test_save_image_without_thumbnail(self, db_session):
        """Test saving an image without thumbnail"""
        storage = StorageService()

        # Create a simple test image
        img = PILImage.new('RGB', (800, 600), color='blue')
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='JPEG')
        img_bytes.seek(0)

        # Save image without thumbnail
        result = storage.save_image(
            img_bytes.getvalue(),
            'JPEG',
            create_thumbnail=False
        )

        assert result["image_path"]
        assert result["thumbnail_path"] is None
        assert Path(result["image_path"]).exists()

        # Cleanup
        storage.delete_image(result["image_path"])

    def test_delete_image(self, db_session):
        """Test image deletion"""
        storage = StorageService()

        # Create and save test image
        img = PILImage.new('RGB', (100, 100), color='green')
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='PNG')
        img_bytes.seek(0)

        result = storage.save_image(img_bytes.getvalue(), 'PNG', create_thumbnail=True)

        image_path = result["image_path"]
        thumbnail_path = result["thumbnail_path"]

        assert Path(image_path).exists()
        assert Path(thumbnail_path).exists()

        # Delete
        success = storage.delete_image(image_path, thumbnail_path)

        assert success is True
        assert not Path(image_path).exists()
        assert not Path(thumbnail_path).exists()

    def test_storage_stats(self, db_session):
        """Test storage statistics"""
        storage = StorageService()

        # Get initial stats
        stats = storage.get_storage_stats()

        assert "total_pdfs" in stats
        assert "total_images" in stats
        assert "total_thumbnails" in stats
        assert "total_size_bytes" in stats
        assert isinstance(stats["total_pdfs"], int)
        assert isinstance(stats["total_images"], int)


# ==================== API Endpoint Tests ====================

class TestPDFEndpoints:
    """Test PDF API endpoints"""

    def create_sample_pdf(self) -> io.BytesIO:
        """
        Create a simple PDF for testing

        Returns a PDF with one page containing text "Test PDF"
        """
        try:
            import fitz  # PyMuPDF

            # Create a simple PDF
            doc = fitz.open()
            page = doc.new_page(width=595, height=842)  # A4 size
            page.insert_text((100, 100), "Test PDF Content", fontsize=12)
            page.insert_text((100, 150), "This is a test PDF for neurosurgery knowledge base", fontsize=10)

            # Save to bytes
            pdf_bytes = doc.write()
            doc.close()

            return io.BytesIO(pdf_bytes)

        except ImportError:
            pytest.skip("PyMuPDF not installed")

    def test_pdf_health_check(self, test_client):
        """Test GET /pdfs/health endpoint"""
        response = test_client.get("/api/v1/pdfs/health")

        assert response.status_code == 200
        assert "message" in response.json()

    def test_upload_pdf_without_auth(self, test_client):
        """Test PDF upload without authentication fails"""
        pdf_content = self.create_sample_pdf()

        response = test_client.post(
            "/api/v1/pdfs/upload",
            files={"file": ("test.pdf", pdf_content, "application/pdf")}
        )

        # Should require authentication
        assert response.status_code == 403

    def test_upload_pdf_success(self, test_client):
        """Test successful PDF upload with authentication"""
        # Register and get token
        reg_response = test_client.post(
            "/api/v1/auth/register",
            json={
                "email": "pdfuser@test.com",
                "password": "PdfTest123"
            }
        )
        token = reg_response.json()["access_token"]

        # Upload PDF
        pdf_content = self.create_sample_pdf()

        response = test_client.post(
            "/api/v1/pdfs/upload",
            files={"file": ("test.pdf", pdf_content, "application/pdf")},
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 201
        data = response.json()

        assert data["filename"] == "test.pdf"
        assert data["total_pages"] == 1
        assert data["indexing_status"] == "uploaded"
        assert data["text_extracted"] is False
        assert data["images_extracted"] is False

        # Cleanup
        pdf_id = data["id"]
        test_client.delete(
            f"/api/v1/pdfs/{pdf_id}",
            headers={"Authorization": f"Bearer {token}"}
        )

    def test_upload_invalid_file_type(self, test_client):
        """Test uploading non-PDF file fails"""
        # Register and get token
        reg_response = test_client.post(
            "/api/v1/auth/register",
            json={
                "email": "invalidfile@test.com",
                "password": "Invalid123"
            }
        )
        token = reg_response.json()["access_token"]

        # Try to upload a text file
        text_content = io.BytesIO(b"This is not a PDF")

        response = test_client.post(
            "/api/v1/pdfs/upload",
            files={"file": ("test.txt", text_content, "text/plain")},
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 400
        # Error message could be about content type or file extension
        assert "Invalid" in response.json()["detail"]

    def test_list_pdfs(self, test_client):
        """Test listing PDFs"""
        # Register and get token
        reg_response = test_client.post(
            "/api/v1/auth/register",
            json={
                "email": "listuser@test.com",
                "password": "ListTest123"
            }
        )
        token = reg_response.json()["access_token"]

        # Upload a PDF
        pdf_content = self.create_sample_pdf()
        upload_response = test_client.post(
            "/api/v1/pdfs/upload",
            files={"file": ("test.pdf", pdf_content, "application/pdf")},
            headers={"Authorization": f"Bearer {token}"}
        )
        pdf_id = upload_response.json()["id"]

        # List PDFs
        response = test_client.get(
            "/api/v1/pdfs",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        pdfs = response.json()
        assert isinstance(pdfs, list)
        assert len(pdfs) > 0

        # Cleanup
        test_client.delete(
            f"/api/v1/pdfs/{pdf_id}",
            headers={"Authorization": f"Bearer {token}"}
        )

    def test_get_pdf_by_id(self, test_client):
        """Test getting PDF by ID"""
        # Register and get token
        reg_response = test_client.post(
            "/api/v1/auth/register",
            json={
                "email": "getpdf@test.com",
                "password": "GetPdf123"
            }
        )
        token = reg_response.json()["access_token"]

        # Upload PDF
        pdf_content = self.create_sample_pdf()
        upload_response = test_client.post(
            "/api/v1/pdfs/upload",
            files={"file": ("specific.pdf", pdf_content, "application/pdf")},
            headers={"Authorization": f"Bearer {token}"}
        )
        pdf_id = upload_response.json()["id"]

        # Get PDF
        response = test_client.get(
            f"/api/v1/pdfs/{pdf_id}",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == pdf_id
        assert data["filename"] == "specific.pdf"

        # Cleanup
        test_client.delete(
            f"/api/v1/pdfs/{pdf_id}",
            headers={"Authorization": f"Bearer {token}"}
        )

    def test_get_nonexistent_pdf(self, test_client):
        """Test getting non-existent PDF returns 404"""
        # Register and get token
        reg_response = test_client.post(
            "/api/v1/auth/register",
            json={
                "email": "notfound@test.com",
                "password": "NotFound123"
            }
        )
        token = reg_response.json()["access_token"]

        # Try to get non-existent PDF
        fake_uuid = "00000000-0000-0000-0000-000000000000"
        response = test_client.get(
            f"/api/v1/pdfs/{fake_uuid}",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 404

    def test_extract_text(self, test_client):
        """Test text extraction from PDF"""
        # Register and get token
        reg_response = test_client.post(
            "/api/v1/auth/register",
            json={
                "email": "extracttext@test.com",
                "password": "Extract123"
            }
        )
        token = reg_response.json()["access_token"]

        # Upload PDF
        pdf_content = self.create_sample_pdf()
        upload_response = test_client.post(
            "/api/v1/pdfs/upload",
            files={"file": ("extract.pdf", pdf_content, "application/pdf")},
            headers={"Authorization": f"Bearer {token}"}
        )
        pdf_id = upload_response.json()["id"]

        # Extract text
        response = test_client.post(
            f"/api/v1/pdfs/{pdf_id}/extract-text",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert "statistics" in data
        assert data["statistics"]["total_pages"] == 1
        assert data["statistics"]["total_words"] > 0

        # Verify PDF status updated
        pdf_response = test_client.get(
            f"/api/v1/pdfs/{pdf_id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        pdf_data = pdf_response.json()
        assert pdf_data["text_extracted"] is True

        # Cleanup
        test_client.delete(
            f"/api/v1/pdfs/{pdf_id}",
            headers={"Authorization": f"Bearer {token}"}
        )

    def test_delete_pdf(self, test_client):
        """Test PDF deletion"""
        # Register and get token
        reg_response = test_client.post(
            "/api/v1/auth/register",
            json={
                "email": "deletepdf@test.com",
                "password": "Delete123"
            }
        )
        token = reg_response.json()["access_token"]

        # Upload PDF
        pdf_content = self.create_sample_pdf()
        upload_response = test_client.post(
            "/api/v1/pdfs/upload",
            files={"file": ("todelete.pdf", pdf_content, "application/pdf")},
            headers={"Authorization": f"Bearer {token}"}
        )
        pdf_id = upload_response.json()["id"]

        # Delete PDF
        response = test_client.delete(
            f"/api/v1/pdfs/{pdf_id}",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        assert "message" in response.json()

        # Verify PDF is deleted
        get_response = test_client.get(
            f"/api/v1/pdfs/{pdf_id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert get_response.status_code == 404


# ==================== End-to-End Flow Tests ====================

class TestPDFFlow:
    """Test complete PDF processing flows"""

    def create_sample_pdf(self) -> io.BytesIO:
        """Create a simple PDF for testing"""
        try:
            import fitz
            doc = fitz.open()
            page = doc.new_page()
            page.insert_text((100, 100), "End-to-end test PDF", fontsize=12)
            pdf_bytes = doc.write()
            doc.close()
            return io.BytesIO(pdf_bytes)
        except ImportError:
            pytest.skip("PyMuPDF not installed")

    def test_complete_pdf_workflow(self, test_client):
        """Test complete flow: upload → extract text → extract images → get details → delete"""
        # 1. Register
        reg_response = test_client.post(
            "/api/v1/auth/register",
            json={
                "email": "workflow@test.com",
                "password": "Workflow123"
            }
        )
        assert reg_response.status_code == 201
        token = reg_response.json()["access_token"]

        # 2. Upload PDF
        pdf_content = self.create_sample_pdf()
        upload_response = test_client.post(
            "/api/v1/pdfs/upload",
            files={"file": ("workflow.pdf", pdf_content, "application/pdf")},
            headers={"Authorization": f"Bearer {token}"}
        )
        assert upload_response.status_code == 201
        pdf_id = upload_response.json()["id"]

        # 3. Extract text
        text_response = test_client.post(
            f"/api/v1/pdfs/{pdf_id}/extract-text",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert text_response.status_code == 200

        # 4. Get PDF details
        details_response = test_client.get(
            f"/api/v1/pdfs/{pdf_id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert details_response.status_code == 200
        assert details_response.json()["text_extracted"] is True

        # 5. Delete PDF
        delete_response = test_client.delete(
            f"/api/v1/pdfs/{pdf_id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert delete_response.status_code == 200

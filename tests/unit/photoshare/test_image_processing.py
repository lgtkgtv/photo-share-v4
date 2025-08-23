#!/usr/bin/env python3
"""
Unit tests for image processing functionality.
"""
import pytest
import tempfile
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from PIL import Image
import io

from services.photoshare.image_processing import (
    ImageProcessor, ImageMetadata, ThumbnailSize, 
    ProcessingResult, create_thumbnail, get_image_metadata,
    optimize_image, apply_watermark
)


class TestImageMetadata:
    """Test Image Metadata class."""
    
    def test_metadata_creation(self):
        """Test image metadata creation."""
        metadata = ImageMetadata(
            width=1920,
            height=1080,
            format="JPEG",
            mode="RGB",
            file_size=524288,
            has_transparency=False,
            color_profile="sRGB"
        )
        
        assert metadata.width == 1920
        assert metadata.height == 1080
        assert metadata.format == "JPEG"
        assert metadata.mode == "RGB"
        assert metadata.file_size == 524288
        assert metadata.has_transparency is False
        assert metadata.color_profile == "sRGB"
    
    def test_metadata_aspect_ratio(self):
        """Test aspect ratio calculation."""
        metadata = ImageMetadata(width=1920, height=1080)
        assert abs(metadata.aspect_ratio - 1.7777777777777777) < 0.0001
    
    def test_metadata_to_dict(self):
        """Test metadata serialization."""
        metadata = ImageMetadata(
            width=800,
            height=600,
            format="PNG",
            mode="RGBA"
        )
        
        metadata_dict = metadata.to_dict()
        
        assert metadata_dict["width"] == 800
        assert metadata_dict["height"] == 600
        assert metadata_dict["format"] == "PNG"
        assert metadata_dict["mode"] == "RGBA"


class TestThumbnailSize:
    """Test Thumbnail Size enumeration."""
    
    def test_thumbnail_sizes(self):
        """Test thumbnail size definitions."""
        assert ThumbnailSize.SMALL.value == (150, 150)
        assert ThumbnailSize.MEDIUM.value == (300, 300)
        assert ThumbnailSize.LARGE.value == (600, 600)


class TestProcessingResult:
    """Test Processing Result class."""
    
    def test_processing_result_success(self):
        """Test successful processing result."""
        result = ProcessingResult(
            success=True,
            output_path="/tmp/processed_image.jpg",
            metadata=ImageMetadata(width=800, height=600),
            processing_time=1.23
        )
        
        assert result.success is True
        assert result.output_path == "/tmp/processed_image.jpg"
        assert result.metadata.width == 800
        assert result.processing_time == 1.23
        assert result.error is None
    
    def test_processing_result_failure(self):
        """Test failed processing result."""
        result = ProcessingResult(
            success=False,
            error="Invalid image format"
        )
        
        assert result.success is False
        assert result.error == "Invalid image format"
        assert result.output_path is None


class TestUtilityFunctions:
    """Test utility functions."""
    
    def test_get_image_metadata_jpeg(self):
        """Test getting JPEG image metadata."""
        # Create test JPEG image
        img = Image.new('RGB', (800, 600), color='red')
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='JPEG')
        img_bytes.seek(0)
        
        with tempfile.NamedTemporaryFile(suffix='.jpg') as tmp_file:
            tmp_file.write(img_bytes.getvalue())
            tmp_file.flush()
            
            metadata = get_image_metadata(tmp_file.name)
            
            assert metadata.width == 800
            assert metadata.height == 600
            assert metadata.format == "JPEG"
            assert metadata.mode == "RGB"
    
    def test_get_image_metadata_png(self):
        """Test getting PNG image metadata."""
        # Create test PNG image with transparency
        img = Image.new('RGBA', (400, 300), color=(255, 0, 0, 128))
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='PNG')
        img_bytes.seek(0)
        
        with tempfile.NamedTemporaryFile(suffix='.png') as tmp_file:
            tmp_file.write(img_bytes.getvalue())
            tmp_file.flush()
            
            metadata = get_image_metadata(tmp_file.name)
            
            assert metadata.width == 400
            assert metadata.height == 300
            assert metadata.format == "PNG"
            assert metadata.mode == "RGBA"
            assert metadata.has_transparency is True
    
    def test_create_thumbnail_small(self):
        """Test small thumbnail creation."""
        # Create test image
        img = Image.new('RGB', (1000, 800), color='blue')
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='JPEG')
        img_bytes.seek(0)
        
        with tempfile.NamedTemporaryFile(suffix='.jpg') as input_file:
            with tempfile.NamedTemporaryFile(suffix='_thumb.jpg') as output_file:
                input_file.write(img_bytes.getvalue())
                input_file.flush()
                
                success = create_thumbnail(
                    input_file.name, 
                    output_file.name, 
                    ThumbnailSize.SMALL
                )
                
                assert success is True
                
                # Verify thumbnail dimensions
                thumb_img = Image.open(output_file.name)
                assert thumb_img.width <= 150
                assert thumb_img.height <= 150
    
    def test_create_thumbnail_preserve_aspect_ratio(self):
        """Test thumbnail creation preserves aspect ratio."""
        # Create test image with specific aspect ratio (2:1)
        img = Image.new('RGB', (1000, 500), color='green')
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='JPEG')
        img_bytes.seek(0)
        
        with tempfile.NamedTemporaryFile(suffix='.jpg') as input_file:
            with tempfile.NamedTemporaryFile(suffix='_thumb.jpg') as output_file:
                input_file.write(img_bytes.getvalue())
                input_file.flush()
                
                success = create_thumbnail(
                    input_file.name, 
                    output_file.name, 
                    ThumbnailSize.MEDIUM
                )
                
                assert success is True
                
                # Verify aspect ratio is preserved
                thumb_img = Image.open(output_file.name)
                original_ratio = 1000 / 500
                thumb_ratio = thumb_img.width / thumb_img.height
                assert abs(original_ratio - thumb_ratio) < 0.1
    
    def test_optimize_image_jpeg(self):
        """Test JPEG image optimization."""
        # Create test image
        img = Image.new('RGB', (800, 600), color='red')
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='JPEG', quality=100)
        img_bytes.seek(0)
        
        with tempfile.NamedTemporaryFile(suffix='.jpg') as input_file:
            with tempfile.NamedTemporaryFile(suffix='_opt.jpg') as output_file:
                input_file.write(img_bytes.getvalue())
                input_file.flush()
                
                original_size = len(img_bytes.getvalue())
                
                success = optimize_image(input_file.name, output_file.name, quality=85)
                
                assert success is True
                
                # Verify optimization reduced file size
                with open(output_file.name, 'rb') as f:
                    optimized_size = len(f.read())
                
                assert optimized_size < original_size
    
    @pytest.mark.asyncio
    async def test_apply_watermark(self):
        """Test watermark application."""
        # Create test image
        img = Image.new('RGB', (800, 600), color='white')
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='JPEG')
        img_bytes.seek(0)
        
        with tempfile.NamedTemporaryFile(suffix='.jpg') as input_file:
            with tempfile.NamedTemporaryFile(suffix='_watermarked.jpg') as output_file:
                input_file.write(img_bytes.getvalue())
                input_file.flush()
                
                success = await apply_watermark(
                    input_file.name,
                    output_file.name,
                    "© PhotoShare",
                    position="bottom_right",
                    opacity=0.7
                )
                
                assert success is True
                
                # Verify watermarked image was created
                watermarked_img = Image.open(output_file.name)
                assert watermarked_img.width == 800
                assert watermarked_img.height == 600


class TestImageProcessor:
    """Test Image Processor functionality."""
    
    @pytest.fixture
    def image_processor(self):
        """Create image processor instance."""
        return ImageProcessor()
    
    def test_image_processor_initialization(self, image_processor):
        """Test image processor initialization."""
        assert image_processor.supported_formats == {'JPEG', 'PNG', 'GIF', 'BMP', 'WEBP'}
        assert image_processor.max_dimension == 4096
        assert image_processor.quality == 85
    
    @pytest.mark.asyncio
    async def test_process_image_success(self, image_processor):
        """Test successful image processing."""
        # Create test image
        img = Image.new('RGB', (1000, 800), color='blue')
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='JPEG')
        img_bytes.seek(0)
        
        with tempfile.NamedTemporaryFile(suffix='.jpg') as input_file:
            input_file.write(img_bytes.getvalue())
            input_file.flush()
            
            result = await image_processor.process_image(
                input_file.name,
                "/tmp/processed.jpg"
            )
            
            assert result.success is True
            assert result.metadata.width == 1000
            assert result.metadata.height == 800
            assert result.processing_time > 0
    
    @pytest.mark.asyncio
    async def test_process_image_resize_large(self, image_processor):
        """Test processing oversized image."""
        # Create oversized image
        img = Image.new('RGB', (5000, 4000), color='green')
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='JPEG')
        img_bytes.seek(0)
        
        with tempfile.NamedTemporaryFile(suffix='.jpg') as input_file:
            input_file.write(img_bytes.getvalue())
            input_file.flush()
            
            result = await image_processor.process_image(
                input_file.name,
                "/tmp/processed.jpg"
            )
            
            assert result.success is True
            # Should be resized to max dimensions
            assert result.metadata.width <= image_processor.max_dimension
            assert result.metadata.height <= image_processor.max_dimension
    
    @pytest.mark.asyncio
    async def test_process_image_invalid_format(self, image_processor):
        """Test processing invalid image format."""
        with tempfile.NamedTemporaryFile(suffix='.txt') as invalid_file:
            invalid_file.write(b'This is not an image')
            invalid_file.flush()
            
            result = await image_processor.process_image(
                invalid_file.name,
                "/tmp/processed.jpg"
            )
            
            assert result.success is False
            assert "format" in result.error.lower() or "image" in result.error.lower()
    
    @pytest.mark.asyncio
    async def test_create_thumbnails(self, image_processor):
        """Test thumbnail creation for all sizes."""
        # Create test image
        img = Image.new('RGB', (1200, 900), color='purple')
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='JPEG')
        img_bytes.seek(0)
        
        with tempfile.NamedTemporaryFile(suffix='.jpg') as input_file:
            input_file.write(img_bytes.getvalue())
            input_file.flush()
            
            thumbnails = await image_processor.create_thumbnails(
                input_file.name,
                "/tmp"
            )
            
            assert "small" in thumbnails
            assert "medium" in thumbnails
            assert "large" in thumbnails
            assert len(thumbnails) == 3
    
    @pytest.mark.asyncio
    async def test_get_processing_stats(self, image_processor):
        """Test processing statistics."""
        # Create test image and process it
        img = Image.new('RGB', (800, 600), color='yellow')
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='JPEG')
        img_bytes.seek(0)
        
        with tempfile.NamedTemporaryFile(suffix='.jpg') as input_file:
            input_file.write(img_bytes.getvalue())
            input_file.flush()
            
            await image_processor.process_image(input_file.name, "/tmp/processed.jpg")
            await image_processor.create_thumbnails(input_file.name, "/tmp")
            
            stats = await image_processor.get_processing_stats()
            
            assert stats["images_processed"] >= 1
            assert stats["thumbnails_created"] >= 3
            assert stats["total_processing_time"] > 0
            assert "avg_processing_time" in stats
    
    @pytest.mark.asyncio 
    async def test_validate_image_format(self, image_processor):
        """Test image format validation."""
        # Valid JPEG
        img = Image.new('RGB', (100, 100), color='red')
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='JPEG')
        img_bytes.seek(0)
        
        with tempfile.NamedTemporaryFile(suffix='.jpg') as valid_file:
            valid_file.write(img_bytes.getvalue())
            valid_file.flush()
            
            is_valid = await image_processor.validate_image_format(valid_file.name)
            assert is_valid is True
        
        # Invalid file
        with tempfile.NamedTemporaryFile(suffix='.jpg') as invalid_file:
            invalid_file.write(b'Not an image')
            invalid_file.flush()
            
            is_valid = await image_processor.validate_image_format(invalid_file.name)
            assert is_valid is False
    
    @pytest.mark.asyncio
    async def test_extract_exif_data(self, image_processor):
        """Test EXIF data extraction."""
        # Create image with EXIF data
        img = Image.new('RGB', (800, 600), color='cyan')
        
        # Add some basic EXIF data
        exif_dict = {
            "0th": {256: 800, 257: 600},  # ImageWidth, ImageLength
        }
        
        with patch('PIL.ExifTags.TAGS', {'ImageWidth': 256, 'ImageLength': 257}):
            img_bytes = io.BytesIO()
            img.save(img_bytes, format='JPEG')
            img_bytes.seek(0)
            
            with tempfile.NamedTemporaryFile(suffix='.jpg') as img_file:
                img_file.write(img_bytes.getvalue())
                img_file.flush()
                
                exif_data = await image_processor.extract_exif_data(img_file.name)
                
                assert isinstance(exif_data, dict)
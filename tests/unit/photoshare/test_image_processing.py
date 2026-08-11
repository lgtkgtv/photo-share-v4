#!/usr/bin/env python3
"""
Unit tests for image processing functionality.

Rewritten to match the actual ImageProcessor implementation
(services/photoshare/image_processing.py). The API this file used to test
(ImageMetadata, ThumbnailSize, ProcessingResult, file-path-based
create_thumbnail/get_image_metadata/optimize_image/apply_watermark helpers)
does not exist in the codebase -- the real ImageProcessor operates on raw
bytes in memory (validate_image, extract_exif_data, optimize_image,
generate_thumbnails, add_watermark, apply_filters, get_image_hash), and is
synchronous except where noted.
"""
import io

import pytest
from PIL import Image

from services.photoshare.image_processing import ImageProcessor


def _jpeg_bytes(size=(800, 600), color="red"):
    img = Image.new("RGB", size, color=color)
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


def _png_bytes(size=(400, 300), color=(255, 0, 0, 128)):
    img = Image.new("RGBA", size, color=color)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


@pytest.fixture
def processor():
    return ImageProcessor()


class TestImageProcessorInitialization:
    def test_default_config(self, processor):
        assert processor.max_dimension == 4000
        assert processor.jpeg_quality == 85
        assert processor.webp_quality == 80

    def test_thumbnail_sizes(self, processor):
        assert processor.THUMBNAIL_SIZES["small"] == (150, 150)
        assert processor.THUMBNAIL_SIZES["medium"] == (300, 300)
        assert processor.THUMBNAIL_SIZES["large"] == (800, 600)
        assert processor.THUMBNAIL_SIZES["original"] is None


class TestValidateImage:
    def test_validate_image_jpeg_valid(self, processor):
        result = processor.validate_image(_jpeg_bytes(), filename="a.jpg")

        assert result["valid"] is True
        assert result["format"] == "JPEG"
        assert result["size"] == (800, 600)
        assert result["has_transparency"] is False

    def test_validate_image_png_transparency_detected(self, processor):
        result = processor.validate_image(_png_bytes(), filename="a.png")

        assert result["valid"] is True
        assert result["format"] == "PNG"
        assert result["has_transparency"] is True

    def test_validate_image_rejects_oversized_dimensions(self, processor):
        processor.max_dimension = 100
        result = processor.validate_image(_jpeg_bytes(size=(800, 600)))

        assert result["valid"] is False
        assert "too large" in result["error"].lower()

    def test_validate_image_rejects_garbage_bytes(self, processor):
        result = processor.validate_image(b"not an image")

        assert result["valid"] is False
        assert "error" in result


class TestExtractExifData:
    def test_extract_exif_data_includes_basic_dimensions(self, processor):
        exif = processor.extract_exif_data(_jpeg_bytes(size=(640, 480)))

        assert exif["width"] == 640
        assert exif["height"] == 480
        assert exif["format"] == "JPEG"

    def test_extract_exif_data_on_invalid_bytes_returns_empty_dict(self, processor):
        assert processor.extract_exif_data(b"garbage") == {}


class TestOptimizeImage:
    def test_optimize_image_returns_smaller_or_equal_jpeg(self, processor):
        original = _jpeg_bytes(size=(800, 600))
        # Re-encode at very high quality first so optimization has something to shrink
        img = Image.open(io.BytesIO(original))
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=100)
        high_quality = buf.getvalue()

        optimized = processor.optimize_image(high_quality, target_format="JPEG")

        assert isinstance(optimized, bytes)
        assert len(optimized) <= len(high_quality)

    def test_optimize_image_resizes_to_max_size(self, processor):
        original = _jpeg_bytes(size=(1000, 800))
        optimized = processor.optimize_image(original, target_format="JPEG", max_size=(200, 200))

        result_img = Image.open(io.BytesIO(optimized))
        assert result_img.width <= 200
        assert result_img.height <= 200

    def test_optimize_image_invalid_bytes_raises(self, processor):
        with pytest.raises(ValueError):
            processor.optimize_image(b"garbage", target_format="JPEG")


class TestGenerateThumbnails:
    def test_generate_thumbnails_produces_all_sizes(self, processor):
        thumbnails = processor.generate_thumbnails(_jpeg_bytes(size=(1200, 900)))

        assert set(thumbnails.keys()) == {"small", "medium", "large", "original"}
        for name in ("small", "medium", "large"):
            thumb_img = Image.open(io.BytesIO(thumbnails[name]))
            max_w, max_h = processor.THUMBNAIL_SIZES[name]
            assert thumb_img.width <= max_w
            assert thumb_img.height <= max_h

    def test_generate_thumbnails_preserves_aspect_ratio(self, processor):
        thumbnails = processor.generate_thumbnails(_jpeg_bytes(size=(1000, 500)))

        thumb_img = Image.open(io.BytesIO(thumbnails["medium"]))
        original_ratio = 1000 / 500
        thumb_ratio = thumb_img.width / thumb_img.height
        assert abs(original_ratio - thumb_ratio) < 0.1


class TestAddWatermark:
    def test_add_watermark_preserves_dimensions(self, processor):
        watermarked = processor.add_watermark(_jpeg_bytes(size=(800, 600)), "© PhotoShare", position="bottom_right")

        result_img = Image.open(io.BytesIO(watermarked))
        assert result_img.width == 800
        assert result_img.height == 600


class TestApplyFilters:
    @pytest.mark.parametrize("filter_name", ["blur", "sharpen", "smooth", "edge_enhance", "grayscale", "sepia", "vintage"])
    def test_apply_filters_known_filters_succeed(self, processor, filter_name):
        result = processor.apply_filters(_jpeg_bytes(), filter_name)
        assert isinstance(result, bytes)
        assert len(result) > 0

    def test_apply_filters_unknown_filter_raises(self, processor):
        with pytest.raises(ValueError):
            processor.apply_filters(_jpeg_bytes(), "not_a_real_filter")


def _checkerboard_jpeg_bytes(size=(64, 64), light=(255, 255, 255), dark=(0, 0, 0)):
    """A patterned (non-solid-color) image -- get_image_hash's average-vs-pixel
    perceptual hash is all-zero for any solid color, so hash-difference tests
    need actual variation within the image."""
    img = Image.new("RGB", size, color=light)
    for y in range(0, size[1], 8):
        for x in range(0, size[0], 8):
            if (x // 8 + y // 8) % 2 == 0:
                for dy in range(8):
                    for dx in range(8):
                        img.putpixel((x + dx, y + dy), dark)
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


class TestImageHash:
    def test_get_image_hash_is_deterministic(self, processor):
        data = _checkerboard_jpeg_bytes()
        assert processor.get_image_hash(data) == processor.get_image_hash(data)

    def test_get_image_hash_differs_for_different_images(self, processor):
        inverted = _checkerboard_jpeg_bytes(light=(0, 0, 0), dark=(255, 255, 255))
        assert processor.get_image_hash(_checkerboard_jpeg_bytes()) != processor.get_image_hash(inverted)


class TestProcessingStats:
    def test_get_processing_stats_reports_config(self, processor):
        stats = processor.get_processing_stats()

        assert "JPEG" in stats["supported_input_formats"]
        assert "JPEG" in stats["supported_output_formats"]
        assert stats["max_dimension"] == processor.max_dimension
        assert stats["jpeg_quality"] == processor.jpeg_quality
        assert "sepia" in stats["available_filters"]

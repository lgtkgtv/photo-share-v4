#!/usr/bin/env python3
"""
Image Processing Service for Photo Share Application
==================================================

Advanced image processing capabilities including:
- Image optimization and compression
- Thumbnail generation in multiple sizes
- EXIF data extraction and processing
- Image format conversion
- Watermarking and metadata embedding
"""

import io
import os
import logging
import hashlib
from typing import Dict, Any, Tuple, Optional
from datetime import datetime
from PIL import Image, ImageOps, ImageFilter, ImageDraw, ImageFont
from PIL.ExifTags import TAGS
import pillow_heif

# Enable HEIF support
pillow_heif.register_heif_opener()

logger = logging.getLogger(__name__)

class ImageProcessor:
    """Advanced image processing service."""
    
    # Standard thumbnail sizes
    THUMBNAIL_SIZES = {
        "small": (150, 150),
        "medium": (300, 300), 
        "large": (800, 600),
        "original": None  # Keep original size
    }
    
    # Supported formats
    SUPPORTED_INPUT_FORMATS = {
        "JPEG", "JPG", "PNG", "WEBP", "GIF", "HEIC", "HEIF", "TIFF", "BMP"
    }
    
    SUPPORTED_OUTPUT_FORMATS = {
        "JPEG": {"extension": ".jpg", "mime": "image/jpeg"},
        "PNG": {"extension": ".png", "mime": "image/png"},
        "WEBP": {"extension": ".webp", "mime": "image/webp"}
    }
    
    def __init__(self):
        self.max_dimension = int(os.getenv("MAX_IMAGE_DIMENSION", "4000"))
        self.jpeg_quality = int(os.getenv("JPEG_QUALITY", "85"))
        self.webp_quality = int(os.getenv("WEBP_QUALITY", "80"))
        self.png_optimize = True
        
    def validate_image(self, image_data: bytes, filename: str = None) -> Dict[str, Any]:
        """Validate and analyze image data."""
        try:
            with Image.open(io.BytesIO(image_data)) as img:
                # Basic validation
                if img.format not in self.SUPPORTED_INPUT_FORMATS:
                    return {
                        "valid": False,
                        "error": f"Unsupported format: {img.format}. Supported: {', '.join(self.SUPPORTED_INPUT_FORMATS)}"
                    }
                
                # Size validation
                width, height = img.size
                if width > self.max_dimension or height > self.max_dimension:
                    return {
                        "valid": False,
                        "error": f"Image too large: {width}x{height}. Max dimension: {self.max_dimension}"
                    }
                
                # File size validation (50MB limit)
                max_size = 50 * 1024 * 1024
                if len(image_data) > max_size:
                    return {
                        "valid": False,
                        "error": f"File too large: {len(image_data)} bytes. Max: {max_size} bytes"
                    }
                
                return {
                    "valid": True,
                    "format": img.format,
                    "mode": img.mode,
                    "size": img.size,
                    "has_transparency": img.mode in ("RGBA", "LA") or "transparency" in img.info,
                    "file_size": len(image_data),
                    "estimated_quality": self._estimate_jpeg_quality(img) if img.format == "JPEG" else None
                }
                
        except Exception as e:
            logger.error(f"Image validation failed: {e}")
            return {"valid": False, "error": f"Invalid image data: {str(e)}"}
    
    def _estimate_jpeg_quality(self, img: Image.Image) -> Optional[int]:
        """Estimate JPEG quality (approximation)."""
        try:
            if hasattr(img, '_getexif') and img._getexif():
                # This is a rough estimation based on quantization tables
                return 85  # Default assumption
            return None
        except:
            return None
    
    def extract_exif_data(self, image_data: bytes) -> Dict[str, Any]:
        """Extract EXIF metadata from image."""
        try:
            with Image.open(io.BytesIO(image_data)) as img:
                exif_dict = {}
                
                if hasattr(img, '_getexif') and img._getexif():
                    exif_data = img._getexif()
                    
                    for tag_id, value in exif_data.items():
                        tag_name = TAGS.get(tag_id, tag_id)
                        
                        # Handle specific tags
                        if tag_name == "DateTime":
                            try:
                                exif_dict["date_taken"] = datetime.strptime(value, "%Y:%m:%d %H:%M:%S")
                            except:
                                exif_dict["date_taken"] = value
                        elif tag_name in ["Make", "Model", "LensModel"]:
                            exif_dict[tag_name.lower()] = str(value)
                        elif tag_name in ["ExposureTime", "FNumber", "ISOSpeedRatings", "FocalLength"]:
                            exif_dict[tag_name.lower()] = value
                        elif tag_name in ["ImageWidth", "ImageLength"]:
                            exif_dict[tag_name.lower()] = value
                        elif tag_name == "Orientation":
                            exif_dict["orientation"] = value
                        elif tag_name == "Software":
                            exif_dict["software"] = str(value)
                        elif tag_name in ["GPSInfo"]:
                            # GPS data parsing
                            if isinstance(value, dict):
                                gps_data = self._parse_gps_data(value)
                                if gps_data:
                                    exif_dict.update(gps_data)
                
                # Add basic image info
                exif_dict.update({
                    "width": img.width,
                    "height": img.height,
                    "format": img.format,
                    "mode": img.mode,
                    "has_transparency": img.mode in ("RGBA", "LA") or "transparency" in img.info
                })
                
                return exif_dict
                
        except Exception as e:
            logger.error(f"EXIF extraction failed: {e}")
            return {}
    
    def _parse_gps_data(self, gps_info: Dict) -> Dict[str, float]:
        """Parse GPS coordinates from EXIF data."""
        try:
            def convert_to_degrees(value):
                """Convert GPS coordinates to decimal degrees."""
                d, m, s = value
                return d + (m / 60.0) + (s / 3600.0)
            
            gps_data = {}
            
            if 2 in gps_info and 1 in gps_info:  # Latitude
                lat = convert_to_degrees(gps_info[2])
                if gps_info[1] == 'S':
                    lat = -lat
                gps_data["latitude"] = lat
                
            if 4 in gps_info and 3 in gps_info:  # Longitude
                lon = convert_to_degrees(gps_info[4])
                if gps_info[3] == 'W':
                    lon = -lon
                gps_data["longitude"] = lon
                
            if 6 in gps_info:  # Altitude
                gps_data["altitude"] = float(gps_info[6])
                
            return gps_data
            
        except Exception as e:
            logger.error(f"GPS parsing failed: {e}")
            return {}
    
    def optimize_image(self, image_data: bytes, target_format: str = "JPEG", max_size: Optional[Tuple[int, int]] = None) -> bytes:
        """Optimize image for storage and web delivery."""
        try:
            with Image.open(io.BytesIO(image_data)) as img:
                # Handle EXIF orientation
                img = ImageOps.exif_transpose(img)
                
                # Resize if needed
                if max_size:
                    img.thumbnail(max_size, Image.Resampling.LANCZOS)
                
                # Convert mode if necessary
                if target_format == "JPEG" and img.mode in ("RGBA", "LA"):
                    # Create white background for JPEG
                    background = Image.new("RGB", img.size, (255, 255, 255))
                    if img.mode == "RGBA":
                        background.paste(img, mask=img.split()[-1])
                    else:
                        background.paste(img)
                    img = background
                elif target_format in ["PNG", "WEBP"] and img.mode not in ("RGBA", "RGB"):
                    img = img.convert("RGBA")
                
                # Save with optimization
                output_buffer = io.BytesIO()
                save_params = {"format": target_format}
                
                if target_format == "JPEG":
                    save_params.update({
                        "quality": self.jpeg_quality,
                        "optimize": True,
                        "progressive": True
                    })
                elif target_format == "PNG":
                    save_params.update({
                        "optimize": self.png_optimize,
                        "compress_level": 6
                    })
                elif target_format == "WEBP":
                    save_params.update({
                        "quality": self.webp_quality,
                        "optimize": True
                    })
                
                img.save(output_buffer, **save_params)
                return output_buffer.getvalue()
                
        except Exception as e:
            logger.error(f"Image optimization failed: {e}")
            raise ValueError(f"Image optimization failed: {str(e)}")
    
    def generate_thumbnails(self, image_data: bytes) -> Dict[str, bytes]:
        """Generate multiple thumbnail sizes."""
        thumbnails = {}
        
        try:
            with Image.open(io.BytesIO(image_data)) as img:
                # Handle EXIF orientation
                img = ImageOps.exif_transpose(img)
                
                for size_name, dimensions in self.THUMBNAIL_SIZES.items():
                    if dimensions is None:  # Original size
                        thumbnails[size_name] = self.optimize_image(image_data, "JPEG")
                        continue
                    
                    # Create thumbnail
                    thumb_img = img.copy()
                    thumb_img.thumbnail(dimensions, Image.Resampling.LANCZOS)
                    
                    # Convert to RGB if needed for JPEG
                    if thumb_img.mode in ("RGBA", "LA"):
                        background = Image.new("RGB", thumb_img.size, (255, 255, 255))
                        if thumb_img.mode == "RGBA":
                            background.paste(thumb_img, mask=thumb_img.split()[-1])
                        else:
                            background.paste(thumb_img)
                        thumb_img = background
                    
                    # Save thumbnail
                    thumb_buffer = io.BytesIO()
                    quality = 90 if size_name == "large" else 85
                    thumb_img.save(thumb_buffer, format="JPEG", quality=quality, optimize=True)
                    thumbnails[size_name] = thumb_buffer.getvalue()
                    
        except Exception as e:
            logger.error(f"Thumbnail generation failed: {e}")
            raise ValueError(f"Thumbnail generation failed: {str(e)}")
        
        return thumbnails
    
    def add_watermark(self, image_data: bytes, watermark_text: str, position: str = "bottom_right") -> bytes:
        """Add text watermark to image."""
        try:
            with Image.open(io.BytesIO(image_data)) as img:
                # Handle EXIF orientation
                img = ImageOps.exif_transpose(img)
                
                # Create a drawing context
                draw = ImageDraw.Draw(img)
                
                # Calculate font size based on image size
                font_size = max(12, min(img.width, img.height) // 30)
                
                try:
                    # Try to use a nice font
                    font = ImageFont.truetype("arial.ttf", font_size)
                except:
                    # Fall back to default font
                    font = ImageFont.load_default()
                
                # Get text dimensions
                bbox = draw.textbbox((0, 0), watermark_text, font=font)
                text_width = bbox[2] - bbox[0]
                text_height = bbox[3] - bbox[1]
                
                # Calculate position
                margin = 10
                if position == "bottom_right":
                    x = img.width - text_width - margin
                    y = img.height - text_height - margin
                elif position == "bottom_left":
                    x = margin
                    y = img.height - text_height - margin
                elif position == "top_right":
                    x = img.width - text_width - margin
                    y = margin
                elif position == "top_left":
                    x = margin
                    y = margin
                else:  # center
                    x = (img.width - text_width) // 2
                    y = (img.height - text_height) // 2
                
                # Add text with shadow/outline for better visibility
                shadow_offset = 1
                # Draw shadow
                draw.text((x + shadow_offset, y + shadow_offset), watermark_text, font=font, fill=(0, 0, 0, 128))
                # Draw main text
                draw.text((x, y), watermark_text, font=font, fill=(255, 255, 255, 180))
                
                # Save result
                output_buffer = io.BytesIO()
                img.save(output_buffer, format="JPEG", quality=self.jpeg_quality, optimize=True)
                return output_buffer.getvalue()
                
        except Exception as e:
            logger.error(f"Watermark addition failed: {e}")
            raise ValueError(f"Watermark addition failed: {str(e)}")
    
    def apply_filters(self, image_data: bytes, filter_name: str) -> bytes:
        """Apply image filters."""
        try:
            with Image.open(io.BytesIO(image_data)) as img:
                # Handle EXIF orientation
                img = ImageOps.exif_transpose(img)
                
                if filter_name == "blur":
                    img = img.filter(ImageFilter.BLUR)
                elif filter_name == "sharpen":
                    img = img.filter(ImageFilter.SHARPEN)
                elif filter_name == "smooth":
                    img = img.filter(ImageFilter.SMOOTH)
                elif filter_name == "edge_enhance":
                    img = img.filter(ImageFilter.EDGE_ENHANCE)
                elif filter_name == "grayscale":
                    img = ImageOps.grayscale(img)
                elif filter_name == "sepia":
                    img = self._apply_sepia(img)
                elif filter_name == "vintage":
                    img = self._apply_vintage(img)
                else:
                    raise ValueError(f"Unknown filter: {filter_name}")
                
                # Save result
                output_buffer = io.BytesIO()
                save_format = "JPEG" if img.mode == "RGB" else "PNG"
                img.save(output_buffer, format=save_format, quality=self.jpeg_quality, optimize=True)
                return output_buffer.getvalue()
                
        except Exception as e:
            logger.error(f"Filter application failed: {e}")
            raise ValueError(f"Filter application failed: {str(e)}")
    
    def _apply_sepia(self, img: Image.Image) -> Image.Image:
        """Apply sepia tone effect."""
        if img.mode != "RGB":
            img = img.convert("RGB")
        
        pixels = img.load()
        for y in range(img.height):
            for x in range(img.width):
                r, g, b = pixels[x, y]
                
                # Sepia formula
                tr = int(0.393 * r + 0.769 * g + 0.189 * b)
                tg = int(0.349 * r + 0.686 * g + 0.168 * b)
                tb = int(0.272 * r + 0.534 * g + 0.131 * b)
                
                # Clamp values
                pixels[x, y] = (min(255, tr), min(255, tg), min(255, tb))
        
        return img
    
    def _apply_vintage(self, img: Image.Image) -> Image.Image:
        """Apply vintage effect."""
        if img.mode != "RGB":
            img = img.convert("RGB")
        
        # Reduce saturation and add warm tone
        pixels = img.load()
        for y in range(img.height):
            for x in range(img.width):
                r, g, b = pixels[x, y]
                
                # Desaturate slightly
                gray = int(0.3 * r + 0.6 * g + 0.1 * b)
                r = int(r * 0.8 + gray * 0.2)
                g = int(g * 0.8 + gray * 0.2)
                b = int(b * 0.7 + gray * 0.3)  # Reduce blue more for warm tone
                
                # Add slight yellow tint
                r = min(255, int(r * 1.1))
                g = min(255, int(g * 1.05))
                
                pixels[x, y] = (r, g, b)
        
        return img
    
    def get_image_hash(self, image_data: bytes) -> str:
        """Generate perceptual hash for duplicate detection."""
        try:
            with Image.open(io.BytesIO(image_data)) as img:
                # Convert to grayscale and resize to 8x8
                img = ImageOps.grayscale(img)
                img = img.resize((8, 8), Image.Resampling.LANCZOS)
                
                # Get pixel values
                pixels = list(img.getdata())
                
                # Calculate average
                avg = sum(pixels) / len(pixels)
                
                # Create hash
                hash_bits = []
                for pixel in pixels:
                    hash_bits.append('1' if pixel > avg else '0')
                
                # Convert to hex
                hash_string = ''.join(hash_bits)
                hash_int = int(hash_string, 2)
                return format(hash_int, '016x')
                
        except Exception as e:
            logger.error(f"Image hashing failed: {e}")
            return hashlib.md5(image_data).hexdigest()
    
    def get_processing_stats(self) -> Dict[str, Any]:
        """Get image processing statistics."""
        return {
            "supported_input_formats": list(self.SUPPORTED_INPUT_FORMATS),
            "supported_output_formats": list(self.SUPPORTED_OUTPUT_FORMATS.keys()),
            "thumbnail_sizes": self.THUMBNAIL_SIZES,
            "max_dimension": self.max_dimension,
            "jpeg_quality": self.jpeg_quality,
            "webp_quality": self.webp_quality,
            "available_filters": ["blur", "sharpen", "smooth", "edge_enhance", "grayscale", "sepia", "vintage"]
        }

# Global image processor instance
image_processor = ImageProcessor()
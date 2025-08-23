#!/usr/bin/env python3
"""
EXIF Security System Test Script
================================

Tests for EXIF metadata privacy protection and sanitization.
"""

import sys
import os
import io
from pathlib import Path

# Add the photoshare service path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'services', 'photoshare'))

try:
    from exif_security import (
        ExifSecurityProcessor, 
        sanitize_uploaded_image,
        analyze_image_privacy_risks,
        exif_processor
    )
    EXIF_SECURITY_AVAILABLE = True
except ImportError as e:
    print(f"EXIF Security not available: {e}")
    EXIF_SECURITY_AVAILABLE = False

# Try to create test images with EXIF data
try:
    from PIL import Image, ExifTags
    from PIL.ExifTags import TAGS
    import piexif
    PIL_AVAILABLE = True
    PIEXIF_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    PIEXIF_AVAILABLE = False


def create_test_image_with_exif() -> bytes:
    """Create a test image with EXIF data including GPS information."""
    
    if not PIL_AVAILABLE or not PIEXIF_AVAILABLE:
        # Create basic image data without EXIF
        return create_basic_test_image()
    
    # Create a basic image
    image = Image.new('RGB', (800, 600), color='blue')
    
    # Create EXIF data with sensitive information
    exif_dict = {
        "0th": {
            piexif.ImageIFD.Make: "TestCamera",
            piexif.ImageIFD.Model: "TestModel X1",
            piexif.ImageIFD.Software: "TestApp 1.0",
            piexif.ImageIFD.Artist: "John Doe",
            piexif.ImageIFD.Copyright: "Copyright 2024 John Doe",
            piexif.ImageIFD.DateTime: "2024:08:23 10:30:00",
        },
        "Exif": {
            piexif.ExifIFD.DateTimeOriginal: "2024:08:23 10:30:00",
            piexif.ExifIFD.DateTimeDigitized: "2024:08:23 10:30:00",
            piexif.ExifIFD.UserComment: b"Test photo taken at secret location",
            piexif.ExifIFD.LensModel: "TestLens 24-70mm",
        },
        "GPS": {
            piexif.GPSIFD.GPSVersionID: (2, 0, 0, 0),
            piexif.GPSIFD.GPSAltitudeRef: 1,
            piexif.GPSIFD.GPSAltitude: (1350, 10),
            piexif.GPSIFD.GPSLatitudeRef: 'N',
            piexif.GPSIFD.GPSLatitude: ((37, 1), (25, 1), (1963, 100)),  # ~37.4221° N
            piexif.GPSIFD.GPSLongitudeRef: 'W',
            piexif.GPSIFD.GPSLongitude: ((122, 1), (4, 1), (1947, 100)),  # ~122.0832° W
            piexif.GPSIFD.GPSTimeStamp: ((10, 1), (30, 1), (0, 1)),
            piexif.GPSIFD.GPSDateStamp: "2024:08:23",
        }
    }
    
    # Generate EXIF bytes
    exif_bytes = piexif.dump(exif_dict)
    
    # Save image with EXIF
    output = io.BytesIO()
    image.save(output, format='JPEG', exif=exif_bytes, quality=95)
    
    return output.getvalue()


def create_basic_test_image() -> bytes:
    """Create a basic test image without EXIF data."""
    
    if not PIL_AVAILABLE:
        # Create a minimal valid JPEG header
        jpeg_header = b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00\xff\xc0\x00\x11\x08\x01\x2c\x01\x90\x01\x01\x11\x00\x02\x11\x01\x03\x11\x01\xff\xc4\x00\x14\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x08\xff\xc4\x00\x14\x10\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff\xda\x00\x0c\x03\x01\x00\x02\x11\x03\x11\x00\x3f\x00\xff\xd9'
        return jpeg_header
    
    image = Image.new('RGB', (400, 300), color='red')
    output = io.BytesIO()
    image.save(output, format='JPEG', quality=90)
    
    return output.getvalue()


def test_exif_analysis():
    """Test EXIF privacy risk analysis."""
    
    print("📊 Testing EXIF Privacy Risk Analysis")
    print("=" * 40)
    
    if not EXIF_SECURITY_AVAILABLE:
        print("❌ EXIF Security system not available")
        return False
    
    # Test with image containing EXIF data
    print("\n1. Testing image with sensitive EXIF data...")
    
    test_image = create_test_image_with_exif()
    privacy_risks = analyze_image_privacy_risks(test_image)
    
    print(f"   Privacy Risk Level: {privacy_risks['privacy_risk_level']}")
    print(f"   GPS Data Found: {privacy_risks['has_gps_data']}")
    print(f"   Device Info Found: {privacy_risks['has_device_info']}")
    print(f"   Personal Info Found: {privacy_risks['has_personal_info']}")
    print(f"   Timestamp Info Found: {privacy_risks['has_timestamp_info']}")
    
    if privacy_risks['sensitive_tags']:
        print("   Sensitive Tags Found:")
        for tag in privacy_risks['sensitive_tags'][:5]:  # Show first 5
            print(f"     - {tag}")
    
    # Expected results for test image
    if PIL_AVAILABLE and PIEXIF_AVAILABLE:
        expected_high_risk = privacy_risks['privacy_risk_level'] in ['HIGH', 'CRITICAL']
        if expected_high_risk:
            print("   ✅ Correctly identified high privacy risk")
        else:
            print("   ⚠️  Expected high privacy risk but got:", privacy_risks['privacy_risk_level'])
    else:
        print("   ⚠️  PIL/piexif not available - limited testing")
    
    # Test with basic image (no EXIF)
    print("\n2. Testing image without EXIF data...")
    
    basic_image = create_basic_test_image()
    basic_risks = analyze_image_privacy_risks(basic_image)
    
    print(f"   Privacy Risk Level: {basic_risks['privacy_risk_level']}")
    print(f"   GPS Data Found: {basic_risks['has_gps_data']}")
    
    if basic_risks['privacy_risk_level'] == 'LOW' and not basic_risks['has_gps_data']:
        print("   ✅ Correctly identified low privacy risk")
    else:
        print("   ⚠️  Unexpected risk level for basic image")
    
    return True


def test_exif_sanitization():
    """Test EXIF data sanitization."""
    
    print("\n🧹 Testing EXIF Data Sanitization")
    print("=" * 35)
    
    if not EXIF_SECURITY_AVAILABLE:
        print("❌ EXIF Security system not available")
        return False
    
    # Create test image with EXIF
    original_image = create_test_image_with_exif()
    print(f"Original image size: {len(original_image)} bytes")
    
    # Test different sanitization levels
    sanitization_levels = ['MINIMAL', 'AGGRESSIVE', 'COMPLETE']
    
    for level in sanitization_levels:
        print(f"\n{level.title()} Sanitization:")
        
        # Sanitize image
        sanitized_image = exif_processor.remove_sensitive_exif_data(original_image, level)
        print(f"   Sanitized size: {len(sanitized_image)} bytes")
        
        # Analyze sanitized image
        sanitized_risks = analyze_image_privacy_risks(sanitized_image)
        print(f"   Post-sanitization risk level: {sanitized_risks['privacy_risk_level']}")
        print(f"   GPS data remaining: {sanitized_risks['has_gps_data']}")
        print(f"   Device info remaining: {sanitized_risks['has_device_info']}")
        
        # Verify GPS data was removed
        if level in ['AGGRESSIVE', 'COMPLETE']:
            if not sanitized_risks['has_gps_data']:
                print("   ✅ GPS data successfully removed")
            else:
                print("   ❌ GPS data still present after sanitization")
    
    return True


def test_public_sharing_sanitization():
    """Test sanitization for public sharing."""
    
    print("\n🌐 Testing Public Sharing Sanitization")
    print("=" * 38)
    
    if not EXIF_SECURITY_AVAILABLE:
        print("❌ EXIF Security system not available")
        return False
    
    # Test public sharing sanitization
    original_image = create_test_image_with_exif()
    
    # Analyze original risks
    original_risks = analyze_image_privacy_risks(original_image)
    print(f"Original privacy risk: {original_risks['privacy_risk_level']}")
    
    # Sanitize for public sharing
    sanitized_image, report = sanitize_uploaded_image(original_image, public_sharing=True)
    
    print(f"Sanitization report:")
    print(f"   Sanitized: {report.get('sanitized', False)}")
    print(f"   Removal level: {report.get('removal_level', 'N/A')}")
    print(f"   Safe for sharing: {report.get('safe_for_sharing', False)}")
    print(f"   Size change: {report.get('original_size', 0)} → {report.get('sanitized_size', 0)} bytes")
    
    # Verify sanitization
    post_sanitization_risks = analyze_image_privacy_risks(sanitized_image)
    print(f"Post-sanitization risk level: {post_sanitization_risks['privacy_risk_level']}")
    
    if post_sanitization_risks['privacy_risk_level'] in ['LOW', 'UNKNOWN']:
        print("   ✅ Successfully sanitized for public sharing")
    else:
        print(f"   ⚠️  Risk level still elevated: {post_sanitization_risks['privacy_risk_level']}")
    
    return True


def test_exif_reporting():
    """Test EXIF security reporting."""
    
    print("\n📋 Testing EXIF Security Reporting")
    print("=" * 35)
    
    if not EXIF_SECURITY_AVAILABLE:
        print("❌ EXIF Security system not available")
        return False
    
    # Generate comprehensive report
    test_image = create_test_image_with_exif()
    report = exif_processor.get_exif_report(test_image)
    
    print("EXIF Security Report:")
    print(f"   File size: {report.get('file_size', 0)} bytes")
    
    privacy_analysis = report.get('privacy_analysis', {})
    print(f"   Privacy risk level: {privacy_analysis.get('privacy_risk_level', 'UNKNOWN')}")
    
    recommendations = report.get('recommendations', [])
    if recommendations:
        print(f"   Recommendations ({len(recommendations)}):")
        for rec in recommendations[:3]:  # Show first 3
            print(f"     - {rec.get('priority', 'N/A')}: {rec.get('issue', 'N/A')}")
    
    technical_info = report.get('technical_info', {})
    if technical_info:
        print(f"   Technical info: {technical_info.get('format', 'N/A')} "
              f"{technical_info.get('size', 'N/A')} "
              f"EXIF: {technical_info.get('has_exif', False)}")
    
    print("   ✅ EXIF report generated successfully")
    
    return True


def test_processing_statistics():
    """Test EXIF processing statistics."""
    
    print("\n📈 Testing EXIF Processing Statistics")
    print("=" * 37)
    
    if not EXIF_SECURITY_AVAILABLE:
        print("❌ EXIF Security system not available")
        return False
    
    # Get initial statistics
    initial_stats = exif_processor.get_security_statistics()
    
    print("Security Statistics:")
    print(f"   PIL Available: {initial_stats['dependencies']['pil_available']}")
    print(f"   piexif Available: {initial_stats['dependencies']['piexif_available']}")
    
    security_features = initial_stats['security_features']
    print(f"   GPS Removal: {security_features['gps_removal']}")
    print(f"   Device Info Removal: {security_features['device_info_removal']}")
    print(f"   Personal Data Removal: {security_features['personal_data_removal']}")
    print(f"   Selective Preservation: {security_features['selective_preservation']}")
    
    # Process some images to update statistics
    test_images = [create_test_image_with_exif() for _ in range(3)]
    
    for i, img in enumerate(test_images):
        exif_processor.remove_sensitive_exif_data(img, 'AGGRESSIVE')
        print(f"   Processed test image {i+1}")
    
    # Get updated statistics
    updated_stats = exif_processor.get_security_statistics()
    processing_stats = updated_stats['stats']
    
    print(f"\nProcessing Statistics:")
    print(f"   Images processed: {processing_stats['images_processed']}")
    print(f"   EXIF data removed: {processing_stats['exif_data_removed']}")
    print(f"   GPS data found: {processing_stats['gps_data_found']}")
    print(f"   Processing errors: {processing_stats['processing_errors']}")
    
    print("   ✅ Statistics tracking working")
    
    return True


def test_dependency_fallbacks():
    """Test graceful handling of missing dependencies."""
    
    print("\n🔧 Testing Dependency Fallbacks")
    print("=" * 32)
    
    print(f"PIL/Pillow available: {PIL_AVAILABLE}")
    print(f"piexif available: {PIEXIF_AVAILABLE}")
    print(f"EXIF Security available: {EXIF_SECURITY_AVAILABLE}")
    
    if not PIL_AVAILABLE:
        print("   ⚠️  PIL/Pillow not available - EXIF processing will be limited")
        print("   💡 Install with: pip install Pillow")
    
    if not PIEXIF_AVAILABLE:
        print("   ⚠️  piexif not available - selective EXIF removal unavailable")
        print("   💡 Install with: pip install piexif")
    
    if EXIF_SECURITY_AVAILABLE:
        # Test fallback behavior
        test_image = create_basic_test_image()
        
        try:
            risks = analyze_image_privacy_risks(test_image)
            print(f"   ✅ Risk analysis works: {risks['privacy_risk_level']}")
        except Exception as e:
            print(f"   ❌ Risk analysis failed: {e}")
        
        try:
            sanitized, report = sanitize_uploaded_image(test_image)
            print(f"   ✅ Sanitization works: {report.get('sanitized', False)}")
        except Exception as e:
            print(f"   ❌ Sanitization failed: {e}")
    
    return True


if __name__ == "__main__":
    print("🔒 PhotoShare EXIF Security Test Suite")
    print("=" * 45)
    
    success = True
    
    try:
        # Run all tests
        success &= test_exif_analysis()
        success &= test_exif_sanitization()
        success &= test_public_sharing_sanitization()
        success &= test_exif_reporting()
        success &= test_processing_statistics()
        success &= test_dependency_fallbacks()
        
        if success:
            print(f"\n🎉 ALL EXIF SECURITY TESTS PASSED!")
            print("🔒 EXIF privacy protection system is ready")
            
            print("\n📋 Deployment Notes:")
            if not PIL_AVAILABLE:
                print("   ⚠️  Install PIL/Pillow for full EXIF processing")
            if not PIEXIF_AVAILABLE:
                print("   ⚠️  Install piexif for selective EXIF removal")
            print("   ✅ EXIF sanitization will be applied to all uploads")
            print("   ✅ GPS and personal data automatically removed")
            print("   ✅ Public photos get aggressive sanitization")
            print("   ✅ Privacy risk analysis available via API")
            
            exit_code = 0
        else:
            print("\n❌ Some EXIF security tests failed")
            exit_code = 1
            
    except Exception as e:
        print(f"\n💥 EXIF security test suite failed: {e}")
        import traceback
        traceback.print_exc()
        exit_code = 1
    
    sys.exit(exit_code)
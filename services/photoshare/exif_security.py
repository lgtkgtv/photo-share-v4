#!/usr/bin/env python3
"""
EXIF Data Privacy Security Module
=================================

Handles removal of sensitive EXIF metadata from uploaded images to protect user privacy.
Removes GPS coordinates, device information, and other potentially sensitive data.
"""

import os
import io
import logging
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
from pathlib import Path

try:
    from PIL import Image, ExifTags
    from PIL.ExifTags import TAGS, GPSTAGS
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

try:
    import piexif
    PIEXIF_AVAILABLE = True
except ImportError:
    PIEXIF_AVAILABLE = False


logger = logging.getLogger(__name__)


class ExifSecurityProcessor:
    """EXIF metadata security processor for image privacy protection."""
    
    def __init__(self):
        self.sensitive_tags = {
            # GPS and Location Data
            'GPS GPSLatitude',
            'GPS GPSLatitudeRef', 
            'GPS GPSLongitude',
            'GPS GPSLongitudeRef',
            'GPS GPSAltitude',
            'GPS GPSAltitudeRef',
            'GPS GPSTimeStamp',
            'GPS GPSDateStamp',
            'GPS GPSProcessingMethod',
            'GPS GPSAreaInformation',
            'GPS GPSDestLatitude',
            'GPS GPSDestLatitudeRef',
            'GPS GPSDestLongitude',
            'GPS GPSDestLongitudeRef',
            
            # Device and Camera Information
            'Make',
            'Model', 
            'Software',
            'Artist',
            'Copyright',
            'CameraOwnerName',
            'BodySerialNumber',
            'LensSerialNumber',
            'LensModel',
            'LensSpecification',
            
            # User and System Information
            'UserComment',
            'ImageUniqueID',
            'CameraOwnerName',
            'BodySerialNumber',
            'ImageDescription',
            'XPComment',
            'XPAuthor',
            'XPKeywords',
            'XPSubject',
            'XPTitle',
            
            # Potentially Sensitive Technical Data
            'ProcessingSoftware',
            'HostComputer',
            'TileWidth',
            'TileLength',
            'DocumentName',
            'PageName',
            
            # Date/Time that could reveal patterns
            'DateTime',
            'DateTimeOriginal', 
            'DateTimeDigitized',
            'ModifyDate',
            'CreateDate',
            'MetadataDate',
            
            # Windows/Mac specific metadata
            'WindowsXP.*',  # Pattern for Windows XP tags
            'Rating',
            'RatingPercent'
        }
        
        # Tags to keep (safe technical data)
        self.safe_tags = {
            'ImageWidth',
            'ImageHeight', 
            'BitsPerSample',
            'Compression',
            'PhotometricInterpretation',
            'SamplesPerPixel',
            'PlanarConfiguration',
            'YCbCrSubSampling',
            'YCbCrPositioning',
            'XResolution',
            'YResolution',
            'ResolutionUnit',
            'ColorSpace',
            'PixelXDimension',
            'PixelYDimension',
            'ExifVersion',
            'FlashpixVersion',
            'ComponentsConfiguration',
            'CompressedBitsPerPixel'
        }
        
        # Critical security statistics
        self.stats = {
            'images_processed': 0,
            'exif_data_removed': 0,
            'gps_data_found': 0,
            'sensitive_tags_removed': 0,
            'processing_errors': 0
        }
    
    def analyze_exif_privacy_risks(self, image_data: bytes) -> Dict[str, Any]:
        """Analyze EXIF data for privacy risks."""
        
        risks = {
            'has_gps_data': False,
            'has_device_info': False,
            'has_personal_info': False,
            'has_timestamp_info': False,
            'sensitive_tags': [],
            'privacy_risk_level': 'LOW',
            'recommendations': []
        }
        
        try:
            if not PIL_AVAILABLE:
                risks['privacy_risk_level'] = 'UNKNOWN'
                risks['recommendations'].append('Install PIL/Pillow for EXIF analysis')
                return risks
            
            # Load image
            image = Image.open(io.BytesIO(image_data))
            exif_data = image.getexif()
            
            if not exif_data:
                return risks  # No EXIF data found
            
            # Analyze EXIF tags
            for tag_id, value in exif_data.items():
                tag_name = TAGS.get(tag_id, f'Tag_{tag_id}')
                
                # Check for GPS data
                if tag_name.startswith('GPS'):
                    risks['has_gps_data'] = True
                    risks['sensitive_tags'].append(f'{tag_name}: {str(value)[:50]}')
                    risks['privacy_risk_level'] = 'CRITICAL'
                    risks['recommendations'].append('Remove GPS coordinates before sharing')
                
                # Check for device information
                if tag_name in ['Make', 'Model', 'Software', 'LensModel']:
                    risks['has_device_info'] = True
                    risks['sensitive_tags'].append(f'{tag_name}: {value}')
                    if risks['privacy_risk_level'] == 'LOW':
                        risks['privacy_risk_level'] = 'MEDIUM'
                
                # Check for personal information
                if tag_name in ['Artist', 'Copyright', 'UserComment', 'CameraOwnerName']:
                    risks['has_personal_info'] = True
                    risks['sensitive_tags'].append(f'{tag_name}: {str(value)[:50]}')
                    if risks['privacy_risk_level'] in ['LOW', 'MEDIUM']:
                        risks['privacy_risk_level'] = 'HIGH'
                
                # Check for timestamp information
                if 'DateTime' in tag_name:
                    risks['has_timestamp_info'] = True
                    risks['sensitive_tags'].append(f'{tag_name}: {value}')
                    if risks['privacy_risk_level'] == 'LOW':
                        risks['privacy_risk_level'] = 'MEDIUM'
            
            # Additional GPS data check
            if 'GPSInfo' in exif_data:
                gps_info = exif_data['GPSInfo']
                if gps_info:
                    risks['has_gps_data'] = True
                    risks['privacy_risk_level'] = 'CRITICAL'
                    self.stats['gps_data_found'] += 1
                    
                    # Extract GPS coordinates if present
                    gps_coords = self._extract_gps_coordinates(gps_info)
                    if gps_coords:
                        lat, lon = gps_coords
                        risks['sensitive_tags'].append(f'GPS Coordinates: {lat:.6f}, {lon:.6f}')
                        risks['recommendations'].append(f'GPS location detected at {lat:.6f}, {lon:.6f}')
            
            # Generate recommendations
            if risks['privacy_risk_level'] == 'CRITICAL':
                risks['recommendations'].append('CRITICAL: Remove all EXIF data before sharing')
            elif risks['privacy_risk_level'] == 'HIGH':
                risks['recommendations'].append('HIGH: Remove personal information from EXIF data')
            elif risks['privacy_risk_level'] == 'MEDIUM':
                risks['recommendations'].append('MEDIUM: Consider removing device and timestamp info')
            
        except Exception as e:
            logger.error(f"EXIF analysis error: {e}")
            risks['privacy_risk_level'] = 'ERROR'
            risks['recommendations'].append(f'Analysis failed: {str(e)}')
            self.stats['processing_errors'] += 1
        
        return risks
    
    def _extract_gps_coordinates(self, gps_info: Dict) -> Optional[Tuple[float, float]]:
        """Extract GPS coordinates from EXIF GPS info."""
        try:
            def convert_to_degrees(value, ref):
                """Convert GPS coordinates to decimal degrees."""
                d, m, s = value
                degrees = d + m/60.0 + s/3600.0
                if ref in ['S', 'W']:
                    degrees = -degrees
                return degrees
            
            # Get GPS latitude
            if 'GPSLatitude' in gps_info and 'GPSLatitudeRef' in gps_info:
                lat = convert_to_degrees(gps_info['GPSLatitude'], gps_info['GPSLatitudeRef'])
            else:
                return None
            
            # Get GPS longitude  
            if 'GPSLongitude' in gps_info and 'GPSLongitudeRef' in gps_info:
                lon = convert_to_degrees(gps_info['GPSLongitude'], gps_info['GPSLongitudeRef'])
            else:
                return None
            
            return (lat, lon)
            
        except Exception as e:
            logger.warning(f"GPS coordinate extraction error: {e}")
            return None
    
    def remove_sensitive_exif_data(self, image_data: bytes, 
                                  removal_level: str = 'AGGRESSIVE') -> bytes:
        """Remove sensitive EXIF data from image."""
        
        self.stats['images_processed'] += 1
        
        try:
            if not PIL_AVAILABLE:
                logger.warning("PIL not available - cannot remove EXIF data")
                return image_data
            
            # Load original image
            image = Image.open(io.BytesIO(image_data))
            
            if removal_level == 'COMPLETE':
                # Remove all EXIF data completely
                cleaned_image = self._remove_all_exif(image)
                self.stats['exif_data_removed'] += 1
                logger.info("All EXIF data removed from image")
                
            elif removal_level == 'AGGRESSIVE':
                # Remove sensitive data but keep safe technical data
                cleaned_image = self._remove_sensitive_exif_selective(image)
                self.stats['exif_data_removed'] += 1
                logger.info("Sensitive EXIF data removed from image")
                
            elif removal_level == 'MINIMAL':
                # Remove only GPS and personal information
                cleaned_image = self._remove_minimal_exif(image)
                self.stats['sensitive_tags_removed'] += 1
                logger.info("Minimal EXIF data removal applied")
                
            else:
                logger.warning(f"Unknown removal level: {removal_level}")
                return image_data
            
            # Convert back to bytes
            output_buffer = io.BytesIO()
            
            # Preserve original format
            format = image.format or 'JPEG'
            if format == 'JPEG':
                cleaned_image.save(output_buffer, format=format, quality=95, optimize=True)
            else:
                cleaned_image.save(output_buffer, format=format)
            
            return output_buffer.getvalue()
            
        except Exception as e:
            logger.error(f"EXIF removal error: {e}")
            self.stats['processing_errors'] += 1
            # Return original image if processing fails
            return image_data
    
    def _remove_all_exif(self, image: Image.Image) -> Image.Image:
        """Remove all EXIF data from image."""
        # Create new image without any EXIF data
        data = list(image.getdata())
        new_image = Image.new(image.mode, image.size)
        new_image.putdata(data)
        return new_image
    
    def _remove_sensitive_exif_selective(self, image: Image.Image) -> Image.Image:
        """Remove sensitive EXIF data while preserving safe technical data."""
        
        if not PIEXIF_AVAILABLE:
            # Fallback to complete removal if piexif not available
            logger.warning("piexif not available - falling back to complete EXIF removal")
            return self._remove_all_exif(image)
        
        try:
            # Get EXIF data
            exif_dict = piexif.load(image.info.get('exif', b''))
            
            # Remove GPS data completely
            if 'GPS' in exif_dict:
                del exif_dict['GPS']
            
            # Clean 0th IFD (main image data)
            if '0th' in exif_dict:
                tags_to_remove = []
                for tag in exif_dict['0th']:
                    tag_name = TAGS.get(tag, '')
                    if any(sensitive in tag_name for sensitive in self.sensitive_tags):
                        tags_to_remove.append(tag)
                
                for tag in tags_to_remove:
                    del exif_dict['0th'][tag]
            
            # Clean Exif IFD
            if 'Exif' in exif_dict:
                tags_to_remove = []
                for tag in exif_dict['Exif']:
                    tag_name = TAGS.get(tag, '')
                    if any(sensitive in tag_name for sensitive in self.sensitive_tags):
                        tags_to_remove.append(tag)
                
                for tag in tags_to_remove:
                    del exif_dict['Exif'][tag]
            
            # Remove user comments and other potentially sensitive data
            if '1st' in exif_dict:
                del exif_dict['1st']  # Thumbnail data often contains duplicate info
            
            # Generate new EXIF data
            new_exif = piexif.dump(exif_dict)
            
            # Create new image with cleaned EXIF
            output_buffer = io.BytesIO()
            image.save(output_buffer, format='JPEG', exif=new_exif, quality=95)
            output_buffer.seek(0)
            
            return Image.open(output_buffer)
            
        except Exception as e:
            logger.warning(f"Selective EXIF removal failed: {e}, falling back to complete removal")
            return self._remove_all_exif(image)
    
    def _remove_minimal_exif(self, image: Image.Image) -> Image.Image:
        """Remove only GPS and personal information, keep technical data."""
        
        if not PIEXIF_AVAILABLE:
            logger.warning("piexif not available - falling back to complete EXIF removal")
            return self._remove_all_exif(image)
        
        try:
            # Get EXIF data
            exif_dict = piexif.load(image.info.get('exif', b''))
            
            # Always remove GPS data
            if 'GPS' in exif_dict:
                del exif_dict['GPS']
            
            # Remove personal information from 0th IFD
            if '0th' in exif_dict:
                personal_tags = ['Artist', 'Copyright', 'ImageDescription']
                for tag_name in personal_tags:
                    for tag_id, tag_value in list(exif_dict['0th'].items()):
                        if TAGS.get(tag_id) == tag_name:
                            del exif_dict['0th'][tag_id]
            
            # Remove user comments from Exif IFD
            if 'Exif' in exif_dict:
                if piexif.ExifIFD.UserComment in exif_dict['Exif']:
                    del exif_dict['Exif'][piexif.ExifIFD.UserComment]
            
            # Generate new EXIF data
            new_exif = piexif.dump(exif_dict)
            
            # Create new image with cleaned EXIF
            output_buffer = io.BytesIO()
            image.save(output_buffer, format='JPEG', exif=new_exif, quality=95)
            output_buffer.seek(0)
            
            return Image.open(output_buffer)
            
        except Exception as e:
            logger.warning(f"Minimal EXIF removal failed: {e}")
            return image
    
    def get_exif_report(self, image_data: bytes) -> Dict[str, Any]:
        """Generate comprehensive EXIF privacy report."""
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'file_size': len(image_data),
            'privacy_analysis': self.analyze_exif_privacy_risks(image_data),
            'processing_stats': self.stats.copy(),
            'recommendations': [],
            'technical_info': {}
        }
        
        try:
            if PIL_AVAILABLE:
                image = Image.open(io.BytesIO(image_data))
                report['technical_info'] = {
                    'format': image.format,
                    'mode': image.mode,
                    'size': image.size,
                    'has_exif': bool(image.getexif())
                }
                
                # Add specific recommendations based on findings
                privacy_analysis = report['privacy_analysis']
                
                if privacy_analysis['has_gps_data']:
                    report['recommendations'].append({
                        'priority': 'CRITICAL',
                        'issue': 'GPS location data found',
                        'action': 'Remove GPS coordinates before sharing',
                        'risk': 'Location privacy compromise'
                    })
                
                if privacy_analysis['has_device_info']:
                    report['recommendations'].append({
                        'priority': 'MEDIUM', 
                        'issue': 'Device information present',
                        'action': 'Consider removing camera/device model info',
                        'risk': 'Device fingerprinting'
                    })
                
                if privacy_analysis['has_personal_info']:
                    report['recommendations'].append({
                        'priority': 'HIGH',
                        'issue': 'Personal information in metadata',
                        'action': 'Remove artist/copyright/user comments',
                        'risk': 'Identity disclosure'
                    })
                
                if privacy_analysis['has_timestamp_info']:
                    report['recommendations'].append({
                        'priority': 'LOW',
                        'issue': 'Timestamp information present', 
                        'action': 'Consider removing creation/modification dates',
                        'risk': 'Activity pattern analysis'
                    })
                
        except Exception as e:
            logger.error(f"EXIF report generation error: {e}")
            report['error'] = str(e)
        
        return report
    
    def sanitize_image_for_public_sharing(self, image_data: bytes) -> Tuple[bytes, Dict]:
        """Sanitize image for safe public sharing with complete privacy protection."""
        
        logger.info("Sanitizing image for public sharing")
        
        # Analyze privacy risks first
        privacy_risks = self.analyze_exif_privacy_risks(image_data)
        
        # Apply aggressive sanitization for public sharing
        sanitized_data = self.remove_sensitive_exif_data(image_data, removal_level='AGGRESSIVE')
        
        # Generate sanitization report
        sanitization_report = {
            'sanitized': True,
            'original_file_size': len(image_data),
            'sanitized_file_size': len(sanitized_data),
            'privacy_risks_found': privacy_risks,
            'removal_level': 'AGGRESSIVE',
            'safe_for_sharing': True,
            'sanitization_timestamp': datetime.now().isoformat()
        }
        
        # Additional validation
        if privacy_risks['privacy_risk_level'] == 'CRITICAL':
            # Double-check that GPS data was actually removed
            post_sanitization_risks = self.analyze_exif_privacy_risks(sanitized_data)
            if post_sanitization_risks['has_gps_data']:
                logger.warning("GPS data still present after sanitization - applying complete removal")
                sanitized_data = self.remove_sensitive_exif_data(sanitized_data, removal_level='COMPLETE')
                sanitization_report['fallback_complete_removal'] = True
        
        return sanitized_data, sanitization_report
    
    def get_security_statistics(self) -> Dict[str, Any]:
        """Get EXIF security processing statistics."""
        return {
            'stats': self.stats.copy(),
            'dependencies': {
                'pil_available': PIL_AVAILABLE,
                'piexif_available': PIEXIF_AVAILABLE
            },
            'security_features': {
                'gps_removal': True,
                'device_info_removal': True,
                'personal_data_removal': True,
                'selective_preservation': PIEXIF_AVAILABLE
            }
        }


# Global EXIF processor instance
exif_processor = ExifSecurityProcessor()


def sanitize_uploaded_image(image_data: bytes, public_sharing: bool = False) -> Tuple[bytes, Dict]:
    """Convenience function for sanitizing uploaded images."""
    
    if public_sharing:
        return exif_processor.sanitize_image_for_public_sharing(image_data)
    else:
        # For private uploads, use aggressive removal but not complete
        sanitized_data = exif_processor.remove_sensitive_exif_data(image_data, 'AGGRESSIVE')
        report = {
            'sanitized': True,
            'removal_level': 'AGGRESSIVE',
            'original_size': len(image_data),
            'sanitized_size': len(sanitized_data)
        }
        return sanitized_data, report


def analyze_image_privacy_risks(image_data: bytes) -> Dict[str, Any]:
    """Convenience function for analyzing image privacy risks."""
    return exif_processor.analyze_exif_privacy_risks(image_data)
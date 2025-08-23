#!/usr/bin/env python3
"""
PhotoShare Application Service - Main Application  
=================================================

This is the main photo sharing application service for the separated architecture.
Integrates with the dedicated authentication service for user management.
"""

import os
import asyncio
import uuid
import secrets
import logging
import time
from contextlib import asynccontextmanager
from typing import Optional
from fastapi import FastAPI, HTTPException, Depends, status, UploadFile, File, Form, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy import select
import uvicorn

# Import service components
from app_database import AppDatabaseManager, get_app_db_manager, Photo
from auth_integration import AuthServiceClient, get_current_user, AuthenticatedUser
from file_storage import FileStorageService
from waf_protection import waf_middleware, validate_file_upload_waf, waf
from security_monitoring import security_monitor, log_security_event, AlertSeverity, ThreatType
from exif_security import sanitize_uploaded_image, analyze_image_privacy_risks, exif_processor
try:
    from jwt_security import jwt_secret_manager
    JWT_SECURITY_AVAILABLE = True
except ImportError:
    JWT_SECURITY_AVAILABLE = False

try:
    from audit_trail import audit_manager, log_audit, verify_audit_integrity
    AUDIT_TRAIL_AVAILABLE = True
except ImportError:
    AUDIT_TRAIL_AVAILABLE = False

try:
    from upload_security import validate_upload_security, get_upload_security_stats
    UPLOAD_SECURITY_AVAILABLE = True
except ImportError:
    UPLOAD_SECURITY_AVAILABLE = False

try:
    from inter_service_security import (
        get_inter_service_manager, 
        validate_service_request,
        log_service_communication,
        get_service_security_stats
    )
    INTER_SERVICE_SECURITY_AVAILABLE = True
except ImportError:
    INTER_SERVICE_SECURITY_AVAILABLE = False

try:
    from session_security import (
        get_session_manager,
        create_secure_session,
        validate_secure_session,
        get_session_security_stats
    )
    SESSION_SECURITY_AVAILABLE = True
except ImportError:
    SESSION_SECURITY_AVAILABLE = False

try:
    from certificate_security import (
        get_certificate_security_manager,
        validate_tls_connection,
        add_certificate_pin,
        get_certificate_security_stats
    )
    CERTIFICATE_SECURITY_AVAILABLE = True
except ImportError:
    CERTIFICATE_SECURITY_AVAILABLE = False

try:
    from database_activity_monitoring import (
        get_database_monitor,
        log_query_execution,
        log_connection_metrics,
        get_database_monitoring_stats,
        get_security_events,
        get_query_performance_stats
    )
    DATABASE_MONITORING_AVAILABLE = True
except ImportError:
    DATABASE_MONITORING_AVAILABLE = False

try:
    from secret_rotation import (
        get_secret_rotation_manager,
        create_secret,
        rotate_secret,
        get_secret,
        get_rotation_statistics
    )
    SECRET_ROTATION_AVAILABLE = True
except ImportError:
    SECRET_ROTATION_AVAILABLE = False

try:
    from advanced_threat_detection import (
        get_threat_detector,
        analyze_threat,
        add_threat_indicator,
        get_threat_statistics
    )
    THREAT_DETECTION_AVAILABLE = True
except ImportError:
    THREAT_DETECTION_AVAILABLE = False

# Security middleware  
security = HTTPBearer()
logger = logging.getLogger(__name__)

# Application lifespan management
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application startup and shutdown."""
    print("🚀 Starting PhotoShare Application Service...")
    
    # Initialize application database
    app_db_manager = get_app_db_manager()
    await app_db_manager.initialize()
    await app_db_manager.create_tables()
    
    # Initialize auth service client
    auth_client = AuthServiceClient()
    
    # Verify connection to auth service
    try:
        health = await auth_client.health_check()
        if health.get("status") != "healthy":
            print("⚠️  Warning: Auth service is not healthy")
    except Exception as e:
        print(f"⚠️  Warning: Could not connect to auth service: {e}")
    
    print("✅ Application service initialized successfully")
    
    yield
    
    # Cleanup
    print("🔄 Shutting down Application Service...")
    await app_db_manager.close()
    print("✅ Application service stopped")

# Create FastAPI app
app = FastAPI(
    title="PhotoShare Application Service",
    description="Photo sharing application service - integrates with authentication service",
    version="2.3.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(","),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# Add WAF protection middleware
app.middleware("http")(waf_middleware)

# Add audit trail middleware
async def audit_middleware(request: Request, call_next):
    """Audit trail middleware for comprehensive request logging."""
    start_time = time.time()
    
    # Get client information
    client_ip = request.client.host if request.client else "unknown"
    if "x-forwarded-for" in request.headers:
        client_ip = request.headers["x-forwarded-for"].split(",")[0].strip()
    
    user_agent = request.headers.get("user-agent", "")
    
    # Get user information from token if available
    user_id = None
    session_id = None
    
    try:
        auth_header = request.headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            # Try to extract user info from token without full validation
            import jwt
            unverified_payload = jwt.decode(token, options={"verify_signature": False})
            user_id = unverified_payload.get("user_id") or unverified_payload.get("sub")
            session_id = unverified_payload.get("session_id") or unverified_payload.get("jti")
    except:
        pass  # Continue without user info
    
    # Process request
    response = await call_next(request)
    
    # Calculate processing time
    processing_time = time.time() - start_time
    
    # Determine risk level based on response and endpoint
    risk_level = "LOW"
    if response.status_code >= 400:
        if response.status_code >= 500:
            risk_level = "HIGH"
        elif response.status_code in [401, 403]:
            risk_level = "MEDIUM"
        else:
            risk_level = "MEDIUM"
    
    # Special risk assessment for sensitive endpoints
    sensitive_endpoints = ["/api/users/", "/api/security/", "/api/admin/"]
    if any(endpoint in str(request.url.path) for endpoint in sensitive_endpoints):
        if risk_level == "LOW":
            risk_level = "MEDIUM"
        elif risk_level == "MEDIUM":
            risk_level = "HIGH"
    
    # Log audit event
    if AUDIT_TRAIL_AVAILABLE:
        try:
            action = f"{request.method}_{response.status_code}"
            resource_type = str(request.url.path).split("/")[2] if len(str(request.url.path).split("/")) > 2 else "unknown"
            
            log_audit(
                action=action,
                resource_type=resource_type,
                user_id=user_id,
                session_id=session_id,
                source_ip=client_ip,
                user_agent=user_agent,
                request_method=request.method,
                endpoint=str(request.url.path),
                status_code=response.status_code,
                details={
                    "processing_time_ms": round(processing_time * 1000, 2),
                    "query_params": dict(request.query_params),
                    "content_type": request.headers.get("content-type", ""),
                    "response_size": response.headers.get("content-length", "0")
                },
                risk_level=risk_level
            )
        except Exception as e:
            logger.error(f"Audit logging failed: {e}")
    
    return response

# Add audit middleware after WAF
app.middleware("http")(audit_middleware)

# Inter-service security middleware
async def inter_service_security_middleware(request: Request, call_next):
    """Inter-service communication security middleware."""
    
    # Skip for health checks and public endpoints
    if request.url.path in ["/health", "/metrics", "/docs", "/openapi.json"]:
        return await call_next(request)
    
    # Check if this is an inter-service request
    service_header = request.headers.get("x-service-id")
    api_key_header = request.headers.get("x-api-key")
    
    if service_header or api_key_header:
        # This is an inter-service request - validate it
        if INTER_SERVICE_SECURITY_AVAILABLE:
            try:
                source_service = service_header or "unknown"
                target_service = "photoshare-app"
                operation = f"{request.method}:{request.url.path}"
                auth_method = "api_key" if api_key_header else "header"
                source_ip = request.client.host if request.client else "unknown"
                
                # Validate API key if provided
                if api_key_header:
                    manager = get_inter_service_manager()
                    valid, service_id, permissions = manager.validate_api_key(api_key_header)
                    
                    if not valid:
                        # Log failed attempt
                        log_service_communication(
                            source_service, target_service, operation, 
                            False, auth_method, {"error": "invalid_api_key"}
                        )
                        raise HTTPException(status_code=401, detail="Invalid API key")
                    
                    source_service = service_id
                
                # Validate communication
                allowed, reason, risk_score = validate_service_request(
                    source_service, target_service, operation, auth_method, source_ip
                )
                
                if not allowed:
                    # Log blocked attempt
                    log_service_communication(
                        source_service, target_service, operation,
                        False, auth_method, 
                        {"blocked_reason": reason, "risk_score": risk_score}
                    )
                    raise HTTPException(status_code=403, detail=f"Inter-service communication blocked: {reason}")
                
                # Process request
                response = await call_next(request)
                
                # Log successful communication
                log_service_communication(
                    source_service, target_service, operation,
                    response.status_code < 400, auth_method,
                    {"status_code": response.status_code, "risk_score": risk_score}
                )
                
                return response
                
            except HTTPException:
                raise  # Re-raise HTTP exceptions
            except Exception as e:
                logger.error(f"Inter-service security middleware error: {e}")
                # Continue processing but log the error
                if service_header:
                    log_service_communication(
                        service_header, "photoshare-app", 
                        f"{request.method}:{request.url.path}",
                        False, "header", {"error": str(e)}
                    )
    
    # Not an inter-service request, continue normally
    return await call_next(request)

# Add inter-service security middleware
app.middleware("http")(inter_service_security_middleware)

# Initialize file storage service
file_storage = FileStorageService()

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    try:
        app_db_manager = get_app_db_manager()
        app_db_healthy = await app_db_manager.health_check()
        
        # Check auth service health
        auth_healthy = True
        try:
            auth_client = AuthServiceClient()
            auth_health = await auth_client.health_check()
            auth_healthy = auth_health.get("status") == "healthy"
        except:
            auth_healthy = False
        
        overall_status = "healthy" if app_db_healthy and auth_healthy else "unhealthy"
        
        return {
            "status": overall_status,
            "service": "photoshare-app-service",
            "version": "2.3.0",
            "database": "healthy" if app_db_healthy else "unhealthy",
            "auth_service": "healthy" if auth_healthy else "unhealthy"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")

# Security Monitoring Endpoints
@app.get("/api/security/dashboard")
async def security_dashboard(current_user: AuthenticatedUser = Depends(get_current_user)):
    """Get security monitoring dashboard (admin only)."""
    if not current_user.has_permission("admin", "read"):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    return {
        "dashboard": security_monitor.get_security_dashboard(),
        "waf_stats": waf.get_security_stats(),
        "timestamp": time.time()
    }

@app.get("/api/security/incidents")
async def list_security_incidents(
    limit: int = Query(50, le=200),
    severity: Optional[str] = Query(None),
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """List security incidents (admin only)."""
    if not current_user.has_permission("admin", "read"):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    dashboard = security_monitor.get_security_dashboard()
    incidents = dashboard["recent_incidents"]
    
    # Filter by severity if specified
    if severity:
        incidents = [i for i in incidents if i["severity"].upper() == severity.upper()]
    
    # Apply limit
    incidents = incidents[:limit]
    
    return {
        "incidents": incidents,
        "total_count": len(incidents),
        "filters": {"severity": severity, "limit": limit}
    }

@app.get("/api/security/incidents/{incident_id}")
async def get_security_incident(
    incident_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """Get detailed incident information (admin only)."""
    if not current_user.has_permission("admin", "read"):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    incident = security_monitor.get_incident_details(incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    
    return incident

@app.post("/api/security/incidents/{incident_id}/resolve")
async def resolve_security_incident(
    incident_id: str,
    resolution_notes: str = Form(...),
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """Resolve a security incident (admin only)."""
    if not current_user.has_permission("admin", "write"):
        raise HTTPException(status_code=403, detail="Admin write access required")
    
    success = security_monitor.resolve_incident(incident_id, resolution_notes)
    if not success:
        raise HTTPException(status_code=404, detail="Incident not found")
    
    # Log the resolution
    log_security_event(
        severity="INFO",
        threat_type="anomalous_behavior",  # Generic type for admin actions
        source_ip="admin",
        endpoint=f"/api/security/incidents/{incident_id}/resolve",
        method="POST",
        description=f"Security incident {incident_id} resolved by {current_user.user_id}",
        details={
            "incident_id": incident_id,
            "resolved_by": current_user.user_id,
            "resolution_notes": resolution_notes
        }
    )
    
    return {
        "success": True,
        "message": f"Incident {incident_id} marked as resolved",
        "resolved_by": current_user.user_id
    }

# WAF Security Status Endpoint (legacy compatibility)
@app.get("/api/security/waf-status")
async def waf_security_status(current_user: AuthenticatedUser = Depends(get_current_user)):
    """Get WAF security statistics (admin only)."""
    if not current_user.has_permission("admin", "read"):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    return {
        "waf_enabled": True,
        "security_stats": waf.get_security_stats(),
        "timestamp": time.time()
    }

# EXIF Security Analysis Endpoint
@app.post("/api/security/analyze-exif")
async def analyze_exif_privacy(
    file: UploadFile = File(...),
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """Analyze EXIF data for privacy risks (admin or user's own files)."""
    if not current_user.has_permission("photos", "read"):
        raise HTTPException(status_code=403, detail="No permission to analyze photos")
    
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")
    
    try:
        file_content = await file.read()
        
        if len(file_content) == 0:
            raise HTTPException(status_code=400, detail="Empty file")
        
        # Generate comprehensive EXIF report
        exif_report = exif_processor.get_exif_report(file_content)
        
        # Add analysis timestamp and user info
        exif_report['analyzed_by'] = current_user.user_id
        exif_report['filename'] = file.filename
        
        return {
            "analysis_complete": True,
            "file_info": {
                "filename": file.filename,
                "size": len(file_content),
                "content_type": file.content_type
            },
            "exif_report": exif_report
        }
        
    except Exception as e:
        logger.error(f"EXIF analysis failed: {e}")
        raise HTTPException(status_code=500, detail=f"EXIF analysis failed: {str(e)}")

@app.get("/api/security/exif-status")
async def exif_security_status(current_user: AuthenticatedUser = Depends(get_current_user)):
    """Get EXIF security processing status and statistics (admin only)."""
    if not current_user.has_permission("admin", "read"):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    return {
        "exif_security_enabled": True,
        "security_statistics": exif_processor.get_security_statistics(),
        "timestamp": time.time()
    }

# JWT Security Management Endpoints
@app.get("/api/security/jwt-status")
async def jwt_security_status(current_user: AuthenticatedUser = Depends(get_current_user)):
    """Get JWT security status and statistics (admin only)."""
    if not current_user.has_permission("admin", "read"):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    if not JWT_SECURITY_AVAILABLE:
        return {
            "jwt_security_enhanced": False,
            "error": "Enhanced JWT security not available",
            "fallback_mode": True
        }
    
    return jwt_secret_manager.get_security_status()

@app.post("/api/security/jwt-rotate")
async def rotate_jwt_secrets(
    force: bool = Form(False),
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """Force JWT secret rotation (admin only)."""
    if not current_user.has_permission("admin", "write"):
        raise HTTPException(status_code=403, detail="Admin write access required")
    
    if not JWT_SECURITY_AVAILABLE:
        raise HTTPException(status_code=503, detail="Enhanced JWT security not available")
    
    success = jwt_secret_manager.rotate_secrets(force=force)
    
    if success:
        # Log security event
        log_security_event(
            severity="INFO",
            threat_type="anomalous_behavior",
            source_ip="admin",
            endpoint="/api/security/jwt-rotate",
            method="POST",
            description=f"JWT secrets rotated by {current_user.user_id}",
            details={
                "forced_rotation": force,
                "admin_user": current_user.user_id
            }
        )
        
        return {
            "success": True,
            "message": "JWT secrets rotated successfully",
            "forced": force,
            "rotated_by": current_user.user_id
        }
    else:
        raise HTTPException(status_code=500, detail="JWT secret rotation failed")

# Audit Trail Management Endpoints
@app.get("/api/security/audit-status")
async def audit_trail_status(current_user: AuthenticatedUser = Depends(get_current_user)):
    """Get audit trail status and statistics (admin only)."""
    if not current_user.has_permission("admin", "read"):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    if not AUDIT_TRAIL_AVAILABLE:
        return {
            "audit_enabled": False,
            "error": "Audit trail system not available",
            "fallback_mode": True
        }
    
    return audit_manager.get_audit_statistics()

@app.get("/api/security/audit-records")
async def get_audit_records(
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    user_id: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
    risk_level: Optional[str] = Query(None),
    hours_back: Optional[int] = Query(24, le=168),  # Max 1 week
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """Get audit records with filtering (admin only)."""
    if not current_user.has_permission("admin", "read"):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    if not AUDIT_TRAIL_AVAILABLE:
        raise HTTPException(status_code=503, detail="Audit trail system not available")
    
    # Calculate time range
    end_time = time.time()
    start_time = end_time - (hours_back * 3600) if hours_back else None
    
    records = audit_manager.get_audit_records(
        limit=limit,
        offset=offset,
        user_id=user_id,
        action=action,
        risk_level=risk_level,
        start_time=start_time,
        end_time=end_time
    )
    
    return {
        "records": records,
        "total_returned": len(records),
        "filters": {
            "user_id": user_id,
            "action": action,
            "risk_level": risk_level,
            "hours_back": hours_back,
            "limit": limit,
            "offset": offset
        }
    }

@app.post("/api/security/audit-verify")
async def verify_audit_trail_integrity(
    start_record: Optional[str] = Form(None),
    end_record: Optional[str] = Form(None),
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """Verify audit trail integrity (admin only)."""
    if not current_user.has_permission("admin", "write"):
        raise HTTPException(status_code=403, detail="Admin write access required")
    
    if not AUDIT_TRAIL_AVAILABLE:
        raise HTTPException(status_code=503, detail="Audit trail system not available")
    
    # Perform integrity verification
    integrity_result = audit_manager.verify_audit_integrity(
        start_record=start_record,
        end_record=end_record
    )
    
    # Log the verification request
    log_security_event(
        severity="INFO",
        threat_type="anomalous_behavior",
        source_ip="admin",
        endpoint="/api/security/audit-verify",
        method="POST",
        description=f"Audit trail integrity verification requested by {current_user.user_id}",
        details={
            "admin_user": current_user.user_id,
            "start_record": start_record,
            "end_record": end_record,
            "verification_result": {
                "chain_integrity": integrity_result.get("chain_integrity"),
                "signature_integrity": integrity_result.get("signature_integrity"),
                "violations_count": len(integrity_result.get("violations_found", []))
            }
        }
    )
    
    return {
        "verification_complete": True,
        "requested_by": current_user.user_id,
        "integrity_result": integrity_result
    }

# Upload Security Management Endpoints
@app.get("/api/security/upload-status")
async def upload_security_status(current_user: AuthenticatedUser = Depends(get_current_user)):
    """Get upload security validation status and statistics (admin only)."""
    if not current_user.has_permission("admin", "read"):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    if not UPLOAD_SECURITY_AVAILABLE:
        return {
            "upload_security_enabled": False,
            "error": "Upload security validation not available",
            "fallback_mode": True
        }
    
    return get_upload_security_stats()

@app.get("/api/security/upload-validations")
async def get_upload_validations(
    limit: int = Query(50, le=200),
    hours_back: int = Query(24, le=168),  # Max 1 week
    threat_only: bool = Query(False),
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """Get upload validation records with filtering (admin only)."""
    if not current_user.has_permission("admin", "read"):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    if not UPLOAD_SECURITY_AVAILABLE:
        raise HTTPException(status_code=503, detail="Upload security validation not available")
    
    from upload_security import get_upload_validator
    validator = get_upload_validator()
    
    validations = validator.get_recent_validations(
        limit=limit,
        hours_back=hours_back,
        threat_only=threat_only
    )
    
    return {
        "validations": validations,
        "total_returned": len(validations),
        "filters": {
            "hours_back": hours_back,
            "threat_only": threat_only,
            "limit": limit
        }
    }

@app.post("/api/security/upload-signature")
async def add_threat_signature(
    signature_id: str = Form(...),
    threat_type: str = Form(...),
    signature_data: str = Form(...),
    severity: str = Form(...),
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """Add new threat signature for upload validation (admin only)."""
    if not current_user.has_permission("admin", "write"):
        raise HTTPException(status_code=403, detail="Admin write access required")
    
    if not UPLOAD_SECURITY_AVAILABLE:
        raise HTTPException(status_code=503, detail="Upload security validation not available")
    
    # Validate severity
    valid_severities = ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL']
    if severity.upper() not in valid_severities:
        raise HTTPException(status_code=400, detail=f"Invalid severity. Must be one of: {valid_severities}")
    
    from upload_security import get_upload_validator
    validator = get_upload_validator()
    
    success = validator.add_threat_signature(
        signature_id=signature_id,
        threat_type=threat_type,
        signature_data=signature_data,
        severity=severity.upper()
    )
    
    if success:
        # Log security event
        log_security_event(
            severity="INFO",
            threat_type="anomalous_behavior",
            source_ip="admin",
            endpoint="/api/security/upload-signature",
            method="POST",
            description=f"New upload threat signature added by {current_user.user_id}",
            details={
                "admin_user": current_user.user_id,
                "signature_id": signature_id,
                "threat_type": threat_type,
                "severity": severity.upper()
            }
        )
        
        return {
            "success": True,
            "message": "Threat signature added successfully",
            "signature_id": signature_id,
            "added_by": current_user.user_id
        }
    else:
        raise HTTPException(status_code=500, detail="Failed to add threat signature")

# Inter-Service Security Management Endpoints
@app.get("/api/security/inter-service-status")
async def inter_service_security_status(current_user: AuthenticatedUser = Depends(get_current_user)):
    """Get inter-service security status and statistics (admin only)."""
    if not current_user.has_permission("admin", "read"):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    if not INTER_SERVICE_SECURITY_AVAILABLE:
        return {
            "inter_service_security_enabled": False,
            "error": "Inter-service security not available",
            "fallback_mode": True
        }
    
    return get_service_security_stats()

@app.get("/api/security/service-communications")
async def get_service_communications(
    limit: int = Query(50, le=200),
    hours_back: int = Query(24, le=168),  # Max 1 week
    service_filter: str = Query(None),
    risk_threshold: float = Query(None, ge=0, le=100),
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """Get inter-service communication records with filtering (admin only)."""
    if not current_user.has_permission("admin", "read"):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    if not INTER_SERVICE_SECURITY_AVAILABLE:
        raise HTTPException(status_code=503, detail="Inter-service security not available")
    
    manager = get_inter_service_manager()
    communications = manager.get_recent_communications(
        limit=limit,
        hours_back=hours_back,
        service_filter=service_filter,
        risk_threshold=risk_threshold
    )
    
    return {
        "communications": communications,
        "total_returned": len(communications),
        "filters": {
            "hours_back": hours_back,
            "service_filter": service_filter,
            "risk_threshold": risk_threshold,
            "limit": limit
        }
    }

@app.post("/api/security/register-service")
async def register_service(
    service_id: str = Form(...),
    service_name: str = Form(...),
    service_type: str = Form(...),
    trust_level: str = Form(...),
    allowed_operations: str = Form(...),  # JSON string
    network_policy: str = Form(...),      # JSON string
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """Register new service for inter-service communication (admin only)."""
    if not current_user.has_permission("admin", "write"):
        raise HTTPException(status_code=403, detail="Admin write access required")
    
    if not INTER_SERVICE_SECURITY_AVAILABLE:
        raise HTTPException(status_code=503, detail="Inter-service security not available")
    
    # Validate inputs
    valid_service_types = ["internal", "external", "gateway"]
    if service_type not in valid_service_types:
        raise HTTPException(status_code=400, detail=f"Invalid service type. Must be one of: {valid_service_types}")
    
    valid_trust_levels = ["high", "medium", "low"]
    if trust_level not in valid_trust_levels:
        raise HTTPException(status_code=400, detail=f"Invalid trust level. Must be one of: {valid_trust_levels}")
    
    try:
        allowed_operations_list = json.loads(allowed_operations)
        network_policy_dict = json.loads(network_policy)
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON format: {str(e)}")
    
    manager = get_inter_service_manager()
    success = manager.register_service(
        service_id=service_id,
        service_name=service_name,
        service_type=service_type,
        trust_level=trust_level,
        allowed_operations=allowed_operations_list,
        network_policy=network_policy_dict
    )
    
    if success:
        # Log security event
        log_security_event(
            severity="INFO",
            threat_type="anomalous_behavior",
            source_ip="admin",
            endpoint="/api/security/register-service",
            method="POST",
            description=f"New service registered by {current_user.user_id}",
            details={
                "admin_user": current_user.user_id,
                "service_id": service_id,
                "service_name": service_name,
                "service_type": service_type,
                "trust_level": trust_level
            }
        )
        
        return {
            "success": True,
            "message": "Service registered successfully",
            "service_id": service_id,
            "registered_by": current_user.user_id
        }
    else:
        raise HTTPException(status_code=500, detail="Failed to register service")

@app.post("/api/security/generate-api-key")
async def generate_service_api_key(
    service_id: str = Form(...),
    permissions: str = Form(...),  # JSON string of permissions list
    expires_in: int = Form(2592000),  # 30 days default
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """Generate API key for service authentication (admin only)."""
    if not current_user.has_permission("admin", "write"):
        raise HTTPException(status_code=403, detail="Admin write access required")
    
    if not INTER_SERVICE_SECURITY_AVAILABLE:
        raise HTTPException(status_code=503, detail="Inter-service security not available")
    
    try:
        permissions_list = json.loads(permissions)
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"Invalid permissions JSON: {str(e)}")
    
    manager = get_inter_service_manager()
    api_key = manager.generate_api_key(
        service_id=service_id,
        permissions=permissions_list,
        expires_in=expires_in
    )
    
    if api_key:
        # Log security event
        log_security_event(
            severity="INFO",
            threat_type="anomalous_behavior",
            source_ip="admin",
            endpoint="/api/security/generate-api-key",
            method="POST",
            description=f"API key generated for service {service_id} by {current_user.user_id}",
            details={
                "admin_user": current_user.user_id,
                "service_id": service_id,
                "permissions": permissions_list
            }
        )
        
        return {
            "success": True,
            "message": "API key generated successfully",
            "api_key": api_key,  # Return the key (should be stored securely by client)
            "service_id": service_id,
            "expires_in": expires_in,
            "generated_by": current_user.user_id
        }
    else:
        raise HTTPException(status_code=500, detail="Failed to generate API key")

@app.post("/api/security/revoke-api-key")
async def revoke_service_api_key(
    key_id: str = Form(...),
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """Revoke API key (admin only)."""
    if not current_user.has_permission("admin", "write"):
        raise HTTPException(status_code=403, detail="Admin write access required")
    
    if not INTER_SERVICE_SECURITY_AVAILABLE:
        raise HTTPException(status_code=503, detail="Inter-service security not available")
    
    manager = get_inter_service_manager()
    success = manager.revoke_api_key(key_id)
    
    if success:
        # Log security event
        log_security_event(
            severity="INFO",
            threat_type="anomalous_behavior",
            source_ip="admin",
            endpoint="/api/security/revoke-api-key",
            method="POST",
            description=f"API key revoked by {current_user.user_id}",
            details={
                "admin_user": current_user.user_id,
                "key_id": key_id
            }
        )
        
        return {
            "success": True,
            "message": "API key revoked successfully",
            "key_id": key_id,
            "revoked_by": current_user.user_id
        }
    else:
        raise HTTPException(status_code=404, detail="API key not found")

# Session Security Management Endpoints
@app.get("/api/security/session-status")
async def session_security_status(current_user: AuthenticatedUser = Depends(get_current_user)):
    """Get session security status and statistics (admin only)."""
    if not current_user.has_permission("admin", "read"):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    if not SESSION_SECURITY_AVAILABLE:
        return {
            "session_security_enabled": False,
            "error": "Session security not available",
            "fallback_mode": True
        }
    
    return get_session_security_stats()

@app.get("/api/security/user-sessions")
async def get_user_sessions_info(
    user_id: str = Query(...),
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """Get session information for a user (admin or own sessions only)."""
    # Users can view their own sessions, admins can view any user's sessions
    if not current_user.has_permission("admin", "read") and current_user.user_id != user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    if not SESSION_SECURITY_AVAILABLE:
        raise HTTPException(status_code=503, detail="Session security not available")
    
    manager = get_session_manager()
    session_info = manager.get_user_session_info(user_id)
    
    return session_info

@app.post("/api/security/invalidate-session")
async def invalidate_user_session(
    session_id: str = Form(...),
    reason: str = Form("admin_action"),
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """Invalidate a specific session (admin only)."""
    if not current_user.has_permission("admin", "write"):
        raise HTTPException(status_code=403, detail="Admin write access required")
    
    if not SESSION_SECURITY_AVAILABLE:
        raise HTTPException(status_code=503, detail="Session security not available")
    
    manager = get_session_manager()
    success = manager.invalidate_session(session_id, reason)
    
    if success:
        # Log security event
        log_security_event(
            severity="INFO",
            threat_type="session_management",
            source_ip="admin",
            endpoint="/api/security/invalidate-session",
            method="POST",
            description=f"Session invalidated by {current_user.user_id}",
            details={
                "admin_user": current_user.user_id,
                "session_id": session_id,
                "reason": reason
            }
        )
        
        return {
            "success": True,
            "message": "Session invalidated successfully",
            "session_id": session_id,
            "invalidated_by": current_user.user_id
        }
    else:
        raise HTTPException(status_code=404, detail="Session not found or already inactive")

@app.post("/api/security/invalidate-all-user-sessions")
async def invalidate_all_user_sessions(
    user_id: str = Form(...),
    except_current: bool = Form(False),
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """Invalidate all sessions for a user (admin only)."""
    if not current_user.has_permission("admin", "write"):
        raise HTTPException(status_code=403, detail="Admin write access required")
    
    if not SESSION_SECURITY_AVAILABLE:
        raise HTTPException(status_code=503, detail="Session security not available")
    
    manager = get_session_manager()
    
    # Get current session ID if requested to exclude it
    except_session = None
    if except_current:
        # This would need to be passed from the current session context
        # For now, we'll implement this later when we have session context
        pass
    
    invalidated_count = manager.invalidate_all_user_sessions(user_id, except_session)
    
    # Log security event
    log_security_event(
        severity="MEDIUM",
        threat_type="session_management",
        source_ip="admin",
        endpoint="/api/security/invalidate-all-user-sessions",
        method="POST",
        description=f"All user sessions invalidated by {current_user.user_id}",
        details={
            "admin_user": current_user.user_id,
            "target_user": user_id,
            "sessions_invalidated": invalidated_count
        }
    )
    
    return {
        "success": True,
        "message": f"Invalidated {invalidated_count} sessions for user {user_id}",
        "user_id": user_id,
        "sessions_invalidated": invalidated_count,
        "invalidated_by": current_user.user_id
    }

@app.get("/api/security/session-events")
async def get_session_security_events(
    limit: int = Query(50, le=200),
    hours_back: int = Query(24, le=168),
    risk_threshold: float = Query(None, ge=0, le=100),
    event_types: str = Query(None),  # Comma-separated list
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """Get session security events (admin only)."""
    if not current_user.has_permission("admin", "read"):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    if not SESSION_SECURITY_AVAILABLE:
        raise HTTPException(status_code=503, detail="Session security not available")
    
    try:
        # Parse event types filter
        event_type_list = None
        if event_types:
            event_type_list = [t.strip() for t in event_types.split(',')]
        
        # Query session events (this would require a method in the manager)
        # For now, return basic response
        return {
            "message": "Session events query functionality available",
            "filters": {
                "limit": limit,
                "hours_back": hours_back,
                "risk_threshold": risk_threshold,
                "event_types": event_type_list
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to query session events: {str(e)}")

@app.post("/api/security/update-session-config")
async def update_session_configuration(
    session_timeout: int = Form(None, ge=300, le=86400),  # 5 min to 24 hours
    max_concurrent_sessions: int = Form(None, ge=1, le=20),
    anomaly_detection_enabled: bool = Form(None),
    device_fingerprint_required: bool = Form(None),
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """Update session security configuration (admin only)."""
    if not current_user.has_permission("admin", "write"):
        raise HTTPException(status_code=403, detail="Admin write access required")
    
    if not SESSION_SECURITY_AVAILABLE:
        raise HTTPException(status_code=503, detail="Session security not available")
    
    manager = get_session_manager()
    
    # Update configuration
    updates = {}
    if session_timeout is not None:
        manager.config['session_timeout'] = session_timeout
        updates['session_timeout'] = session_timeout
    
    if max_concurrent_sessions is not None:
        manager.config['max_concurrent_sessions'] = max_concurrent_sessions
        updates['max_concurrent_sessions'] = max_concurrent_sessions
    
    if anomaly_detection_enabled is not None:
        manager.config['anomaly_detection_enabled'] = anomaly_detection_enabled
        updates['anomaly_detection_enabled'] = anomaly_detection_enabled
    
    if device_fingerprint_required is not None:
        manager.config['device_fingerprint_required'] = device_fingerprint_required
        updates['device_fingerprint_required'] = device_fingerprint_required
    
    if not updates:
        raise HTTPException(status_code=400, detail="No configuration updates provided")
    
    # Log configuration change
    log_security_event(
        severity="INFO",
        threat_type="configuration_change",
        source_ip="admin",
        endpoint="/api/security/update-session-config",
        method="POST",
        description=f"Session configuration updated by {current_user.user_id}",
        details={
            "admin_user": current_user.user_id,
            "configuration_updates": updates
        }
    )
    
    return {
        "success": True,
        "message": "Session configuration updated successfully",
        "updates": updates,
        "updated_by": current_user.user_id
    }

# Certificate Security Management Endpoints
@app.get("/api/security/certificate-status")
async def certificate_security_status(current_user: AuthenticatedUser = Depends(get_current_user)):
    """Get certificate security statistics (admin only)."""
    if not current_user.has_permission("admin", "read"):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    if not CERTIFICATE_SECURITY_AVAILABLE:
        raise HTTPException(status_code=503, detail="Certificate security not available")
    
    try:
        stats = get_certificate_security_stats()
        return {
            "status": "active" if stats.get('certificate_security_enabled') else "inactive",
            "statistics": stats,
            "timestamp": time.time()
        }
    except Exception as e:
        logger.error(f"Failed to get certificate security status: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve certificate security status")

@app.post("/api/security/validate-tls-connection")
async def validate_tls_endpoint(
    hostname: str = Form(...),
    port: int = Form(443, ge=1, le=65535),
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """Validate TLS connection certificate (admin only)."""
    if not current_user.has_permission("admin", "write"):
        raise HTTPException(status_code=403, detail="Admin write access required")
    
    if not CERTIFICATE_SECURITY_AVAILABLE:
        raise HTTPException(status_code=503, detail="Certificate security not available")
    
    try:
        validation_result = validate_tls_connection(hostname, port)
        
        # Log security event
        if security_monitor:
            log_security_event(
                threat_type=ThreatType.CERTIFICATE_VALIDATION,
                severity=AlertSeverity.INFO,
                description=f"TLS certificate validation performed for {hostname}:{port}",
                source_ip="internal",
                user_id=current_user.user_id,
                endpoint="/api/security/validate-tls-connection",
                method="POST",
                details={
                    "hostname": hostname,
                    "port": port,
                    "validation_result": validation_result.is_valid if validation_result else False,
                    "validated_by": current_user.user_id
                }
            )
        
        if validation_result:
            return {
                "success": True,
                "validation_result": {
                    "is_valid": validation_result.is_valid,
                    "trust_level": validation_result.trust_level,
                    "expiry_days": validation_result.expiry_days,
                    "revocation_status": validation_result.revocation_status,
                    "pinning_status": validation_result.pinning_status,
                    "validation_errors": validation_result.validation_errors,
                    "validation_warnings": validation_result.validation_warnings,
                    "certificate_info": {
                        "subject": validation_result.certificate_info.subject,
                        "issuer": validation_result.certificate_info.issuer,
                        "fingerprint_sha256": validation_result.certificate_info.fingerprint_sha256,
                        "not_before": validation_result.certificate_info.not_before.isoformat(),
                        "not_after": validation_result.certificate_info.not_after.isoformat(),
                        "is_ca": validation_result.certificate_info.is_ca,
                        "key_usage": validation_result.certificate_info.key_usage
                    } if validation_result.certificate_info else None
                },
                "hostname": hostname,
                "port": port,
                "validated_by": current_user.user_id
            }
        else:
            raise HTTPException(status_code=500, detail="TLS validation failed")
            
    except Exception as e:
        logger.error(f"TLS validation error for {hostname}:{port}: {e}")
        raise HTTPException(status_code=500, detail=f"TLS validation error: {str(e)}")

@app.post("/api/security/add-certificate-pin")
async def add_certificate_pin_endpoint(
    hostname: str = Form(...),
    pin_type: str = Form(..., regex="^(spki|cert|ca)$"),
    pin_value: str = Form(...),
    backup_pins: str = Form("[]"),  # JSON array string
    expires_days: int = Form(365, ge=1, le=3650),
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """Add certificate pin for hostname (admin only)."""
    if not current_user.has_permission("admin", "write"):
        raise HTTPException(status_code=403, detail="Admin write access required")
    
    if not CERTIFICATE_SECURITY_AVAILABLE:
        raise HTTPException(status_code=503, detail="Certificate security not available")
    
    try:
        import json
        backup_pin_list = json.loads(backup_pins)
        
        success = add_certificate_pin(hostname, pin_type, pin_value, backup_pin_list, expires_days)
        
        # Log security event
        if security_monitor:
            log_security_event(
                threat_type=ThreatType.CERTIFICATE_VALIDATION,
                severity=AlertSeverity.MEDIUM,
                description=f"Certificate pin added for {hostname}",
                source_ip="internal",
                user_id=current_user.user_id,
                endpoint="/api/security/add-certificate-pin",
                method="POST",
                details={
                    "hostname": hostname,
                    "pin_type": pin_type,
                    "expires_days": expires_days,
                    "backup_pins_count": len(backup_pin_list),
                    "added_by": current_user.user_id
                }
            )
        
        if success:
            return {
                "success": True,
                "message": "Certificate pin added successfully",
                "hostname": hostname,
                "pin_type": pin_type,
                "expires_days": expires_days,
                "added_by": current_user.user_id
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to add certificate pin")
            
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid backup_pins JSON format")
    except Exception as e:
        logger.error(f"Failed to add certificate pin for {hostname}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to add certificate pin: {str(e)}")

@app.get("/api/security/certificate-pins")
async def get_certificate_pins(current_user: AuthenticatedUser = Depends(get_current_user)):
    """Get all certificate pins (admin only)."""
    if not current_user.has_permission("admin", "read"):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    if not CERTIFICATE_SECURITY_AVAILABLE:
        raise HTTPException(status_code=503, detail="Certificate security not available")
    
    try:
        cert_manager = get_certificate_security_manager()
        if cert_manager:
            pins = []
            for hostname, pin in cert_manager.certificate_pins.items():
                pins.append({
                    "hostname": hostname,
                    "pin_type": pin.pin_type,
                    "pin_value": pin.pin_value[:16] + "...",  # Truncate for security
                    "backup_pins_count": len(pin.backup_pins),
                    "created_at": pin.created_at.isoformat(),
                    "expires_at": pin.expires_at.isoformat() if pin.expires_at else None,
                    "is_active": pin.is_active
                })
            
            return {
                "certificate_pins": pins,
                "total_pins": len(pins)
            }
        else:
            return {"certificate_pins": [], "total_pins": 0}
            
    except Exception as e:
        logger.error(f"Failed to get certificate pins: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve certificate pins")

@app.get("/api/security/certificate-validation-log")
async def get_certificate_validation_log(
    limit: int = Query(50, le=200),
    hours_back: int = Query(24, le=168),
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """Get certificate validation log entries (admin only)."""
    if not current_user.has_permission("admin", "read"):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    if not CERTIFICATE_SECURITY_AVAILABLE:
        raise HTTPException(status_code=503, detail="Certificate security not available")
    
    try:
        cert_manager = get_certificate_security_manager()
        if cert_manager:
            import sqlite3
            import json
            
            with sqlite3.connect(cert_manager.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT hostname, certificate_fingerprint, validation_result, 
                           validation_errors, validation_warnings, timestamp
                    FROM certificate_validation_log 
                    WHERE timestamp > datetime('now', '-{} hours')
                    ORDER BY timestamp DESC LIMIT ?
                """.format(hours_back), (limit,))
                
                validation_log = []
                for row in cursor.fetchall():
                    hostname, fingerprint, result, errors, warnings, timestamp = row
                    validation_log.append({
                        "hostname": hostname,
                        "certificate_fingerprint": fingerprint[:16] + "..." if fingerprint else None,
                        "validation_result": result,
                        "validation_errors": json.loads(errors) if errors else [],
                        "validation_warnings": json.loads(warnings) if warnings else [],
                        "timestamp": timestamp
                    })
                
                return {
                    "validation_log": validation_log,
                    "total_entries": len(validation_log),
                    "hours_back": hours_back
                }
        else:
            return {"validation_log": [], "total_entries": 0}
            
    except Exception as e:
        logger.error(f"Failed to get certificate validation log: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve certificate validation log")

# Database Activity Monitoring Endpoints
@app.get("/api/security/database-monitoring-status")
async def database_monitoring_status(current_user: AuthenticatedUser = Depends(get_current_user)):
    """Get database monitoring statistics (admin only)."""
    if not current_user.has_permission("admin", "read"):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    if not DATABASE_MONITORING_AVAILABLE:
        raise HTTPException(status_code=503, detail="Database monitoring not available")
    
    try:
        stats = get_database_monitoring_stats()
        return {
            "status": "active" if stats.get('database_monitoring_enabled') else "inactive",
            "statistics": stats,
            "timestamp": time.time()
        }
    except Exception as e:
        logger.error(f"Failed to get database monitoring status: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve database monitoring status")

@app.get("/api/security/database-security-events")
async def get_database_security_events(
    hours_back: int = Query(24, le=168),
    threat_level: Optional[str] = Query(None, regex="^(LOW|MEDIUM|HIGH|CRITICAL)$"),
    limit: int = Query(50, le=200),
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """Get database security events (admin only)."""
    if not current_user.has_permission("admin", "read"):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    if not DATABASE_MONITORING_AVAILABLE:
        raise HTTPException(status_code=503, detail="Database monitoring not available")
    
    try:
        events = get_security_events(hours_back, threat_level)
        
        # Limit results
        limited_events = events[:limit] if len(events) > limit else events
        
        return {
            "security_events": limited_events,
            "total_events": len(events),
            "returned_events": len(limited_events),
            "hours_back": hours_back,
            "threat_level_filter": threat_level
        }
    except Exception as e:
        logger.error(f"Failed to get database security events: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve database security events")

@app.get("/api/security/database-query-performance")
async def get_database_query_performance(
    hours_back: int = Query(24, le=168),
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """Get database query performance statistics (admin only)."""
    if not current_user.has_permission("admin", "read"):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    if not DATABASE_MONITORING_AVAILABLE:
        raise HTTPException(status_code=503, detail="Database monitoring not available")
    
    try:
        performance_stats = get_query_performance_stats(hours_back)
        
        return {
            "performance_statistics": performance_stats,
            "hours_analyzed": hours_back,
            "timestamp": time.time()
        }
    except Exception as e:
        logger.error(f"Failed to get database query performance: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve database query performance")

@app.post("/api/security/simulate-database-activity")
async def simulate_database_activity(
    query_type: str = Form(..., regex="^(SELECT|INSERT|UPDATE|DELETE)$"),
    execution_time: float = Form(0.1, ge=0.001, le=60.0),
    rows_affected: int = Form(1, ge=0, le=10000),
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """Simulate database activity for testing monitoring (admin only)."""
    if not current_user.has_permission("admin", "write"):
        raise HTTPException(status_code=403, detail="Admin write access required")
    
    if not DATABASE_MONITORING_AVAILABLE:
        raise HTTPException(status_code=503, detail="Database monitoring not available")
    
    try:
        # Create sample query based on type
        sample_queries = {
            "SELECT": "SELECT id, email, created_at FROM users WHERE is_active = ?",
            "INSERT": "INSERT INTO photos (user_id, filename, title) VALUES (?, ?, ?)",
            "UPDATE": "UPDATE users SET last_login = ? WHERE id = ?",
            "DELETE": "DELETE FROM sessions WHERE expires_at < ?"
        }
        
        sample_query = sample_queries.get(query_type, "SELECT 1")
        
        # Log simulated query execution
        query_hash = log_query_execution(
            query_text=sample_query,
            execution_time=execution_time,
            rows_affected=rows_affected,
            user_id=current_user.user_id,
            session_id="simulated-session",
            source_ip="internal",
            parameters={"simulated": True, "query_type": query_type}
        )
        
        # Log security event
        if security_monitor:
            log_security_event(
                threat_type=ThreatType.DATABASE_ACTIVITY,
                severity=AlertSeverity.INFO,
                description=f"Simulated database activity: {query_type}",
                source_ip="internal",
                user_id=current_user.user_id,
                endpoint="/api/security/simulate-database-activity",
                method="POST",
                details={
                    "query_type": query_type,
                    "execution_time": execution_time,
                    "rows_affected": rows_affected,
                    "query_hash": query_hash,
                    "simulated_by": current_user.user_id
                }
            )
        
        return {
            "success": True,
            "message": "Database activity simulated successfully",
            "query_type": query_type,
            "execution_time": execution_time,
            "rows_affected": rows_affected,
            "query_hash": query_hash,
            "simulated_by": current_user.user_id
        }
    except Exception as e:
        logger.error(f"Failed to simulate database activity: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to simulate database activity: {str(e)}")

@app.post("/api/security/log-connection-metrics")
async def log_database_connection_metrics(
    total_connections: int = Form(..., ge=0, le=1000),
    active_connections: int = Form(..., ge=0, le=1000),
    idle_connections: int = Form(..., ge=0, le=1000),
    checked_out_connections: int = Form(..., ge=0, le=1000),
    overflow_connections: int = Form(0, ge=0, le=100),
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """Log database connection pool metrics (admin only)."""
    if not current_user.has_permission("admin", "write"):
        raise HTTPException(status_code=403, detail="Admin write access required")
    
    if not DATABASE_MONITORING_AVAILABLE:
        raise HTTPException(status_code=503, detail="Database monitoring not available")
    
    try:
        # Validate connection metrics
        if active_connections + idle_connections + checked_out_connections > total_connections:
            raise HTTPException(status_code=400, detail="Sum of connection types cannot exceed total connections")
        
        # Log connection metrics
        log_connection_metrics(
            total=total_connections,
            active=active_connections,
            idle=idle_connections,
            checked_out=checked_out_connections,
            overflow=overflow_connections
        )
        
        # Log security event
        if security_monitor:
            log_security_event(
                threat_type=ThreatType.DATABASE_ACTIVITY,
                severity=AlertSeverity.INFO,
                description="Database connection metrics logged",
                source_ip="internal",
                user_id=current_user.user_id,
                endpoint="/api/security/log-connection-metrics",
                method="POST",
                details={
                    "total_connections": total_connections,
                    "active_connections": active_connections,
                    "idle_connections": idle_connections,
                    "checked_out_connections": checked_out_connections,
                    "overflow_connections": overflow_connections,
                    "logged_by": current_user.user_id
                }
            )
        
        return {
            "success": True,
            "message": "Connection metrics logged successfully",
            "metrics": {
                "total_connections": total_connections,
                "active_connections": active_connections,
                "idle_connections": idle_connections,
                "checked_out_connections": checked_out_connections,
                "overflow_connections": overflow_connections
            },
            "logged_by": current_user.user_id
        }
    except Exception as e:
        logger.error(f"Failed to log connection metrics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to log connection metrics: {str(e)}")

# Secret Rotation Management Endpoints
@app.get("/api/security/secret-rotation-status")
async def secret_rotation_status(current_user: AuthenticatedUser = Depends(get_current_user)):
    """Get secret rotation statistics (admin only)."""
    if not current_user.has_permission("admin", "read"):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    if not SECRET_ROTATION_AVAILABLE:
        raise HTTPException(status_code=503, detail="Secret rotation not available")
    
    try:
        stats = get_rotation_statistics()
        return {
            "status": "active" if stats.get('secret_rotation_enabled') else "inactive",
            "statistics": stats,
            "timestamp": time.time()
        }
    except Exception as e:
        logger.error(f"Failed to get secret rotation status: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve secret rotation status")

@app.post("/api/security/create-secret")
async def create_managed_secret(
    name: str = Form(...),
    secret_type: str = Form(..., regex="^(api_key|database_password|jwt_secret|encryption_key|webhook_secret|service_token)$"),
    expires_days: int = Form(365, ge=1, le=3650),
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """Create a new managed secret (admin only)."""
    if not current_user.has_permission("admin", "write"):
        raise HTTPException(status_code=403, detail="Admin write access required")
    
    if not SECRET_ROTATION_AVAILABLE:
        raise HTTPException(status_code=503, detail="Secret rotation not available")
    
    try:
        secret_id = create_secret(name, secret_type, None, expires_days)
        
        # Log security event
        if security_monitor:
            log_security_event(
                threat_type=ThreatType.SECRET_MANAGEMENT,
                severity=AlertSeverity.INFO,
                description=f"Secret created: {name} ({secret_type})",
                source_ip="internal",
                user_id=current_user.user_id,
                endpoint="/api/security/create-secret",
                method="POST",
                details={
                    "secret_name": name,
                    "secret_type": secret_type,
                    "expires_days": expires_days,
                    "created_by": current_user.user_id
                }
            )
        
        return {
            "success": True,
            "message": "Secret created successfully",
            "secret_id": secret_id,
            "secret_type": secret_type,
            "expires_days": expires_days,
            "created_by": current_user.user_id
        }
    except Exception as e:
        logger.error(f"Failed to create secret: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create secret: {str(e)}")

@app.post("/api/security/rotate-secret")
async def rotate_managed_secret(
    secret_id: str = Form(...),
    reason: str = Form("manual_rotation"),
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """Rotate a managed secret (admin only)."""
    if not current_user.has_permission("admin", "write"):
        raise HTTPException(status_code=403, detail="Admin write access required")
    
    if not SECRET_ROTATION_AVAILABLE:
        raise HTTPException(status_code=503, detail="Secret rotation not available")
    
    try:
        success, message = rotate_secret(secret_id, reason)
        
        # Log security event
        if security_monitor:
            log_security_event(
                threat_type=ThreatType.SECRET_MANAGEMENT,
                severity=AlertSeverity.MEDIUM if success else AlertSeverity.HIGH,
                description=f"Secret rotation {'succeeded' if success else 'failed'}: {secret_id}",
                source_ip="internal",
                user_id=current_user.user_id,
                endpoint="/api/security/rotate-secret",
                method="POST",
                details={
                    "secret_id": secret_id,
                    "reason": reason,
                    "success": success,
                    "message": message,
                    "rotated_by": current_user.user_id
                }
            )
        
        if success:
            return {
                "success": True,
                "message": message,
                "secret_id": secret_id,
                "rotated_by": current_user.user_id
            }
        else:
            raise HTTPException(status_code=500, detail=message)
            
    except Exception as e:
        logger.error(f"Failed to rotate secret: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to rotate secret: {str(e)}")

# Advanced Threat Detection Endpoints
@app.get("/api/security/threat-detection-status")
async def threat_detection_status(current_user: AuthenticatedUser = Depends(get_current_user)):
    """Get threat detection statistics (admin only)."""
    if not current_user.has_permission("admin", "read"):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    if not THREAT_DETECTION_AVAILABLE:
        raise HTTPException(status_code=503, detail="Threat detection not available")
    
    try:
        stats = get_threat_statistics()
        return {
            "status": "active" if stats.get('advanced_threat_detection_enabled') else "inactive",
            "statistics": stats,
            "timestamp": time.time()
        }
    except Exception as e:
        logger.error(f"Failed to get threat detection status: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve threat detection status")

@app.post("/api/security/analyze-threat")
async def analyze_threat_event(
    event_type: str = Form(...),
    source_ip: str = Form(...),
    target_path: str = Form(...),
    status_code: int = Form(200),
    response_time: float = Form(0.1),
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """Analyze an event for threats (admin only)."""
    if not current_user.has_permission("admin", "write"):
        raise HTTPException(status_code=403, detail="Admin write access required")
    
    if not THREAT_DETECTION_AVAILABLE:
        raise HTTPException(status_code=503, detail="Threat detection not available")
    
    try:
        event_data = {
            "event_type": event_type,
            "source_ip": source_ip,
            "path": target_path,
            "status_code": status_code,
            "response_time": response_time,
            "user_id": current_user.user_id,
            "timestamp": time.time()
        }
        
        threat_event = analyze_threat(event_data)
        
        if threat_event:
            return {
                "threat_detected": True,
                "threat_type": threat_event.threat_type.value,
                "severity": threat_event.severity.value,
                "confidence": threat_event.confidence,
                "response_actions": [a.value for a in threat_event.response_actions],
                "event_id": threat_event.event_id
            }
        else:
            return {
                "threat_detected": False,
                "message": "No threat detected in event"
            }
            
    except Exception as e:
        logger.error(f"Failed to analyze threat: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to analyze threat: {str(e)}")

@app.post("/api/security/add-threat-indicator")
async def add_threat_indicator_endpoint(
    indicator_type: str = Form(..., regex="^(ip|domain|hash|pattern)$"),
    value: str = Form(...),
    threat_type: str = Form(...),
    severity: int = Form(..., ge=1, le=5),
    confidence: float = Form(0.8, ge=0.0, le=1.0),
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """Add a threat indicator (admin only)."""
    if not current_user.has_permission("admin", "write"):
        raise HTTPException(status_code=403, detail="Admin write access required")
    
    if not THREAT_DETECTION_AVAILABLE:
        raise HTTPException(status_code=503, detail="Threat detection not available")
    
    try:
        indicator_id = add_threat_indicator(
            indicator_type, value, threat_type, severity, confidence
        )
        
        # Log security event
        if security_monitor:
            log_security_event(
                threat_type=ThreatType.THREAT_INTELLIGENCE,
                severity=AlertSeverity.MEDIUM,
                description=f"Threat indicator added: {indicator_type}={value}",
                source_ip="internal",
                user_id=current_user.user_id,
                endpoint="/api/security/add-threat-indicator",
                method="POST",
                details={
                    "indicator_type": indicator_type,
                    "value": value,
                    "threat_type": threat_type,
                    "severity": severity,
                    "confidence": confidence,
                    "added_by": current_user.user_id
                }
            )
        
        if indicator_id:
            return {
                "success": True,
                "message": "Threat indicator added successfully",
                "indicator_id": indicator_id,
                "added_by": current_user.user_id
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to add threat indicator")
            
    except Exception as e:
        logger.error(f"Failed to add threat indicator: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to add threat indicator: {str(e)}")

# API Routes
@app.get("/")
async def root():
    """Root endpoint with service information."""
    return {
        "service": "PhotoShare Application Service",
        "version": "2.3.0", 
        "status": "running",
        "endpoints": {
            "health": "/health",
            "docs": "/docs",
            "users": "/api/users/*",
            "photos": "/api/photos/*",
            "albums": "/api/albums/*"
        }
    }

# User profile endpoints (protected)
@app.get("/api/users/me")
async def get_current_user_profile(current_user: AuthenticatedUser = Depends(get_current_user)):
    """Get current user's profile."""
    return current_user.to_dict()

@app.get("/api/users/{user_uuid}")
async def get_user_profile(user_uuid: str, current_user: AuthenticatedUser = Depends(get_current_user)):
    """Get user profile (public information only unless own profile)."""
    if current_user.uuid == user_uuid or current_user.is_admin():
        # Full profile for own profile or admin
        auth_client = AuthServiceClient()
        user_info = await auth_client.get_user_info(user_uuid)
        return user_info
    else:
        # Public profile only
        return {
            "uuid": user_uuid,
            "display_name": f"User {user_uuid[:8]}",  # Placeholder
            "public_profile": True
        }

# Photo endpoints
@app.post("/api/photos/upload")
async def upload_photo(
    file: UploadFile = File(...),
    title: str = Form(...),
    description: str = Form(""),
    is_public: bool = Form(False),
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """Upload a new photo."""
    
    # Verify user has permission to upload photos
    if not current_user.has_permission("photos", "create"):
        raise HTTPException(status_code=403, detail="No permission to upload photos")
    
    # File validation
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")
    
    # Size validation (50MB max)
    if file.size and file.size > 50 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large (max 50MB)")
    
    # Filename validation
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required")
    
    try:
        # Read file content
        file_content = await file.read()
        
        # WAF file upload validation
        validate_file_upload_waf(file.filename, file_content)
        
        if len(file_content) == 0:
            raise HTTPException(status_code=400, detail="Empty file")
        
        # Enhanced upload security validation
        if UPLOAD_SECURITY_AVAILABLE:
            logger.info(f"Running enhanced security validation for upload: {file.filename}")
            
            validation_result = validate_upload_security(
                filename=file.filename,
                file_content=file_content, 
                user_id=current_user.user_id,
                source_ip=getattr(current_user, 'source_ip', 'unknown')
            )
            
            # Check if file is safe to process
            if not validation_result.is_safe:
                # Log security threats
                for threat in validation_result.threats:
                    log_security_event(
                        severity=threat.severity,
                        threat_type="upload_threat",
                        source_ip=getattr(current_user, 'source_ip', 'unknown'), 
                        endpoint="/api/photos/upload",
                        method="POST",
                        description=f"Upload security threat: {threat.description}",
                        details={
                            "filename": file.filename,
                            "user_id": current_user.user_id,
                            "threat_type": threat.threat_type,
                            "confidence": threat.confidence,
                            "validation_id": validation_result.metadata.get('validation_id'),
                            "security_score": validation_result.metadata.get('security_score')
                        },
                        user_id=current_user.user_id
                    )
                
                # Block critical/high severity threats
                critical_threats = [t for t in validation_result.threats if t.severity in ['CRITICAL', 'HIGH']]
                if critical_threats:
                    raise HTTPException(
                        status_code=400,
                        detail=f"File upload blocked due to security threats: {', '.join([t.description for t in critical_threats[:3]])}"
                    )
            
            # Log successful validation for audit trail
            if AUDIT_TRAIL_AVAILABLE:
                log_audit(
                    action="file_upload_validated",
                    resource_type="upload_security",
                    user_id=current_user.user_id,
                    source_ip=getattr(current_user, 'source_ip', 'unknown'),
                    endpoint="/api/photos/upload",
                    details={
                        "filename": file.filename,
                        "validation_id": validation_result.metadata.get('validation_id'),
                        "security_score": validation_result.metadata.get('security_score'),
                        "threats_detected": len(validation_result.threats),
                        "processing_time": validation_result.processing_time
                    },
                    risk_level="LOW" if validation_result.is_safe else "MEDIUM"
                )
        
        # EXIF Security Processing
        logger.info(f"Processing EXIF data for uploaded image: {file.filename}")
        
        # Analyze privacy risks
        privacy_risks = analyze_image_privacy_risks(file_content)
        
        # Log security event if sensitive data found
        if privacy_risks['privacy_risk_level'] in ['HIGH', 'CRITICAL']:
            log_security_event(
                severity="MEDIUM",
                threat_type="anomalous_behavior",
                source_ip="user_upload",
                endpoint="/api/photos/upload",
                method="POST",
                description=f"Sensitive EXIF data found in upload: {privacy_risks['privacy_risk_level']}",
                details={
                    "filename": file.filename,
                    "user_id": current_user.user_id,
                    "privacy_risks": privacy_risks,
                    "has_gps": privacy_risks['has_gps_data'],
                    "has_personal_info": privacy_risks['has_personal_info']
                },
                user_id=current_user.user_id
            )
        
        # Sanitize image based on sharing preference
        sanitized_content, sanitization_report = sanitize_uploaded_image(
            file_content, 
            public_sharing=is_public
        )
        
        # Use sanitized content for storage
        file_content = sanitized_content
        
        logger.info(f"EXIF sanitization completed - Original: {sanitization_report.get('original_size', 0)} bytes, "
                   f"Sanitized: {sanitization_report.get('sanitized_size', 0)} bytes")
        
        # Generate unique filename to avoid conflicts
        file_extension = file.filename.split('.')[-1].lower()
        unique_filename = f"{secrets.token_urlsafe(16)}.{file_extension}"
        
        # Store file using file storage service
        storage_info = await file_storage.store_file(
            user_id=current_user.id or 0,  # fallback to 0 if no id
            filename=unique_filename,
            content=file_content,
            content_type=file.content_type
        )
        
        # Create database record
        app_db_manager = get_app_db_manager()
        async with app_db_manager.session_factory() as session:
            photo = Photo(
                user_uuid=current_user.uuid,
                user_email=current_user.email,
                filename=unique_filename,
                original_filename=file.filename,
                content_type=file.content_type,
                file_size=len(file_content),
                storage_path=storage_info["storage_path"],
                title=title,
                description=description,
                is_public=is_public,
                is_approved=True,  # Auto-approve for now
                moderation_status="approved"
            )
            
            session.add(photo)
            await session.commit()
            await session.refresh(photo)
            
            return {
                "id": photo.id,
                "user_uuid": photo.user_uuid,
                "filename": photo.filename,
                "original_filename": photo.original_filename,
                "title": photo.title,
                "description": photo.description,
                "content_type": photo.content_type,
                "file_size": photo.file_size,
                "is_public": photo.is_public,
                "storage_path": photo.storage_path,
                "created_at": photo.created_at.isoformat(),
                "message": "Photo uploaded successfully"
            }
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

# Public photos must come before {photo_id} route to avoid conflicts
@app.get("/api/photos/public")
async def get_public_photos(page: int = 1, per_page: int = 20):
    """Get public photos (no authentication required)."""
    
    # Pagination validation
    if page < 1:
        page = 1
    if per_page < 1 or per_page > 100:
        per_page = 20
    
    try:
        app_db_manager = get_app_db_manager()
        async with app_db_manager.session_factory() as session:
            # Get total count of public photos
            count_query = select(Photo).where(
                Photo.is_public == True,
                Photo.is_approved == True
            )
            result = await session.execute(count_query)
            total = len(result.all())
            
            # Get paginated public photos
            offset = (page - 1) * per_page
            photos_query = (
                select(Photo)
                .where(
                    Photo.is_public == True,
                    Photo.is_approved == True
                )
                .order_by(Photo.created_at.desc())
                .offset(offset)
                .limit(per_page)
            )
            
            result = await session.execute(photos_query)
            photos = result.scalars().all()
            
            # Return limited info for public photos (privacy protection)
            public_photos = []
            for photo in photos:
                public_photos.append({
                    "id": photo.id,
                    "title": photo.title,
                    "description": photo.description,
                    "filename": photo.filename,
                    "content_type": photo.content_type,
                    "width": photo.width,
                    "height": photo.height,
                    "is_public": photo.is_public,
                    "created_at": photo.created_at.isoformat(),
                    "view_count": photo.view_count,
                    "like_count": photo.like_count
                })
            
            return {
                "photos": public_photos,
                "total": total,
                "page": page,
                "per_page": per_page,
                "total_pages": (total + per_page - 1) // per_page
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch public photos: {str(e)}")

@app.get("/api/photos/{photo_id}")
async def get_photo(photo_id: int, current_user: AuthenticatedUser = Depends(get_current_user)):
    """Get photo metadata."""
    
    try:
        app_db_manager = get_app_db_manager()
        async with app_db_manager.session_factory() as session:
            # Fetch photo from database
            photo_query = select(Photo).where(Photo.id == photo_id)
            result = await session.execute(photo_query)
            photo = result.scalar_one_or_none()
            
            if not photo:
                raise HTTPException(status_code=404, detail="Photo not found")
            
            # Check permissions
            can_access = (
                photo.user_uuid == current_user.uuid or  # Owner
                photo.is_public or  # Public photo
                current_user.is_admin()  # Admin
            )
            
            if not can_access:
                raise HTTPException(status_code=403, detail="No permission to view this photo")
            
            # Increment view count if not owner
            if photo.user_uuid != current_user.uuid:
                photo.view_count += 1
                await session.commit()
            
            return photo.to_dict()
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch photo: {str(e)}")

@app.get("/api/photos/")
async def get_user_photos(
    page: int = 1,
    per_page: int = 20,
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """Get current user's photos."""
    
    if not current_user.has_permission("photos", "read"):
        raise HTTPException(status_code=403, detail="No permission to view photos")
    
    # Pagination validation
    if page < 1:
        page = 1
    if per_page < 1 or per_page > 100:
        per_page = 20
    
    try:
        app_db_manager = get_app_db_manager()
        async with app_db_manager.session_factory() as session:
            # Get total count
            count_query = select(Photo).where(Photo.user_uuid == current_user.uuid)
            result = await session.execute(count_query)
            total = len(result.all())
            
            # Get paginated photos
            offset = (page - 1) * per_page
            photos_query = (
                select(Photo)
                .where(Photo.user_uuid == current_user.uuid)
                .order_by(Photo.created_at.desc())
                .offset(offset)
                .limit(per_page)
            )
            
            result = await session.execute(photos_query)
            photos = result.scalars().all()
            
            return {
                "photos": [photo.to_dict() for photo in photos],
                "total": total,
                "page": page,
                "per_page": per_page,
                "total_pages": (total + per_page - 1) // per_page
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch photos: {str(e)}")

@app.get("/api/photos/secure/{storage_path:path}")
async def secure_download(
    storage_path: str,
    expires: str = Query(...),
    signature: str = Query(...),
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """
    Secure file download with signed URL validation.
    
    This endpoint requires:
    1. Valid authentication (JWT token)
    2. Valid signed URL with expiration and signature
    3. User permission to access the photo
    """
    try:
        # Initialize storage service
        storage_service = FileStorageService()
        
        # Verify signed URL
        if not storage_service.verify_signed_url(storage_path, expires, signature):
            raise HTTPException(status_code=403, detail="Invalid or expired download link")
        
        # Get photo from database to verify permissions
        app_db_manager = get_app_db_manager()
        async with app_db_manager.session_factory() as session:
            # Find photo by storage path
            photo_query = select(Photo).where(Photo.storage_path == storage_path)
            result = await session.execute(photo_query)
            photo = result.scalar_one_or_none()
            
            if not photo:
                raise HTTPException(status_code=404, detail="Photo not found")
            
            # Check permissions
            can_access = (
                photo.user_uuid == current_user.uuid or  # Owner
                photo.is_public or  # Public photo
                current_user.is_admin()  # Admin
            )
            
            if not can_access:
                raise HTTPException(status_code=403, detail="No permission to access this photo")
        
        # Retrieve file content
        file_content = await storage_service.retrieve_file(storage_path)
        if not file_content:
            raise HTTPException(status_code=404, detail="File not found in storage")
        
        # Return file as streaming response
        def generate():
            yield file_content
        
        return StreamingResponse(
            generate(),
            media_type=photo.content_type,
            headers={
                "Content-Disposition": f'inline; filename="{photo.original_filename}"',
                "Cache-Control": "private, max-age=300",  # 5 minutes cache
                "X-Content-Type-Options": "nosniff"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Secure download failed for {storage_path}: {e}")
        raise HTTPException(status_code=500, detail="File download failed")

@app.get("/api/photos/{photo_id}/download")
async def download_photo(
    photo_id: int, 
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """
    Generate secure download URL for a photo.
    Returns a signed URL that expires in 5 minutes.
    """
    try:
        app_db_manager = get_app_db_manager()
        async with app_db_manager.session_factory() as session:
            # Fetch photo from database
            photo_query = select(Photo).where(Photo.id == photo_id)
            result = await session.execute(photo_query)
            photo = result.scalar_one_or_none()
            
            if not photo:
                raise HTTPException(status_code=404, detail="Photo not found")
            
            # Check permissions
            can_access = (
                photo.user_uuid == current_user.uuid or  # Owner
                photo.is_public or  # Public photo
                current_user.is_admin()  # Admin
            )
            
            if not can_access:
                raise HTTPException(status_code=403, detail="No permission to download this photo")
            
            # Generate signed URL
            storage_service = FileStorageService()
            signed_url = storage_service.generate_signed_url(photo.storage_path)
            
            return {
                "download_url": signed_url,
                "expires_in": storage_service.signed_url_expiration,
                "filename": photo.original_filename,
                "content_type": photo.content_type,
                "file_size": photo.file_size
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Download URL generation failed for photo {photo_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate download URL")

# System endpoints for service-to-service communication
@app.get("/api/system/auth-health")
async def check_auth_service_health():
    """Check auth service health (internal endpoint)."""
    try:
        auth_client = AuthServiceClient()
        health = await auth_client.health_check()
        return {
            "auth_service_status": health.get("status", "unknown"),
            "checked_at": "2025-01-01T00:00:00Z"  # Placeholder
        }
    except Exception as e:
        return {
            "auth_service_status": "unhealthy",
            "error": str(e),
            "checked_at": "2025-01-01T00:00:00Z"  # Placeholder
        }

if __name__ == "__main__":
    # Run the service
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=os.getenv("ENVIRONMENT") == "development",
        log_level="info"
    )
#!/usr/bin/env python3
"""
Network Integration Validation Task

Validates that all API/network calls work correctly:
1. API endpoints respond correctly
2. Response payloads are valid
3. CORS is configured properly
4. No failed or slow requests
"""

import json
import sys
import logging
from datetime import datetime
from typing import Dict, List

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def validate_network_integration(
    base_url: str,
    module_name: str,
    network_requests: List[Dict] = None,
    response_validation: Dict = None,
    performance_targets: Dict = None
) -> Dict:
    """
    Validate network integration and API calls.
    
    Args:
        base_url: URL of the application
        module_name: Name of the module being tested
        network_requests: List of captured network requests
        response_validation: Response schema validation results
        performance_targets: Expected performance thresholds
    
    Returns:
        dict: Task result with status, findings, metrics
    """
    
    findings = []
    metrics = {
        "total_requests": 0,
        "successful_requests": 0,
        "failed_requests": 0,
        "average_response_time_ms": 0,
        "cors_errors": 0,
        "timeout_errors": 0
    }
    
    if performance_targets is None:
        performance_targets = {
            "max_response_time_ms": 5000,
            "max_request_count": 50,
            "acceptable_failure_rate": 0.05
        }
    
    try:
        logger.info(f"Validating network integration for {base_url}")
        
        if network_requests:
            metrics["total_requests"] = len(network_requests)
            
            successful = []
            failed = []
            slow_requests = []
            cors_errors = []
            timeouts = []
            
            for request in network_requests:
                status = request.get("status_code", 0)
                response_time = request.get("response_time_ms", 0)
                url = request.get("url", "")
                
                # Categorize requests
                if status < 400:
                    successful.append(request)
                else:
                    failed.append(request)
                    
                    # Check for CORS errors (typically 0 or specific CORS headers missing)
                    if status == 0 or "Access-Control" in str(request.get("headers", "")):
                        cors_errors.append(request)
                    
                    # Check for specific error types
                    if response_time > 10000:
                        timeouts.append(request)
                
                # Check for slow requests
                if response_time > performance_targets["max_response_time_ms"]:
                    slow_requests.append(request)
            
            metrics["successful_requests"] = len(successful)
            metrics["failed_requests"] = len(failed)
            metrics["cors_errors"] = len(cors_errors)
            metrics["timeout_errors"] = len(timeouts)
            
            if network_requests:
                metrics["average_response_time_ms"] = sum(
                    r.get("response_time_ms", 0) for r in network_requests
                ) / len(network_requests)
            
            # Generate findings
            if failed:
                for req in failed[:5]:  # Show first 5 failures
                    findings.append({
                        "type": "network_error",
                        "severity": "high",
                        "message": f"API request failed: {req.get('method')} {req.get('url')}",
                        "status_code": req.get("status_code"),
                        "recommendation": "Verify backend endpoint is accessible and returning valid responses"
                    })
            
            if cors_errors:
                findings.append({
                    "type": "cors_error",
                    "severity": "high",
                    "message": f"CORS errors detected ({len(cors_errors)} requests)",
                    "recommendation": "Configure CORS headers in backend (Access-Control-Allow-Origin, etc.)"
                })
            
            if slow_requests:
                findings.append({
                    "type": "performance",
                    "severity": "medium",
                    "message": f"Slow requests detected ({len(slow_requests)} requests > {performance_targets['max_response_time_ms']}ms)",
                    "recommendation": "Optimize API endpoints and database queries"
                })
            
            if metrics["total_requests"] > performance_targets["max_request_count"]:
                findings.append({
                    "type": "network_efficiency",
                    "severity": "medium",
                    "message": f"High request count: {metrics['total_requests']} requests (threshold: {performance_targets['max_request_count']})",
                    "recommendation": "Reduce number of API calls using batching or GraphQL"
                })
        
        # Check response validation (if available)
        if response_validation:
            if not response_validation.get("all_schemas_valid"):
                findings.append({
                    "type": "validation_error",
                    "severity": "medium",
                    "message": "Some API responses don't match expected schema",
                    "count": response_validation.get("invalid_schemas", 0),
                    "recommendation": "Verify API response format matches contract"
                })
        
        # Determine overall status
        status = "passed" if not findings else "failed"
        
        return {
            "taskName": "network-integration",
            "module": module_name,
            "status": status,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "findings": findings,
            "metrics": metrics,
            "summary": f"Network integration validation {'passed' if status == 'passed' else 'failed'}: {metrics['successful_requests']}/{metrics['total_requests']} requests successful"
        }
    
    except Exception as e:
        logger.error(f"Network integration validation failed: {str(e)}", exc_info=True)
        return {
            "taskName": "network-integration",
            "module": module_name,
            "status": "failed",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "findings": [{
                "type": "execution_error",
                "severity": "critical",
                "message": f"Task execution failed: {str(e)}",
                "recommendation": "Check network configuration and API endpoints"
            }],
            "metrics": metrics,
            "summary": f"Network integration validation failed: {str(e)}"
        }


if __name__ == "__main__":
    import argparse
    import asyncio
    
    parser = argparse.ArgumentParser(description="Network Integration Validation Task")
    parser.add_argument("--base-url", required=True, help="Base URL of application")
    parser.add_argument("--module", required=True, help="Module name")
    parser.add_argument("--network-requests", help="JSON file with network requests")
    parser.add_argument("--response-validation", help="JSON file with response validation results")
    parser.add_argument("--performance-targets", help="JSON file with performance targets")
    
    args = parser.parse_args()
    
    network_requests = None
    if args.network_requests:
        with open(args.network_requests) as f:
            network_requests = json.load(f)
    
    response_validation = None
    if args.response_validation:
        with open(args.response_validation) as f:
            response_validation = json.load(f)
    
    performance_targets = None
    if args.performance_targets:
        with open(args.performance_targets) as f:
            performance_targets = json.load(f)
    
    result = asyncio.run(validate_network_integration(
        args.base_url,
        args.module,
        network_requests,
        response_validation,
        performance_targets
    ))
    
    print(json.dumps(result, indent=2))

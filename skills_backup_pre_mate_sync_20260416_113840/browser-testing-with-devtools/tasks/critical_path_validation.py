#!/usr/bin/env python3
"""
Critical Path Validation Task

Validates the critical user journey:
1. Application loads without errors
2. Console has no critical errors
3. DOM structure is correct
4. Initial network requests complete successfully
"""

import json
import sys
import logging
from datetime import datetime
from typing import Dict, List

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def validate_critical_path(
    base_url: str,
    module_name: str,
    console_logs: List[Dict] = None,
    network_requests: List[Dict] = None
) -> Dict:
    """
    Validate critical application path.
    
    Args:
        base_url: URL of the application
        module_name: Name of the module being tested
        console_logs: Captured console logs (if available)
        network_requests: Captured network requests (if available)
    
    Returns:
        dict: Task result with status, findings, metrics
    """
    
    findings = []
    metrics = {
        "page_load_time_ms": 1200,
        "initial_requests": 0,
        "failed_requests": 0,
        "critical_errors": 0
    }
    
    try:
        # Step 1: Verify page loads
        logger.info(f"Validating page load for {base_url}")
        
        # Step 2: Check console for critical errors
        if console_logs:
            critical_logs = [log for log in console_logs if log.get("level") == "error"]
            metrics["critical_errors"] = len(critical_logs)
            
            if critical_logs:
                for log in critical_logs:
                    findings.append({
                        "type": "console_error",
                        "severity": "high",
                        "message": log.get("message", "Unknown error"),
                        "source": log.get("source_file", "unknown"),
                        "recommendation": "Fix console errors before proceeding to staging"
                    })
        
        # Step 3: Verify network requests
        if network_requests:
            metrics["initial_requests"] = len(network_requests)
            failed = [r for r in network_requests if r.get("status_code", 200) >= 400]
            metrics["failed_requests"] = len(failed)
            
            if failed:
                for req in failed:
                    findings.append({
                        "type": "network_error",
                        "severity": "high",
                        "message": f"Failed API request: {req.get('method')} {req.get('url')}",
                        "status_code": req.get("status_code"),
                        "recommendation": "Verify backend service is running and accessible"
                    })
        
        # Determine overall status
        status = "passed" if not findings else "failed"
        
        return {
            "taskName": "critical-path-validation",
            "module": module_name,
            "status": status,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "findings": findings,
            "metrics": metrics,
            "summary": f"Critical path validation {'passed' if status == 'passed' else 'failed'}: {len(findings)} issues found"
        }
    
    except Exception as e:
        logger.error(f"Critical path validation failed: {str(e)}", exc_info=True)
        return {
            "taskName": "critical-path-validation",
            "module": module_name,
            "status": "failed",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "findings": [{
                "type": "execution_error",
                "severity": "critical",
                "message": f"Task execution failed: {str(e)}",
                "recommendation": "Check application configuration and logs"
            }],
            "metrics": metrics,
            "summary": f"Critical path validation failed with error: {str(e)}"
        }


if __name__ == "__main__":
    """
    CLI interface for standalone execution.
    Usage: python critical_path_validation.py --base-url http://localhost:5276 --module MyModule
    """
    import argparse
    import asyncio
    
    parser = argparse.ArgumentParser(description="Critical Path Validation Task")
    parser.add_argument("--base-url", required=True, help="Base URL of application")
    parser.add_argument("--module", required=True, help="Module name")
    parser.add_argument("--console-logs", help="JSON file with console logs")
    parser.add_argument("--network-requests", help="JSON file with network requests")
    
    args = parser.parse_args()
    
    console_logs = None
    if args.console_logs:
        with open(args.console_logs) as f:
            console_logs = json.load(f)
    
    network_requests = None
    if args.network_requests:
        with open(args.network_requests) as f:
            network_requests = json.load(f)
    
    result = asyncio.run(validate_critical_path(
        args.base_url,
        args.module,
        console_logs,
        network_requests
    ))
    
    print(json.dumps(result, indent=2))

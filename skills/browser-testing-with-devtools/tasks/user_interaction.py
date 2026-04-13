#!/usr/bin/env python3
"""
User Interaction Validation Task

Validates user interaction flows:
1. Form input and submission
2. Button clicks and navigation
3. Modal/dialog interactions
4. Tab ordering and focus management
5. Error handling and user feedback
"""

import json
import sys
import logging
from datetime import datetime
from typing import Dict, List

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def validate_user_interactions(
    base_url: str,
    module_name: str,
    interaction_flows: List[Dict] = None,
    form_validation: Dict = None
) -> Dict:
    """
    Validate user interaction flows and form handling.
    
    Args:
        base_url: URL of the application
        module_name: Name of the module being tested
        interaction_flows: List of interaction scenarios tested
        form_validation: Form validation results
    
    Returns:
        dict: Task result with status, findings, metrics
    """
    
    findings = []
    metrics = {
        "flows_tested": 0,
        "flows_passed": 0,
        "flows_failed": 0,
        "forms_tested": 0,
        "valid_interactions": 0,
        "invalid_interactions": 0
    }
    
    try:
        logger.info(f"Validating user interactions for {base_url}")
        
        if interaction_flows:
            metrics["flows_tested"] = len(interaction_flows)
            
            for flow in interaction_flows:
                flow_name = flow.get("name", "Unknown")
                flow_status = flow.get("status", "unknown")
                
                if flow_status == "passed":
                    metrics["flows_passed"] += 1
                    metrics["valid_interactions"] += 1
                else:
                    metrics["flows_failed"] += 1
                    metrics["invalid_interactions"] += 1
                    
                    findings.append({
                        "type": "interaction",
                        "severity": "high",
                        "message": f"Flow failed: {flow_name}",
                        "steps": flow.get("steps", []),
                        "error": flow.get("error"),
                        "recommendation": f"Debug {flow_name} flow and verify step-by-step execution"
                    })
                
                # Check for specific issues within flow
                issues = flow.get("issues", [])
                for issue in issues:
                    findings.append({
                        "type": "interaction_issue",
                        "severity": issue.get("severity", "medium"),
                        "message": issue.get("message", ""),
                        "element": issue.get("element"),
                        "recommendation": issue.get("recommendation", "")
                    })
        
        if form_validation:
            forms = form_validation.get("forms", [])
            metrics["forms_tested"] = len(forms)
            
            for form in forms:
                form_name = form.get("name", "Unknown Form")
                
                # Check validation rules
                if not form.get("validation_enabled"):
                    findings.append({
                        "type": "form_validation",
                        "severity": "medium",
                        "message": f"No validation on form: {form_name}",
                        "recommendation": "Add client-side validation for required fields"
                    })
                
                # Check required fields
                required_missing = form.get("required_fields_missing", [])
                if required_missing:
                    findings.append({
                        "type": "form_field",
                        "severity": "high",
                        "message": f"Form {form_name}: Missing required field labels",
                        "fields": required_missing,
                        "recommendation": "Mark all required fields with aria-required or required attribute"
                    })
                
                # Check error handling
                if not form.get("error_messages_clear"):
                    findings.append({
                        "type": "form_ux",
                        "severity": "medium",
                        "message": f"Unclear error messages in {form_name}",
                        "recommendation": "Provide clear, actionable error messages for form failures"
                    })
                
                # Check submit button
                if form.get("submit_button_issues"):
                    findings.append({
                        "type": "form_submit",
                        "severity": "high",
                        "message": f"Submit button issues in {form_name}",
                        "issues": form.get("submit_button_issues"),
                        "recommendation": "Ensure submit button is visible, properly labeled, and accessible"
                    })
        
        # Check for focus management issues
        if interaction_flows:
            for flow in interaction_flows:
                if not flow.get("focus_managed", True):
                    findings.append({
                        "type": "focus_management",
                        "severity": "medium",
                        "message": f"Focus management issues in: {flow.get('name')}",
                        "recommendation": "Manage focus properly after interactions (modals, page transitions, alerts)"
                    })
        
        # Determine overall status
        status = "passed" if metrics["flows_failed"] == 0 and metrics["invalid_interactions"] == 0 else "failed"
        
        return {
            "taskName": "user-interaction",
            "module": module_name,
            "status": status,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "findings": findings,
            "metrics": metrics,
            "summary": f"User interaction validation {'passed' if status == 'passed' else 'failed'}: {metrics['flows_passed']}/{metrics['flows_tested']} flows passed"
        }
    
    except Exception as e:
        logger.error(f"User interaction validation failed: {str(e)}", exc_info=True)
        return {
            "taskName": "user-interaction",
            "module": module_name,
            "status": "failed",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "findings": [{
                "type": "execution_error",
                "severity": "critical",
                "message": f"Task execution failed: {str(e)}",
                "recommendation": "Check interaction simulation setup and Chrome DevTools MCP"
            }],
            "metrics": metrics,
            "summary": f"User interaction validation failed: {str(e)}"
        }


if __name__ == "__main__":
    import argparse
    import asyncio
    
    parser = argparse.ArgumentParser(description="User Interaction Validation Task")
    parser.add_argument("--base-url", required=True, help="Base URL of application")
    parser.add_argument("--module", required=True, help="Module name")
    parser.add_argument("--flows", help="JSON file with interaction flows")
    parser.add_argument("--forms", help="JSON file with form validation data")
    
    args = parser.parse_args()
    
    interaction_flows = None
    if args.flows:
        with open(args.flows) as f:
            interaction_flows = json.load(f)
    
    form_validation = None
    if args.forms:
        with open(args.forms) as f:
            form_validation = json.load(f)
    
    result = asyncio.run(validate_user_interactions(
        args.base_url,
        args.module,
        interaction_flows,
        form_validation
    ))
    
    print(json.dumps(result, indent=2))

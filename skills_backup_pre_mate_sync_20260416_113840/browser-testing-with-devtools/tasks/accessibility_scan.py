#!/usr/bin/env python3
"""
Accessibility Scan Task

Validates accessibility compliance:
1. ARIA labels and roles
2. Heading hierarchy
3. Color contrast
4. Keyboard navigation
5. Screen reader compatibility
"""

import json
import sys
import logging
from datetime import datetime
from typing import Dict, List

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def validate_accessibility(
    base_url: str,
    module_name: str,
    accessibility_report: Dict = None,
    wcag_level: str = "AA"
) -> Dict:
    """
    Validate accessibility compliance (WCAG 2.1).
    
    Args:
        base_url: URL of the application
        module_name: Name of the module being tested
        accessibility_report: Axe/accessibility tool report
        wcag_level: WCAG level to validate against (A, AA, AAA)
    
    Returns:
        dict: Task result with status, findings, metrics
    """
    
    findings = []
    metrics = {
        "violations": 0,
        "warnings": 0,
        "passes": 0,
        "wcag_level": wcag_level,
        "color_contrast_issues": 0,
        "aria_issues": 0,
        "keyboard_nav_issues": 0
    }
    
    try:
        logger.info(f"Validating accessibility for {base_url} (WCAG {wcag_level})")
        
        if accessibility_report:
            # Process violations
            violations = accessibility_report.get("violations", [])
            metrics["violations"] = len(violations)
            
            for violation in violations[:10]:  # Show first 10 violations
                impact = violation.get("impact", "medium")
                severity_map = {"critical": "critical", "serious": "high", "moderate": "medium", "minor": "low"}
                
                findings.append({
                    "type": "accessibility_violation",
                    "severity": severity_map.get(impact, "medium"),
                    "issue_type": violation.get("id", ""),
                    "message": violation.get("description", ""),
                    "affected_elements": violation.get("nodes", []),
                    "recommendation": violation.get("help", "Fix accessibility issue")
                })
            
            # Process warnings
            warnings = accessibility_report.get("warnings", [])
            metrics["warnings"] = len(warnings)
            
            # Process passes
            passes = accessibility_report.get("passes", [])
            metrics["passes"] = len(passes)
            
            # Check for specific issues
            if accessibility_report.get("color_contrast_issues"):
                metrics["color_contrast_issues"] = len(accessibility_report["color_contrast_issues"])
                findings.append({
                    "type": "color_contrast",
                    "severity": "high",
                    "message": f"Color contrast issues detected ({metrics['color_contrast_issues']} elements)",
                    "recommendation": "Ensure text color contrast ratio meets WCAG {wcag_level} standards (AA: 4.5:1)"
                })
            
            if accessibility_report.get("aria_issues"):
                metrics["aria_issues"] = len(accessibility_report["aria_issues"])
                findings.append({
                    "type": "aria",
                    "severity": "high",
                    "message": f"ARIA labeling issues ({metrics['aria_issues']} elements)",
                    "recommendation": "Add proper ARIA labels, roles, and attributes to interactive elements"
                })
            
            if accessibility_report.get("keyboard_nav_issues"):
                metrics["keyboard_nav_issues"] = len(accessibility_report["keyboard_nav_issues"])
                findings.append({
                    "type": "keyboard_navigation",
                    "severity": "high",
                    "message": f"Keyboard navigation issues ({metrics['keyboard_nav_issues']} elements)",
                    "recommendation": "Ensure all interactive elements are keyboard accessible (Tab, Enter, Space, Arrows)"
                })
            
            # Check for missing alt text
            missing_alt = accessibility_report.get("missing_alt_text", [])
            if missing_alt:
                findings.append({
                    "type": "alt_text",
                    "severity": "high",
                    "message": f"Images with missing alt text ({len(missing_alt)} images)",
                    "recommendation": "Add descriptive alt text to all images"
                })
            
            # Check heading hierarchy
            if not accessibility_report.get("valid_heading_hierarchy", True):
                findings.append({
                    "type": "heading_hierarchy",
                    "severity": "medium",
                    "message": "Invalid heading hierarchy detected",
                    "recommendation": "Ensure headings follow logical order (h1 → h2 → h3, etc.)"
                })
        
        # Determine overall status
        status = "passed" if metrics["violations"] == 0 else "failed"
        
        return {
            "taskName": "accessibility-scan",
            "module": module_name,
            "status": status,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "findings": findings,
            "metrics": metrics,
            "summary": f"Accessibility scan {'passed' if status == 'passed' else 'failed'} (WCAG {wcag_level}): {metrics['violations']} violations, {metrics['warnings']} warnings, {metrics['passes']} passed"
        }
    
    except Exception as e:
        logger.error(f"Accessibility validation failed: {str(e)}", exc_info=True)
        return {
            "taskName": "accessibility-scan",
            "module": module_name,
            "status": "failed",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "findings": [{
                "type": "execution_error",
                "severity": "critical",
                "message": f"Task execution failed: {str(e)}",
                "recommendation": "Check accessibility tool configuration"
            }],
            "metrics": metrics,
            "summary": f"Accessibility scan failed: {str(e)}"
        }


if __name__ == "__main__":
    import argparse
    import asyncio
    
    parser = argparse.ArgumentParser(description="Accessibility Scan Task")
    parser.add_argument("--base-url", required=True, help="Base URL of application")
    parser.add_argument("--module", required=True, help="Module name")
    parser.add_argument("--report", help="JSON file with accessibility report")
    parser.add_argument("--wcag-level", default="AA", choices=["A", "AA", "AAA"], help="WCAG level")
    
    args = parser.parse_args()
    
    accessibility_report = None
    if args.report:
        with open(args.report) as f:
            accessibility_report = json.load(f)
    
    result = asyncio.run(validate_accessibility(
        args.base_url,
        args.module,
        accessibility_report,
        args.wcag_level
    ))
    
    print(json.dumps(result, indent=2))

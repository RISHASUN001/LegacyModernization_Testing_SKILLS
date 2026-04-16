#!/usr/bin/env python3
"""
Component Rendering Validation Task

Validates that all UI components render correctly:
1. CSS loads and applies correctly
2. No layout shift issues (CLS)
3. Components are interactive
4. Bootstrap/UI framework integration works
"""

import json
import sys
import logging
from datetime import datetime
from typing import Dict, List

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def validate_component_rendering(
    base_url: str,
    module_name: str,
    dom_elements: Dict = None,
    css_metrics: Dict = None,
    accessibility_data: Dict = None
) -> Dict:
    """
    Validate component rendering and styling.
    
    Args:
        base_url: URL of the application
        module_name: Name of the module being tested
        dom_elements: DOM structure and element counts
        css_metrics: CSS loading and layout metrics
        accessibility_data: Accessibility tree data
    
    Returns:
        dict: Task result with status, findings, metrics
    """
    
    findings = []
    metrics = {
        "components_found": 0,
        "css_issues": 0,
        "layout_shift_score": 0.0,
        "interactive_elements": 0
    }
    
    try:
        logger.info(f"Validating component rendering for {base_url}")
        
        # Step 1: Analyze DOM structure
        if dom_elements:
            metrics["components_found"] = dom_elements.get("element_count", 0)
            
            # Check for common issues
            if dom_elements.get("missing_alt_text"):
                findings.append({
                    "type": "accessibility",
                    "severity": "medium",
                    "message": "Some images missing alt text",
                    "count": dom_elements.get("missing_alt_text"),
                    "recommendation": "Add descriptive alt text to all images"
                })
        
        # Step 2: Check CSS metrics
        if css_metrics:
            metrics["css_issues"] = css_metrics.get("errors", 0)
            metrics["layout_shift_score"] = css_metrics.get("CLS", 0.0)
            
            if metrics["layout_shift_score"] > 0.1:
                findings.append({
                    "type": "performance",
                    "severity": "high",
                    "message": f"High layout shift detected (CLS: {metrics['layout_shift_score']})",
                    "threshold": 0.1,
                    "recommendation": "Optimize component sizing to prevent layout thrashing"
                })
            
            if css_metrics.get("failed_loads", 0) > 0:
                findings.append({
                    "type": "css_error",
                    "severity": "high",
                    "message": "CSS files failed to load",
                    "count": css_metrics.get("failed_loads"),
                    "recommendation": "Verify CSS file paths and check browser network tab"
                })
        
        # Step 3: Analyze accessibility
        if accessibility_data:
            metrics["interactive_elements"] = accessibility_data.get("interactive_count", 0)
            
            if not accessibility_data.get("semantic_html_valid"):
                findings.append({
                    "type": "accessibility",
                    "severity": "medium",
                    "message": "Semantic HTML structure issues detected",
                    "recommendation": "Use semantic HTML elements (nav, main, section, article, etc.)"
                })
        
        # Determine overall status
        status = "passed" if not findings else "failed"
        
        return {
            "taskName": "component-rendering",
            "module": module_name,
            "status": status,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "findings": findings,
            "metrics": metrics,
            "summary": f"Component rendering validation {'passed' if status == 'passed' else 'failed'}: {metrics['components_found']} components analyzed"
        }
    
    except Exception as e:
        logger.error(f"Component rendering validation failed: {str(e)}", exc_info=True)
        return {
            "taskName": "component-rendering",
            "module": module_name,
            "status": "failed",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "findings": [{
                "type": "execution_error",
                "severity": "critical",
                "message": f"Task execution failed: {str(e)}",
                "recommendation": "Check application DOM structure and CSS"
            }],
            "metrics": metrics,
            "summary": f"Component rendering validation failed: {str(e)}"
        }


if __name__ == "__main__":
    import argparse
    import asyncio
    
    parser = argparse.ArgumentParser(description="Component Rendering Validation Task")
    parser.add_argument("--base-url", required=True, help="Base URL of application")
    parser.add_argument("--module", required=True, help="Module name")
    parser.add_argument("--dom-elements", help="JSON file with DOM structure")
    parser.add_argument("--css-metrics", help="JSON file with CSS metrics")
    parser.add_argument("--accessibility", help="JSON file with accessibility data")
    
    args = parser.parse_args()
    
    dom_elements = None
    if args.dom_elements:
        with open(args.dom_elements) as f:
            dom_elements = json.load(f)
    
    css_metrics = None
    if args.css_metrics:
        with open(args.css_metrics) as f:
            css_metrics = json.load(f)
    
    accessibility_data = None
    if args.accessibility:
        with open(args.accessibility) as f:
            accessibility_data = json.load(f)
    
    result = asyncio.run(validate_component_rendering(
        args.base_url,
        args.module,
        dom_elements,
        css_metrics,
        accessibility_data
    ))
    
    print(json.dumps(result, indent=2))

#!/usr/bin/env python3
"""
Performance Profiling Task

Captures and analyzes Core Web Vitals:
1. LCP (Largest Contentful Paint) - target < 2.5s
2. INP (Interaction to Next Paint) - target < 200ms
3. CLS (Cumulative Layout Shift) - target < 0.1
4. TTFB (Time to Byte) - target < 600ms
5. FCP (First Contentful Paint)
"""

import json
import sys
import logging
from datetime import datetime
from typing import Dict

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def profile_performance(
    base_url: str,
    module_name: str,
    performance_data: Dict = None,
    custom_thresholds: Dict = None
) -> Dict:
    """
    Profile application performance using Core Web Vitals.
    
    Args:
        base_url: URL of the application
        module_name: Name of the module being tested
        performance_data: Captured performance metrics
        custom_thresholds: Custom performance thresholds
    
    Returns:
        dict: Task result with status, findings, metrics
    """
    
    # Default Web Vitals thresholds (good performance)
    default_thresholds = {
        "LCP_ms": 2500,
        "INP_ms": 200,
        "CLS": 0.1,
        "TTFB_ms": 600,
        "FCP_ms": 1800
    }
    
    thresholds = {**default_thresholds, **(custom_thresholds or {})}
    
    findings = []
    metrics = {
        "LCP_ms": 0,
        "INP_ms": 0,
        "CLS": 0.0,
        "TTFB_ms": 0,
        "FCP_ms": 0,
        "vitals_passing": 0,
        "vitals_total": 5
    }
    
    try:
        logger.info(f"Profiling performance for {base_url}")
        
        if performance_data:
            # Extract metrics from performance data
            vitals_passing = 0
            
            # Largest Contentful Paint
            lcp = performance_data.get("LCP_ms")
            if lcp:
                metrics["LCP_ms"] = lcp
                if lcp > thresholds["LCP_ms"]:
                    findings.append({
                        "type": "performance",
                        "severity": "high",
                        "metric": "LCP",
                        "message": f"LCP is {lcp}ms (threshold: {thresholds['LCP_ms']}ms)",
                        "recommendation": "Optimize render-blocking resources, minimize CSS/JS, use modern image formats"
                    })
                else:
                    vitals_passing += 1
            
            # Interaction to Next Paint
            inp = performance_data.get("INP_ms")
            if inp:
                metrics["INP_ms"] = inp
                if inp > thresholds["INP_ms"]:
                    findings.append({
                        "type": "performance",
                        "severity": "high",
                        "metric": "INP",
                        "message": f"INP is {inp}ms (threshold: {thresholds['INP_ms']}ms)",
                        "recommendation": "Optimize JavaScript execution time, break up long tasks, profile with DevTools"
                    })
                else:
                    vitals_passing += 1
            
            # Cumulative Layout Shift
            cls = performance_data.get("CLS")
            if cls is not None:
                metrics["CLS"] = cls
                if cls > thresholds["CLS"]:
                    findings.append({
                        "type": "performance",
                        "severity": "medium",
                        "metric": "CLS",
                        "message": f"CLS is {cls:.3f} (threshold: {thresholds['CLS']})",
                        "recommendation": "Avoid layout thrashing, reserve space for dynamic content, prevent unsized images"
                    })
                else:
                    vitals_passing += 1
            
            # Time to First Byte
            ttfb = performance_data.get("TTFB_ms")
            if ttfb:
                metrics["TTFB_ms"] = ttfb
                if ttfb > thresholds["TTFB_ms"]:
                    findings.append({
                        "type": "performance",
                        "severity": "medium",
                        "metric": "TTFB",
                        "message": f"TTFB is {ttfb}ms (threshold: {thresholds['TTFB_ms']}ms)",
                        "recommendation": "Improve server response time, enable caching, use CDN"
                    })
                else:
                    vitals_passing += 1
            
            # First Contentful Paint
            fcp = performance_data.get("FCP_ms")
            if fcp:
                metrics["FCP_ms"] = fcp
                if fcp > thresholds["FCP_ms"]:
                    findings.append({
                        "type": "performance",
                        "severity": "medium",
                        "metric": "FCP",
                        "message": f"FCP is {fcp}ms (threshold: {thresholds['FCP_ms']}ms)",
                        "recommendation": "Reduce CSS/JS, use preload hints, optimize server response time"
                    })
                else:
                    vitals_passing += 1
            
            metrics["vitals_passing"] = vitals_passing
            
            # Check for javascript execution time
            if performance_data.get("total_js_time_ms"):
                js_time = performance_data["total_js_time_ms"]
                if js_time > 1000:
                    findings.append({
                        "type": "performance",
                        "severity": "medium",
                        "message": f"High JavaScript execution time: {js_time}ms",
                        "recommendation": "Profile JS with DevTools, identify slow functions, consider code splitting"
                    })
            
            # Check for main thread blocking
            if performance_data.get("long_tasks", 0) > 0:
                findings.append({
                    "type": "performance",
                    "severity": "medium",
                    "message": f"{performance_data['long_tasks']} long-running tasks detected (>50ms)",
                    "recommendation": "Break up long tasks, yield to browser using requestIdleCallback"
                })
        
        # Determine overall status
        status = "passed" if len(findings) == 0 else "failed"
        
        return {
            "taskName": "performance-profiling",
            "module": module_name,
            "status": status,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "findings": findings,
            "metrics": metrics,
            "thresholds": thresholds,
            "summary": f"Performance profile {'passed' if status == 'passed' else 'failed'}: {metrics['vitals_passing']}/{metrics['vitals_total']} Core Web Vitals within threshold"
        }
    
    except Exception as e:
        logger.error(f"Performance profiling failed: {str(e)}", exc_info=True)
        return {
            "taskName": "performance-profiling",
            "module": module_name,
            "status": "failed",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "findings": [{
                "type": "execution_error",
                "severity": "critical",
                "message": f"Task execution failed: {str(e)}",
                "recommendation": "Check Chrome DevTools and performance monitoring setup"
            }],
            "metrics": metrics,
            "summary": f"Performance profiling failed: {str(e)}"
        }


if __name__ == "__main__":
    import argparse
    import asyncio
    
    parser = argparse.ArgumentParser(description="Performance Profiling Task")
    parser.add_argument("--base-url", required=True, help="Base URL of application")
    parser.add_argument("--module", required=True, help="Module name")
    parser.add_argument("--performance-data", help="JSON file with performance metrics")
    parser.add_argument("--custom-thresholds", help="JSON file with custom thresholds")
    
    args = parser.parse_args()
    
    performance_data = None
    if args.performance_data:
        with open(args.performance_data) as f:
            performance_data = json.load(f)
    
    custom_thresholds = None
    if args.custom_thresholds:
        with open(args.custom_thresholds) as f:
            custom_thresholds = json.load(f)
    
    result = asyncio.run(profile_performance(
        args.base_url,
        args.module,
        performance_data,
        custom_thresholds
    ))
    
    print(json.dumps(result, indent=2))

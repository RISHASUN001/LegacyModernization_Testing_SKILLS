#!/usr/bin/env python3
"""
Browser Testing Skill - Test Runner

Executes browser-testing-with-devtools skill against a running dashboard instance
with mock test data. Useful for development and validation without real Chrome DevTools.

Usage:
    python test_runner.py --base-url http://localhost:5276 --module Checklist --run-id run-001
"""

import asyncio
import json
import sys
import logging
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, Any
import urllib.request
import urllib.error

# Import the shared skill runtime
skill_dir = Path(__file__).parent
sys.path.insert(0, str(skill_dir / ".." / ".." / "_common"))

try:
    from skill_runtime import run_python_skill, RESULT_CONTRACT_VERSION
except ImportError:
    # Fallback if runtime not available
    RESULT_CONTRACT_VERSION = "2.0"

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class MockDataProvider:
    """Provides mock test data from the running dashboard API."""
    
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')
        self.api_url = f"{self.base_url}/api/test"
    
    def fetch_json(self, endpoint: str) -> Dict[str, Any]:
        """Fetch JSON data from the test API."""
        url = f"{self.api_url}/{endpoint}"
        try:
            logger.info(f"Fetching: {url}")
            with urllib.request.urlopen(url, timeout=5) as response:
                return json.loads(response.read().decode('utf-8'))
        except urllib.error.URLError as e:
            logger.warning(f"Failed to fetch {endpoint}: {e}")
            return {}
        except Exception as e:
            logger.error(f"Error fetching {endpoint}: {e}")
            return {}
    
    def get_console_logs(self) -> list:
        """Get mock console logs."""
        data = self.fetch_json("console-logs")
        return data.get("messages", [])
    
    def get_network_requests(self) -> list:
        """Get mock network requests."""
        data = self.fetch_json("network-requests")
        return data.get("requests", [])
    
    def get_performance_metrics(self) -> dict:
        """Get mock performance metrics."""
        data = self.fetch_json("performance-metrics")
        return data.get("metrics", {})
    
    def get_accessibility_report(self) -> dict:
        """Get mock accessibility report."""
        return self.fetch_json("accessibility-report")
    
    def get_dom_structure(self) -> dict:
        """Get mock DOM structure."""
        return self.fetch_json("dom-structure")
    
    def get_interaction_flows(self) -> list:
        """Get mock interaction flows."""
        data = self.fetch_json("interaction-flows")
        return data.get("flows", [])


async def run_browser_tests_with_mock_data(
    base_url: str,
    module_name: str,
    run_id: str,
    database_path: str
) -> Dict[str, Any]:
    """
    Run browser tests using mock data from the dashboard API.
    
    Args:
        base_url: Base URL of the running dashboard
        module_name: Module name
        run_id: Run ID
        database_path: Path to SQLite database
    
    Returns:
        dict: Combined test results
    """
    logger.info(f"Starting browser testing for {module_name} (run: {run_id})")
    logger.info(f"Dashboard URL: {base_url}")
    
    started_at = datetime.utcnow().isoformat() + "Z"
    provider = MockDataProvider(base_url)
    
    try:
        # Verify dashboard is running
        logger.info("Verifying dashboard is running...")
        health_check = provider.fetch_json("health")
        if not health_check:
            raise Exception("Dashboard health check failed - ensure application is running at " + base_url)
        
        logger.info(f"Dashboard health: {health_check.get('status', 'unknown')}")
        
        # Import task modules
        logger.info("Importing task modules...")
        sys.path.insert(0, str(skill_dir / "tasks"))
        
        from critical_path_validation import validate_critical_path
        from component_rendering import validate_component_rendering
        from network_integration import validate_network_integration
        from accessibility_scan import validate_accessibility
        from performance_profiling import profile_performance
        from user_interaction import validate_user_interactions
        
        # Fetch mock data
        logger.info("Fetching mock data from dashboard...")
        console_logs = provider.get_console_logs()
        network_requests = provider.get_network_requests()
        perf_metrics = provider.get_performance_metrics()
        a11y_report = provider.get_accessibility_report()
        dom_structure = provider.get_dom_structure()
        flows = provider.get_interaction_flows()
        
        # Run all tasks
        logger.info("Executing test tasks...")
        
        results = {
            "critical_path": await validate_critical_path(
                base_url, module_name, console_logs, network_requests
            ),
            "component_rendering": await validate_component_rendering(
                base_url, module_name, dom_structure, {}, a11y_report
            ),
            "network_integration": await validate_network_integration(
                base_url, module_name, network_requests, None, None
            ),
            "accessibility": await validate_accessibility(
                base_url, module_name, a11y_report, "AA"
            ),
            "performance": await profile_performance(
                base_url, module_name, perf_metrics, None
            ),
            "user_interaction": await validate_user_interactions(
                base_url, module_name, flows, None
            )
        }
        
        # Aggregate findings
        all_findings = []
        all_recommendations = []
        
        for task_name, result in results.items():
            logger.info(f"{task_name}: {result.get('status', 'unknown')}")
            all_findings.extend(result.get("findings", []))
            
            # Some tasks have recommendations
            if "summary" in result:
                all_recommendations.append({
                    "task": task_name,
                    "summary": result.get("summary", "")
                })
        
        ended_at = datetime.utcnow().isoformat() + "Z"
        
        # Create combined result
        combined_result = {
            "skillName": "browser-testing-with-devtools",
            "stage": "execution",
            "status": "passed" if all(r.get("status") == "passed" for r in results.values()) else "completed",
            "startedAt": started_at,
            "endedAt": ended_at,
            "summary": f"Browser testing completed with mock data. Tasks: {len(results)}, Findings: {len(all_findings)}",
            "metrics": {
                "tasks_completed": len(results),
                "total_findings": len(all_findings),
                "tasks_passed": sum(1 for r in results.values() if r.get("status") == "passed"),
                "tasks_failed": sum(1 for r in results.values() if r.get("status") == "failed")
            },
            "findings": all_findings,
            "recommendations": all_recommendations,
            "artifacts": [],
            "resultContractVersion": RESULT_CONTRACT_VERSION,
            "taskResults": results,
            "testMode": True,
            "mockDataUsed": True
        }
        
        return combined_result
    
    except Exception as e:
        logger.error(f"Browser testing failed: {str(e)}", exc_info=True)
        ended_at = datetime.utcnow().isoformat() + "Z"
        
        return {
            "skillName": "browser-testing-with-devtools",
            "stage": "execution",
            "status": "failed",
            "startedAt": started_at,
            "endedAt": ended_at,
            "summary": f"Browser testing failed: {str(e)}",
            "metrics": {},
            "findings": [{
                "type": "error",
                "severity": "critical",
                "message": f"Test execution failed: {str(e)}",
                "recommendation": "Ensure dashboard is running at " + base_url + " and test API endpoints are available"
            }],
            "recommendations": [],
            "artifacts": [],
            "resultContractVersion": RESULT_CONTRACT_VERSION,
            "testMode": True
        }


def save_results(results: Dict[str, Any], output_file: str = None) -> str:
    """Save test results to a JSON file."""
    if output_file is None:
        output_file = f"browser-test-results-{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
    
    output_path = Path(output_file)
    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2)
    
    logger.info(f"Results saved to: {output_path}")
    return str(output_path)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Browser Testing Skill - Test Runner with Mock Data"
    )
    parser.add_argument(
        "--base-url",
        default="http://localhost:5276",
        help="Base URL of the dashboard (default: http://localhost:5276)"
    )
    parser.add_argument(
        "--module",
        default="Checklist",
        help="Module name to test (default: Checklist)"
    )
    parser.add_argument(
        "--run-id",
        default="run-001",
        help="Run ID (default: run-001)"
    )
    parser.add_argument(
        "--database",
        default="data/modernization.db",
        help="Path to SQLite database (default: data/modernization.db)"
    )
    parser.add_argument(
        "--output",
        help="Output file for results (optional)"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Run the test
    results = asyncio.run(run_browser_tests_with_mock_data(
        args.base_url,
        args.module,
        args.run_id,
        args.database
    ))
    
    # Print results
    print("\n" + "="*70)
    print("BROWSER TESTING RESULTS")
    print("="*70)
    print(json.dumps(results, indent=2))
    print("="*70 + "\n")
    
    # Save results
    output_file = save_results(results, args.output)
    print(f"✅ Test completed. Results saved to: {output_file}")
    
    # Return exit code based on status
    return 0 if results.get("status") in ["passed", "completed"] else 1


if __name__ == "__main__":
    sys.exit(main())

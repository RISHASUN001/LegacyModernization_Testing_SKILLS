"""
Browser Testing Tasks Module

Individual task implementations for Chrome DevTools-based testing.
Each task can be executed independently or as part of the coordinated workflow.

Tasks:
- critical_path_validation: Page load, console errors, initial network
- component_rendering: DOM structure, CSS, Bootstrap integration
- network_integration: API calls, CORS, response validation
- accessibility_scan: WCAG 2.1 compliance, ARIA, keyboard navigation
- performance_profiling: Core Web Vitals, JavaScript execution
- user_interaction: Forms, user flows, focus management
"""

from .critical_path_validation import validate_critical_path
from .component_rendering import validate_component_rendering
from .network_integration import validate_network_integration
from .accessibility_scan import validate_accessibility
from .performance_profiling import profile_performance
from .user_interaction import validate_user_interactions

__all__ = [
    "validate_critical_path",
    "validate_component_rendering",
    "validate_network_integration",
    "validate_accessibility",
    "profile_performance",
    "validate_user_interactions"
]

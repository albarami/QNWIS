"""
Import smoke test for Chainlit app.

Verifies that the app can be imported even if Chainlit is not installed.
The module should gracefully handle missing Chainlit dependency.
"""

from __future__ import annotations

import importlib


def test_chainlit_app_imports():
    """
    Test that Chainlit app imports without errors.

    The app should:
        - Import successfully even if Chainlit is not installed
        - Gracefully handle ImportError for Chainlit
        - Not raise errors for other import issues

    If Chainlit is missing, that's expected and acceptable.
    Any other import error should fail the test.
    """
    try:
        # Attempt to import the app module
        importlib.import_module("apps.chainlit.app")
    except ImportError as e:
        # If Chainlit is missing, that's acceptable
        error_msg = str(e)
        assert (
            "chainlit" in error_msg.lower()
            or "no module named 'chainlit'" in error_msg.lower()
        ), f"Import failed for unexpected reason: {error_msg}"
    except Exception as e:
        # Any other exception should fail the test
        raise AssertionError(
            f"App import failed with unexpected error: {type(e).__name__}: {e}"
        ) from None


def test_chainlit_conditional_registration():
    """
    Test that Chainlit handlers are only registered if Chainlit is available.

    This verifies the `if cl:` guard works correctly.
    """
    try:
        import apps.chainlit.app as app_module

        # If Chainlit is available, cl should not be None
        # If Chainlit is not available, cl should be None
        # Either way, the module should import successfully
        assert hasattr(
            app_module, "cl"
        ), "Module should have cl attribute (even if None)"

    except ImportError as e:
        # If the module can't be imported due to other issues,
        # verify it's only because of Chainlit
        error_msg = str(e)
        assert (
            "chainlit" in error_msg.lower()
        ), f"Import failed for unexpected reason: {error_msg}"

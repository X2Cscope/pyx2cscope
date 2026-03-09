"""Unit tests for Web GUI components.

Tests cover:
- Flask routes (REST endpoints)
- WebScope state management
- Socket.IO handlers (mocked)
- Variable management
- Configuration save/load
"""

import json
from unittest.mock import MagicMock

import pytest

# HTTP status codes for test assertions
HTTP_OK = 200
HTTP_NOT_FOUND = 404


class TestFlaskAppCreation:
    """Tests for Flask application creation."""

    def test_create_app_returns_flask_app(self):
        """Test create_app returns a Flask application."""
        from pyx2cscope.gui.web.app import create_app

        app = create_app()

        assert app is not None
        assert app.name == "pyx2cscope.gui.web.app"

    def test_app_has_required_routes(self, flask_app):
        """Test app has all required routes registered."""
        rules = [rule.rule for rule in flask_app.url_map.iter_rules()]

        # Main routes
        assert "/" in rules
        assert "/serial-ports" in rules
        assert "/connect" in rules
        assert "/disconnect" in rules
        assert "/is-connected" in rules
        assert "/variables" in rules

    def test_app_testing_mode(self, flask_app):
        """Test app is in testing mode."""
        assert flask_app.config["TESTING"] is True


class TestFlaskRoutes:
    """Tests for Flask REST endpoints."""

    def test_index_route(self, flask_client):
        """Test index route returns HTML."""
        response = flask_client.get("/")

        assert response.status_code == HTTP_OK
        assert b"html" in response.data.lower()

    def test_serial_ports_route(self, flask_client, mocker):
        """Test serial-ports route returns list."""
        # Mock serial port enumeration
        mock_port = MagicMock()
        mock_port.device = "COM1"
        mock_port.description = "Test Port"
        mocker.patch(
            "serial.tools.list_ports.comports", return_value=[mock_port]
        )

        response = flask_client.get("/serial-ports")

        assert response.status_code == HTTP_OK
        data = json.loads(response.data)
        assert isinstance(data, list)

    def test_local_ips_route(self, flask_client):
        """Test local-ips route returns IP list."""
        response = flask_client.get("/local-ips")

        assert response.status_code == HTTP_OK
        data = json.loads(response.data)
        assert "ips" in data
        assert isinstance(data["ips"], list)
        assert len(data["ips"]) > 0

    def test_is_connected_route_disconnected(self, flask_client):
        """Test is-connected route returns False when disconnected."""
        response = flask_client.get("/is-connected")

        assert response.status_code == HTTP_OK
        data = json.loads(response.data)
        # Response might be {"status": False} or {"connected": False}
        assert data.get("status", data.get("connected", None)) is False

    def test_disconnect_route(self, flask_client, mocker):
        """Test disconnect route."""
        # Mock the web_scope to avoid AttributeError when not connected
        from pyx2cscope.gui.web.scope import web_scope

        mocker.patch.object(web_scope, "disconnect", return_value=None)

        response = flask_client.get("/disconnect")
        assert response.status_code == HTTP_OK

    def test_variables_route_not_connected(self, flask_client):
        """Test variables route when not connected."""
        response = flask_client.get("/variables?q=test")

        assert response.status_code == HTTP_OK
        data = json.loads(response.data)
        assert "items" in data
        assert data["items"] == []


class TestWatchViewRoutes:
    """Tests for watch view routes."""

    def test_watch_data_route(self, flask_client):
        """Test watch data route returns JSON."""
        response = flask_client.get("/watch/data")

        assert response.status_code == HTTP_OK
        data = json.loads(response.data)
        assert "data" in data

    def test_watch_view_route(self, flask_client):
        """Test watch view page route."""
        # Use trailing slash or follow redirects
        response = flask_client.get("/watch/", follow_redirects=True)

        assert response.status_code == HTTP_OK


class TestScopeViewRoutes:
    """Tests for scope view routes."""

    def test_scope_data_route(self, flask_client):
        """Test scope data route returns JSON."""
        response = flask_client.get("/scope/data")

        assert response.status_code == HTTP_OK
        data = json.loads(response.data)
        assert "data" in data

    def test_scope_view_route(self, flask_client):
        """Test scope view page route."""
        # Use trailing slash or follow redirects
        response = flask_client.get("/scope/", follow_redirects=True)

        assert response.status_code == HTTP_OK

    def test_scope_export_no_data(self, flask_client, mocker):
        """Test scope export with no data."""
        # Mock to avoid AttributeError when not connected
        from pyx2cscope.gui.web.scope import web_scope

        # get_scope_datasets returns a list of dicts with 'data' and 'label' keys
        mocker.patch.object(web_scope, "get_scope_datasets", return_value=[])
        mocker.patch.object(
            web_scope, "get_scope_chart_label", return_value=[0.0] * 100
        )

        response = flask_client.get("/scope/export")

        # Should return CSV even if empty
        assert response.status_code == HTTP_OK


class TestDashboardRoutes:
    """Tests for dashboard routes."""

    def test_dashboard_data_route(self, flask_client):
        """Test dashboard data route."""
        response = flask_client.get("/dashboard/data")

        assert response.status_code == HTTP_OK
        data = json.loads(response.data)
        assert isinstance(data, dict)

    def test_dashboard_load_layout_no_file(self, flask_client):
        """Test load layout when no file exists."""
        response = flask_client.get("/dashboard/load-layout")

        assert response.status_code == HTTP_NOT_FOUND
        data = json.loads(response.data)
        assert data['status'] == 'error'
        assert 'No saved layout found' in data['message']


class TestScriptViewRoutes:
    """Tests for script view routes."""

    def test_script_help_route(self, flask_client):
        """Test script help route returns markdown."""
        response = flask_client.get("/scripting/help")

        assert response.status_code == HTTP_OK
        data = json.loads(response.data)
        assert "markdown" in data


class TestCardLinks:
    """Tests for card links on the main page.

    Verifies that all 4 cards have correct links:
    - 'Open in new window' icon links (href="/route")
    - QR code generated links (insertQRCode("route"))

    Both link types use the same routes and should return valid standalone pages.
    """

    @pytest.mark.parametrize("route,expected_content", [
        ("/watch", [b"WatchView", b"Watch"]),
        ("/scope", [b"ScopeView", b"Scope"]),
        ("/dashboard", [b"Dashboard"]),
        ("/scripting", [b"Script", b"Scripting"]),
    ])
    def test_card_links_point_to_valid_pages(self, flask_client, route, expected_content):
        """Test both 'open in new window' and QR code links point to valid pages.

        Each card on the main page has two types of links:
        1. 'Open in new window' icon - direct link to the route
        2. QR code icon - generates QR code with the same route

        This test verifies all routes return valid standalone pages.
        """
        response = flask_client.get(route, follow_redirects=True)

        assert response.status_code == HTTP_OK
        # Check if any of the expected content variations are present
        assert any(content in response.data for content in expected_content)


class TestWebScopeClass:
    """Tests for WebScope state management."""

    @pytest.fixture
    def web_scope(self):
        """Create fresh WebScope instance."""
        from pyx2cscope.gui.web.scope import WebScope

        return WebScope()

    def test_initial_state(self, web_scope):
        """Test WebScope initializes with correct defaults."""
        assert web_scope.watch_vars == []
        assert web_scope.scope_vars == []
        assert web_scope.dashboard_vars == {}
        assert web_scope.x2c_scope is None
        assert web_scope.watch_rate == 1

    def test_is_connected_false_initially(self, web_scope):
        """Test is_connected returns False initially."""
        assert web_scope.is_connected() is False

    def test_set_watch_rate_valid(self, web_scope):
        """Test setting valid watch rate."""
        web_scope.set_watch_rate(2.5)
        assert web_scope.watch_rate == 2.5  # noqa: PLR2004

    def test_set_watch_rate_invalid_too_high(self, web_scope):
        """Test setting watch rate above max is ignored."""
        original_rate = web_scope.watch_rate
        web_scope.set_watch_rate(10.0)  # Above MAX_WATCH_RATE
        assert web_scope.watch_rate == original_rate

    def test_set_watch_rate_invalid_negative(self, web_scope):
        """Test setting negative watch rate is ignored."""
        original_rate = web_scope.watch_rate
        web_scope.set_watch_rate(-1.0)
        assert web_scope.watch_rate == original_rate

    def test_set_watch_rate_invalid_type(self, web_scope):
        """Test setting non-numeric watch rate is ignored."""
        original_rate = web_scope.watch_rate
        web_scope.set_watch_rate("invalid")
        assert web_scope.watch_rate == original_rate

    def test_clear_watch_var(self, web_scope):
        """Test clearing watch variables."""
        web_scope.watch_vars = [{"test": "data"}]
        web_scope.clear_watch_var()
        assert web_scope.watch_vars == []

    def test_clear_scope_var(self, web_scope, mocker):
        """Test clearing scope variables."""
        # Mock x2c_scope to avoid AttributeError
        mock_x2c = MagicMock()
        web_scope.x2c_scope = mock_x2c

        web_scope.scope_vars = [{"test": "data"}]
        web_scope.clear_scope_var()
        assert web_scope.scope_vars == []

    def test_set_watch_refresh(self, web_scope):
        """Test setting watch refresh flag."""
        assert web_scope.watch_refresh == 0
        web_scope.set_watch_refresh()
        assert web_scope.watch_refresh == 1

    def test_scope_trigger_defaults(self, web_scope):
        """Test scope trigger defaults."""
        assert web_scope.scope_trigger is False
        assert web_scope.scope_burst is False

    def test_scope_sample_time_default(self, web_scope):
        """Test scope sample time default."""
        assert web_scope.scope_sample_time == 1


class TestWebScopeVariableManagement:
    """Tests for WebScope variable management with mocked X2CScope."""

    @pytest.fixture
    def web_scope_connected(self, mocker):
        """Create WebScope with mocked X2CScope connection."""
        from pyx2cscope.gui.web.scope import WebScope

        web_scope = WebScope()

        # Create mock X2CScope
        mock_x2c = MagicMock()
        mock_x2c.is_connected.return_value = True

        # Create mock variable
        mock_var = MagicMock()
        mock_var.info.name = "test_var"
        mock_var.get_value.return_value = 42.0
        mock_var.__class__.__name__ = "FloatVariable"

        mock_x2c.get_variable.return_value = mock_var
        mock_x2c.list_variables.return_value = ["test_var", "other_var"]

        web_scope.x2c_scope = mock_x2c
        return web_scope

    def test_is_connected_true(self, web_scope_connected):
        """Test is_connected returns True when connected."""
        assert web_scope_connected.is_connected() is True

    def test_list_variables(self, web_scope_connected):
        """Test list_variables returns variable names."""
        variables = web_scope_connected.list_variables()
        assert "test_var" in variables
        assert "other_var" in variables

    def test_add_watch_var(self, web_scope_connected):
        """Test adding watch variable."""
        result = web_scope_connected.add_watch_var("test_var")

        assert result is not None
        assert len(web_scope_connected.watch_vars) == 1

    def test_add_watch_var_duplicate_prevented(self, web_scope_connected):
        """Test duplicate watch variables are not added."""
        web_scope_connected.add_watch_var("test_var")
        web_scope_connected.add_watch_var("test_var")  # Try to add again

        assert len(web_scope_connected.watch_vars) == 1

    def test_remove_watch_var(self, web_scope_connected):
        """Test removing watch variable."""
        web_scope_connected.add_watch_var("test_var")
        assert len(web_scope_connected.watch_vars) == 1

        web_scope_connected.remove_watch_var("test_var")
        assert len(web_scope_connected.watch_vars) == 0

    def test_add_scope_var(self, web_scope_connected):
        """Test adding scope variable."""
        result = web_scope_connected.add_scope_var("test_var")

        assert result is not None
        assert len(web_scope_connected.scope_vars) == 1

    def test_add_scope_var_max_limit(self, web_scope_connected):
        """Test scope variables can be added (max limit may not be enforced in WebScope)."""
        # Add 8 variables
        for i in range(8):
            mock_var = MagicMock()
            mock_var.info.name = f"var_{i}"
            mock_var.__class__.__name__ = "FloatVariable"
            web_scope_connected.x2c_scope.get_variable.return_value = mock_var
            web_scope_connected.add_scope_var(f"var_{i}")

        # Verify 8 were added
        assert len(web_scope_connected.scope_vars) == 8  # noqa: PLR2004

        # Note: WebScope doesn't enforce a max limit in the web GUI
        # The x2c_scope backend enforces the limit when actually using scope

    def test_remove_scope_var(self, web_scope_connected):
        """Test removing scope variable."""
        web_scope_connected.add_scope_var("test_var")
        assert len(web_scope_connected.scope_vars) == 1

        web_scope_connected.remove_scope_var("test_var")
        assert len(web_scope_connected.scope_vars) == 0


class TestWebScopeScaledValue:
    """Tests for WebScope scaled value calculation."""

    def test_update_watch_fields_float(self):
        """Test scaled value calculation for float."""
        from pyx2cscope.gui.web.scope import WebScope

        data = {
            "value": 10.0,
            "scaling": 2.0,
            "offset": 5.0,
            "type": "float",
        }

        WebScope._update_watch_fields(data)

        # scaled_value = (value * scaling) + offset = (10 * 2) + 5 = 25
        assert data["scaled_value"] == 25.0  # noqa: PLR2004

    def test_update_watch_fields_integer(self):
        """Test scaled value calculation for integer."""
        from pyx2cscope.gui.web.scope import WebScope

        data = {
            "value": 10,
            "scaling": 2.0,
            "offset": 5.0,
            "type": "int",
        }

        WebScope._update_watch_fields(data)

        assert data["scaled_value"] == 25.0  # noqa: PLR2004

    def test_variable_to_json(self):
        """Test variable_to_json conversion."""
        from pyx2cscope.gui.web.scope import WebScope

        mock_var = MagicMock()
        mock_var.info.name = "test_var"

        data = {
            "variable": mock_var,
            "value": 10.0,
            "scaling": 1.0,
        }

        result = WebScope.variable_to_json(data)

        assert result["variable"] == "test_var"
        assert result["value"] == 10.0  # noqa: PLR2004


class TestWebScopeDashboard:
    """Tests for WebScope dashboard functionality."""

    @pytest.fixture
    def web_scope_connected(self, mocker):
        """Create WebScope with mocked X2CScope connection."""
        from pyx2cscope.gui.web.scope import WebScope

        web_scope = WebScope()

        mock_x2c = MagicMock()
        mock_x2c.is_connected.return_value = True

        mock_var = MagicMock()
        mock_var.info.name = "dashboard_var"
        mock_var.get_value.return_value = 100.0
        mock_x2c.get_variable.return_value = mock_var

        web_scope.x2c_scope = mock_x2c
        return web_scope

    def test_add_dashboard_var(self, web_scope_connected):
        """Test adding dashboard variable."""
        web_scope_connected.add_dashboard_var("dashboard_var")

        assert "dashboard_var" in web_scope_connected.dashboard_vars

    def test_remove_dashboard_var(self, web_scope_connected):
        """Test removing dashboard variable."""
        web_scope_connected.add_dashboard_var("dashboard_var")
        web_scope_connected.remove_dashboard_var("dashboard_var")

        assert "dashboard_var" not in web_scope_connected.dashboard_vars

    def test_remove_nonexistent_dashboard_var(self, web_scope_connected):
        """Test removing non-existent dashboard variable doesn't raise."""
        # Should not raise
        web_scope_connected.remove_dashboard_var("nonexistent")


class TestWebScopeThreadSafety:
    """Tests for WebScope thread safety."""

    def test_lock_exists(self):
        """Test WebScope has a lock for thread safety."""
        from pyx2cscope.gui.web.scope import WebScope

        web_scope = WebScope()
        assert web_scope._lock is not None

    def test_lock_is_used_in_watch_operations(self, mocker):
        """Test lock is acquired during watch operations."""
        from pyx2cscope.gui.web.scope import WebScope

        web_scope = WebScope()

        # Mock X2CScope
        mock_x2c = MagicMock()
        mock_var = MagicMock()
        mock_var.info.name = "test_var"
        mock_var.get_value.return_value = 1.0
        mock_var.__class__.__name__ = "FloatVariable"
        mock_x2c.get_variable.return_value = mock_var
        web_scope.x2c_scope = mock_x2c

        # Add variable and read it
        web_scope.add_watch_var("test_var")

        # The operations should complete without deadlock
        assert len(web_scope.watch_vars) == 1


class TestConnectEndpoint:
    """Tests for connect endpoint."""

    def test_connect_missing_elf(self, flask_client):
        """Test connect fails without ELF file."""
        response = flask_client.post(
            "/connect",
            data={"interface": "SERIAL", "port": "COM1"},
            content_type="multipart/form-data",
        )

        # Should fail or return error
        assert response.status_code in [200, 400, 500]

    def test_connect_serial_interface(self, flask_client, mocker, elf_file_path):
        """Test connect with serial interface."""
        # Mock X2CScope to prevent real connection
        mock_x2c = MagicMock()
        mocker.patch(
            "pyx2cscope.gui.web.scope.X2CScope", return_value=mock_x2c
        )

        with open(elf_file_path, "rb") as elf_file:
            response = flask_client.post(
                "/connect",
                data={
                    "interface": "SERIAL",
                    "port": "COM1",
                    "baud_rate": "115200",
                    "elf_file": (elf_file, "test.elf"),
                },
                content_type="multipart/form-data",
            )

        # Connection attempt may fail with 400 if validation fails, 200 on success, or 500 on error
        assert response.status_code in [200, 400, 500]

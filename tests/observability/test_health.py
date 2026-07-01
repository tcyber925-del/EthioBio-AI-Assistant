from src.observability.health import ModuleHealthRegistry


class TestModuleHealthRegistry:
    def test_register_and_get(self):
        reg = ModuleHealthRegistry()
        m = reg.register("test_module")
        assert m.name == "test_module"
        assert m.status == "healthy"
        assert reg.get("test_module") is m

    def test_register_duplicate_returns_same(self):
        reg = ModuleHealthRegistry()
        m1 = reg.register("dup")
        m2 = reg.register("dup")
        assert m1 is m2

    def test_record_request(self):
        reg = ModuleHealthRegistry()
        reg.register("m")
        reg.record_request("m", error=False)
        reg.record_request("m", error=True)
        m = reg.get("m")
        assert m._request_count == 2
        assert m._error_count == 1

    def test_set_status(self):
        reg = ModuleHealthRegistry()
        reg.set_status("m", "degraded", details="slow", error="timeout")
        m = reg.get("m")
        assert m.status == "degraded"
        assert m.details == "slow"
        assert m.last_error == "timeout"

    def test_overall_status_healthy(self):
        reg = ModuleHealthRegistry()
        reg.register("a")
        reg.register("b")
        assert reg.overall_status() == "healthy"

    def test_overall_status_degraded(self):
        reg = ModuleHealthRegistry()
        reg.register("a")
        reg.set_status("b", "degraded")
        assert reg.overall_status() == "degraded"

    def test_overall_status_unhealthy(self):
        reg = ModuleHealthRegistry()
        reg.set_status("b", "unhealthy")
        assert reg.overall_status() == "unhealthy"

    def test_to_dict_basic(self):
        reg = ModuleHealthRegistry()
        reg.register("x")
        d = reg.to_dict(include_details=True)
        assert "overall_status" in d
        assert "uptime_seconds" in d
        assert "modules" in d
        assert len(d["modules"]) == 1

    def test_to_dict_no_details(self):
        reg = ModuleHealthRegistry()
        reg.register("x")
        d = reg.to_dict(include_details=False)
        assert d["modules"] == []

    def test_get_nonexistent(self):
        reg = ModuleHealthRegistry()
        assert reg.get("nope") is None

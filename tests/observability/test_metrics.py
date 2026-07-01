from src.observability.metrics import Counter, Gauge, Histogram, MetricsRegistry, Timer


class TestCounter:
    def test_increment(self):
        c = Counter("t")
        assert c._value == 0
        c.inc()
        assert c._value == 1

    def test_inc_with_labels(self):
        c = Counter("t")
        c.inc(labels={"a": "1"})
        assert c._value == 1


class TestGauge:
    def test_set_and_get(self):
        g = Gauge("t")
        g.set(42.5)
        assert g._value == 42.5
        g.set(0)
        assert g._value == 0

    def test_set_with_labels(self):
        g = Gauge("t")
        g.set(1.0, labels={"env": "test"})
        assert g._value == 1.0


class TestHistogram:
    def test_observe(self):
        h = Histogram("t")
        h.observe(10)
        h.observe(20)
        assert h._value == 20

    def test_observe_with_labels(self):
        h = Histogram("t")
        h.observe(15, labels={"op": "fast"})
        assert h._value == 15


class TestMetricsRegistry:
    def test_counter_convenience(self):
        r = MetricsRegistry()
        c = r.counter("x")
        assert isinstance(c, Counter)
        assert c.name == "x"

    def test_gauge_convenience(self):
        r = MetricsRegistry()
        g = r.gauge("y")
        assert isinstance(g, Gauge)
        assert g.name == "y"

    def test_histogram_convenience(self):
        r = MetricsRegistry()
        h = r.histogram("z")
        assert isinstance(h, Histogram)
        assert h.name == "z"

    def test_shared_instance(self):
        r = MetricsRegistry()
        c1 = r.counter("m")
        c2 = r.counter("m")
        assert c1 is c2

    def test_to_dict(self):
        r = MetricsRegistry()
        r.counter("a").inc()
        r.gauge("b").set(1.5)
        d = r.to_dict()
        assert d["a"] == 1
        assert d["b"] == 1.5


class TestPrometheusText:
    def test_empty_registry(self):
        r = MetricsRegistry()
        text = r.prometheus_text()
        assert text.endswith("\n")
        assert text.strip() == ""

    def test_counter_and_gauge(self):
        r = MetricsRegistry()
        r.counter("requests_total").inc()
        r.gauge("cpu_temp").set(42.5)
        text = r.prometheus_text()
        assert "# HELP requests_total" in text
        assert "# TYPE requests_total counter" in text
        assert "requests_total 1" in text
        assert "# HELP cpu_temp" in text
        assert "# TYPE cpu_temp gauge" in text
        assert "cpu_temp 42.5" in text


class TestTimer:
    def test_timer_records_duration(self):
        with Timer("dur"):
            pass

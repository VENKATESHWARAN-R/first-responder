"""Unit tests for RBAC namespace filtering."""

from app.services.auth import filter_namespaces


class TestFilterNamespaces:
    """Tests for the namespace access filtering logic."""

    def test_wildcard_access_returns_all(self):
        user_ns = ["*"]
        available = ["default", "kube-system", "monitoring", "app"]
        result = filter_namespaces(user_ns, available)
        assert result == available

    def test_specific_namespaces_filters_correctly(self):
        user_ns = ["default", "app"]
        available = ["default", "kube-system", "monitoring", "app"]
        result = filter_namespaces(user_ns, available)
        assert result == ["default", "app"]

    def test_empty_user_namespaces_returns_nothing(self):
        user_ns = []
        available = ["default", "kube-system"]
        result = filter_namespaces(user_ns, available)
        assert result == []

    def test_user_namespace_not_in_cluster(self):
        """User has access to a namespace that doesn't exist in the cluster."""
        user_ns = ["staging", "production"]
        available = ["default", "kube-system"]
        result = filter_namespaces(user_ns, available)
        assert result == []

    def test_partial_overlap(self):
        user_ns = ["default", "staging"]
        available = ["default", "kube-system", "monitoring"]
        result = filter_namespaces(user_ns, available)
        assert result == ["default"]

    def test_empty_cluster_namespaces(self):
        user_ns = ["*"]
        available = []
        result = filter_namespaces(user_ns, available)
        assert result == []

    def test_preserves_order_of_available(self):
        user_ns = ["c", "a"]
        available = ["a", "b", "c"]
        result = filter_namespaces(user_ns, available)
        assert result == ["a", "c"]  # Order follows available, not user_ns

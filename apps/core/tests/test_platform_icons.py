import pytest
from django.utils.safestring import SafeString

from apps.core.templatetags.platform_icons import platform_icon


@pytest.mark.parametrize("platform", ["facebook", "twitter", "x", "linkedin", "pinterest"])
def test_platform_icon_returns_svg_for_known_platforms(platform):
    rendered = platform_icon(platform)

    assert "<svg" in str(rendered)
    assert "</svg>" in str(rendered)
    assert isinstance(rendered, SafeString)


def test_platform_icon_returns_safe_fallback_for_unknown_platform():
    rendered = platform_icon("mastodon")

    assert "<svg" in str(rendered)
    assert "#64748B" in str(rendered)
    assert isinstance(rendered, SafeString)

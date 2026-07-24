from django.conf import settings


def test_main_css_defines_shared_ui_components():
    css_path = settings.BASE_DIR / "static" / "css" / "main.css"
    css = css_path.read_text()

    assert ".btn-primary" in css
    assert ".btn-accent" in css
    assert ".btn-outline" in css
    assert ".btn-disabled" in css
    assert ".file-input::file-selector-button" in css
    assert ".sidebar-link-active" in css

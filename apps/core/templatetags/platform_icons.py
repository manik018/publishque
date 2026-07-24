from django import template
from django.utils.html import format_html
from django.utils.safestring import mark_safe


register = template.Library()


ICONS = {
    "facebook": (
        "#1877F2",
        '<svg class="h-6 w-6" viewBox="0 0 24 24" aria-hidden="true">'
        '<circle cx="12" cy="12" r="10" fill="{color}"/>'
        '<path fill="white" d="M13.4 20v-7h2.2l.4-2.7h-2.6V8.6c0-.8.2-1.3 1.3-1.3H16V5a17 17 0 0 0-2.1-.1c-2.1 0-3.5 1.3-3.5 3.6v1.8H8v2.7h2.4v7h3z"/>'
        "</svg>",
    ),
    "twitter": (
        "#111111",
        '<svg class="h-6 w-6" viewBox="0 0 24 24" aria-hidden="true">'
        '<rect x="3" y="3" width="18" height="18" rx="6" fill="{color}"/>'
        '<path fill="white" d="m7 7 4.1 5.4L7.3 17h2.2l2.7-3.2 2.4 3.2H17l-4-5.3L16.7 7h-2.1l-2.7 3.1L9.5 7H7z"/>'
        "</svg>",
    ),
    "x": (
        "#111111",
        '<svg class="h-6 w-6" viewBox="0 0 24 24" aria-hidden="true">'
        '<rect x="3" y="3" width="18" height="18" rx="6" fill="{color}"/>'
        '<path fill="white" d="m7 7 4.1 5.4L7.3 17h2.2l2.7-3.2 2.4 3.2H17l-4-5.3L16.7 7h-2.1l-2.7 3.1L9.5 7H7z"/>'
        "</svg>",
    ),
    "linkedin": (
        "#0A66C2",
        '<svg class="h-6 w-6" viewBox="0 0 24 24" aria-hidden="true">'
        '<rect x="3" y="3" width="18" height="18" rx="4" fill="{color}"/>'
        '<path fill="white" d="M7.2 10h2.3v7H7.2v-7zm1.2-3.4a1.3 1.3 0 1 1 0 2.6 1.3 1.3 0 0 1 0-2.6zM11 10h2.2v1c.3-.6 1.1-1.2 2.3-1.2 2.4 0 2.8 1.6 2.8 3.6V17H16v-3.3c0-.8 0-1.8-1.1-1.8s-1.3.9-1.3 1.8V17H11v-7z"/>'
        "</svg>",
    ),
    "pinterest": (
        "#E60023",
        '<svg class="h-6 w-6" viewBox="0 0 24 24" aria-hidden="true">'
        '<circle cx="12" cy="12" r="10" fill="{color}"/>'
        '<path fill="white" d="M11.4 15.1c-.3 1.4-.6 2.8-1.4 4 .3.1.6.1.9.1 5 0 8.3-3.2 8.3-7.7 0-4-3.3-6.8-7.3-6.8-5 0-7.7 3.4-7.7 7.1 0 1.7.9 3.8 2.4 4.5.2.1.4.1.5-.2l.3-1.1c.1-.3 0-.4-.2-.7-.5-.6-.8-1.4-.8-2.3 0-2.6 2-5.2 5.3-5.2 2.9 0 4.9 2 4.9 4.7 0 3-1.5 5-3.5 5-1.1 0-1.9-.9-1.6-2l.5-1.8c.2-.8.6-1.7.6-2.3 0-.5-.3-1-1-1-.8 0-1.5.9-1.5 2 0 .7.2 1.2.2 1.2l-.9 3.5z"/>'
        "</svg>",
    ),
}


@register.simple_tag
def platform_icon(platform_name):
    key = str(platform_name or "").lower()
    if key not in ICONS:
        return mark_safe(
            '<svg class="h-6 w-6" viewBox="0 0 24 24" aria-hidden="true">'
            '<circle cx="12" cy="12" r="10" fill="#64748B"/>'
            '<path fill="white" d="M12 6a6 6 0 1 0 0 12 6 6 0 0 0 0-12zm0 3.5 3 5H9l3-5z"/>'
            "</svg>"
        )
    color, svg = ICONS[key]
    return format_html(svg, color=color)

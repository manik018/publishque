from django import forms

from .models import NotificationPreference


class NotificationPreferenceForm(forms.ModelForm):
    class Meta:
        model = NotificationPreference
        fields = (
            "email_on_post_success",
            "email_on_post_failure",
            "in_app_on_post_success",
            "in_app_on_post_failure",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update(
                {
                    "class": "h-5 w-5 rounded border-slate-300 text-accent focus:ring-accent",
                }
            )

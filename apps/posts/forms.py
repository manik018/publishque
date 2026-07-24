from django import forms
from django.utils import timezone

from apps.profiles.models import ConnectedProfile

from .models import Post


class PostComposerForm(forms.ModelForm):
    connected_profiles = forms.ModelMultipleChoiceField(
        queryset=ConnectedProfile.objects.none(),
        widget=forms.CheckboxSelectMultiple,
    )
    scheduled_time = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={"type": "datetime-local"}),
        input_formats=["%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"],
    )

    class Meta:
        model = Post
        fields = ("content", "media", "connected_profiles", "scheduled_time")
        widgets = {
            "content": forms.Textarea(
                attrs={
                    "rows": 6,
                    "required": True,
                    "placeholder": "Write the post you want to schedule...",
                }
            )
        }

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["connected_profiles"].queryset = ConnectedProfile.objects.filter(
            user=user,
            is_active=True,
        ).order_by("platform", "display_name")
        self.fields["content"].widget.attrs.update(
            {
                "class": "block w-full rounded border border-slate-300 px-3 py-2 text-sm shadow-sm focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary",
            }
        )
        self.fields["media"].widget.attrs.update(
            {
                "class": "block w-full text-sm text-slate-700 file:mr-4 file:rounded file:border-0 file:bg-primary file:px-3 file:py-2 file:text-sm file:font-semibold file:text-white",
            }
        )
        self.fields["scheduled_time"].widget.attrs.update(
            {
                "class": "block w-full rounded border border-slate-300 px-3 py-2 text-sm shadow-sm focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary",
                "required": True,
            }
        )

    def clean_content(self):
        content = self.cleaned_data["content"].strip()
        if not content:
            raise forms.ValidationError("Post content cannot be empty.")
        return content

    def clean_scheduled_time(self):
        scheduled_time = self.cleaned_data["scheduled_time"]
        if scheduled_time <= timezone.now():
            raise forms.ValidationError("Scheduled time must be in the future.")
        return scheduled_time

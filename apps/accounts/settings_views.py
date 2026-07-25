from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth import logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.core.mail import send_mail
from django.core.signing import BadSignature, SignatureExpired, TimestampSigner
from django.shortcuts import redirect, render
from django.urls import reverse

from apps.notifications.forms import NotificationPreferenceForm
from apps.notifications.models import NotificationPreference
from apps.profiles.models import ConnectedProfile

from .forms import ProfileSettingsForm


EMAIL_VERIFY_SALT = "publishque.email-verification"


def build_email_verification_token(user, email):
    return TimestampSigner(salt=EMAIL_VERIFY_SALT).sign(f"{user.pk}:{email}")


def send_email_verification(request, user, email):
    token = build_email_verification_token(user, email)
    verify_url = request.build_absolute_uri(
        reverse("settings_email_verify", kwargs={"token": token})
    )
    send_mail(
        subject="Verify your new Publishque email address",
        message=(
            "Confirm your new Publishque email address using this link:\n\n"
            f"{verify_url}\n\n"
            "Your current login email will remain active until you verify this address."
        ),
        from_email=None,
        recipient_list=[email],
        fail_silently=False,
    )


@login_required
def settings_hub(request):
    return redirect("settings_profile")


@login_required
def profile_settings(request):
    user = request.user
    if request.method == "POST":
        current_email = user.email
        form = ProfileSettingsForm(request.POST, instance=user, user=user)
        if form.is_valid():
            new_email = form.cleaned_data["email"]
            email_changed = new_email != current_email
            user.full_name = form.cleaned_data["full_name"]
            user.timezone = form.cleaned_data["timezone"]
            if email_changed:
                user.email = current_email
                user.pending_email = new_email
                user.is_email_verified = False
                user.save(
                    update_fields=[
                        "full_name",
                        "timezone",
                        "pending_email",
                        "is_email_verified",
                    ]
                )
                send_email_verification(request, user, new_email)
                messages.success(
                    request,
                    "Profile updated. Please verify your new email address.",
                )
            else:
                user.save(update_fields=["full_name", "timezone"])
                messages.success(request, "Profile updated successfully.")
            return redirect("settings_profile")
    else:
        form = ProfileSettingsForm(instance=user, user=user)

    return render(
        request,
        "settings/profile.html",
        {
            "form": form,
            "active_settings_section": "profile",
        },
    )


def verify_email(request, token):
    signer = TimestampSigner(salt=EMAIL_VERIFY_SALT)
    User = get_user_model()
    try:
        value = signer.unsign(token, max_age=60 * 60 * 24)
        user_id, email = value.split(":", 1)
        user = User.objects.get(pk=user_id, pending_email=email)
    except (BadSignature, SignatureExpired, ValueError, User.DoesNotExist):
        messages.error(request, "That email verification link is invalid or expired.")
        return redirect("settings_profile")

    user.email = email
    user.pending_email = ""
    user.is_email_verified = True
    user.save(update_fields=["email", "pending_email", "is_email_verified"])
    messages.success(request, "Your email address has been verified.")
    return redirect("settings_profile")


@login_required
def security_settings(request):
    if request.method == "POST":
        if request.POST.get("action") == "change_password":
            password_form = PasswordChangeForm(request.user, request.POST)
            if password_form.is_valid():
                user = password_form.save()
                update_session_auth_hash(request, user)
                messages.success(request, "Password changed successfully.")
                return redirect("settings_security")
        elif request.POST.get("action") == "delete_account":
            if request.POST.get("confirm_delete") == "DELETE":
                user = request.user
                logout(request)
                user.delete()
                return redirect("account_deleted")
            password_form = PasswordChangeForm(request.user)
            messages.error(request, "Type DELETE to confirm account deletion.")
        else:
            password_form = PasswordChangeForm(request.user)
    else:
        password_form = PasswordChangeForm(request.user)

    connected_profiles = ConnectedProfile.objects.filter(user=request.user).order_by(
        "platform", "display_name"
    )
    return render(
        request,
        "settings/security.html",
        {
            "password_form": password_form,
            "connected_profiles": connected_profiles,
            "active_settings_section": "security",
        },
    )


@login_required
def notification_settings(request):
    preferences, _ = NotificationPreference.objects.get_or_create(user=request.user)
    if request.method == "POST":
        form = NotificationPreferenceForm(request.POST, instance=preferences)
        if form.is_valid():
            form.save()
            messages.success(request, "Notification preferences saved.")
            return redirect("settings_notifications")
    else:
        form = NotificationPreferenceForm(instance=preferences)

    return render(
        request,
        "settings/notifications.html",
        {
            "form": form,
            "active_settings_section": "notifications",
        },
    )


def account_deleted(request):
    return render(request, "settings/account_deleted.html")

import pytest
from django.urls import reverse


pytestmark = pytest.mark.django_db


def test_user_registration_success(client, django_user_model):
    response = client.post(
        reverse("accounts:register"),
        {
            "email": "new@example.com",
            "full_name": "New User",
            "password1": "StrongPass123!",
            "password2": "StrongPass123!",
        },
    )

    assert response.status_code == 302
    assert response.url == reverse("dashboard")

    user = django_user_model.objects.get(email="new@example.com")
    assert user.full_name == "New User"
    assert user.check_password("StrongPass123!")
    assert "_auth_user_id" in client.session


def test_registration_with_duplicate_email_fails(client, django_user_model):
    django_user_model.objects.create_user(
        email="existing@example.com",
        full_name="Existing User",
        password="StrongPass123!",
    )

    response = client.post(
        reverse("accounts:register"),
        {
            "email": "existing@example.com",
            "full_name": "Another User",
            "password1": "StrongPass123!",
            "password2": "StrongPass123!",
        },
    )

    assert response.status_code == 200
    assert "A user with this email already exists." in response.content.decode()
    assert django_user_model.objects.filter(email="existing@example.com").count() == 1


def test_login_with_correct_credentials_succeeds(client, django_user_model):
    django_user_model.objects.create_user(
        email="login@example.com",
        full_name="Login User",
        password="StrongPass123!",
    )

    response = client.post(
        reverse("accounts:login"),
        {
            "username": "login@example.com",
            "password": "StrongPass123!",
        },
    )

    assert response.status_code == 302
    assert response.url == reverse("dashboard")
    assert "_auth_user_id" in client.session


def test_login_with_wrong_password_fails(client, django_user_model):
    django_user_model.objects.create_user(
        email="login@example.com",
        full_name="Login User",
        password="StrongPass123!",
    )

    response = client.post(
        reverse("accounts:login"),
        {
            "username": "login@example.com",
            "password": "WrongPass123!",
        },
    )

    assert response.status_code == 200
    assert "Please enter a correct email and password." in response.content.decode()
    assert "_auth_user_id" not in client.session


def test_logout_works(client, django_user_model):
    user = django_user_model.objects.create_user(
        email="logout@example.com",
        full_name="Logout User",
        password="StrongPass123!",
    )
    client.force_login(user)

    response = client.post(reverse("accounts:logout"))

    assert response.status_code == 302
    assert response.url == reverse("accounts:login")
    assert "_auth_user_id" not in client.session


from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse


class AccountTests(TestCase):
    def test_register_creates_regular_user_and_logs_in(self):
        response = self.client.post(reverse("accounts:register"), {
            "username": "newlearner", "first_name": "هنرجو",
            "password1": "Learning-6428!", "password2": "Learning-6428!",
        })
        self.assertRedirects(response, reverse("listings:mine"))
        user = get_user_model().objects.get(username="newlearner")
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertEqual(int(self.client.session["_auth_user_id"]), user.pk)

    def test_duplicate_registration_shows_error(self):
        get_user_model().objects.create_user("existing", password="Learning-6428!")
        response = self.client.post(reverse("accounts:register"), {
            "username": "existing", "first_name": "کاربر",
            "password1": "Learning-6428!", "password2": "Learning-6428!",
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn("username", response.context["form"].errors)
        self.assertEqual(get_user_model().objects.count(), 1)

    def test_login_rejects_external_next_redirect(self):
        get_user_model().objects.create_user("learner", password="Learning-6428!")
        response = self.client.post(reverse("accounts:login"), {
            "username": "learner", "password": "Learning-6428!", "next": "https://evil.example/",
        })
        self.assertEqual(response.url, reverse("listings:mine"))

    def test_logout_requires_post(self):
        user = get_user_model().objects.create_user("learner")
        self.client.force_login(user)
        self.assertEqual(self.client.get(reverse("accounts:logout")).status_code, 405)
        self.assertIn("_auth_user_id", self.client.session)
        self.assertRedirects(self.client.post(reverse("accounts:logout")), reverse("listings:list"))
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_registration_requires_csrf_token(self):
        response = Client(enforce_csrf_checks=True).post(reverse("accounts:register"), {})
        self.assertEqual(response.status_code, 403)

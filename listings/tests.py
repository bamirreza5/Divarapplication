from io import BytesIO, StringIO
import tempfile

from PIL import Image
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.db import IntegrityError, transaction
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from .forms import AdForm
from .models import Ad, Bookmark, Category, City


class ListingsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = get_user_model().objects.create_user("seller", password="Learning-6428!")
        cls.other = get_user_model().objects.create_user("buyer", password="Learning-6428!")
        cls.staff = get_user_model().objects.create_superuser("manager", "manager@example.test", "Learning-6428!")
        cls.category = Category.objects.create(name="دیجیتال", slug="digital", icon="▣")
        cls.city = City.objects.create(name="تهران", slug="tehran")
        cls.ad = Ad.objects.create(owner=cls.owner, category=cls.category, city=cls.city,
            title="لپ‌تاپ آموزشی سالم", description="این لپ‌تاپ سالم است و برای آموزش برنامه‌نویسی استفاده شده است.",
            price_type="fixed", price=10000000, phone="09123456789", status="published")

    def payload(self, **changes):
        data = {"title": "عنوان آگهی آزمایشی جدید", "description": "توضیحات کافی برای یک آگهی آزمایشی با ویژگی‌های مشخص.",
            "category": self.category.pk, "city": self.city.pk, "district": "ونک",
            "price_type": "fixed", "price": "۱٬۲۰۰٬۰۰۰", "phone": "۰۹۱۲۳۴۵۶۷۸۹"}
        data.update(changes)
        return data

    def login_owner(self):
        self.client.force_login(self.owner)

    def test_only_published_ads_are_public(self):
        for status in ("pending", "rejected", "sold"):
            Ad.objects.create(owner=self.owner, category=self.category, city=self.city,
                title=f"آگهی خصوصی {status}", description="توضیحات یک آگهی خصوصی برای آزمایش.",
                price_type="free", price=0, phone="09123456789", status=status)
        response = self.client.get(reverse("listings:list"))
        self.assertEqual(response.context["page_obj"].paginator.count, 1)
        self.assertContains(response, self.ad.title)
        self.assertNotContains(response, "آگهی خصوصی")

    def test_create_requires_login(self):
        response = self.client.post(reverse("listings:create"), self.payload())
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("accounts:login"), response.url)
        self.assertEqual(Ad.objects.count(), 1)

    def test_create_normalizes_numbers_and_ignores_owner_status_injection(self):
        self.login_owner()
        response = self.client.post(reverse("listings:create"), self.payload(owner=self.other.pk, status="published"))
        self.assertRedirects(response, reverse("listings:mine"))
        ad = Ad.objects.latest("pk")
        self.assertEqual(ad.owner, self.owner)
        self.assertEqual(ad.status, "pending")
        self.assertEqual(ad.phone, "09123456789")
        self.assertEqual(ad.price, 1200000)

    def test_invalid_phone_and_empty_fixed_price(self):
        form = AdForm(self.payload(phone="123", price=""))
        self.assertFalse(form.is_valid())
        self.assertIn("phone", form.errors)
        self.assertIn("price", form.errors)

    def test_zero_or_negative_fixed_price_is_invalid(self):
        for price in ("0", "-10"):
            with self.subTest(price=price):
                form = AdForm(self.payload(price=price))
                self.assertFalse(form.is_valid())
                self.assertIn("price", form.errors)

    def test_free_and_negotiable_price_rules(self):
        for kind, expected in (("free", 0), ("negotiable", None)):
            with self.subTest(kind=kind):
                form = AdForm(self.payload(price_type=kind, price=""))
                self.assertTrue(form.is_valid(), form.errors)
                self.assertEqual(form.cleaned_data["price"], expected)

    def test_edit_free_ad_works_without_javascript(self):
        self.login_owner()
        response = self.client.post(reverse("listings:edit", args=[self.ad.pk]), self.payload(price_type="free", price="0"))
        self.assertEqual(response.status_code, 302)
        self.ad.refresh_from_db()
        self.assertEqual(self.ad.price, 0)
        self.assertEqual(self.ad.price_type, "free")

    def test_price_rule_is_enforced_by_database(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            Ad.objects.filter(pk=self.ad.pk).update(price_type="fixed", price=None)

    def test_other_user_cannot_edit_delete_or_sell(self):
        self.client.force_login(self.other)
        for action in ("edit", "delete", "sold"):
            with self.subTest(action=action):
                response = self.client.post(reverse(f"listings:{action}", args=[self.ad.pk]), self.payload())
                self.assertEqual(response.status_code, 404)
        self.ad.refresh_from_db()
        self.assertEqual(self.ad.status, "published")
        self.assertEqual(self.ad.title, "لپ‌تاپ آموزشی سالم")

    def test_other_user_cannot_see_private_detail_or_contact(self):
        self.ad.status = "pending"
        self.ad.save()
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(self.ad.get_absolute_url()).status_code, 404)
        self.assertEqual(self.client.post(reverse("listings:contact", args=[self.ad.pk])).status_code, 404)
        self.login_owner()
        self.assertEqual(self.client.get(self.ad.get_absolute_url()).status_code, 200)

    def test_edit_resubmits_for_moderation(self):
        self.login_owner()
        response = self.client.post(reverse("listings:edit", args=[self.ad.pk]), self.payload(status="published"))
        self.assertRedirects(response, reverse("listings:mine"))
        self.ad.refresh_from_db()
        self.assertEqual(self.ad.status, "pending")
        self.client.logout()
        self.assertNotContains(self.client.get(reverse("listings:list")), self.ad.title)

    def test_delete_get_is_confirmation_only_and_post_deletes(self):
        self.login_owner()
        Bookmark.objects.create(user=self.other, ad=self.ad)
        response = self.client.get(reverse("listings:delete", args=[self.ad.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(Ad.objects.filter(pk=self.ad.pk).exists())
        self.assertRedirects(self.client.post(reverse("listings:delete", args=[self.ad.pk])), reverse("listings:mine"))
        self.assertFalse(Ad.objects.filter(pk=self.ad.pk).exists())
        self.assertEqual(Bookmark.objects.count(), 0)

    def test_sold_is_post_only_and_removed_from_public_list(self):
        self.login_owner()
        url = reverse("listings:sold", args=[self.ad.pk])
        self.assertEqual(self.client.get(url).status_code, 405)
        self.assertRedirects(self.client.post(url), reverse("listings:mine"))
        self.ad.refresh_from_db()
        self.assertEqual(self.ad.status, "sold")
        self.assertEqual(self.client.get(reverse("listings:list")).context["page_obj"].paginator.count, 0)

    def test_my_ads_are_isolated(self):
        self.client.force_login(self.other)
        response = self.client.get(reverse("listings:mine"))
        self.assertEqual(response.context["page_obj"].paginator.count, 0)

    def test_phone_is_hidden_until_authenticated_post(self):
        self.assertNotContains(self.client.get(self.ad.get_absolute_url()), self.ad.phone)
        url = reverse("listings:contact", args=[self.ad.pk])
        self.assertEqual(self.client.post(url).status_code, 302)
        self.client.force_login(self.other)
        self.assertNotContains(self.client.get(self.ad.get_absolute_url()), self.ad.phone)
        self.assertEqual(self.client.get(url).status_code, 405)
        response = self.client.post(url)
        self.assertContains(response, self.ad.phone)
        self.assertEqual(response["Cache-Control"], "private, no-store")

    def test_bookmark_toggle_and_private_status_hiding(self):
        self.client.force_login(self.other)
        url = reverse("listings:bookmark", args=[self.ad.pk])
        self.assertEqual(self.client.get(url).status_code, 405)
        self.client.post(url)
        self.assertEqual(Bookmark.objects.filter(user=self.other, ad=self.ad).count(), 1)
        self.assertContains(self.client.get(reverse("listings:bookmarks")), self.ad.title)
        self.ad.status = "sold"
        self.ad.save()
        self.assertNotContains(self.client.get(reverse("listings:bookmarks")), self.ad.title)
        self.assertEqual(self.client.post(url).status_code, 404)
        self.ad.status = "published"
        self.ad.save()
        self.client.post(url)
        self.assertEqual(Bookmark.objects.count(), 0)

    def test_bookmark_unique_constraint(self):
        Bookmark.objects.create(user=self.other, ad=self.ad)
        with self.assertRaises(IntegrityError), transaction.atomic():
            Bookmark.objects.create(user=self.other, ad=self.ad)

    def test_search_combines_city_category_text_and_persian_price(self):
        response = self.client.get(reverse("listings:list"), {"q": "آموزشی", "city": "tehran",
            "category": "digital", "min_price": "۹٬۰۰۰٬۰۰۰", "max_price": "۱۱٬۰۰۰٬۰۰۰"})
        self.assertEqual(response.context["page_obj"].paginator.count, 1)
        self.assertEqual(self.client.get(reverse("listings:list"), {"q": "وجودندارد"}).context["page_obj"].paginator.count, 0)

    def test_invalid_filters_show_errors_without_crashing(self):
        for query in ({"max_price": "wrong"}, {"city": "missing"},
            {"min_price": "100", "max_price": "50"}, {"sort": "unsafe"}):
            with self.subTest(query=query):
                response = self.client.get(reverse("listings:list"), query)
                self.assertEqual(response.status_code, 200)
                self.assertTrue(response.context["form"].errors)
                self.assertEqual(response.context["page_obj"].paginator.count, 0)

    def test_price_sort_places_negotiable_last(self):
        cheap = Ad.objects.create(owner=self.owner, category=self.category, city=self.city,
            title="کالای ارزان آزمایشی", description="توضیحات یک کالای ارزان برای آزمایش.",
            price_type="free", price=0, phone="09123456789", status="published")
        negotiable = Ad.objects.create(owner=self.owner, category=self.category, city=self.city,
            title="کالای توافقی آزمایشی", description="توضیحات یک کالای توافقی برای آزمایش.",
            price_type="negotiable", price=None, phone="09123456789", status="published")
        for sort, first in (("cheapest", cheap.pk), ("expensive", self.ad.pk)):
            response = self.client.get(reverse("listings:list"), {"sort": sort})
            ids = [ad.pk for ad in response.context["page_obj"]]
            self.assertEqual(ids[0], first)
            self.assertEqual(ids[-1], negotiable.pk)

    def test_pagination_preserves_search_and_handles_bad_page(self):
        Ad.objects.bulk_create([Ad(owner=self.owner, category=self.category, city=self.city,
            title=f"آموزشی شماره {i}", description="توضیحات یک آگهی برای آزمایش صفحه‌بندی.",
            price_type="free", price=0, phone="09123456789", status="published") for i in range(13)])
        response = self.client.get(reverse("listings:list"), {"q": "آموزشی", "page": "bad"})
        self.assertEqual(response.context["page_obj"].number, 1)
        self.assertEqual(len(response.context["page_obj"]), 12)
        self.assertContains(response, "q=")
        self.assertContains(response, "page=2")

    def test_uploaded_image_is_reencoded_and_saved(self):
        output = BytesIO()
        Image.new("RGB", (60, 40), "#a62626").save(output, format="PNG")
        upload = SimpleUploadedFile("../../unsafe.png", output.getvalue(), content_type="image/png")
        with tempfile.TemporaryDirectory() as directory, override_settings(MEDIA_ROOT=directory):
            self.login_owner()
            self.assertEqual(self.client.post(reverse("listings:create"), self.payload(image=upload)).status_code, 302)
            ad = Ad.objects.latest("pk")
            self.assertTrue(ad.image.name.startswith("ads/"))
            self.assertTrue(ad.image.name.endswith(".jpg"))
            self.assertNotIn("unsafe", ad.image.name)
            with ad.image.open("rb") as file, Image.open(file) as image:
                self.assertEqual(image.format, "JPEG")

    def test_fake_image_is_rejected(self):
        upload = SimpleUploadedFile("fake.jpg", b"<script>alert(1)</script>", content_type="image/jpeg")
        form = AdForm(self.payload(), {"image": upload})
        self.assertFalse(form.is_valid())
        self.assertIn("image", form.errors)

    def test_oversized_image_is_rejected(self):
        output = BytesIO()
        Image.new("RGB", (10, 10), "white").save(output, format="PNG")
        upload = SimpleUploadedFile("large.png", output.getvalue() + b"0" * (3 * 1024 * 1024), content_type="image/png")
        form = AdForm(self.payload(), {"image": upload})
        self.assertFalse(form.is_valid())
        self.assertIn("image", form.errors)

    def test_mutations_require_csrf(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.owner)
        for action in ("create", "edit", "delete", "sold", "bookmark", "contact"):
            args = [] if action == "create" else [self.ad.pk]
            with self.subTest(action=action):
                self.assertEqual(client.post(reverse(f"listings:{action}", args=args), self.payload()).status_code, 403)

    def test_user_content_is_escaped_in_detail(self):
        self.ad.description = '<script>alert("XSS")</script> این متن برای آزمایش فراردهی است.'
        self.ad.save()
        response = self.client.get(self.ad.get_absolute_url())
        self.assertNotContains(response, '<script>alert("XSS")</script>')
        self.assertContains(response, "&lt;script&gt;")

    def test_admin_can_moderate_and_regular_user_cannot(self):
        self.ad.status = "pending"
        self.ad.save()
        url = reverse("admin:listings_ad_changelist")
        self.login_owner()
        self.assertEqual(self.client.get(url).status_code, 302)
        self.client.force_login(self.staff)
        self.assertEqual(self.client.get(reverse("admin:listings_ad_change", args=[self.ad.pk])).status_code, 200)
        self.client.post(url, {"action": "publish_ads", "_selected_action": [self.ad.pk]})
        self.ad.refresh_from_db()
        self.assertEqual(self.ad.status, "published")
        self.client.post(url, {"action": "reject_ads", "_selected_action": [self.ad.pk]})
        self.ad.refresh_from_db()
        self.assertEqual(self.ad.status, "rejected")


class DemoCommandTests(TestCase):
    @override_settings(DEBUG=True)
    def test_seed_is_repeatable_and_preserves_password_and_ad_edits(self):
        call_command("seed_demo", stdout=StringIO())
        count = Ad.objects.count()
        user = get_user_model().objects.get(username="demo")
        self.assertFalse(user.is_staff)
        self.assertTrue(user.check_password("Demo12345!"))
        user.set_password("Changed-6428!")
        user.save()
        ad = Ad.objects.first()
        ad.description = "توضیحات ویرایش‌شده که نباید در اجرای بعدی از بین برود."
        ad.save()
        call_command("seed_demo", stdout=StringIO())
        self.assertEqual(Ad.objects.count(), count)
        user.refresh_from_db()
        ad.refresh_from_db()
        self.assertTrue(user.check_password("Changed-6428!"))
        self.assertIn("ویرایش‌شده", ad.description)

    @override_settings(DEBUG=False)
    def test_seed_refuses_production_settings(self):
        from django.core.management.base import CommandError
        with self.assertRaises(CommandError):
            call_command("seed_demo", stdout=StringIO())

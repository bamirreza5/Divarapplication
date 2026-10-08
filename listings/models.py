from pathlib import Path
from uuid import uuid4

from django.conf import settings
from django.core.validators import MaxValueValidator, MinLengthValidator, RegexValidator
from django.db import models
from django.urls import reverse

MAX_PRICE = 999_999_999_999
phone_validator = RegexValidator(r"^09[0-9]{9}$", "شماره همراه را با ۰۹ و در ۱۱ رقم وارد کنید.")


def ad_image_path(instance, filename):
    # Random names prevent filename collisions and revealing original filenames.
    extension = Path(filename).suffix.lower()
    return f"ads/{uuid4().hex}{extension}"


class Category(models.Model):
    name = models.CharField("عنوان", max_length=60, unique=True)
    slug = models.SlugField("شناسه", unique=True)
    icon = models.CharField("نماد", max_length=5, default="◇")

    class Meta:
        ordering = ["id"]
        verbose_name = "دسته‌بندی"
        verbose_name_plural = "دسته‌بندی‌ها"

    def __str__(self):
        return self.name


class City(models.Model):
    name = models.CharField("نام شهر", max_length=60, unique=True)
    slug = models.SlugField("شناسه", unique=True)

    class Meta:
        ordering = ["id"]
        verbose_name = "شهر"
        verbose_name_plural = "شهرها"

    def __str__(self):
        return self.name


class Ad(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "در انتظار تأیید"
        PUBLISHED = "published", "منتشرشده"
        REJECTED = "rejected", "ردشده"
        SOLD = "sold", "فروخته‌شده"

    class PriceType(models.TextChoices):
        FIXED = "fixed", "قیمت مشخص"
        NEGOTIABLE = "negotiable", "توافقی"
        FREE = "free", "رایگان"

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="ads", verbose_name="آگهی‌دهنده")
    category = models.ForeignKey(Category, on_delete=models.PROTECT,
        related_name="ads", verbose_name="دسته‌بندی")
    city = models.ForeignKey(City, on_delete=models.PROTECT, related_name="ads", verbose_name="شهر")
    title = models.CharField("عنوان آگهی", max_length=120, validators=[MinLengthValidator(5)])
    description = models.TextField("توضیحات", max_length=5000, validators=[MinLengthValidator(20)])
    district = models.CharField("محله", max_length=80, blank=True)
    price_type = models.CharField("نوع قیمت", max_length=12,
        choices=PriceType.choices, default=PriceType.FIXED)
    price = models.PositiveBigIntegerField("قیمت (تومان)", blank=True, null=True,
        validators=[MaxValueValidator(MAX_PRICE)])
    phone = models.CharField("شماره تماس", max_length=11, validators=[phone_validator])
    image = models.ImageField("تصویر آگهی", upload_to=ad_image_path, blank=True)
    status = models.CharField("وضعیت", max_length=12, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField("زمان ثبت", auto_now_add=True)
    updated_at = models.DateTimeField("آخرین تغییر", auto_now=True)

    class Meta:
        ordering = ["-created_at", "-pk"]
        verbose_name = "آگهی"
        verbose_name_plural = "آگهی‌ها"
        indexes = [
            models.Index(fields=["status", "-created_at"], name="ad_status_date_idx"),
            models.Index(fields=["city", "category", "status"], name="ad_filter_idx"),
        ]
        constraints = [models.CheckConstraint(
            condition=(
                models.Q(price_type="fixed", price__gt=0, price__lte=MAX_PRICE)
                & models.Q(price__isnull=False)
                | models.Q(price_type="negotiable", price__isnull=True)
                | models.Q(price_type="free", price=0) & models.Q(price__isnull=False)
            ), name="ad_price_matches_type",
        )]

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("listings:detail", args=[self.pk])


class Bookmark(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="bookmarks", verbose_name="کاربر")
    ad = models.ForeignKey(Ad, on_delete=models.CASCADE, related_name="bookmarks", verbose_name="آگهی")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["user", "ad"], name="unique_user_ad_bookmark")]
        verbose_name = "نشان"
        verbose_name_plural = "نشان‌ها"

    def __str__(self):
        return f"{self.user} / {self.ad}"

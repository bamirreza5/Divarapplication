from django.contrib import admin
from django.utils import timezone

from .forms import AdForm
from .models import Ad, Bookmark, Category, City

admin.site.site_header = "مدیریت دیوارک"
admin.site.site_title = "دیوارک"
admin.site.index_title = "مدیریت آگهی‌ها و دسته‌بندی‌ها"


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "icon")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(City)
class CityAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Ad)
class AdAdmin(admin.ModelAdmin):
    form = AdForm
    fields = ("owner", "title", "category", "city", "district", "price_type", "price",
        "description", "phone", "image", "status", "created_at", "updated_at")
    list_display = ("title", "owner", "category", "city", "price_type", "price", "status", "created_at")
    list_filter = ("status", "category", "city", "price_type")
    search_fields = ("title", "description", "owner__username")
    readonly_fields = ("created_at", "updated_at")
    list_select_related = ("owner", "category", "city")
    actions = ("publish_ads", "reject_ads")

    @admin.action(description="تأیید و انتشار آگهی‌های در انتظار یا ردشده")
    def publish_ads(self, request, queryset):
        count = queryset.filter(status__in=[Ad.Status.PENDING, Ad.Status.REJECTED]).update(
            status=Ad.Status.PUBLISHED, updated_at=timezone.now())
        self.message_user(request, f"{count} آگهی منتشر شد.")

    @admin.action(description="رد آگهی‌های در انتظار یا منتشرشده")
    def reject_ads(self, request, queryset):
        count = queryset.filter(status__in=[Ad.Status.PENDING, Ad.Status.PUBLISHED]).update(
            status=Ad.Status.REJECTED, updated_at=timezone.now())
        self.message_user(request, f"{count} آگهی رد شد.")


@admin.register(Bookmark)
class BookmarkAdmin(admin.ModelAdmin):
    list_display = ("user", "ad", "created_at")
    list_select_related = ("user", "ad")

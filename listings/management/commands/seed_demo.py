from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from listings.models import Ad, Category, City


class Command(BaseCommand):
    help = "Create local demo categories, cities, a non-admin user, and ads (repeatable)."

    def add_arguments(self, parser):
        parser.add_argument("--username", default="demo")
        parser.add_argument("--password", default="Demo12345!")

    @transaction.atomic
    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError("Demo data is only allowed with DJANGO_DEBUG=true.")
        categories = {}
        for slug, name, icon in [
            ("property", "املاک", "⌂"), ("vehicles", "وسایل نقلیه", "↗"),
            ("digital", "کالای دیجیتال", "▣"), ("home", "خانه و آشپزخانه", "◈"),
            ("personal", "وسایل شخصی", "◇"), ("leisure", "سرگرمی و فراغت", "✳"),
            ("services", "خدمات", "⚒"), ("jobs", "استخدام", "▤"),
        ]:
            categories[slug], _ = Category.objects.get_or_create(slug=slug, defaults={"name": name, "icon": icon})
        cities = {}
        for slug, name in [("tehran", "تهران"), ("karaj", "کرج"), ("shiraz", "شیراز"),
            ("isfahan", "اصفهان"), ("mashhad", "مشهد"), ("tabriz", "تبریز")]:
            cities[slug], _ = City.objects.get_or_create(slug=slug, defaults={"name": name})
        user, created = get_user_model().objects.get_or_create(username=options["username"], defaults={"first_name": "کاربر نمونه"})
        if created:
            user.set_password(options["password"])
            user.save()
        # All contact numbers are placeholders. They are never real seller contacts.
        samples = [
            ("دوچرخه شهری سایز ۲۶، بسیار تمیز", "leisure", "tehran", "یوسف‌آباد", "fixed", 8500000),
            ("مبل راحتی هفت‌نفره با پارچه خاکستری", "home", "tehran", "پونک", "fixed", 24000000),
            ("دوربین عکاسی همراه با لنز و کیف", "digital", "shiraz", "معالی‌آباد", "fixed", 18500000),
            ("اجاره آپارتمان روشن ۸۵ متری", "property", "tehran", "سعادت‌آباد", "negotiable", None),
            ("خودروی کم‌کارکرد، مدل ۱۴۰۰", "vehicles", "karaj", "گوهردشت", "fixed", 650000000),
            ("گیتار کلاسیک مناسب شروع یادگیری", "leisure", "tehran", "صادقیه", "fixed", 4200000),
            ("میز کار چوبی با دو کشو", "home", "isfahan", "مرداویج", "fixed", 3200000),
            ("کتاب‌های داستان؛ واگذاری رایگان", "leisure", "mashhad", "سجاد", "free", 0),
            ("کفش ورزشی نو، سایز ۴۲", "personal", "tabriz", "ولیعصر", "fixed", 1900000),
            ("تعمیر و سرویس لوازم خانگی", "services", "tehran", "نارمک", "negotiable", None),
            ("همکاری با برنامه‌نویس پایتون", "jobs", "tehran", "ونک", "negotiable", None),
            ("لپ‌تاپ سبک مناسب کار و دانشگاه", "digital", "karaj", "عظیمیه", "fixed", 32000000),
            ("چراغ مطالعه سالم و کم‌مصرف", "home", "tehran", "تهرانپارس", "fixed", 650000),
        ]
        for title, category, city, district, kind, price in samples:
            Ad.objects.get_or_create(owner=user, title=title, defaults={
                "category": categories[category], "city": cities[city], "district": district,
                "price_type": kind, "price": price, "phone": "09000000000",
                "description": "این یک آگهی ساختگی برای تمرین پروژه است. مشخصات، قیمت و شماره تماس صرفاً نمونه آموزشی هستند و برای معامله واقعی استفاده نمی‌شوند.",
                "status": Ad.Status.PUBLISHED,
            })
        self.stdout.write(self.style.SUCCESS("Demo data is ready. Existing records/passwords were preserved."))
        if created:
            self.stdout.write(f"Local demo username: {user.username}; password: as supplied (default Demo12345!)")

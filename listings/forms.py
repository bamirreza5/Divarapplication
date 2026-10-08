from io import BytesIO

from PIL import Image, ImageOps, UnidentifiedImageError
from django import forms
from django.core.files.uploadedfile import SimpleUploadedFile, UploadedFile

from .models import Ad, Category, City, MAX_PRICE
from .utils import normalize_digits, normalize_phone


class PersianIntegerField(forms.IntegerField):
    def to_python(self, value):
        if value not in self.empty_values:
            value = normalize_digits(value).replace(",", "").replace("٬", "")
        return super().to_python(value)


class AdForm(forms.ModelForm):
    price = PersianIntegerField(label="قیمت (تومان)", required=False, min_value=0,
        max_value=MAX_PRICE, widget=forms.TextInput(attrs={
            "inputmode": "numeric", "placeholder": "مثلاً ۱۲٬۰۰۰٬۰۰۰",
        }))
    phone = forms.CharField(label="شماره تماس", max_length=20, widget=forms.TextInput(attrs={
        "inputmode": "tel", "dir": "ltr", "placeholder": "09123456789",
    }))

    class Meta:
        model = Ad
        # owner/status must never be taken from user-submitted form data.
        fields = ["title", "category", "city", "district", "price_type", "price",
            "description", "phone", "image"]
        widgets = {
            "title": forms.TextInput(attrs={"placeholder": "مثلاً دوچرخه شهری سالم، سایز ۲۶"}),
            "district": forms.TextInput(attrs={"placeholder": "مثلاً یوسف‌آباد"}),
            "description": forms.Textarea(attrs={"rows": 6, "placeholder": "وضعیت کالا، ویژگی‌ها و شرایط فروش را بنویسید."}),
            "image": forms.ClearableFileInput(attrs={"accept": "image/jpeg,image/png,image/webp"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["image"].help_text = "یک عکس JPEG، PNG یا WebP؛ حداکثر ۳ مگابایت."
        self.fields["phone"].help_text = "شماره شما فقط پس از ورود و درخواست تماس نمایش داده می‌شود."
        self.fields["category"].empty_label = "انتخاب دسته‌بندی"
        self.fields["city"].empty_label = "انتخاب شهر"
        self.fields["price"].help_text = "برای قیمت مشخص، مبلغ را به تومان وارد کنید."

    def clean_title(self):
        return self.cleaned_data["title"].strip()

    def clean_phone(self):
        # ModelForm's model validation will apply phone_validator afterward.
        return normalize_phone(self.cleaned_data["phone"])

    def clean_image(self):
        upload = self.cleaned_data.get("image")
        if not upload or not isinstance(upload, UploadedFile):
            return upload  # unchanged FieldFile, no image, or clear-checkbox
        if upload.size > 3 * 1024 * 1024:
            raise forms.ValidationError("حجم عکس باید کمتر از ۳ مگابایت باشد.")
        try:
            upload.seek(0)
            with Image.open(upload) as source:
                if source.format not in {"JPEG", "PNG", "WEBP"}:
                    raise forms.ValidationError("فقط عکس JPEG، PNG یا WebP پذیرفته می‌شود.")
                if source.width * source.height > 16_000_000:
                    raise forms.ValidationError("ابعاد عکس بیش از حد بزرگ است؛ عکس کوچک‌تری انتخاب کنید.")
                source.load()
                image = ImageOps.exif_transpose(source).convert("RGB")
                image.thumbnail((1600, 1600))
                output = BytesIO()
                # Re-encoding drops metadata and ignores the uploaded filename.
                image.save(output, format="JPEG", quality=85)
            return SimpleUploadedFile("photo.jpg", output.getvalue(), content_type="image/jpeg")
        except (OSError, UnidentifiedImageError, Image.DecompressionBombError, Image.DecompressionBombWarning):
            raise forms.ValidationError("فایل انتخاب‌شده یک عکس معتبر نیست.")

    def clean(self):
        cleaned = super().clean()
        kind = cleaned.get("price_type")
        if kind == Ad.PriceType.FIXED and not cleaned.get("price") and "price" not in self.errors:
            self.add_error("price", "برای قیمت مشخص، مبلغی بیشتر از صفر وارد کنید.")
        elif kind == Ad.PriceType.NEGOTIABLE:
            cleaned["price"] = None
        elif kind == Ad.PriceType.FREE:
            cleaned["price"] = 0
        return cleaned


class SearchForm(forms.Form):
    q = forms.CharField(label="جست‌وجو", required=False, max_length=120,
        widget=forms.TextInput(attrs={"placeholder": "دنبال چی می‌گردید؟", "type": "search"}))
    category = forms.ModelChoiceField(label="دسته‌بندی", queryset=Category.objects.all(),
        required=False, empty_label="همه دسته‌ها", to_field_name="slug")
    city = forms.ModelChoiceField(label="شهر", queryset=City.objects.all(), required=False,
        empty_label="همه شهرها", to_field_name="slug")
    min_price = PersianIntegerField(label="از قیمت (تومان)", required=False, min_value=0,
        max_value=MAX_PRICE, widget=forms.TextInput(attrs={"inputmode": "numeric", "placeholder": "حداقل"}))
    max_price = PersianIntegerField(label="تا قیمت (تومان)", required=False, min_value=0,
        max_value=MAX_PRICE, widget=forms.TextInput(attrs={"inputmode": "numeric", "placeholder": "حداکثر"}))
    sort = forms.ChoiceField(label="مرتب‌سازی", required=False, initial="newest", choices=[
        ("newest", "جدیدترین"), ("cheapest", "ارزان‌ترین"), ("expensive", "گران‌ترین"),
    ])

    def clean(self):
        cleaned = super().clean()
        low, high = cleaned.get("min_price"), cleaned.get("max_price")
        if low is not None and high is not None and low > high:
            raise forms.ValidationError("حداقل قیمت نمی‌تواند از حداکثر بیشتر باشد.")
        return cleaned

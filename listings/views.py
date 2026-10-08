"""Function-based views: follow each request from URL to form/query to template."""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q, F
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods, require_POST

from .forms import AdForm, SearchForm
from .models import Ad, Bookmark, Category


def public_ads():
    return Ad.objects.filter(status=Ad.Status.PUBLISHED).select_related("category", "city", "owner")


def visible_ad(request, pk):
    # Private statuses are visible only to the owner on the public website.
    visibility = Q(status=Ad.Status.PUBLISHED)
    if request.user.is_authenticated:
        visibility |= Q(owner=request.user)
    return get_object_or_404(Ad.objects.select_related("category", "city", "owner").filter(visibility), pk=pk)


@require_http_methods(["GET"])
def ad_list(request):
    form = SearchForm(request.GET)
    ads = public_ads()
    if form.is_valid():
        data = form.cleaned_data
        if data["q"]:
            ads = ads.filter(Q(title__icontains=data["q"]) | Q(description__icontains=data["q"]))
        for field in ("category", "city"):
            if data[field]:
                ads = ads.filter(**{field: data[field]})
        for field, lookup in (("min_price", "gte"), ("max_price", "lte")):
            if data[field] is not None:
                # A negotiable price is NULL and deliberately excluded from numeric ranges.
                ads = ads.filter(**{f"price__{lookup}": data[field]})
        if data["sort"] == "cheapest":
            ads = ads.order_by(F("price").asc(nulls_last=True), "-pk")
        elif data["sort"] == "expensive":
            ads = ads.order_by(F("price").desc(nulls_last=True), "-pk")
    else:
        ads = ads.none()  # Invalid query values never produce unfiltered results.
    page = Paginator(ads, 12).get_page(request.GET.get("page"))
    return render(request, "listings/list.html", {
        "form": form, "page_obj": page, "categories": Category.objects.all(),
    })


def detail_context(request, ad, show_contact=False):
    bookmarked = request.user.is_authenticated and Bookmark.objects.filter(user=request.user, ad=ad).exists()
    return {"ad": ad, "is_bookmarked": bookmarked, "show_contact": show_contact,
        "related_ads": public_ads().filter(category=ad.category).exclude(pk=ad.pk)[:3]}


@require_http_methods(["GET"])
def ad_detail(request, pk):
    ad = visible_ad(request, pk)
    return render(request, "listings/detail.html", detail_context(request, ad))


@login_required
@require_POST
def contact(request, pk):
    ad = visible_ad(request, pk)
    response = render(request, "listings/detail.html", detail_context(request, ad, show_contact=True))
    response["Cache-Control"] = "private, no-store"
    return response


@login_required
@require_http_methods(["GET", "POST"])
def ad_create(request):
    form = AdForm(request.POST if request.method == "POST" else None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        ad = form.save(commit=False)
        ad.owner = request.user
        ad.status = Ad.Status.PENDING
        ad.save()
        messages.success(request, "آگهی ثبت شد و پس از تأیید مدیر منتشر می‌شود.")
        return redirect("listings:mine")
    return render(request, "listings/form.html", {"form": form, "is_edit": False})


@login_required
@require_http_methods(["GET", "POST"])
def ad_edit(request, pk):
    ad = get_object_or_404(Ad, pk=pk, owner=request.user)
    form = AdForm(request.POST if request.method == "POST" else None, request.FILES or None, instance=ad)
    if request.method == "POST" and form.is_valid():
        ad = form.save(commit=False)
        ad.status = Ad.Status.PENDING  # Re-review edited published, rejected or sold ads.
        ad.save()
        messages.success(request, "تغییرات ذخیره شد؛ آگهی دوباره در انتظار تأیید است.")
        return redirect("listings:mine")
    return render(request, "listings/form.html", {"form": form, "is_edit": True, "ad": ad})


@login_required
@require_http_methods(["GET", "POST"])
def ad_delete(request, pk):
    ad = get_object_or_404(Ad, pk=pk, owner=request.user)
    if request.method == "POST":
        ad.delete()
        messages.success(request, "آگهی حذف شد.")
        return redirect("listings:mine")
    return render(request, "listings/delete.html", {"ad": ad})


@login_required
@require_POST
def mark_sold(request, pk):
    ad = get_object_or_404(Ad, pk=pk, owner=request.user, status=Ad.Status.PUBLISHED)
    ad.status = Ad.Status.SOLD
    ad.save(update_fields=["status", "updated_at"])
    messages.success(request, "آگهی فروخته‌شده شد و از فهرست عمومی کنار رفت.")
    return redirect("listings:mine")


@login_required
@require_http_methods(["GET"])
def my_ads(request):
    ads = Ad.objects.filter(owner=request.user).select_related("category", "city")
    return render(request, "listings/mine.html", {"page_obj": Paginator(ads, 10).get_page(request.GET.get("page"))})


@login_required
@require_POST
def toggle_bookmark(request, pk):
    ad = get_object_or_404(public_ads(), pk=pk)
    bookmark, created = Bookmark.objects.get_or_create(user=request.user, ad=ad)
    if not created:
        bookmark.delete()
    messages.success(request, "آگهی نشان شد." if created else "نشان آگهی برداشته شد.")
    return redirect("listings:detail", pk=ad.pk)


@login_required
@require_http_methods(["GET"])
def bookmarks(request):
    ads = public_ads().filter(bookmarks__user=request.user).order_by("-bookmarks__created_at", "-pk")
    return render(request, "listings/bookmarks.html", {"page_obj": Paginator(ads, 12).get_page(request.GET.get("page"))})

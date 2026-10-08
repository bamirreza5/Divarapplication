from django.urls import path
from . import views

app_name = "listings"
urlpatterns = [
    path("", views.ad_list, name="list"),
    path("ads/new/", views.ad_create, name="create"),
    path("my-ads/", views.my_ads, name="mine"),
    path("bookmarks/", views.bookmarks, name="bookmarks"),
    path("ads/<int:pk>/", views.ad_detail, name="detail"),
    path("ads/<int:pk>/edit/", views.ad_edit, name="edit"),
    path("ads/<int:pk>/delete/", views.ad_delete, name="delete"),
    path("ads/<int:pk>/sold/", views.mark_sold, name="sold"),
    path("ads/<int:pk>/bookmark/", views.toggle_bookmark, name="bookmark"),
    path("ads/<int:pk>/contact/", views.contact, name="contact"),
]

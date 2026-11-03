from django.urls import include, path

from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("act-as/<str:user_id>/", views.act_as, name="act-as"),
    path("preferences/", views.preferences, name="preferences"),
    path("offers/send/", views.send_offer, name="send-offer"),
    path("offers/digest/", views.DigestView.as_view(), name="digest"),
    path("dpdp/", include("dpdpkit.django.urls")),
]

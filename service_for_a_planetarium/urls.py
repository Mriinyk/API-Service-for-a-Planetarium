from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .views import (
    AstronomyShowViewSet,
    PlanetariumDomeViewSet,
    RegisterView,
    ReservationViewSet,
    ShowSessionViewSet,
    ShowThemeViewSet,
)

router = DefaultRouter()
router.register("themes", ShowThemeViewSet)
router.register("astronomy-shows", AstronomyShowViewSet)
router.register("domes", PlanetariumDomeViewSet)
router.register("sessions", ShowSessionViewSet)
router.register("reservations", ReservationViewSet, basename="reservation")

urlpatterns = [
    path("auth/register/", RegisterView.as_view(), name="register"),
    path("auth/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("", include(router.urls)),
]

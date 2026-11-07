from django.contrib.auth import get_user_model
from django.db.models import Count
from rest_framework import generics, viewsets
from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticated

from service_for_a_planetarium.models import (
    AstronomyShow,
    PlanetariumDome,
    Reservation,
    ShowSession,
    ShowTheme,
)
from service_for_a_planetarium.serializers import (
    AstronomyShowSerializer,
    PlanetariumDomeSerializer,
    ReservationSerializer,
    ShowSessionSerializer,
    ShowThemeSerializer,
    UserSerializer,
)


class RegisterView(generics.CreateAPIView):
    queryset = get_user_model().objects.all()
    serializer_class = UserSerializer
    permission_classes = (AllowAny,)


class ReadOnlyOrAdmin(viewsets.ModelViewSet):
    ordering = ("id",)

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [AllowAny()]
        return [IsAdminUser()]


class ShowThemeViewSet(ReadOnlyOrAdmin):
    queryset = ShowTheme.objects.all()
    serializer_class = ShowThemeSerializer


class AstronomyShowViewSet(ReadOnlyOrAdmin):
    queryset = AstronomyShow.objects.prefetch_related("themes")
    serializer_class = AstronomyShowSerializer
    search_fields = ("title", "description")
    filterset_fields = ("themes",)


class PlanetariumDomeViewSet(ReadOnlyOrAdmin):
    queryset = PlanetariumDome.objects.all()
    serializer_class = PlanetariumDomeSerializer


class ShowSessionViewSet(ReadOnlyOrAdmin):
    queryset = ShowSession.objects.select_related("astronomy_show", "planetarium_dome").annotate(
        _ticket_count=Count("tickets")
    )
    serializer_class = ShowSessionSerializer
    filterset_fields = ("astronomy_show", "planetarium_dome", "show_time")
    ordering_fields = ("show_time",)
    ordering = ("show_time",)


class ReservationViewSet(viewsets.ModelViewSet):
    queryset = Reservation.objects.all()
    serializer_class = ReservationSerializer
    permission_classes = (IsAuthenticated,)
    http_method_names = ("get", "post", "head", "options", "delete")

    def get_queryset(self):
        queryset = Reservation.objects.prefetch_related(
            "tickets__show_session"
        ).order_by("id")
        if self.request.user.is_staff:
            return queryset
        return queryset.filter(user=self.request.user)

from django.contrib import admin

from service_for_a_planetarium.models import (
    AstronomyShow,
    PlanetariumDome,
    Reservation,
    ShowSession,
    ShowTheme,
    Ticket,
)


@admin.register(AstronomyShow)
class AstronomyShowAdmin(admin.ModelAdmin):
    list_display = ("title",)
    search_fields = ("title",)
    filter_horizontal = ("themes",)


@admin.register(ShowTheme)
class ShowThemeAdmin(admin.ModelAdmin):
    search_fields = ("name",)


@admin.register(PlanetariumDome)
class PlanetariumDomeAdmin(admin.ModelAdmin):
    list_display = ("name", "rows", "seats_in_row")


@admin.register(ShowSession)
class ShowSessionAdmin(admin.ModelAdmin):
    list_display = ("astronomy_show", "planetarium_dome", "show_time")
    list_filter = ("planetarium_dome",)
    search_fields = ("astronomy_show__title", "planetarium_dome__name")


@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "created_at")
    readonly_fields = ("created_at",)


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ("show_session", "row", "seat", "reservation")

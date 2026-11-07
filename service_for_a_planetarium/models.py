from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q
from django.utils import timezone


class ShowTheme(models.Model):
    name = models.CharField(max_length=255, unique=True)

    def __str__(self):
        return self.name


class AstronomyShow(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField()
    themes = models.ManyToManyField(ShowTheme, related_name="shows", blank=True)

    def __str__(self):
        return self.title


class PlanetariumDome(models.Model):
    name = models.CharField(max_length=255, unique=True)
    rows = models.PositiveSmallIntegerField(validators=[MinValueValidator(1)])
    seats_in_row = models.PositiveSmallIntegerField(validators=[MinValueValidator(1)])

    @property
    def capacity(self):
        return self.rows * self.seats_in_row

    def __str__(self):
        return self.name


class ShowSession(models.Model):
    astronomy_show = models.ForeignKey(
        AstronomyShow, on_delete=models.CASCADE, related_name="sessions"
    )
    planetarium_dome = models.ForeignKey(
        PlanetariumDome, on_delete=models.CASCADE, related_name="sessions"
    )
    show_time = models.DateTimeField()

    def clean(self):
        super().clean()
        if self.show_time and self.show_time <= timezone.now():
            raise ValidationError(
                {"show_time": "Session must be scheduled in the future."}
            )

    class Meta:
        ordering = ["show_time"]

    def __str__(self):
        return f"{self.astronomy_show} at {self.show_time}"


class Reservation(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reservations"
    )

    def __str__(self):
        return f"Reservation #{self.pk} by {self.user}"


class Ticket(models.Model):
    row = models.PositiveSmallIntegerField(validators=[MinValueValidator(1)])
    seat = models.PositiveSmallIntegerField(validators=[MinValueValidator(1)])
    show_session = models.ForeignKey(
        ShowSession, on_delete=models.CASCADE, related_name="tickets"
    )
    reservation = models.ForeignKey(
        Reservation, on_delete=models.CASCADE, related_name="tickets"
    )

    class Meta:
        constraints = [
            models.CheckConstraint(condition=Q(row__gte=1), name="ticket_row_gte_1"),
            models.CheckConstraint(condition=Q(seat__gte=1), name="ticket_seat_gte_1"),
            models.UniqueConstraint(
                fields=["show_session", "row", "seat"], name="unique_seat_per_session"
            )
        ]

    def clean(self):
        super().clean()
        errors = {}
        if self.show_session_id:
            dome = self.show_session.planetarium_dome
            if self.row is not None and not 1 <= self.row <= dome.rows:
                errors["row"] = "Row must be within the dome's row count."
            if self.seat is not None and not 1 <= self.seat <= dome.seats_in_row:
                errors["seat"] = "Seat must be within the dome's seat count."
            if self.show_session.show_time <= timezone.now():
                errors["show_session"] = "Tickets can only be booked for future sessions."
        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return f"{self.show_session}: row {self.row}, seat {self.seat}"

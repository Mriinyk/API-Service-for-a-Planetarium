from datetime import timedelta
from types import SimpleNamespace

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Count
from django.test import TestCase
from django.utils import timezone
from rest_framework import serializers
from rest_framework.test import APIClient

from service_for_a_planetarium.models import (
    AstronomyShow,
    PlanetariumDome,
    Reservation,
    ShowSession,
    ShowTheme,
    Ticket,
)
from service_for_a_planetarium.serializers import (
    AstronomyShowSerializer,
    PlanetariumDomeSerializer,
    ReservationSerializer,
    ShowSessionSerializer,
    TicketSerializer,
    UserSerializer,
)

User = get_user_model()


class PlanetariumFixtureMixin:
    def create_planetarium_data(self, *, show_time=None):
        self.theme = ShowTheme.objects.create(name="Solar system")
        self.astronomy_show = AstronomyShow.objects.create(
            title="Journey through space", description="A tour of the planets."
        )
        self.astronomy_show.themes.add(self.theme)
        self.dome = PlanetariumDome.objects.create(
            name="Main dome", rows=3, seats_in_row=4
        )
        self.session = ShowSession.objects.create(
            astronomy_show=self.astronomy_show,
            planetarium_dome=self.dome,
            show_time=show_time or timezone.now() + timedelta(days=1),
        )

    def reservation_payload(self, *seats, session=None):
        session = session or self.session
        return {
            "tickets": [
                {"row": row, "seat": seat, "show_session": session.pk}
                for row, seat in seats
            ]
        }


class SerializerTests(PlanetariumFixtureMixin, TestCase):
    def setUp(self):
        self.create_planetarium_data()
        self.user = User.objects.create_user(
            username="viewer", password="safe-password-123"
        )

    def test_user_serializer_hashes_password(self):
        serializer = UserSerializer(
            data={"username": "new-viewer", "email": "viewer@example.com", "password": "safe-password-123"}
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        user = serializer.save()
        self.assertTrue(user.check_password("safe-password-123"))
        self.assertNotEqual(user.password, "safe-password-123")

    def test_user_serializer_enforces_django_password_validators(self):
        serializer = UserSerializer(
            data={"username": "new-viewer", "password": "password"}
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("password", serializer.errors)

    def test_show_serializer_reads_themes_and_accepts_theme_ids(self):
        data = AstronomyShowSerializer(self.astronomy_show).data
        self.assertEqual(data["themes"][0]["name"], self.theme.name)

        serializer = AstronomyShowSerializer(
            data={"title": "New show", "description": "Description", "theme_ids": [self.theme.pk]}
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(list(serializer.validated_data["themes"]), [self.theme])

    def test_dome_serializer_exposes_capacity(self):
        self.assertEqual(PlanetariumDomeSerializer(self.dome).data["capacity"], 12)

    def test_session_serializer_uses_annotated_ticket_count_without_extra_queries(self):
        session = ShowSession.objects.select_related(
            "astronomy_show", "planetarium_dome"
        ).annotate(_ticket_count=Count("tickets")).get(pk=self.session.pk)
        with self.assertNumQueries(0):
            data = ShowSessionSerializer(session).data
        self.assertEqual(data["available_seats"], 12)

    def test_ticket_serializer_rejects_seat_outside_dome(self):
        serializer = TicketSerializer(
            data={"row": 4, "seat": 1, "show_session": self.session.pk}
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("does not exist", str(serializer.errors))

    def test_ticket_serializer_rejects_past_session(self):
        past_session = ShowSession.objects.create(
            astronomy_show=self.astronomy_show,
            planetarium_dome=self.dome,
            show_time=timezone.now() - timedelta(days=1),
        )
        serializer = TicketSerializer(
            data={"row": 1, "seat": 1, "show_session": past_session.pk}
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("future sessions", str(serializer.errors))

    def test_ticket_serializer_rejects_already_booked_seat(self):
        reservation = Reservation.objects.create(user=self.user)
        Ticket.objects.create(
            row=1, seat=1, show_session=self.session, reservation=reservation
        )
        serializer = TicketSerializer(
            data={"row": 1, "seat": 1, "show_session": self.session.pk}
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("already been booked", str(serializer.errors))

    def test_reservation_serializer_rejects_empty_ticket_list(self):
        serializer = ReservationSerializer(data={"tickets": []})
        self.assertTrue(serializer.is_valid(), serializer.errors)
        request = type("Request", (), {"user": self.user})()
        with self.assertRaises(serializers.ValidationError):
            serializer.save(request=request)

    def test_reservation_serializer_rejects_duplicate_seats_in_payload(self):
        serializer = ReservationSerializer(
            data=self.reservation_payload((1, 1), (1, 1))
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        request = type("Request", (), {"user": self.user})()
        with self.assertRaises(serializers.ValidationError):
            serializer.save(request=request)
        self.assertEqual(Reservation.objects.count(), 0)

    def test_reservation_serializer_rejects_multiple_sessions(self):
        other_session = ShowSession.objects.create(
            astronomy_show=self.astronomy_show,
            planetarium_dome=self.dome,
            show_time=timezone.now() + timedelta(days=2),
        )
        serializer = ReservationSerializer(
            data={
                "tickets": [
                    {"row": 1, "seat": 1, "show_session": self.session.pk},
                    {"row": 1, "seat": 2, "show_session": other_session.pk},
                ]
            }
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        request = type("Request", (), {"user": self.user})()
        with self.assertRaises(serializers.ValidationError):
            serializer.save(request=request)


class PlanetariumAPITests(PlanetariumFixtureMixin, TestCase):
    def setUp(self):
        self.create_planetarium_data()
        self.user = User.objects.create_user(
            username="viewer", password="safe-password-123"
        )
        self.other_user = User.objects.create_user(
            username="other-viewer", password="safe-password-123"
        )
        self.staff = User.objects.create_superuser(
            username="manager", email="manager@example.com", password="safe-password-123"
        )
        self.client = APIClient()

    def authenticate(self, user=None):
        self.client.force_authenticate(user=user or self.user)

    def test_registration_and_jwt_token_endpoints(self):
        response = self.client.post(
            "/api/auth/register/",
            {"username": "registered", "email": "registered@example.com", "password": "safe-password-123"},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertNotIn("password", response.data)

        response = self.client.post(
            "/api/auth/token/",
            {"username": "registered", "password": "safe-password-123"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

    def test_public_catalog_endpoints_and_filters(self):
        self.assertEqual(self.client.get("/api/themes/").status_code, 200)
        self.assertEqual(self.client.get("/api/astronomy-shows/?search=Journey").status_code, 200)
        filtered = self.client.get(f"/api/astronomy-shows/?themes={self.theme.pk}")
        self.assertEqual(filtered.status_code, 200)
        self.assertEqual(len(filtered.data["results"]), 1)
        self.assertEqual(self.client.get("/api/domes/").status_code, 200)
        self.assertEqual(self.client.get("/api/sessions/").status_code, 200)

    def test_catalogue_lists_are_paginated(self):
        for index in range(21):
            AstronomyShow.objects.create(
                title=f"Extra show {index}", description="Description"
            )
        response = self.client.get("/api/astronomy-shows/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 20)
        self.assertIsNotNone(response.data["next"])

    def test_model_clean_rejects_invalid_ticket_bounds_and_past_session(self):
        reservation = Reservation.objects.create(user=self.user)
        invalid_ticket = Ticket(
            row=self.dome.rows + 1,
            seat=1,
            show_session=self.session,
            reservation=reservation,
        )
        with self.assertRaises(DjangoValidationError):
            invalid_ticket.full_clean()

        past_session = ShowSession(
            astronomy_show=self.astronomy_show,
            planetarium_dome=self.dome,
            show_time=timezone.now() - timedelta(minutes=1),
        )
        with self.assertRaises(DjangoValidationError):
            past_session.full_clean()

        past_session.pk = self.session.pk
        invalid_ticket.row = 1
        invalid_ticket.show_session = past_session
        with self.assertRaises(DjangoValidationError):
            invalid_ticket.full_clean()

    def test_catalog_writes_require_staff(self):
        payload = {"name": "New theme"}
        self.assertIn(self.client.post("/api/themes/", payload, format="json").status_code, (401, 403))

        self.authenticate(self.user)
        self.assertEqual(self.client.post("/api/themes/", payload, format="json").status_code, 403)

        self.authenticate(self.staff)
        self.assertEqual(self.client.post("/api/themes/", payload, format="json").status_code, 201)

    def test_authenticated_user_can_create_and_list_own_reservations(self):
        self.authenticate(self.user)
        response = self.client.post(
            "/api/reservations/", self.reservation_payload((1, 1), (1, 2)), format="json"
        )
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(len(response.data["tickets"]), 2)
        self.assertEqual(
            len(self.client.get("/api/reservations/").data["results"]), 1
        )

        self.authenticate(self.other_user)
        self.assertEqual(self.client.get("/api/reservations/").data["results"], [])

    def test_staff_can_view_all_reservations(self):
        reservation = Reservation.objects.create(user=self.user)
        Ticket.objects.create(
            row=1, seat=1, show_session=self.session, reservation=reservation
        )
        self.authenticate(self.staff)
        self.assertEqual(len(self.client.get("/api/reservations/").data["results"]), 1)

    def test_reservation_endpoint_rejects_duplicate_seat_and_keeps_no_partial_data(self):
        self.authenticate(self.user)
        response = self.client.post(
            "/api/reservations/", self.reservation_payload((1, 1), (1, 1)), format="json"
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Reservation.objects.count(), 0)

    def test_reservation_endpoint_rejects_past_session(self):
        past_session = ShowSession.objects.create(
            astronomy_show=self.astronomy_show,
            planetarium_dome=self.dome,
            show_time=timezone.now() - timedelta(days=1),
        )
        self.authenticate(self.user)
        response = self.client.post(
            "/api/reservations/",
            self.reservation_payload((1, 1), session=past_session),
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Reservation.objects.count(), 0)

    def test_two_booking_attempts_cannot_reserve_the_same_seat(self):
        self.authenticate(self.user)
        first = self.client.post(
            "/api/reservations/", self.reservation_payload((1, 1)), format="json"
        )
        second = self.client.post(
            "/api/reservations/", self.reservation_payload((1, 1)), format="json"
        )
        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 400)
        self.assertEqual(Ticket.objects.filter(show_session=self.session, row=1, seat=1).count(), 1)


class ConcurrentReservationTests(PlanetariumFixtureMixin, TestCase):
    def setUp(self):
        self.create_planetarium_data()
        self.user = User.objects.create_user(
            username="concurrent-viewer", password="safe-password-123"
        )

    def test_simultaneous_requests_for_same_seat_only_create_one_ticket(self):
        payload = self.reservation_payload((1, 1))
        request = SimpleNamespace(user=self.user)
        first_attempt = ReservationSerializer(
            data=payload, context={"request": request}
        )
        second_attempt = ReservationSerializer(
            data=payload, context={"request": request}
        )

        # Both requests pass seat validation before either one writes to SQLite.
        self.assertTrue(first_attempt.is_valid(), first_attempt.errors)
        self.assertTrue(second_attempt.is_valid(), second_attempt.errors)
        first_attempt.save()
        with self.assertRaises(serializers.ValidationError):
            second_attempt.save()

        self.assertEqual(
            Ticket.objects.filter(
                show_session=self.session, row=1, seat=1
            ).count(),
            1,
        )
        self.assertEqual(Reservation.objects.count(), 1)

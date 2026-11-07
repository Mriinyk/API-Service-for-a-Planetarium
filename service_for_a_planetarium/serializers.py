from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework import serializers

from service_for_a_planetarium.models import (
    AstronomyShow,
    PlanetariumDome,
    Reservation,
    ShowSession,
    ShowTheme,
    Ticket,
)

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ("id", "username", "email", "password")

    def validate_password(self, value):
        user = User(username=self.initial_data.get("username", ""))
        try:
            validate_password(value, user=user)
        except DjangoValidationError as error:
            raise serializers.ValidationError(error.messages) from error
        return value

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)


class ShowThemeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShowTheme
        fields = "__all__"


class AstronomyShowSerializer(serializers.ModelSerializer):
    themes = ShowThemeSerializer(many=True, read_only=True)
    theme_ids = serializers.PrimaryKeyRelatedField(
        many=True, queryset=ShowTheme.objects.all(), source="themes", write_only=True,
        required=False,
    )

    class Meta:
        model = AstronomyShow
        fields = ("id", "title", "description", "themes", "theme_ids")


class PlanetariumDomeSerializer(serializers.ModelSerializer):
    capacity = serializers.IntegerField(read_only=True)

    class Meta:
        model = PlanetariumDome
        fields = ("id", "name", "rows", "seats_in_row", "capacity")


class ShowSessionSerializer(serializers.ModelSerializer):
    astronomy_show_title = serializers.CharField(source="astronomy_show.title", read_only=True)
    planetarium_dome_name = serializers.CharField(source="planetarium_dome.name", read_only=True)
    available_seats = serializers.SerializerMethodField()

    class Meta:
        model = ShowSession
        fields = (
            "id", "astronomy_show", "astronomy_show_title", "planetarium_dome",
            "planetarium_dome_name", "show_time", "available_seats",
        )

    def get_available_seats(self, obj) -> int:
        return max(0, obj.planetarium_dome.capacity - obj._ticket_count)


class TicketSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ticket
        fields = ("id", "row", "seat", "show_session")
        validators = []

    def validate(self, attrs):
        session = attrs["show_session"]
        row, seat = attrs["row"], attrs["seat"]
        dome = session.planetarium_dome
        if row > dome.rows or seat > dome.seats_in_row:
            raise serializers.ValidationError("The selected seat does not exist in this dome.")
        if Ticket.objects.filter(show_session=session, row=row, seat=seat).exists():
            raise serializers.ValidationError("This seat has already been booked.")
        if session.show_time <= timezone.now():
            raise serializers.ValidationError("Tickets can only be booked for future sessions.")
        try:
            Ticket(
                row=row,
                seat=seat,
                show_session=session,
            ).full_clean(exclude=("reservation",))
        except DjangoValidationError as error:
            raise serializers.ValidationError(error.message_dict) from error
        return attrs


class ReservationSerializer(serializers.ModelSerializer):
    tickets = TicketSerializer(many=True)

    class Meta:
        model = Reservation
        fields = ("id", "created_at", "tickets")
        read_only_fields = ("id", "created_at")

    def create(self, validated_data):
        ticket_data = validated_data.pop("tickets")
        if not ticket_data:
            raise serializers.ValidationError({"tickets": "Add at least one ticket."})
        sessions = {item["show_session"].id for item in ticket_data}
        if len(sessions) != 1:
            raise serializers.ValidationError({"tickets": "A reservation must be for one session."})
        seats = [(item["row"], item["seat"]) for item in ticket_data]
        if len(seats) != len(set(seats)):
            raise serializers.ValidationError({"tickets": "Duplicate seats in this reservation."})
        try:
            with transaction.atomic():
                reservation = Reservation.objects.create(
                    user=self.context["request"].user
                )
                for item in ticket_data:
                    ticket = Ticket(reservation=reservation, **item)
                    try:
                        ticket.full_clean()
                    except DjangoValidationError as error:
                        raise serializers.ValidationError(
                            {"tickets": error.messages}
                        ) from error
                    ticket.save()
        except IntegrityError as error:
            raise serializers.ValidationError(
                {"tickets": "One or more selected seats have already been booked."}
            ) from error
        return reservation

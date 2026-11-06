from rest_framework import serializers

from .models import Complaint, Ticket


class ComplaintSerializer(serializers.ModelSerializer):
    customer_username = serializers.CharField(
        source="customer.username",
        read_only=True,
    )

    class Meta:
        model = Complaint
        fields = [
            "id",
            "customer_username",
            "subject",
            "description",
            "created_at",
        ]
        read_only_fields = ["id", "customer_username", "created_at"]


class TicketSerializer(serializers.ModelSerializer):
    complaint_id = serializers.IntegerField(
        source="complaint.id",
        read_only=True,
    )
    complaint_subject = serializers.CharField(
        source="complaint.subject",
        read_only=True,
    )
    complaint_description = serializers.CharField(
        source="complaint.description",
        read_only=True,
    )
    customer_username = serializers.CharField(
        source="complaint.customer.username",
        read_only=True,
    )
    agent_username = serializers.CharField(
        source="created_by_agent.username",
        read_only=True,
    )

    class Meta:
        model = Ticket
        fields = [
            "id",
            "ticket_number",
            "complaint_id",
            "complaint_subject",
            "complaint_description",
            "customer_username",
            "agent_username",
            "priority",
            "status",
            "resolution_notes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class AgentTicketCreateSerializer(serializers.ModelSerializer):
    complaint = serializers.PrimaryKeyRelatedField(
        queryset=Complaint.objects.all()
    )

    class Meta:
        model = Ticket
        fields = ["complaint", "priority"]

    def validate_complaint(self, complaint):
        if Ticket.objects.filter(complaint=complaint).exists():
            raise serializers.ValidationError(
                "A ticket has already been created for this complaint."
            )
        return complaint


class TicketStatusUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ticket
        fields = ["status", "resolution_notes"]

    def validate(self, attrs):
        status = attrs.get("status", self.instance.status)
        notes = attrs.get(
            "resolution_notes",
            self.instance.resolution_notes,
        )

        if status == Ticket.Status.RESOLVED and not notes.strip():
            raise serializers.ValidationError({
                "resolution_notes": (
                    "Please provide resolution notes before resolving."
                )
            })

        return attrs
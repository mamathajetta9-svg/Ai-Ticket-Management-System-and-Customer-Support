from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Complaint, Ticket
from .serializers import (
    ComplaintSerializer,
    TicketSerializer,
    AgentTicketCreateSerializer,
    TicketStatusUpdateSerializer,
)


class ComplaintListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.role == "CUSTOMER":
            complaints = Complaint.objects.filter(
                customer=request.user
            )
        elif request.user.role in ["AGENT", "ADMIN"]:
            complaints = Complaint.objects.all()
        else:
            raise PermissionDenied("You cannot view complaints.")

        serializer = ComplaintSerializer(complaints, many=True)
        return Response(serializer.data)

    def post(self, request):
        if request.user.role != "CUSTOMER":
            raise PermissionDenied(
                "Only customers can submit complaints."
            )

        serializer = ComplaintSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(customer=request.user)

        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED,
        )


class TicketListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.role == "CUSTOMER":
            tickets = Ticket.objects.filter(
                complaint__customer=request.user
            )
        elif request.user.role == "AGENT":
            tickets = Ticket.objects.filter(
                created_by_agent=request.user
            )
        elif request.user.role == "ADMIN":
            tickets = Ticket.objects.all()
        else:
            raise PermissionDenied("You cannot view tickets.")

        serializer = TicketSerializer(tickets, many=True)
        return Response(serializer.data)

    def post(self, request):
        if request.user.role != "AGENT":
            raise PermissionDenied(
                "Only agents can create tickets from complaints."
            )

        serializer = AgentTicketCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        ticket = serializer.save(created_by_agent=request.user)

        return Response(
            TicketSerializer(ticket).data,
            status=status.HTTP_201_CREATED,
        )


class TicketStatusUpdateView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, ticket_number):
        if request.user.role != "AGENT":
            raise PermissionDenied(
                "Only agents can update ticket status."
            )

        ticket = get_object_or_404(
            Ticket,
            ticket_number=ticket_number,
        )

        if ticket.created_by_agent != request.user:
            raise PermissionDenied(
                "You can only update tickets you created."
            )

        serializer = TicketStatusUpdateSerializer(
            ticket,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(TicketSerializer(ticket).data)


class TrackTicketView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, ticket_number):
        if request.user.role != "CUSTOMER":
            raise PermissionDenied(
                "Only customers can track tickets here."
            )

        ticket = get_object_or_404(
            Ticket,
            ticket_number=ticket_number,
            complaint__customer=request.user,
        )

        return Response(TicketSerializer(ticket).data)
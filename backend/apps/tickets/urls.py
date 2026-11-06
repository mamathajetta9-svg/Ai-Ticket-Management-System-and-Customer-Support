from django.urls import path

from .views import (
    ComplaintListCreateView,
    TicketListCreateView,
    TicketStatusUpdateView,
    TrackTicketView,
)

urlpatterns = [
    path(
        "complaints/",
        ComplaintListCreateView.as_view(),
        name="complaint-list-create",
    ),
    path(
        "",
        TicketListCreateView.as_view(),
        name="ticket-list-create",
    ),
    path(
        "<str:ticket_number>/status/",
        TicketStatusUpdateView.as_view(),
        name="ticket-status-update",
    ),
    path(
        "track/<str:ticket_number>/",
        TrackTicketView.as_view(),
        name="ticket-track",
    ),
]
from django.contrib import admin

from .models import Complaint, Ticket


@admin.register(Complaint)
class ComplaintAdmin(admin.ModelAdmin):
    list_display = ("id", "subject", "customer", "created_at")
    search_fields = ("subject", "description", "customer__username")
    list_filter = ("created_at",)


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = (
        "ticket_number",
        "complaint",
        "created_by_agent",
        "priority",
        "status",
        "created_at",
    )
    search_fields = (
        "ticket_number",
        "complaint__subject",
        "complaint__customer__username",
    )
    list_filter = ("priority", "status", "created_at")
    readonly_fields = ("ticket_number", "created_at", "updated_at")
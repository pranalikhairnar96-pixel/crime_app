from django.contrib import admin
from .models import (
    Incident, Area, PoliceOfficer, Citizen, CrimeReport, Notification
)


@admin.register(Area)
class AreaAdmin(admin.ModelAdmin):
    list_display = ('name', 'code')
    search_fields = ('name', 'code')
    ordering = ('name',)


@admin.register(PoliceOfficer)
class PoliceOfficerAdmin(admin.ModelAdmin):
    list_display = ('officer_id', 'get_name', 'rank', 'assigned_area', 'is_active')
    search_fields = ('officer_id', 'user__first_name', 'user__last_name')
    list_filter = ('rank', 'is_active', 'assigned_area')
    ordering = ('officer_id',)

    def get_name(self, obj):
        return obj.user.get_full_name() or obj.user.username
    get_name.short_description = 'Name'


@admin.register(Citizen)
class CitizenAdmin(admin.ModelAdmin):
    list_display = ('get_name', 'email', 'city', 'profile_area', 'email_verified')
    search_fields = ('user__first_name', 'user__last_name', 'email', 'city')
    list_filter = ('email_verified', 'profile_area', 'created_at')
    ordering = ('-created_at',)

    def get_name(self, obj):
        return obj.user.get_full_name() or obj.user.username
    get_name.short_description = 'Name'


@admin.register(CrimeReport)
class CrimeReportAdmin(admin.ModelAdmin):
    list_display = ('id', 'crime_type', 'location_name', 'status', 'assigned_officer', 'reported_date')
    search_fields = ('location_name', 'crime_type', 'citizen__user__first_name')
    list_filter = ('status', 'crime_type', 'area', 'is_priority', 'reported_date')
    readonly_fields = ('reported_date', 'citizen')
    ordering = ('-reported_date',)

    fieldsets = (
        ('Report Information', {
            'fields': ('citizen', 'crime_type', 'description', 'reported_date')
        }),
        ('Location Details', {
            'fields': ('area', 'location_name', 'latitude', 'longitude')
        }),
        ('Timeline', {
            'fields': ('crime_date',)
        }),
        ('Investigation', {
            'fields': ('status', 'assigned_officer', 'is_priority', 'officer_notes')
        }),
        ('Evidence', {
            'fields': ('evidence_file',)
        }),
    )


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('id', 'recipient', 'notification_type', 'is_read', 'created_at')
    search_fields = ('recipient__officer_id', 'title')
    list_filter = ('notification_type', 'is_read', 'created_at')
    readonly_fields = ('created_at', 'recipient')
    ordering = ('-created_at',)


@admin.register(Incident)
class IncidentAdmin(admin.ModelAdmin):
    list_display = ('city', 'date_reported')
    search_fields = ('city',)

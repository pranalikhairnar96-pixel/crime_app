from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class Area(models.Model):
    """Police jurisdiction areas/regions"""
    name = models.CharField(max_length=255, unique=True)
    code = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.code})"


class PoliceOfficer(models.Model):
    """Police Officer profile with Officer ID"""
    RANK_CHOICES = [
        ('CONSTABLE', 'Constable'),
        ('SUB_INSPECTOR', 'Sub Inspector'),
        ('INSPECTOR', 'Inspector'),
        ('SENIOR_INSPECTOR', 'Senior Inspector'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='police_profile')
    officer_id = models.CharField(max_length=50, unique=True)
    rank = models.CharField(max_length=20, choices=RANK_CHOICES, default='CONSTABLE')
    assigned_area = models.ForeignKey(Area, on_delete=models.SET_NULL, null=True, blank=True, related_name='officers')
    badge_number = models.CharField(max_length=50, unique=True, null=True, blank=True)
    phone = models.CharField(max_length=15, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['officer_id']

    def __str__(self):
        return f"Officer {self.officer_id} - {self.user.get_full_name()}"


class Citizen(models.Model):
    """Citizen profile for crime reporting"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='citizen_profile')
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=15, blank=True)
    address = models.TextField(blank=True)
    city = models.CharField(max_length=128, blank=True)
    profile_area = models.ForeignKey(Area, on_delete=models.SET_NULL, null=True, blank=True, related_name='citizens')
    email_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.email}"


class CrimeReport(models.Model):
    """Crime reports submitted by citizens"""
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('IN_PROGRESS', 'In Progress'),
        ('RESOLVED', 'Resolved'),
        ('CLOSED', 'Closed'),
    ]

    CRIME_TYPE_CHOICES = [
        ('THEFT', 'Theft'),
        ('ASSAULT', 'Assault'),
        ('ROBBERY', 'Robbery'),
        ('FRAUD', 'Fraud'),
        ('HARASSMENT', 'Harassment'),
        ('VANDALISM', 'Vandalism'),
        ('ACCIDENT', 'Accident'),
        ('LOST_PROPERTY', 'Lost Property'),
        ('KIDNAPPING', 'Kidnapping'),
        ('RAPE', 'Rape'),
        ('MURDER', 'Murder'),
        ('OTHER', 'Other'),
    ]

    citizen = models.ForeignKey(Citizen, on_delete=models.CASCADE, related_name='crime_reports')
    assigned_officer = models.ForeignKey(PoliceOfficer, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_reports')
    crime_type = models.CharField(max_length=50, choices=CRIME_TYPE_CHOICES)
    description = models.TextField()
    area = models.ForeignKey(Area, on_delete=models.SET_NULL, null=True, blank=True, related_name='crime_reports')
    location_name = models.CharField(max_length=255)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    crime_date = models.DateTimeField()
    reported_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    evidence_file = models.FileField(upload_to='crime_reports/evidence/', null=True, blank=True)
    officer_notes = models.TextField(blank=True)
    is_priority = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-reported_date']

    def __str__(self):
        return f"{self.crime_type} - {self.location_name} ({self.reported_date.date()})"

    def save(self, *args, **kwargs):
        # Auto-assign to officer from the area
        if not self.assigned_officer and self.area:
            officer = self.area.officers.filter(is_active=True).first()
            if officer:
                self.assigned_officer = officer
        super().save(*args, **kwargs)


class Notification(models.Model):
    """System notifications for police officers"""
    NOTIFICATION_TYPE_CHOICES = [
        ('NEW_REPORT', 'New Crime Report'),
        ('REPORT_UPDATE', 'Report Status Changed'),
        ('MESSAGE', 'Message'),
        ('ALERT', 'Alert'),
    ]

    recipient = models.ForeignKey(PoliceOfficer, on_delete=models.CASCADE, related_name='notifications')
    crime_report = models.ForeignKey(CrimeReport, on_delete=models.CASCADE, null=True, blank=True, related_name='notifications')
    notification_type = models.CharField(max_length=50, choices=NOTIFICATION_TYPE_CHOICES)
    title = models.CharField(max_length=255)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.notification_type} - {self.recipient.officer_id}"

    def mark_as_read(self):
        self.is_read = True
        self.read_at = timezone.now()
        self.save()


class Incident(models.Model):
    """Optional model to store incidents later. Fields mirror CSV columns where possible."""
    date_reported = models.DateField(null=True, blank=True)
    city = models.CharField(max_length=128, blank=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return f"{self.city} - {self.date_reported}"

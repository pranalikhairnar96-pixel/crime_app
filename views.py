from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.core.paginator import Paginator
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from django.views.decorators.http import require_http_methods
from django.contrib.auth.views import PasswordResetView, PasswordResetConfirmView, PasswordResetDoneView, PasswordResetCompleteView
from django.urls import reverse_lazy
from django.db.models import Q
from django.utils import timezone

from . import services, utils
from .models import (
    Area, PoliceOfficer, Citizen, CrimeReport, Notification
)
from .forms import (
    CitizenSignupForm, CitizenProfileForm, CrimeReportForm, 
    CrimeReportUpdateForm, PoliceOfficerLoginForm
)

import folium
from folium.plugins import HeatMap
import networkx as nx


@require_http_methods(["GET", "POST"])
def login_view(request):
    """Redirect to landing page to choose role"""
    return redirect('dashboard:landing')


@require_http_methods(["GET", "POST"])
def landing(request):
    """Landing page - choose between citizen and police officer"""
    if request.user.is_authenticated:
        return redirect('dashboard:role_select')
    return render(request, 'dashboard/landing.html')


def logout_view(request):
    logout(request)
    messages.success(request, 'You have been logged out successfully')
    return redirect('dashboard:login')


@login_required
def role_select(request):
    """Display role selection for authenticated users"""
    user = request.user
    
    # Check if user has both profiles
    has_citizen = hasattr(user, 'citizen_profile')
    has_police = hasattr(user, 'police_profile')
    
    context = {
        'has_citizen': has_citizen,
        'has_police': has_police
    }
    return render(request, 'dashboard/role_select.html', context)


@login_required
def citizen_homepage(request):
    """Citizen dashboard/homepage"""
    try:
        citizen = request.user.citizen_profile
    except Citizen.DoesNotExist:
        messages.error(request, 'Please complete your citizen profile first.')
        return redirect('dashboard:complete_citizen_profile')
    
    # Get citizen's recent reports
    recent_reports = CrimeReport.objects.filter(citizen=citizen).order_by('-reported_date')[:5]
    total_reports = CrimeReport.objects.filter(citizen=citizen).count()
    resolved_reports = CrimeReport.objects.filter(citizen=citizen, status='RESOLVED').count()
    
    context = {
        'citizen': citizen,
        'recent_reports': recent_reports,
        'total_reports': total_reports,
        'resolved_reports': resolved_reports
    }
    return render(request, 'dashboard/citizen/home.html', context)


@login_required
def police_homepage(request):
    """Police officer dashboard"""
    try:
        officer = request.user.police_profile
    except PoliceOfficer.DoesNotExist:
        messages.error(request, 'Police profile not found.')
        return redirect('dashboard:index')
    
    # Get pending reports for this officer
    pending_reports = CrimeReport.objects.filter(
        assigned_officer=officer,
        status='PENDING'
    ).order_by('-reported_date')
    
    in_progress = CrimeReport.objects.filter(
        assigned_officer=officer,
        status='IN_PROGRESS'
    ).count()
    
    resolved = CrimeReport.objects.filter(
        assigned_officer=officer,
        status='RESOLVED'
    ).count()
    
    # Get unread notifications
    unread_notifications = Notification.objects.filter(
        recipient=officer,
        is_read=False
    ).order_by('-created_at')[:10]
    
    context = {
        'officer': officer,
        'pending_reports': pending_reports,
        'in_progress_count': in_progress,
        'resolved_count': resolved,
        'unread_notifications': unread_notifications
    }
    return render(request, 'dashboard/police/home.html', context)


@login_required
def index(request):
    try:
        df = services.load_dataset()
    except FileNotFoundError as e:
        messages.error(request, str(e))
        df = None

    total_crimes = len(df) if df is not None else 0
    total_cities = df['City'].nunique() if df is not None else 0
    top_city = None
    if df is not None and not df.empty:
        top_city = df['City'].value_counts().idxmax()

    context = {
        'total_crimes': total_crimes,
        'total_cities': total_cities,
        'top_city': top_city,
    }
    return render(request, 'dashboard/saas_dashboard.html', context)


@login_required
def heatmap_view(request):
    try:
        df = services.load_dataset()
    except FileNotFoundError as e:
        messages.error(request, str(e))
        return render(request, 'dashboard/saas_heatmap.html', {'map_html': ''})

    # map cities to coords
    df = df.copy()
    df['Latitude'] = df['City'].map(lambda x: utils.map_city_to_coords(x)[0] if utils.map_city_to_coords(x) else None)
    df['Longitude'] = df['City'].map(lambda x: utils.map_city_to_coords(x)[1] if utils.map_city_to_coords(x) else None)
    df = df.dropna(subset=['Latitude', 'Longitude'])

    m = folium.Map(location=[20.5937, 78.9629], zoom_start=5)
    heat_data = df[['Latitude', 'Longitude']].values.tolist()
    HeatMap(heat_data, radius=20, blur=25, max_zoom=10).add_to(m)

    map_html = m._repr_html_()
    return render(request, 'dashboard/saas_heatmap.html', {'map_html': map_html})


@login_required
def prediction_view(request):
    try:
        df = services.extract_years()
    except FileNotFoundError as e:
        messages.error(request, str(e))
        return render(request, 'dashboard/saas_prediction.html', {})

    cities = sorted(df['City'].dropna().unique().tolist())
    selected = request.GET.get('city') or (cities[0] if cities else None)
    chart_data = {'labels': [], 'values': []}
    if selected:
        city_data = df[df['City'] == selected]
        counts = city_data.groupby('Year').size().sort_index()
        chart_data['labels'] = counts.index.fillna('Unknown').astype(int).tolist()
        chart_data['values'] = counts.values.tolist()

    return render(request, 'dashboard/saas_prediction.html', {'cities': cities, 'selected': selected, 'chart_data': chart_data})


@login_required
def patrol_view(request):
    try:
        df = services.load_dataset()
    except FileNotFoundError as e:
        messages.error(request, str(e))
        return render(request, 'dashboard/saas_patrol.html', {})

    counts = df['City'].value_counts().head(8)
    cities = counts.index.tolist()
    
    # Calculate risk levels for each city
    patrol_data = []
    max_incidents = counts.max() if len(counts) > 0 else 1
    
    for city in cities:
        incident_count = int(counts[city])
        risk_percentage = (incident_count / max_incidents) * 100
        
        # Risk classification
        if risk_percentage >= 70:
            risk_level = "CRITICAL"
            risk_color = "danger"
            risk_icon = "fas fa-exclamation-triangle"
        elif risk_percentage >= 40:
            risk_level = "HIGH"
            risk_color = "warning"
            risk_icon = "fas fa-alert"
        else:
            risk_level = "MODERATE"
            risk_color = "info"
            risk_icon = "fas fa-info-circle"
        
        patrol_data.append({
            'city': city,
            'incidents': incident_count,
            'risk_percentage': round(risk_percentage, 1),
            'risk_level': risk_level,
            'risk_color': risk_color,
            'risk_icon': risk_icon
        })

    # Create graph for patrol route optimization
    G = nx.Graph()
    for city in cities:
        G.add_node(city, risk=int(counts[city]))
    for i in range(len(cities)):
        for j in range(i + 1, len(cities)):
            G.add_edge(cities[i], cities[j], weight=1)

    if cities:
        start = cities[0]
        path = list(nx.dfs_tree(G, start))
    else:
        path = []

    # Create detailed patrol route with risk info
    detailed_path = []
    for idx, city in enumerate(path, 1):
        city_info = next((p for p in patrol_data if p['city'] == city), None)
        if city_info:
            detailed_path.append({
                'order': idx,
                'city': city,
                'incidents': city_info['incidents'],
                'risk_level': city_info['risk_level'],
                'risk_color': city_info['risk_color'],
                'risk_icon': city_info['risk_icon'],
                'risk_percentage': city_info['risk_percentage']
            })

    explanation = 'Patrol order is optimized for maximum efficiency. High-risk zones require increased vigilance and resources. Officers should maintain heightened alert status in CRITICAL zones.'
    total_incidents = sum(counts)
    avg_incidents = round(total_incidents / len(cities), 1) if cities else 0
    
    return render(request, 'dashboard/saas_patrol.html', {
        'patrol_data': patrol_data,
        'detailed_path': detailed_path,
        'explanation': explanation,
        'counts': counts.to_dict(),
        'total_incidents': total_incidents,
        'avg_incidents': avg_incidents,
        'red_zones': [p for p in patrol_data if p['risk_level'] == 'CRITICAL']
    })


@login_required
def ranking_view(request):
    try:
        df = services.load_dataset()
    except FileNotFoundError as e:
        messages.error(request, str(e))
        return render(request, 'dashboard/saas_ranking.html', {'page_obj': None})

    ranking = df['City'].value_counts().reset_index()
    ranking.columns = ['City', 'Crime_Count']
    paginator = Paginator(ranking.to_dict('records'), 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, 'dashboard/saas_ranking.html', {'page_obj': page_obj})


def signup(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Account created successfully. Please log in with your username and password.')
            return redirect('dashboard:login')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{error}')
    else:
        form = UserCreationForm()

    return render(request, 'registration/signup.html', {'form': form})


def citizen_signup(request):
    """Citizen registration"""
    if request.method == 'POST':
        form = CitizenSignupForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Create citizen profile
            citizen = Citizen.objects.create(
                user=user,
                email=form.cleaned_data['email']
            )
            login(request, user)
            messages.success(request, 'Welcome! Please complete your profile.')
            return redirect('dashboard:complete_citizen_profile')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{error}')
    else:
        form = CitizenSignupForm()

    return render(request, 'registration/citizen_signup.html', {'form': form})


@login_required
def complete_citizen_profile(request):
    """Complete citizen profile after signup"""
    try:
        citizen = request.user.citizen_profile
    except Citizen.DoesNotExist:
        messages.error(request, 'Citizen profile not found.')
        return redirect('dashboard:citizen_signup')
    
    if request.method == 'POST':
        form = CitizenProfileForm(request.POST, instance=citizen)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('dashboard:citizen_home')
    else:
        form = CitizenProfileForm(instance=citizen)
    
    return render(request, 'registration/complete_citizen_profile.html', {'form': form})


@require_http_methods(["GET", "POST"])
def police_login(request):
    """Police officer login using Officer ID"""
    if request.user.is_authenticated:
        return redirect('dashboard:role_select')
    
    if request.method == 'POST':
        form = PoliceOfficerLoginForm(request.POST)
        if form.is_valid():
            officer_id = form.cleaned_data['officer_id']
            password = form.cleaned_data['password']
            
            try:
                police = PoliceOfficer.objects.get(officer_id=officer_id)
                user = police.user
                authenticated_user = authenticate(request, username=user.username, password=password)
                
                if authenticated_user is not None:
                    login(request, authenticated_user)
                    messages.success(request, f'Welcome Officer {officer_id}!')
                    return redirect('dashboard:role_select')
                else:
                    messages.error(request, 'Invalid password for this Officer ID.')
            except PoliceOfficer.DoesNotExist:
                messages.error(request, 'Officer ID not found in the system.')
    else:
        form = PoliceOfficerLoginForm()
    
    return render(request, 'registration/police_login.html', {'form': form})


@require_http_methods(["GET", "POST"])
def citizen_login(request):
    """Citizen login using username/email and password"""
    if request.user.is_authenticated:
        return redirect('dashboard:role_select')
    
    if request.method == 'POST':
        username_or_email = request.POST.get('username')
        password = request.POST.get('password')
        
        # Try to authenticate with username first
        user = authenticate(request, username=username_or_email, password=password)
        
        # If username fails, try email
        if user is None:
            try:
                user_obj = User.objects.get(email=username_or_email)
                user = authenticate(request, username=user_obj.username, password=password)
            except User.DoesNotExist:
                pass
        
        if user is not None:
            # Check if user has citizen profile
            try:
                citizen = user.citizen_profile
                login(request, user)
                messages.success(request, f'Welcome back, {user.first_name or user.username}!')
                return redirect('dashboard:role_select')
            except Citizen.DoesNotExist:
                messages.error(request, 'Citizen profile not found. Please contact support.')
        else:
            messages.error(request, 'Invalid username/email or password.')
    
    return render(request, 'registration/citizen_login.html')


# ==================== CRIME REPORTING VIEWS ====================

@login_required
def report_crime(request):
    """Submit a new crime report"""
    try:
        citizen = request.user.citizen_profile
    except Citizen.DoesNotExist:
        messages.error(request, 'Please complete your citizen profile first.')
        return redirect('dashboard:complete_citizen_profile')
    
    if request.method == 'POST':
        form = CrimeReportForm(request.POST, request.FILES)
        if form.is_valid():
            crime_report = form.save(commit=False)
            crime_report.citizen = citizen
            crime_report.save()
            
            # Create notification for assigned officer
            if crime_report.assigned_officer:
                Notification.objects.create(
                    recipient=crime_report.assigned_officer,
                    crime_report=crime_report,
                    notification_type='NEW_REPORT',
                    title=f'New {crime_report.crime_type} Report',
                    message=f'New crime report in {crime_report.area.name}: {crime_report.location_name}'
                )
            
            messages.success(request, '✅ Your crime report has been successfully submitted.')
            return redirect('dashboard:citizen_home')
    else:
        form = CrimeReportForm()
    
    return render(request, 'dashboard/citizen/report_crime.html', {'form': form})


@login_required
def my_reports(request):
    """View citizen's own crime reports"""
    try:
        citizen = request.user.citizen_profile
    except Citizen.DoesNotExist:
        messages.error(request, 'Please complete your citizen profile first.')
        return redirect('dashboard:complete_citizen_profile')
    
    reports = CrimeReport.objects.filter(citizen=citizen).order_by('-reported_date')
    paginator = Paginator(reports, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'dashboard/citizen/my_reports.html', {'page_obj': page_obj})


@login_required
def report_detail(request, report_id):
    """View crime report details"""
    report = get_object_or_404(CrimeReport, id=report_id)
    
    # Check if user is the citizen who filed the report or the assigned officer
    try:
        citizen = request.user.citizen_profile
        if report.citizen != citizen:
            messages.error(request, 'You do not have permission to view this report.')
            return redirect('dashboard:citizen_home')
    except Citizen.DoesNotExist:
        try:
            officer = request.user.police_profile
            if report.assigned_officer != officer:
                messages.error(request, 'You do not have permission to view this report.')
                return redirect('dashboard:police_home')
        except PoliceOfficer.DoesNotExist:
            messages.error(request, 'Unauthorized access.')
            return redirect('dashboard:index')
    
    context = {'report': report}
    return render(request, 'dashboard/report_detail.html', context)


# ==================== POLICE OFFICER VIEWS ====================

@login_required
def view_reports(request):
    """Police officer view assigned crime reports"""
    try:
        officer = request.user.police_profile
    except PoliceOfficer.DoesNotExist:
        messages.error(request, 'Police profile not found.')
        return redirect('dashboard:index')
    
    # Filter reports by status
    status_filter = request.GET.get('status', 'all')
    area_filter = request.GET.get('area', '')
    
    reports = CrimeReport.objects.filter(assigned_officer=officer)
    
    if status_filter != 'all':
        reports = reports.filter(status=status_filter)
    
    if area_filter:
        reports = reports.filter(area__id=area_filter)
    
    reports = reports.order_by('-reported_date')
    
    # Pagination
    paginator = Paginator(reports, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get filter options
    areas = Area.objects.all()
    
    context = {
        'page_obj': page_obj,
        'status_filter': status_filter,
        'area_filter': area_filter,
        'areas': areas
    }
    return render(request, 'dashboard/police/view_reports.html', context)


@login_required
def update_report(request, report_id):
    """Police officer update crime report status"""
    report = get_object_or_404(CrimeReport, id=report_id)
    
    try:
        officer = request.user.police_profile
        if report.assigned_officer != officer:
            messages.error(request, 'You are not assigned to this report.')
            return redirect('dashboard:police_home')
    except PoliceOfficer.DoesNotExist:
        messages.error(request, 'Police profile not found.')
        return redirect('dashboard:index')
    
    if request.method == 'POST':
        form = CrimeReportUpdateForm(request.POST, instance=report)
        if form.is_valid():
            form.save()
            messages.success(request, 'Report updated successfully!')
            return redirect('dashboard:report_detail', report_id=report_id)
    else:
        form = CrimeReportUpdateForm(instance=report)
    
    context = {'form': form, 'report': report}
    return render(request, 'dashboard/police/update_report.html', context)


@login_required
def notifications(request):
    """View police officer notifications"""
    try:
        officer = request.user.police_profile
    except PoliceOfficer.DoesNotExist:
        messages.error(request, 'Police profile not found.')
        return redirect('dashboard:index')
    
    # Mark all as read if requested
    if request.GET.get('mark_all_read'):
        Notification.objects.filter(recipient=officer, is_read=False).update(
            is_read=True,
            read_at=timezone.now()
        )
        messages.success(request, 'All notifications marked as read.')
        return redirect('dashboard:notifications')
    
    notifications = Notification.objects.filter(recipient=officer).order_by('-created_at')
    paginator = Paginator(notifications, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    unread_count = Notification.objects.filter(recipient=officer, is_read=False).count()
    
    context = {
        'page_obj': page_obj,
        'unread_count': unread_count
    }
    return render(request, 'dashboard/police/notifications.html', context)


@login_required
def mark_notification_read(request, notification_id):
    """Mark single notification as read"""
    notification = get_object_or_404(Notification, id=notification_id)
    
    try:
        officer = request.user.police_profile
        if notification.recipient != officer:
            messages.error(request, 'Unauthorized access.')
            return redirect('dashboard:police_home')
    except PoliceOfficer.DoesNotExist:
        messages.error(request, 'Police profile not found.')
        return redirect('dashboard:index')
    
    notification.mark_as_read()
    return redirect('dashboard:notifications')

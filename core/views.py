# --- Django built-in imports ---
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import login, authenticate, logout
from django.contrib import messages
from django.http import HttpResponse
from django.utils.dateparse import parse_date
from django.db.models import Q
from .utils import is_room_available
from django.utils import timezone
from datetime import date
from django.views.decorators.http import require_POST
from django.utils.timezone import now
from .forms import MaintenanceForm
from .models import Maintenance
from django.contrib.auth.decorators import user_passes_test
from .models import InventoryItem, InventoryUsageLog
from .forms import InventoryItemForm, InventoryUsageForm
from .forms import FeedbackForm
from .models import Feedback
from .utils import is_room_available
from .utils import calculate_bill
from django.db.models import Sum
from django.template.loader import render_to_string
from django.core.mail import send_mail
from io import BytesIO
from django.core.mail import EmailMessage
from .forms import GuestUserForm, GuestProfileForm, WalkInBookingForm
from django.contrib.auth import get_user_model
from .models import StaffSalary, StaffAttendance
from .forms import StaffSalaryForm, StaffAttendanceForm
from django.db.models import Count, F
from django.http import HttpResponseForbidden
from .models import Notification, User
from datetime import datetime
User = get_user_model()
from .models import Room, Booking
from .forms import RoomForm, BookingForm, CustomUserCreationForm, ReceptionistBookingForm
from .models import Room, Booking, Maintenance
from datetime import date

# ==============================
# 🔐 User Authentication Views
# ==============================

def register_view(request):
    """
    Handles user registration using a custom form.
    On success, redirects to login page with a success message.
    """
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Registration successful. Please log in.")
            return redirect('login')
    else:
        form = CustomUserCreationForm()
    return render(request, 'core/register.html', {'form': form})


def login_view(request):
    """
    Custom login view that redirects users to role-specific dashboards.
    Also prepares unread notifications if already authenticated.
    """
    unread_notifications = []

    if request.user.is_authenticated:
        unread_notifications = request.user.notification_set.filter(is_read=False).order_by('-created_at')[:5]

    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            role = user.role
            if role == "admin":
                return redirect('admin_dashboard')
            elif role == "manager":
                return redirect('manager_dashboard')
            elif role == "receptionist":
                return redirect('receptionist_dashboard')
            elif role == "housekeeping":
                return redirect('housekeeping_dashboard')
            else:
                return redirect('guest_dashboard')
        else:
            messages.error(request, "Invalid username or password.")
    
    return render(request, "core/login.html", {
        "unread_notifications": unread_notifications
    })


def logout_view(request):
    """
    Logs out the current user and redirects to login page.
    """
    logout(request)
    return redirect('login')

def homepage(request):
    return render(request, 'core/home.html')


# ========================
# 🏨 Room Management Views
# ========================

@login_required(login_url='login')
def room_list(request):
    """
    Displays a list of all rooms (available to logged-in users).
    """
    rooms = Room.objects.all()
    return render(request, 'core/room_list.html', {'rooms': rooms})


@login_required(login_url='login')
def room_create(request):
    """
    Allows creation of a new room entry using RoomForm.
    """
    form = RoomForm(request.POST or None)
    if form.is_valid():
        form.save()
        return redirect('room_list')
    return render(request, 'core/room_form.html', {'form': form})


@login_required(login_url='login')
def room_update(request, pk):
    """
    Updates an existing room based on its primary key.
    """
    room = get_object_or_404(Room, pk=pk)
    form = RoomForm(request.POST or None, instance=room)
    if form.is_valid():
        form.save()
        return redirect('room_list')
    return render(request, 'core/room_form.html', {'form': form})


@login_required(login_url='login')
def room_delete(request, pk):
    """
    Deletes a room after confirmation.
    """
    room = get_object_or_404(Room, pk=pk)
    if request.method == 'POST':
        room.delete()
        return redirect('room_list')
    return render(request, 'core/room_confirm_delete.html', {'room': room})



@login_required
def available_rooms(request):
    check_in = request.GET.get('check_in')
    check_out = request.GET.get('check_out')

    search_performed = False  # ✅ Default: False
    rooms = Room.objects.all()

    if check_in and check_out:
        search_performed = True  # ✅ Set to True only when both dates exist
        try:
            check_in_date = datetime.strptime(check_in, '%Y-%m-%d').date()
            check_out_date = datetime.strptime(check_out, '%Y-%m-%d').date()

            if check_in_date >= check_out_date:
                messages.error(request, "❌ Check-out must be after check-in.")
                rooms = Room.objects.none()
            elif check_in_date < date.today():
                messages.error(request, "❌ Check-in date cannot be in the past.")
                rooms = Room.objects.none()
            else:
                booked_rooms = Booking.objects.filter(
                    check_in__lt=check_out_date,
                    check_out__gt=check_in_date,
                    status__in=['Pending', 'Checked In']
                ).values_list('room_id', flat=True)

                maintenance_rooms = Maintenance.objects.filter(
                    scheduled_date__gte=date.today(),
                    is_completed=False
                ).values_list('room_id', flat=True)

                rooms = rooms.exclude(id__in=booked_rooms).exclude(id__in=maintenance_rooms)

        except ValueError:
            messages.error(request, "❌ Invalid date format. Please use YYYY-MM-DD.")
            rooms = Room.objects.none()

    context = {
        'rooms': rooms,
        'check_in': check_in,
        'check_out': check_out,
        'search_performed': search_performed  # ✅ Pass it to template
    }
    return render(request, 'core/available_rooms.html', context)


# ===========================
# 📅 Booking Management Views
# ===========================

@login_required(login_url='login')
def booking_list(request):
    user = request.user

    if user.role in ['admin', 'manager']:
        bookings = Booking.objects.all()
    else:
        bookings = Booking.objects.filter(user=user)

    # Filters
    check_in = request.GET.get('check_in')
    room_id = request.GET.get('room')
    status = request.GET.get('status')

    if check_in:
        bookings = bookings.filter(check_in=check_in)
    if room_id:
        bookings = bookings.filter(room_id=room_id)
    if status:
        bookings = bookings.filter(status=status)

    rooms = Room.objects.all()
    status_choices = ['Pending', 'Checked In', 'Checked Out', 'Canceled', 'No-Show']

    return render(request, 'core/booking_list.html', {
        'bookings': bookings,
        'rooms': rooms,
        'selected_room': room_id,
        'selected_status': status,
        'check_in': check_in,
        'status_choices': status_choices,  
        'today': date.today()
    })

@login_required(login_url='login')
def booking_create(request, room_id=None):
    if request.method == 'POST':
        form = BookingForm(request.POST, request.FILES, request=request)
        if form.is_valid():
            room = form.cleaned_data['room']
            check_in = form.cleaned_data['check_in']
            check_out = form.cleaned_data['check_out']

            if not is_room_available(room, check_in, check_out):
                messages.error(request, "Room is already booked for the selected dates.")
                return redirect('book_room', room_id=room.id)

            
            num_days = (check_out - check_in).days or 1
            room_price = room.price_per_night * num_days
            
            amenities = form.cleaned_data.get('amenities', [])
            spa_services = form.cleaned_data.get('spa_services', [])
            amenity_price = sum(a.price for a in amenities)
            spa_price = sum(s.price for s in spa_services)
            total_price = room_price + amenity_price + spa_price

            
            booking = form.save(commit=False)
            booking.user = request.user
            booking.total = total_price
            booking.subtotal = total_price
            booking.save()
            form.save_m2m()

            
            request.session['payment_breakdown'] = {
                'room_price': float(room_price),
                'amenity_price': float(amenity_price),
                'spa_price': float(spa_price),
                'total_price': float(total_price),
                'booking_id': booking.id
            }

            messages.success(request, "Booking created successfully. Redirecting to payment.")
            return redirect('razorpay_payment', booking_id=booking.id)

    else:
        if room_id:
            room = get_object_or_404(Room, id=room_id)
            form = BookingForm(initial={'room': room}, request=request)
        else:
            form = BookingForm(request=request)

    return render(request, 'core/guest_booking_create.html', {'form': form})


@login_required
@require_POST
def booking_check_in(request, booking_id):
    """
    Marks a booking as 'Checked In' if today >= check-in date and payment is completed.
    Only accessible to admin, receptionist, or the guest themselves.
    """
    booking = get_object_or_404(Booking, id=booking_id)

    
    if request.user.role not in ['admin', 'receptionist'] and request.user != booking.user:
        messages.error(request, "You don't have permission to check in this booking.")
        return redirect('booking_list')

    
    if not booking.is_paid:
        messages.error(request, "Cannot check in until payment is completed.")
        return redirect('booking_list')

    # ✅ Date and status validation
    if date.today() < booking.check_in:
        messages.error(request, "Cannot check in before the check-in date.")
    elif booking.status != 'Pending':
        messages.warning(request, f"Already {booking.status.lower()}.")
    else:
        booking.status = 'Checked In'
        booking.room.is_available = False
        booking.save()
        messages.success(request, f"Checked in successfully for Room {booking.room.room_number}.")

    
    if request.user.role == 'manager':
        return redirect('manager_dashboard')
    elif request.user.role == 'receptionist':
        return redirect('receptionist_dashboard')
    else:
        return redirect('booking_list')

@login_required
@user_passes_test(lambda u: u.role in ['receptionist', 'manager'])
@require_POST
def booking_check_out(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id)

    
    if booking.status == 'Checked In':
        booking.status = 'Checked Out'
        booking.needs_cleaning = True
        booking.room.is_available = True
        booking.save()
        booking.room.save()

        messages.success(request, f"✅ Booking for Room {booking.room.room_number} has been checked out.")
    else:
        messages.error(request, "❌ Only bookings that are currently 'Checked In' can be checked out.")

    
    if request.user.role == 'manager':
        return redirect('manager_dashboard')
    elif request.user.role == 'receptionist':
        return redirect('receptionist_dashboard')
    else:
        return redirect('booking_list')

@login_required
def cancel_booking(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id, user=request.user)

    if booking.status == 'Pending':
        booking.status = 'Canceled'
        booking.save()
        messages.success(request, "Booking canceled successfully.")
    else:
        messages.warning(request, "Only pending bookings can be canceled.")

    return redirect('guest_bookings') 

# ========================
# 📊 Dashboard Views (Role-Based)
# ========================

@login_required
def admin_dashboard(request):
    return render(request, 'core/dashboard_admin.html')


def is_manager(user):
    return user.is_authenticated and user.role == 'manager'

@login_required
@user_passes_test(is_manager)
def manager_dashboard(request):
    # 📩 Feedback stats
    unread_feedback_count = Feedback.objects.filter(is_read=False).count()
    low_rating_count = Feedback.objects.filter(rating__lte=2).count()

    # 💰 Revenue
    total_revenue = Booking.objects.filter(is_paid=True).aggregate(total=Sum('total'))['total'] or 0

    # 🔔 Low inventory notifications
    low_alerts = request.user.notification_set.filter(
        is_read=False,
        message__icontains='Inventory low'
    )

    return render(request, 'core/dashboard_manager.html', {
        'unread_feedback_count': unread_feedback_count,
        'low_rating_count': low_rating_count,
        'total_revenue': total_revenue,
        'low_alerts': low_alerts,
    })

@login_required
@user_passes_test(lambda u: u.role in ['manager', 'receptionist'])
def mark_payment_received(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id)
    
    if not booking.is_paid:
        booking.is_paid = True
        booking.paid_at = timezone.now()
        booking.payment_method = 'cash'  
        booking.save()
        messages.success(request, f"Marked Booking #{booking.id} as paid.")
    else:
        messages.warning(request, "This booking is already marked as paid.")
    
    return redirect('booking_list')  

@login_required
def receptionist_dashboard(request):
    return render(request, 'core/dashboard_receptionist.html')


@login_required
def housekeeping_dashboard(request):
    if request.user.role != 'housekeeping':
        return redirect('login')

    tasks = Booking.objects.filter(
        status='Checked Out',
        cleaned_by__isnull=True,
    ).order_by('-check_out')

    return render(request, 'core/dashboard_housekeeping.html', {
        'tasks': tasks,
    })
    

@login_required
def guest_dashboard(request):
    check_in = request.GET.get('check_in')
    check_out = request.GET.get('check_out')
    rooms = Room.objects.all()  
    search_performed = False

    if check_in and check_out:
        search_performed = True
        try:
            check_in_date = datetime.strptime(check_in, '%Y-%m-%d').date()
            check_out_date = datetime.strptime(check_out, '%Y-%m-%d').date()

            if check_in_date >= check_out_date:
                messages.error(request, "❌ Check-out must be after check-in.")
                rooms = []
            elif check_in_date < date.today():
                messages.error(request, "❌ Check-in date cannot be in the past.")
                rooms = []
            else:
                # Exclude already booked or maintenance rooms
                booked = Booking.objects.filter(
                    check_in__lt=check_out_date,
                    check_out__gt=check_in_date,
                    status__in=['Pending', 'Checked In']
                ).values_list('room_id', flat=True)

                maintenance = Maintenance.objects.filter(
                    scheduled_date__gte=date.today(),
                    is_completed=False
                ).values_list('room_id', flat=True)

                rooms = rooms.exclude(id__in=booked).exclude(id__in=maintenance)

        except ValueError:
            messages.error(request, "❌ Invalid date format. Please use YYYY-MM-DD.")
            rooms = []

    context = {
        'rooms': rooms,
        'check_in': check_in,
        'check_out': check_out,
        'search_performed': search_performed
    }
    return render(request, 'core/dashboard_guest.html', context)


# ============================
# 👤 Guest Booking Views
# ============================

@login_required
def guest_booking_create(request):
    """
    Allows guests to create a booking for themselves with date conflict check.
    """
    if request.user.role != 'guest':
        return redirect('login')  

    if request.method == 'POST':
        form = BookingForm(request.POST, request.FILES)
        if form.is_valid():
            room = form.cleaned_data['room']
            check_in = form.cleaned_data['check_in']
            check_out = form.cleaned_data['check_out']

            # Check for date conflict
            if not is_room_available(room, check_in, check_out):
                messages.error(request, "Room is already booked for the selected dates.")
                return redirect('guest_booking_create')

            booking = form.save(commit=False)
            booking.user = request.user
            booking.save()
            form.save_m2m()

            # ✅ Create Notification for Guest
            Notification.objects.create(
                user=booking.user,
                message=f"✅ Your booking for Room {booking.room.room_number} is confirmed from {booking.check_in}."
            )

            for staff in User.objects.filter(role='receptionist'):
                Notification.objects.create(
                    user=staff,
                    message=f"📅 New booking for Room {booking.room.room_number} by {booking.user.username}."
                )

            messages.success(request, "Booking successful.")
            return redirect('razorpay_payment', booking_id=booking.id)
    else:
        form = BookingForm()

    return render(request, 'core/guest_booking_create.html', {'form': form})

@login_required
def guest_booking_list(request):
    if request.user.role != 'guest':
        return redirect('login')

    bookings = Booking.objects.filter(user=request.user).prefetch_related('feedback_set').order_by('-created_at')
    return render(request, 'core/guest_booking_list.html', {'bookings': bookings})



# ================================
# 👩‍💼 Receptionist Booking Views
# ================================

def is_receptionist(user):
    """
    Check if user is a receptionist.
    Used with @user_passes_test for access control.
    """
    return user.is_authenticated and user.role == 'receptionist'

from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, redirect
from django.contrib import messages
from .forms import ReceptionistBookingForm
from .utils import is_room_available  
from .models import Booking

def is_receptionist(user):
    return user.role == 'receptionist'

@login_required
@user_passes_test(lambda u: u.role == 'receptionist')  
def walkin_booking(request):
    if request.method == 'POST':
        user_form = GuestUserForm(request.POST)
        profile_form = GuestProfileForm(request.POST, request.FILES)
        booking_form = WalkInBookingForm(request.POST)

        if user_form.is_valid() and profile_form.is_valid() and booking_form.is_valid():
            user = user_form.save(commit=False)
            password = User.objects.make_random_password()
            user.set_password(password)
            user.save()

            profile = profile_form.save(commit=False)
            profile.user = user
            profile.save()

            booking = booking_form.save(commit=False)
            booking.user = user
            booking.is_paid = True  
            booking.save()

            messages.success(request, f"✅ Booking created for {user.username}.")
            return redirect('booking_list')
    else:
        user_form = GuestUserForm()
        profile_form = GuestProfileForm()
        booking_form = WalkInBookingForm()

    return render(request, 'core/walkin_booking.html', {
        'user_form': user_form,
        'profile_form': profile_form,
        'booking_form': booking_form,
    })


@login_required
@user_passes_test(is_receptionist)
def receptionist_booking_create(request):
    """
    Allows receptionists to create walk-in bookings on behalf of guests,
    including amenities and spa selection.
    """
    if request.method == 'POST':
        form = ReceptionistBookingForm(request.POST)
        if form.is_valid():
            room = form.cleaned_data['room']
            check_in = form.cleaned_data['check_in']
            check_out = form.cleaned_data['check_out']

            # ✅ Check room availability
            if not is_room_available(room, check_in, check_out):
                messages.error(request, "❌ Room is already booked for the selected dates.")
                return redirect('receptionist_booking_create')

            # ✅ Save booking
            booking = form.save(commit=False)
            booking.created_at = now()
            booking.save()
            form.save_m2m()

            messages.success(request, "✅ Walk-in booking created successfully.")
            return redirect('receptionist_bookings')
    else:
        form = ReceptionistBookingForm()

    return render(request, 'core/receptionist_booking_create.html', {'form': form})


@login_required
@user_passes_test(is_receptionist)
def receptionist_booking_list(request):
    bookings = Booking.objects.all().order_by('-created_at')
    return render(request, 'core/receptionist_booking_list.html', {
        'bookings': bookings,
        'today': date.today(),  
    })

@login_required
@user_passes_test(is_receptionist)
def booking_cancel(request, booking_id):
    """
    Receptionist cancels a booking by ID.
    """
    booking = Booking.objects.get(id=booking_id)
    booking.status = 'Canceled'
    booking.save()
    return redirect('receptionist_bookings')


@login_required
def payment_list(request):
    if request.user.role not in ['manager', 'receptionist']:
        messages.error(request, "You don't have permission to view this page.")
        return redirect('dashboard')

    bookings = Booking.objects.select_related('user', 'room').all().order_by('-created_at')

    total_paid = bookings.filter(is_paid=True).aggregate(total=Sum('total'))['total'] or 0
    total_unpaid = bookings.filter(is_paid=False).aggregate(total=Sum('total'))['total'] or 0

    return render(request, 'core/payment_list.html', {
        'bookings': bookings,
        'total_paid': total_paid,
        'total_unpaid': total_unpaid,
    })

#cleaning

@login_required
@require_POST
def mark_cleaned(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id)

    if request.method == 'POST' and request.user.role == 'housekeeping':
        booking.cleaned_by = request.user
        booking.cleaned_at = timezone.now()
        booking.save()
        messages.success(request, f"✅ Room {booking.room.room_number} marked as cleaned.")
        return redirect('cleaned_rooms_history')
    
    return redirect('housekeeping_dashboard')

@login_required
def cleaned_rooms_history(request):
    if request.user.role not in ['housekeeping', 'admin']:
        return redirect('login')

    if request.user.role == 'housekeeping':
        # Housekeeper sees rooms that are Checked Out and not yet cleaned OR already cleaned by them
        cleaned_tasks = Booking.objects.filter(
            status='Checked Out'
        ).order_by('-check_out')
    else:
        # Admin sees all cleaned rooms (with cleaned_by not null)
        cleaned_tasks = Booking.objects.filter(
            cleaned_by__isnull=False
        ).order_by('-cleaned_at')

    return render(request, 'core/cleaned_rooms_history.html', {
        'cleaned_tasks': cleaned_tasks
    })
    
    
#----------------------------------------maintenance----------------------------------------------

def can_add_maintenance(user):
    return user.is_authenticated and user.role in ['admin', 'manager', 'housekeeping']

@login_required
@user_passes_test(can_add_maintenance)
def maintenance_create(request):
    initial_data = {}
    room_id = request.GET.get('room')

    if room_id:
        try:
            room = Room.objects.get(id=room_id)
            initial_data['room'] = room
        except Room.DoesNotExist:
            messages.warning(request, "Selected room does not exist.")
            return redirect('maintenance_list')

    if request.method == 'POST':
        form = MaintenanceForm(request.POST)
        if form.is_valid():
            maintenance = form.save()

            
            housekeepers = User.objects.filter(role='housekeeping')
            for staff in housekeepers:
                Notification.objects.create(
                    user=staff,
                    message=f"🛠 New maintenance task assigned: Room {maintenance.room.room_number}."
                )

            messages.success(request, "Maintenance request added and housekeeping notified.")
            return redirect('maintenance_list')
    else:
        form = MaintenanceForm(initial=initial_data)

    return render(request, 'core/maintenance_form.html', {'form': form})

@login_required
def maintenance_list(request):
    if request.user.role not in ['admin', 'manager', 'housekeeping', 'receptionist']:
        messages.error(request, "Access denied.")
        return redirect('dashboard')

    tasks = Maintenance.objects.all().order_by('-scheduled_date')
    can_complete = request.user.role in ['admin', 'manager', 'housekeeping']
    return render(request, 'core/maintenance_list.html', {
        'tasks': tasks,
        'can_complete': can_complete
    })


@login_required
@require_POST
def maintenance_mark_completed(request, maintenance_id):
    maintenance = get_object_or_404(Maintenance, id=maintenance_id)

    if request.user.role not in ['admin', 'manager', 'housekeeping']:
        messages.error(request, "You do not have permission.")
        return redirect('maintenance_list')

    if maintenance.is_completed:
        messages.info(request, "This task is already completed.")
    else:
        maintenance.is_completed = True
        maintenance.save()
        messages.success(request, "Marked as completed.")

    return redirect('maintenance_list')

#-----------------------------------inventory--------------------------

def is_manager(user):
    return user.is_authenticated and user.role == 'manager'

@login_required
@user_passes_test(is_manager)
def inventory_list(request):
    items = InventoryItem.objects.all().order_by('name')
    return render(request, 'core/inventory_list.html', {'items': items})

@login_required
@user_passes_test(is_manager)
def inventory_create(request):
    if request.method == 'POST':
        form = InventoryItemForm(request.POST)
        if form.is_valid():
            item = form.save()
            messages.success(request, "Item added to inventory.")
            return redirect('inventory_list')
    else:
        form = InventoryItemForm()
    return render(request, 'core/inventory_form.html', {'form': form})

@login_required
@user_passes_test(is_manager)
def log_inventory_usage(request):
    if request.method == 'POST':
        form = InventoryUsageForm(request.POST)
        if form.is_valid():
            usage = form.save()
            item = usage.item
            item.quantity -= usage.quantity_used
            item.save()
            messages.success(request, "✅ Inventory usage logged.")
            return redirect('inventory_list')
    else:
        form = InventoryUsageForm()
    return render(request, 'core/inventory_usage_form.html', {'form': form})


@login_required
@user_passes_test(is_manager)
def inventory_edit(request, pk):
    item = get_object_or_404(InventoryItem, pk=pk)
    if request.method == 'POST':
        form = InventoryItemForm(request.POST, instance=item)
        if form.is_valid():
            form.save()
            messages.success(request, "Item updated successfully.")
            return redirect('inventory_list')
    else:
        form = InventoryItemForm(instance=item)
    return render(request, 'core/inventory_form.html', {'form': form, 'edit': True})


#------------payment--------------

@login_required
def booking_payment_view(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id, user=request.user)

    # 🧮 Calculate Bill
    bill = calculate_bill(booking)

    if request.method == 'POST':
        payment_method = request.POST.get('payment_method')
        booking.payment_method = payment_method
        booking.is_paid = True  # Set only if cash
        booking.save()
        messages.success(request, "Payment recorded successfully.")
        return redirect('guest_booking_list')

    return render(request, 'core/booking_payment.html', {
        'booking': booking,
        'bill': bill
    })
    
    
import razorpay
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

@login_required
def initiate_razorpay_payment(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id, user=request.user)

    # 🔢 Calculate the full bill
    bill = calculate_bill(booking)

    # ✅ Convert total to paisa (round to avoid float issues)
    amount_in_paisa = int(round(float(bill['total']) * 100))

    # 💳 Create Razorpay Order
    payment = client.order.create({
        "amount": amount_in_paisa,  # paisa (₹ x 100)
        "currency": "INR",
        "receipt": f"booking_rcpt_{booking.id}",
        "payment_capture": 1
    })
    print("✅ Created Razorpay Order:", payment)

    # 💾 Save Razorpay order ID
    booking.payment_id = payment['id']
    booking.save()

    return render(request, 'core/razorpay_payment.html', {
        'booking': booking,
        'razorpay_key': settings.RAZORPAY_KEY_ID,
        'razorpay_order_id': payment['id'],
        'amount': amount_in_paisa,  # ⚠️ Int only, no float/decimal
        'user': request.user,
        'breakdown': bill,
    })
  
key_id = settings.RAZORPAY_KEY_ID
key_secret = settings.RAZORPAY_KEY_SECRET

@csrf_exempt
def payment_success(request):
    if request.method == "POST":
        payment_id = request.POST.get('razorpay_payment_id')
        order_id = request.POST.get('razorpay_order_id')
        signature = request.POST.get('razorpay_signature')

        try:
            # ✅ Step 1: Verify signature
            client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
            client.utility.verify_payment_signature({
                'razorpay_order_id': order_id,
                'razorpay_payment_id': payment_id,
                'razorpay_signature': signature
            })

            # ✅ Step 2: Update booking
            booking = Booking.objects.get(payment_id=order_id)
            booking.is_paid = True
            booking.paid_at = timezone.now()
            booking.razorpay_payment_id = payment_id
            booking.payment_time = timezone.now()
            booking.save()

            # ✅ Step 3: Generate bill breakdown
            bill = calculate_bill(booking)

            # ✅ Step 4: Render PDF invoice
            html = render_to_string("core/invoice_pdf.html", {
                "booking": booking,
                "breakdown": bill,
            })

            pdf_file = BytesIO()
            pisa.CreatePDF(BytesIO(html.encode("UTF-8")), dest=pdf_file)

            # ✅ Step 5: Send confirmation email with PDF
            subject = f"🎉 Booking Confirmed - Room {booking.room.room_number} | Royal Crest"
            to_email = booking.user.email

            email_body = render_to_string("core/booking_email.html", {
                "booking": booking,
                "user": booking.user,
                "total": bill['total'],
                "breakdown": bill,
            })

            email = EmailMessage(
                subject=subject,
                body=email_body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[to_email],
            )
            email.attach(f"invoice_booking_{booking.id}.pdf", pdf_file.getvalue(), "application/pdf")
            email.content_subtype = "html"
            email.send()

            messages.success(request, "✅ Payment successful and invoice sent to your email.")
            return redirect('invoice_view', booking_id=booking.id)

        except Booking.DoesNotExist:
            messages.error(request, "❌ Booking not found.")
            return redirect('booking_list')

        except razorpay.errors.SignatureVerificationError as e:
            print("❌ Razorpay Signature Verification Failed:", e)
            return HttpResponseBadRequest("Payment verification failed")

    return HttpResponseBadRequest("Invalid request")


@login_required
def invoice_view(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id, user=request.user)
    breakdown = calculate_bill(booking)

    return render(request, 'core/invoice.html', {
        'booking': booking,
        'breakdown': breakdown
    })

from xhtml2pdf import pisa
from django.template.loader import get_template
@login_required
def download_invoice_pdf(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id, user=request.user)
    breakdown = calculate_bill(booking)

    template_path = 'core/invoice_pdf.html'
    context = {'booking': booking, 'breakdown': breakdown}

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="Invoice_{booking.id}.pdf"'

    template = get_template(template_path)
    html = template.render(context)

    pisa_status = pisa.CreatePDF(html, dest=response)

    if pisa_status.err:
        return HttpResponse('PDF generation error', status=500)
    return response


#----feedback------
@login_required
def feedback_list(request):
    if request.user.role not in ['admin', 'manager']:
        return redirect('login')

    feedbacks = Feedback.objects.select_related('user', 'booking__room').order_by('-submitted_at')
    Feedback.objects.filter(is_read=False).update(is_read=True)
    return render(request, 'core/feedback_list.html', {'feedbacks': feedbacks})

@login_required
def submit_feedback(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id, user=request.user)

    if Feedback.objects.filter(booking=booking).exists():
        messages.info(request, "You’ve already submitted feedback for this stay.")
        return redirect('guest_bookings')

    if request.method == 'POST':
        form = FeedbackForm(request.POST)
        if form.is_valid():
            feedback = form.save(commit=False)
            feedback.user = request.user
            feedback.booking = booking
            feedback.save()
            messages.success(request, "✅ Thank you for your feedback!")
            return redirect('guest_bookings')
    else:
        form = FeedbackForm()

    return render(request, 'core/submit_feedback.html', {
        'form': form,
        'booking': booking
    })
    

# Restrict to manager
def manager_required(view_func):
    return user_passes_test(lambda u: u.is_authenticated and u.role == 'manager')(view_func)

@manager_required
def assign_salary(request):
    form = StaffSalaryForm(request.POST or None)
    if form.is_valid():
        salary = form.save(commit=False)
        salary.assigned_by = request.user
        salary.save()
        return redirect('salary_report')
    return render(request, 'core/salary/assign_salary.html', {'form': form})

@manager_required
def mark_attendance(request):
    form = StaffAttendanceForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        attendance = form.save(commit=False)
        
        # Don't allow manager to mark if already present
        already_marked = StaffAttendance.objects.filter(user=attendance.user, date=attendance.date).exists()
        if already_marked:
            messages.warning(request, f"{attendance.user.username} already marked for {attendance.date}.")
        else:
            attendance.present = True
            attendance.save()
            messages.success(request, f"Marked attendance for {attendance.user.username} on {attendance.date}.")
            return redirect('salary_report')

    return render(request, 'core/salary/mark_attendance.html', {'form': form})

@manager_required
def salary_report(request):
    salaries = StaffSalary.objects.all()
    staff_data = []

    for salary in salaries:
        days_present = StaffAttendance.objects.filter(user=salary.user, present=True).count()
        total_salary = days_present * salary.daily_rate
        staff_data.append({
            'user': salary.user,
            'daily_rate': salary.daily_rate,
            'days_present': days_present,
            'total_salary': total_salary
        })

    return render(request, 'core/salary/salary_report.html', {'staff_data': staff_data})

@login_required
def staff_mark_own_attendance(request):
    if request.user.role not in ['receptionist', 'housekeeping']:
        return HttpResponseForbidden("Not allowed")

    today = timezone.now().date()
    already_marked = StaffAttendance.objects.filter(user=request.user, date=today).exists()

    if request.method == 'POST':
        if already_marked:
            messages.info(request, "You have already marked your attendance.")
        else:
            StaffAttendance.objects.create(user=request.user, date=today, present=True)
            messages.success(request, "Attendance marked successfully.")
            return redirect('staff_mark_own_attendance')  # Avoid form resubmission

    return render(request, 'core/salary/staff_attendance_confirmation.html', {
        'already_marked': already_marked
    })

@manager_required
def attendance_list(request):
    attendance_records = StaffAttendance.objects.select_related('user').order_by('-date')
    return render(request, 'core/salary/attendance_list.html', {'attendance_records': attendance_records})


@login_required
def all_notifications_view(request):
    # ✅ Fetch all notifications, newest first
    notifications = request.user.notification_set.order_by('-created_at')
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)

    return render(request, 'notifications/all.html', {
        'notifications': notifications
    })

@login_required
@require_POST
def mark_notifications_read(request):
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    return JsonResponse({'status': 'success'})

def about_us(request):
    return render(request, 'core/about_us.html')

from .forms import ContactForm
from .models import ContactMessage

def contact_us_view(request):
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Your message has been submitted.")
            return redirect('contact')
    else:
        form = ContactForm()
    return render(request, 'core/contact_us.html', {'form': form})

@login_required
def contact_messages_list(request):
    if request.user.role in ['receptionist', 'manager']:
        messages = ContactMessage.objects.order_by('-submitted_at')
        ContactMessage.objects.filter(is_read=False).update(is_read=True)
        return render(request, 'core/contact_messages_list.html', {'messages': messages})
    else:
        return redirect('guest_dashboard') 
     
def unread_contact_messages(request):
    if request.user.is_authenticated and request.user.role in ['receptionist', 'manager']:
        unread_count = ContactMessage.objects.filter(is_read=False).count()
        return {'unread_contact_count': unread_count}
    return {}
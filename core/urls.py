from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    # 🔐 Authentication routes
    path('', views.homepage, name='home'),
    path('login/', views.login_view, name='login'),            # User login page
    path('register/', views.register_view, name='register'),   # User registration page
    path('logout/', views.logout_view, name='logout'),   
    

    # 🏨 Room Management (Admin/Manager)
    path('rooms/', views.room_list, name='room_list'),                  # View list of all rooms
    path('rooms/add/', views.room_create, name='room_create'),         # Add a new room
    path('rooms/<int:pk>/edit/', views.room_update, name='room_update'),  # Edit room details
    path('rooms/<int:pk>/delete/', views.room_delete, name='room_delete'),# Delete a room
    path('available-rooms/', views.available_rooms, name='available_rooms'),

    # 📆 Booking Management (Admin & Guest)
    path('bookings/', views.booking_list, name='booking_list'),         # List bookings (admin sees all, guest sees their own)
    path('bookings/add/', views.booking_create, name='booking_create'), # Create a booking (default form)
    path('bookings/<int:booking_id>/checkin/', views.booking_check_in, name='booking_check_in'),
    path('bookings/<int:booking_id>/checkout/', views.booking_check_out, name='booking_check_out'),
    path('booking/<int:booking_id>/cancel/', views.cancel_booking, name='cancel_booking'),
    path('bookings/add/<int:room_id>/', views.booking_create, name='book_room'),
    

    # 📊 Dashboards for different roles
    path('dashboard/admin/', views.admin_dashboard, name='admin_dashboard'),                 # Admin dashboard
    path('dashboard/manager/', views.manager_dashboard, name='manager_dashboard'),           # Manager dashboard
    path('dashboard/receptionist/', views.receptionist_dashboard, name='receptionist_dashboard'), # Receptionist dashboard
    path('dashboard/housekeeping/', views.housekeeping_dashboard, name='housekeeping_dashboard'), # Housekeeping dashboard
    path('dashboard/guest/', views.guest_dashboard, name='guest_dashboard'),                 # Guest dashboard

    # 👤 Guest Booking
    path('guest/book/', views.guest_booking_create, name='guest_booking_create'),            # Guest creates a booking
    path('guest/bookings/', views.guest_booking_list, name='guest_bookings'),                # Guest views their bookings

    # 🧾 Receptionist Booking (Walk-in or on behalf of guest)
    path('receptionist/book/', views.receptionist_booking_create, name='receptionist_booking_create'),  # Create booking for guest
    path('receptionist/bookings/', views.receptionist_booking_list, name='receptionist_bookings'),      # List all bookings
    path('receptionist/bookings/cancel/<int:booking_id>/', views.booking_cancel, name='booking_cancel'),# Cancel a booking
    path('bookings/checkin/<int:booking_id>/', views.booking_check_in, name='booking_check_in'),
    path('booking/<int:booking_id>/checkout/', views.booking_check_out, name='booking_check_out'),
    path('payments/', views.payment_list, name='payment_list'),
    path('receptionist/bookings/', views.receptionist_booking_list, name='receptionist_booking_list'),
    path('receptionist/walkin-booking/', views.walkin_booking, name='walkin_booking'),
    
    #cleaning_staff
    path('housekeeping/cleaned/<int:booking_id>/', views.mark_cleaned, name='mark_cleaned'),
    path('housekeeping/history/', views.cleaned_rooms_history, name='cleaned_rooms_history'),
    
    #maintenance
    path('maintenance/add/', views.maintenance_create, name='maintenance_create'),
    path('maintenance/', views.maintenance_list, name='maintenance_list'),
    path('maintenance/<int:maintenance_id>/complete/', views.maintenance_mark_completed, name='maintenance_mark_completed'),
    
    #inventory
    path('inventory/', views.inventory_list, name='inventory_list'),
    path('inventory/add/', views.inventory_create, name='inventory_create'),  
    path('inventory/log-usage/', views.log_inventory_usage, name='log_inventory_usage'),
    path('inventory/<int:pk>/edit/', views.inventory_edit, name='inventory_edit'),
    
    # payment
    path('booking/<int:booking_id>/pay/', views.booking_payment_view, name='booking_payment'),
    path('booking/<int:booking_id>/razorpay/', views.initiate_razorpay_payment, name='razorpay_payment'),
    path('payment/success/', views.payment_success, name='payment_success'),
    path('invoice/<int:booking_id>/', views.invoice_view, name='invoice_view'),
    path('invoice/<int:booking_id>/download/', views.download_invoice_pdf, name='download_invoice'),
    
    #feedback
    path('feedback/submit/', views.submit_feedback, name='submit_feedback'),
    path('feedbacks/', views.feedback_list, name='feedback_list'),
    path('feedback/submit/<int:booking_id>/', views.submit_feedback, name='submit_feedback'),
    
    # Salary & Attendance
    path('salary/assign/', views.assign_salary, name='assign_salary'),
    path('salary/attendance/', views.mark_attendance, name='mark_attendance'),
    path('salary/report/', views.salary_report, name='salary_report'),
    path('attendance/mark/', views.staff_mark_own_attendance, name='staff_mark_attendance'),
    path('attendance/mark/', views.staff_mark_own_attendance, name='staff_mark_own_attendance'),
    path('salary/attendance/list/', views.attendance_list, name='attendance_list'),
    path('notifications/', views.all_notifications_view, name='all_notifications'),
    path('notifications/mark-read/', views.mark_notifications_read, name='mark_notifications_read'),
    
    
    path('about/', views.about_us, name='about_us'),
    path('contact/', views.contact_us_view, name='contact'),
    path('contact/messages/', views.contact_messages_list, name='contact_messages_list'),
    
    # Password Reset
    path('password-reset/', auth_views.PasswordResetView.as_view(template_name='core/password_reset.html'), name='password_reset'),
    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(template_name='core/password_reset_done.html'), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(template_name='core/password_reset_confirm.html'), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(template_name='core/password_reset_complete.html'), name='password_reset_complete'),
    
]

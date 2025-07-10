from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html
from .models import GuestProfile
from .models import StaffSalary, StaffAttendance
from .models import (
    CustomUser,
    Room,
    Booking,
    Maintenance,
    Feedback,
    Amenity,
    RoomImage,
    SpaService
)

# --- Custom User Admin ---
class CustomUserAdmin(UserAdmin):
    model = CustomUser
    list_display = ('username', 'email', 'role', 'is_staff')
    fieldsets = UserAdmin.fieldsets + (
        (None, {'fields': ('role',)}),
    )

admin.site.register(CustomUser, CustomUserAdmin)

# --- RoomImage Inline ---
class RoomImageInline(admin.TabularInline):
    model = RoomImage
    extra = 1

# --- Room Admin with Inline Images ---
@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ('room_number', 'room_type', 'price_per_night', 'is_available')
    inlines = [RoomImageInline]

# --- Booking Admin ---
from django.utils.html import format_html

@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'user',
        'room',
        'check_in',
        'check_out',
        'status',
        'is_paid',
        'needs_cleaning',
        'cleaned_by',
        'cleaned_at',
        'created_at',
        'id_proof_thumbnail',  
    )
    list_filter = (
        'status',
        'is_paid',
        'needs_cleaning',
        'cleaned_by',
        'check_in',
        'check_out',
    )
    search_fields = ('user__username', 'room__room_number')

    def id_proof_thumbnail(self, obj):
        if obj.id_proof:
            return format_html('<a href="{}" target="_blank"><img src="{}" width="60" height="60" style="object-fit:cover;" /></a>', obj.id_proof.url, obj.id_proof.url)
        return "-"
    id_proof_thumbnail.short_description = "ID Proof"


# --- Feedback Admin ---
@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    list_display = ('user', 'booking', 'rating', 'submitted_at')
    search_fields = ('user__username', 'booking__room__room_number')

# --- Amenity Admin ---
@admin.register(Amenity)
class AmenityAdmin(admin.ModelAdmin):
    list_display = ['name']

# --- Maintenance Admin ---
admin.site.register(Maintenance)

# --- RoomImage Admin (for separate image management if needed) ---
@admin.register(RoomImage)
class RoomImageAdmin(admin.ModelAdmin):
    list_display = ('room', 'image')
    
    
@admin.register(SpaService)
class SpaServiceAdmin(admin.ModelAdmin):
    list_display = ('name', 'price')
    search_fields = ('name',)

@admin.register(GuestProfile)
class GuestProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'phone', 'id_proof_thumbnail']
    readonly_fields = ['id_proof_preview']

    def id_proof_thumbnail(self, obj):
        if obj.id_proof:
            return f'<img src="{obj.id_proof.url}" width="60" height="60" style="object-fit:cover;" />'
        return "-"
    id_proof_thumbnail.short_description = "ID Proof"
    id_proof_thumbnail.allow_tags = True

    def id_proof_preview(self, obj):
        if obj.id_proof:
            return f'<img src="{obj.id_proof.url}" width="300" />'
        return "No ID Proof Uploaded"
    id_proof_preview.short_description = "ID Proof Preview"
    id_proof_preview.allow_tags = True
    
admin.site.register(StaffSalary)
admin.site.register(StaffAttendance)
    
# toko/admin.py
from django.contrib import admin
from .models import Notification, Order
from .models import Produk, Pesanan, PesananItem

class NotificationAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'status', 'is_read', 'created_at')
    list_filter = ('status', 'is_read', 'created_at')
    search_fields = ('title', 'message', 'user__username', 'user__email')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('-created_at',)
    
    fieldsets = (
        ('Informasi Notifikasi', {
            'fields': ('user', 'title', 'message', 'status')
        }),
        ('Status Pembacaan', {
            'fields': ('is_read',)
        }),
        ('Informasi Tambahan', {
            'fields': ('order_id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['mark_as_read', 'mark_as_unread']
    
    def mark_as_read(self, request, queryset):
        queryset.update(is_read=True)
        self.message_user(request, f"{queryset.count()} notifikasi ditandai sebagai sudah dibaca.")
    mark_as_read.short_description = "Tandai sebagai sudah dibaca"
    
    def mark_as_unread(self, request, queryset):
        queryset.update(is_read=False)
        self.message_user(request, f"{queryset.count()} notifikasi ditandai sebagai belum dibaca.")
    mark_as_unread.short_description = "Tandai sebagai belum dibaca"

# ===== ADMIN ORDER =====
class OrderAdmin(admin.ModelAdmin):
    list_display = ('order_id', 'user', 'total', 'status', 'payment_method', 'created_at')
    list_filter = ('status', 'payment_method', 'created_at')
    search_fields = ('order_id', 'user__username', 'user__email')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('-created_at',)
    
    fieldsets = (
        ('Informasi Pesanan', {
            'fields': ('order_id', 'user', 'items', 'total', 'status')
        }),
        ('Pengiriman & Pembayaran', {
            'fields': ('shipping_cost', 'shipping_service', 'payment_method', 'address')
        }),
        ('Informasi Tambahan', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['mark_as_dikemas', 'mark_as_dikirim', 'mark_as_selesai', 'mark_as_dibatalkan']
    
    def mark_as_dikemas(self, request, queryset):
        queryset.update(status='dikemas')
        self.message_user(request, f"{queryset.count()} pesanan ditandai sebagai DIKEMAS.")
    mark_as_dikemas.short_description = "Tandai sebagai DIKEMAS"
    
    def mark_as_dikirim(self, request, queryset):
        queryset.update(status='dikirim')
        self.message_user(request, f"{queryset.count()} pesanan ditandai sebagai DIKIRIM.")
    mark_as_dikirim.short_description = "Tandai sebagai DIKIRIM"
    
    def mark_as_selesai(self, request, queryset):
        queryset.update(status='selesai')
        self.message_user(request, f"{queryset.count()} pesanan ditandai sebagai SELESAI.")
    mark_as_selesai.short_description = "Tandai sebagai SELESAI"
    
    def mark_as_dibatalkan(self, request, queryset):
        queryset.update(status='dibatalkan')
        self.message_user(request, f"{queryset.count()} pesanan ditandai sebagai DIBATALKAN.")
    mark_as_dibatalkan.short_description = "Tandai sebagai DIBATALKAN"

admin.site.register(Order, OrderAdmin)


@admin.register(Produk)
class ProdukAdmin(admin.ModelAdmin):
    list_display = ['name', 'brand', 'price', 'product_type', 'rating']
    search_fields = ['name', 'brand']
    list_filter = ['brand', 'product_type']
    
@admin.register(Pesanan)
class PesananAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'total', 'status', 'tanggal_pesan']
    list_filter = ['status']
    search_fields = ['id', 'user__username']

@admin.register(PesananItem)
class PesananItemAdmin(admin.ModelAdmin):
    list_display = ['pesanan', 'produk', 'jumlah', 'harga']
from django.urls import path, include
from . import views

app_name = 'toko'

urlpatterns = [
    path('', views.home, name='home'),
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    path('notifications/', views.notifications_view, name='notifications'),
    path('kategori/', views.kategori_view, name='kategori'),
    path('favorit/', views.favorit_view, name='favorit'),
    path('lihat-semua/', views.lihat_semua_view, name='lihat_semua'),
    path('produk/<str:product_id>/', views.detail_produk_view, name='detail_produk'),
    path('keranjang/', views.keranjang_view, name='keranjang'),
    path('checkout/', views.checkout_view, name='checkout'),
    path('pesanan-berhasil/', views.pesanan_berhasil_view, name='pesanan_berhasil'),
    path('tambah-alamat/', views.tambah_alamat_view, name='tambah_alamat'),
    path('akun/', views.akun_view, name='akun'),
    path('bantuan/', views.bantuan_view, name='bantuan'),
    path('pengaturan/', views.pengaturan_view, name='pengaturan'),

    # API Endpoints (untuk frontend)
    path('api/provinces/', views.api_provinces, name='api_provinces'),
    path('api/cities/<int:province_id>/', views.api_cities, name='api_cities'),
    path('api/search-city/', views.api_search_city, name='api_search_city'),
    path('api/districts/<int:city_id>/', views.api_districts, name='api_districts'),
    path('api/shipping-cost/', views.api_shipping_cost, name='api_shipping_cost'),

    # Notifikasi API
    path('api/notifications/', views.get_notifications, name='api_notifications'),
    path('api/notifications/mark-all-read/', views.mark_all_notifications_read, name='api_mark_all_read'),
    path('api/notifications/mark-read/<int:notif_id>/', views.mark_notification_read, name='api_mark_read'),
    path('api/notifications/unread-count/', views.get_unread_count, name='api_unread_count'),
    path('api/notifications/count/', views.get_unread_count, name='api_notifications_count'),
    
    # Api pembayaran
    path('api/create-xendit-payment/', views.create_xendit_payment, name='create_xendit_payment'),
    path('payment/status/<str:order_id>/', views.payment_status_page, name='payment_status_page'),
    path('payment/success/', views.payment_success, name='payment_success'),
    path('payment/failed/', views.payment_failed, name='payment_failed'),

    # URL PESANAN
    path('pesanan-saya/', views.pesanan_saya_view, name='pesanan_saya'),
    path('pesanan/<str:order_id>/', views.detail_pesanan_view, name='detail_pesanan'),
    path('api/update-order-status/', views.update_order_status, name='update_order_status'),
    
    path('api/save-order/', views.save_order, name='save_order'),
    path('api/pesanan-saya/', views.get_pesanan_user, name='api_pesanan_saya'),
    path('api/batal-pesanan/', views.batal_pesanan, name='api_batal_pesanan'),
    path('api/selesai-pesanan/', views.selesai_pesanan, name='api_selesai_pesanan'),

    # AI CHAT
    path('ai-chat/', views.ai_chat_view, name='ai_chat'),
    path('api/ai-chat/', views.ai_chat_api, name='ai_chat_api'),

    # ===== ADMIN DASHBOARD =====
    path('dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('dashboard/orders/', views.admin_orders, name='admin_orders'),
    path('dashboard/users/', views.admin_users, name='admin_users'),
    path('dashboard/products/', views.admin_products, name='admin_products'),
    path('dashboard/notifications/', views.admin_notifications, name='admin_notifications'),
    path('api/admin/update-order-status/', views.admin_update_order_status, name='admin_update_order_status'),
    path('api/admin/send-notification/', views.admin_send_notification, name='admin_send_notification'),
    path('api/update-user-role/', views.update_user_role, name='update_user_role'),
]
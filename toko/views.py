from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.http import JsonResponse
from django.conf import settings
from .models import Order, Notification
from django.views.decorators.csrf import csrf_exempt
from .rajaongkir import get_provinces, get_cities, get_shipping_cost, get_districts, search_city
from .xendit_payment import XenditPayment
import uuid
import json
import os
import requests
import re
from .models import Pesanan, PesananItem, Produk, Notification  
from decimal import Decimal
import google.generativeai as genai

#==============
# fungsi admin
#===============
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Count, Sum, Q
from datetime import datetime, timedelta
from django.core.files.base import ContentFile

# ===== HELPER FUNCTIONS FOR ORDERS =====
def get_orders():
    """Mendapatkan semua orders dari database"""
    orders = Order.objects.all().values(
        'order_id', 'items', 'total', 'status', 
        'created_at', 'user_id', 'shipping_cost',
        'payment_method', 'shipping_service'
    )
    # Konversi ke list of dict
    result = []
    for order in orders:
        result.append({
            'order_id': order['order_id'],
            'items': order['items'],
            'total': float(order['total']),
            'status': order['status'],
            'date': order['created_at'].isoformat(),
            'user_id': order['user_id'],
            'shipping_cost': float(order['shipping_cost']) if order['shipping_cost'] else 0,
            'payment_method': order['payment_method'],
            'shipping_service': order['shipping_service']
        })
    return result

@login_required
@csrf_exempt
def save_order(request):
    """API untuk menyimpan order ke database"""
    if request.method != 'POST':
        return JsonResponse({
            'success': False, 
            'error': 'Method tidak diizinkan'
        }, status=405)
    
    try:
        data = json.loads(request.body)
        
        # Buat pesanan baru dengan total sementara 0
        pesanan = Pesanan.objects.create(
            user=request.user,
            total=0,  # Sementara 0, akan diupdate nanti
            status=data.get('status', 'menunggu'),
            alamat_pengiriman=data.get('address', {}).get('alamat', ''),
            catatan=data.get('catatan', '')
        )
        
        total = 0
        
        # Simpan items dan hitung total
        items = data.get('items', [])
        for item_data in items:
            try:
                produk = Produk.objects.get(id=item_data.get('id'))
                harga = float(item_data.get('price', 0))
                jumlah = int(item_data.get('quantity', 1))
                subtotal = harga * jumlah
                total += subtotal
                
                PesananItem.objects.create(
                    pesanan=pesanan,
                    produk=produk,
                    jumlah=jumlah,
                    harga=harga
                )
            except Produk.DoesNotExist:
                # Jika produk tidak ditemukan, lanjutkan
                continue
        
        # Update total pesanan
        pesanan.total = total
        pesanan.save()
        
        return JsonResponse({
            'success': True,
            'order_id': pesanan.id,
            'total': total,
            'message': 'Order berhasil disimpan'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

# ===== VIEWS =====

@staff_member_required
@login_required
def admin_dashboard(request):
    """Dashboard Admin"""
    # Cek apakah user adalah admin
    if not request.user.is_staff:
        return redirect('toko:beranda')
    
    # Total pesanan
    total_orders = Pesanan.objects.count()
    
    # Total user
    total_users = User.objects.count()
    
    # ===== TOTAL PENDAPATAN (Pesanan dengan status dikirim atau selesai) =====
    # Pendapatan dari pesanan yang sudah dikirim atau selesai
    total_revenue = Pesanan.objects.filter(
        Q(status='dikirim') | Q(status='selesai')
    ).aggregate(Sum('total'))['total__sum'] or 0
    
    # Detail pendapatan per status (untuk informasi tambahan)
    revenue_dikirim = Pesanan.objects.filter(status='dikirim').aggregate(Sum('total'))['total__sum'] or 0
    revenue_selesai = Pesanan.objects.filter(status='selesai').aggregate(Sum('total'))['total__sum'] or 0

    # Status counts
    status_counts = {
        'menunggu': Pesanan.objects.filter(status='menunggu').count(),
        'dikemas': Pesanan.objects.filter(status='dikemas').count(),
        'dikirim': Pesanan.objects.filter(status='dikirim').count(),
        'selesai': Pesanan.objects.filter(status='selesai').count(),
        'dibatalkan': Pesanan.objects.filter(status='dibatalkan').count(),
    }
    
    # Pesanan terbaru (5 terakhir) dengan prefetch items dan produk
    orders = Pesanan.objects.prefetch_related(
        'items__produk'
    ).all().order_by('-tanggal_pesan')[:5]
    
    context = {
        'total_orders': total_orders,
        'total_users': total_users,
        'total_revenue': total_revenue,
        'status_counts': status_counts,
        'orders': orders,
    }
    
    return render(request, 'admin/admin_dashboard.html', context)

@staff_member_required
@login_required
def admin_orders(request):
    """Halaman kelola pesanan untuk admin"""
    # Cek apakah user adalah admin
    if not request.user.is_staff:
        return redirect('toko:beranda')
    
    # Ambil semua pesanan dari database dengan prefetch items dan produk
    orders = Pesanan.objects.prefetch_related(
        'items__produk'
    ).all().order_by('-tanggal_pesan')
    
    context = {
        'orders': orders,
    }
    
    return render(request, 'admin/orders.html', context)

@staff_member_required
def admin_update_order_status(request):
    """API untuk update status pesanan"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method POST required'}, status=405)
    
    try:
        data = json.loads(request.body)
        order_id = data.get('order_id')
        new_status = data.get('status')
        
        # Cari order di database
        try:
            order = Order.objects.get(order_id=order_id)
            old_status = order.status
            order.status = new_status
            order.save()
            
            # ===== KIRIM NOTIFIKASI KE USER =====
            status_labels = {
                'menunggu': 'Menunggu Konfirmasi',
                'dikemas': 'Sedang Dikemas',
                'dikirim': 'Sedang Dikirim',
                'selesai': 'Selesai',
                'dibatalkan': 'Dibatalkan'
            }
            
            status_icons = {
                'menunggu': '⏳',
                'dikemas': '📦',
                'dikirim': '🚚',
                'selesai': '✅',
                'dibatalkan': '❌'
            }
            
            status_messages = {
                'menunggu': 'Pesanan Anda sedang menunggu konfirmasi.',
                'dikemas': 'Pesanan Anda sedang dikemas oleh tim kami.',
                'dikirim': 'Pesanan Anda telah dikirim! Silakan cek status pengiriman.',
                'selesai': 'Pesanan Anda telah selesai. Terima kasih telah berbelanja!',
                'dibatalkan': 'Pesanan Anda dibatalkan. Silakan hubungi CS jika ada pertanyaan.'
            }
            
            # Buat notifikasi untuk user
            if order.user:
                Notification.objects.create(
                    user=order.user,
                    title=f"{status_icons.get(new_status, '📋')} Status Pesanan {order_id}",
                    message=f"Status pesanan Anda berubah menjadi: {status_labels.get(new_status, new_status)}\n{status_messages.get(new_status, '')}",
                    status=new_status,
                    order_id=order_id
                )
            
            return JsonResponse({
                'success': True,
                'new_status': new_status,
                'old_status': old_status
            })
            
        except Order.DoesNotExist:
            return JsonResponse({'error': 'Order not found'}, status=404)
            
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@staff_member_required
def admin_users(request):
    """Kelola User"""
    users = User.objects.all().order_by('-date_joined')
    return render(request, 'admin/users.html', {'users': users})

@staff_member_required
def admin_products(request):
    """Kelola Produk"""
    try:
        response = requests.get('https://makeup-api.herokuapp.com/api/v1/products.json?brand=maybelline', timeout=10)
        products = response.json() if response.status_code == 200 else []
    except:
        products = []
    return render(request, 'admin/products.html', {'products': products})

@staff_member_required
def admin_notifications(request):
    """Kirim Notifikasi Massal"""
    return render(request, 'admin/notifications.html')

@staff_member_required
def admin_send_notification(request):
    """API untuk kirim notifikasi massal"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method POST required'}, status=405)
    
    try:
        data = json.loads(request.body)
        title = data.get('title')
        message = data.get('message')
        user_type = data.get('user_type', 'all')
        
        if user_type == 'all':
            users = User.objects.all()
        elif user_type == 'admin':
            users = User.objects.filter(is_staff=True)
        else:
            users = User.objects.filter(is_staff=False)
        
        count = 0
        for user in users:
            Notification.objects.create(
                user=user,
                title=title,
                message=message,
                status='pending'
            )
            count += 1
        
        return JsonResponse({
            'success': True,
            'sent_to': count
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
    
def get_user_orders(user_id):
    """Mendapatkan orders untuk user tertentu"""
    orders = get_orders()
    return [o for o in orders if o.get('user_id') == user_id]

@login_required
@csrf_exempt
def update_user_role(request):
    """API untuk update role user (admin/staff/user)"""
    if request.method != 'POST':
        return JsonResponse({
            'success': False, 
            'error': 'Method tidak diizinkan'
        }, status=405)
    
    # Cek apakah user adalah admin
    if not request.user.is_superuser:
        return JsonResponse({
            'success': False,
            'error': 'Anda tidak memiliki akses'
        }, status=403)
    
    try:
        data = json.loads(request.body)
        user_id = data.get('user_id')
        role = data.get('role')  # 'admin', 'staff', 'user'
        
        user = User.objects.get(id=user_id)
        
        # Jangan izinkan mengubah role sendiri
        if user.id == request.user.id:
            return JsonResponse({
                'success': False,
                'error': 'Tidak dapat mengubah role sendiri'
            }, status=400)
        
        # Update role
        if role == 'admin':
            user.is_superuser = True
            user.is_staff = True
        elif role == 'staff':
            user.is_superuser = False
            user.is_staff = True
        else:  # user
            user.is_superuser = False
            user.is_staff = False
        
        user.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Role user berhasil diubah menjadi {role}'
        })
        
    except User.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'User tidak ditemukan'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

#============
# HOME 
#============
def home(request):
    if request.user.is_authenticated:
        if request.user.is_staff or request.user.is_superuser:
            return redirect('toko:admin_dashboard')
        else:
            # Arahkan ke halaman produk atau halaman user
            return redirect('toko:home.html')
    else:
        # Jika belum login, tampilkan halaman login
        return render(request, 'toko/login.html')

def login_view(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        
        # Authenticate user
        user = authenticate(request, username=email, password=password)
        
        if user is not None:
            login(request, user)
            messages.success(request, 'Login berhasil!')
            
            # ===== CEK APAKAH ADMIN =====
            if user.is_superuser or user.is_staff:
                return redirect('toko:admin_dashboard')
            else:
                return redirect('toko:home')
        else:
            messages.error(request, 'Email atau password salah.')
    
    return render(request, 'toko/login.html')

def register_view(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')
        
        if password != confirm_password:
            messages.error(request, 'Password tidak cocok.')
            return render(request, 'toko/register.html')
        
        if User.objects.filter(username=email).exists():
            messages.error(request, 'Email sudah terdaftar.')
            return render(request, 'toko/register.html')
        
        # Create user
        user = User.objects.create_user(
            username=email,
            email=email,
            password=password,
            first_name=name
        )
        user.save()
        
        messages.success(request, 'Registrasi berhasil! Silakan login.')
        return redirect('toko:login')
    
    return render(request, 'toko/register.html')

def logout_view(request):
    logout(request)
    return redirect('toko:login')

@login_required
def akun_view(request):
    return render(request, 'toko/akun.html')

@login_required
def notifications_view(request):
    notifications = Notification.objects.filter(user=request.user)
    unread_count = notifications.filter(is_read=False).count()
    
    # Tandai semua sebagai sudah dibaca jika user membuka halaman notifikasi
    if request.method == 'POST':
        notifications.update(is_read=True)
        return JsonResponse({'status': 'success'})
    
    context = {
        'notifications': notifications,
        'unread_count': unread_count,
    }
    return render(request, 'toko/notifications.html', context)

@login_required
def notification_count_api(request):
    count = Notification.objects.filter(user=request.user, is_read=False).count()
    return JsonResponse({'count': count})

#========================
# NOTIFIKSASI
#========================
@login_required
def get_notifications(request):
    """API untuk mendapatkan notifikasi user"""
    try:
        notifications = Notification.objects.filter(user=request.user).order_by('-created_at')
        data = []
        for n in notifications:
            data.append({
                'id': n.id,
                'title': n.title,
                'message': n.message,
                'status': n.status,
                'is_read': n.is_read,
                'created_at': n.created_at.isoformat()
            })
        return JsonResponse({'success': True, 'notifications': data})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@login_required
def mark_notification_read(request, notif_id):
    """API untuk menandai notifikasi sudah dibaca"""
    try:
        notif = Notification.objects.get(id=notif_id, user=request.user)
        notif.is_read = True
        notif.save()
        return JsonResponse({'success': True})
    except Notification.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Notifikasi tidak ditemukan'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@login_required
def mark_all_notifications_read(request):
    """API untuk menandai semua notifikasi sudah dibaca"""
    try:
        Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@login_required
def get_unread_count(request):
    """API untuk mendapatkan jumlah notifikasi belum dibaca"""
    try:
        count = Notification.objects.filter(user=request.user, is_read=False).count()
        return JsonResponse({'success': True, 'unread_count': count})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

#=================
# HALAMAN
#=================
@login_required
def kategori_view(request):
    return render(request, 'toko/kategori.html')

@login_required
def favorit_view(request):
    return render(request, 'toko/favorit.html')

@login_required
def lihat_semua_view(request):
    return render(request, 'toko/lihat_semua.html')

@login_required
def detail_produk_view(request, product_id):
    return render(request, 'toko/detail_produk.html', {'product_id': product_id})

@login_required
def keranjang_view(request):
    return render(request, 'toko/keranjang.html')

@login_required
def checkout_view(request):
    return render(request, 'toko/checkout.html')

@login_required
def tambah_alamat_view(request):
    return render(request, 'toko/tambah_alamat.html')


#===============================
#  API Alamat FORM
#===============================
@login_required
def api_provinces(request):
    """API untuk mendapatkan daftar provinsi"""
    provinces = get_provinces()
    if provinces:
        return JsonResponse(provinces)
    return JsonResponse({'error': 'Gagal mengambil data provinsi'}, status=500)

@login_required
def api_cities(request, province_id):
    """API untuk mendapatkan daftar kota berdasarkan provinsi"""
    cities = get_cities(province_id)
    if cities:
        return JsonResponse(cities)
    return JsonResponse({'error': 'Gagal mengambil data kota'}, status=500)

@login_required
def api_search_city(request):
    """API untuk mencari kota berdasarkan nama"""
    query = request.GET.get('q', '')
    if not query:
        return JsonResponse({'error': 'Parameter q diperlukan'}, status=400)
    
    result = search_city(query)
    if result:
        return JsonResponse(result)
    return JsonResponse({'error': 'Gagal mencari kota'}, status=500)

@login_required
def api_districts(request, city_id):
    """API untuk mendapatkan daftar kecamatan berdasarkan kota"""
    districts = get_districts(city_id)
    if districts:
        return JsonResponse(districts)
    return JsonResponse({'error': 'Gagal mengambil data kecamatan'}, status=500)

#===============================
# API PEMAYARAN
#=================================
@login_required
@csrf_exempt
def api_shipping_cost(request):
    """API untuk menghitung ongkir"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method POST required'}, status=405)
    
    try:
        data = json.loads(request.body)
        destination = data.get('destination')
        weight = data.get('weight', 1000)
        courier = data.get('courier', 'jne')
        
        if not destination:
            return JsonResponse({'error': 'Parameter destination required'}, status=400)
        
        result = get_shipping_cost(destination, weight, courier)
        if result:
            return JsonResponse(result)
        return JsonResponse({'error': 'Gagal menghitung ongkir'}, status=500)
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
    
@login_required
def create_xendit_payment(request):
    """
    API untuk membuat pembayaran via Xendit
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Method POST required'}, status=405)
    
    try:
        data = json.loads(request.body)
        payment_method = data.get('payment_method', 'qris')
        amount = data.get('amount', 0)
        customer_name = data.get('customer_name', request.user.first_name or request.user.username)
        customer_email = data.get('customer_email', request.user.email)
        customer_phone = data.get('customer_phone', '')
        bank_code = data.get('bank_code', 'BCA')
        
        # Generate external ID
        external_id = f"ORDER-{uuid.uuid4().hex[:10].upper()}"
        
        xendit = XenditPayment()
        
        if payment_method == 'qris':
            result = xendit.create_qris_payment(
                external_id=external_id,
                amount=amount,
                customer_name=customer_name,
                customer_email=customer_email,
                customer_phone=customer_phone
            )
        elif payment_method == 'bca' or payment_method == 'va':
            result = xendit.create_va_payment(
                external_id=external_id,
                bank_code=bank_code,
                name=customer_name,
                amount=amount,
                phone=customer_phone
            )
        elif payment_method in ['ovo', 'gopay', 'dana']:
            ewallet_map = {'ovo': 'OVO', 'gopay': 'GOPAY', 'dana': 'DANA'}
            result = xendit.create_ewallet_payment(
                external_id=external_id,
                amount=amount,
                phone=customer_phone,
                ewallet_type=ewallet_map.get(payment_method, 'OVO')
            )
        else:
            return JsonResponse({'error': 'Metode pembayaran tidak didukung'}, status=400)
        
        # Simpan order ke session atau database
        if 'xendit_orders' not in request.session:
            request.session['xendit_orders'] = []
        request.session['xendit_orders'].append({
            'order_id': external_id,
            'payment_method': payment_method,
            'amount': amount,
            'status': 'pending',
            'result': result
        })
        request.session.modified = True
        
        return JsonResponse({
            'success': True,
            'order_id': external_id,
            'payment_method': payment_method,
            'result': result,
            'redirect_url': result.get('redirect_url', ''),
            'qr_string': result.get('qr_string', ''),
            'qr_code_url': result.get('qr_code_url', ''),
            'va_number': result.get('va_numbers', [{}])[0].get('va_number', '') if result.get('va_numbers') else '',
            'bank': result.get('va_numbers', [{}])[0].get('bank', '') if result.get('va_numbers') else '',
            'status': result.get('status', 'pending')
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def payment_status_page(request, order_id):
    """Halaman status pembayaran"""
    return render(request, 'toko/payment_status.html', {'order_id': order_id})

@login_required
def payment_success(request):
    """Halaman sukses pembayaran"""
    return render(request, 'toko/payment_success.html')

@login_required
def payment_failed(request):
    """Halaman gagal pembayaran"""
    return render(request, 'toko/payment_failed.html')

# ==============
# PESANAN VIEWS
# ==============

@login_required
def pesanan_saya_view(request):
    """Halaman pesanan saya"""
    return render(request, 'toko/pesanan_saya.html')

@login_required
def detail_pesanan_view(request, order_id):
    """Halaman detail pesanan"""
    return render(request, 'toko/detail_pesanan.html', {'order_id': order_id})

@login_required
def pesanan_berhasil_view(request):
    """Halaman pesanan berhasil"""
    return render(request, 'toko/pesanan_berhasil.html')

# ==============
# API ENDPOINTS
# ==============

@login_required
def get_pesanan_user(request):
    """API untuk mendapatkan pesanan user dengan status terbaru"""
    try:
        pesanan_list = Pesanan.objects.filter(user=request.user).order_by('-tanggal_pesan')
        data = []
        
        for p in pesanan_list:
            items = []
            for item in p.items.all():
                items.append({
                    'id': str(item.produk.id),
                    'name': item.produk.name,  # ← GANTI: nama → name
                    'brand': item.produk.brand,  # ← SUDAH BENAR
                    'price': float(item.harga),
                    'image': item.produk.image_link if item.produk.image_link else '',  # ← GANTI: gambar → image_link
                    'quantity': item.jumlah
                })
            
            data.append({
                'order_id': p.id,
                'date': p.tanggal_pesan.isoformat(),
                'status': p.status,
                'total': float(p.total),
                'items': items
            })
        
        return JsonResponse({
            'success': True,
            'orders': data
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@login_required
@csrf_exempt
def update_order_status(request):
    """API untuk update status pesanan"""
    if request.method != 'POST':
        return JsonResponse({
            'success': False, 
            'error': 'Method tidak diizinkan'
        }, status=405)
    
    try:
        data = json.loads(request.body)
        order_id = data.get('order_id')
        new_status = data.get('status')
        
        # Validasi status
        valid_status = ['menunggu', 'dikemas', 'dikirim', 'selesai', 'dibatalkan']
        if new_status not in valid_status:
            return JsonResponse({
                'success': False,
                'error': 'Status tidak valid'
            }, status=400)
        
        # Cari pesanan
        # Jika user adalah admin (is_staff), bisa mengubah semua pesanan
        if request.user.is_staff:
            pesanan = Pesanan.objects.get(id=order_id)
        else:
            # User biasa hanya bisa mengubah pesanan miliknya sendiri
            pesanan = Pesanan.objects.get(id=order_id, user=request.user)

        # Simpan status lama
        old_status = pesanan.status
        
        # Validasi status transition
        if pesanan.status == 'selesai' and new_status != 'selesai':
            return JsonResponse({
                'success': False,
                'error': 'Pesanan yang sudah selesai tidak bisa diubah'
            }, status=400)
        
        if pesanan.status == 'dibatalkan':
            return JsonResponse({
                'success': False,
                'error': 'Pesanan yang sudah dibatalkan tidak bisa diubah'
            }, status=400)
        
        # Update status
        pesanan.status = new_status
        pesanan.save()

        # ===== BUAT NOTIFIKASI =====
        try:
            from .models import Notification  # Import di sini atau di atas
            
            status_labels = {
                'menunggu': 'Menunggu Konfirmasi',
                'dikemas': 'Sedang Dikemas',
                'dikirim': 'Sedang Dikirim',
                'selesai': 'Selesai',
                'dibatalkan': 'Dibatalkan'
            }
            
            status_messages = {
                'menunggu': 'Pesanan Anda menunggu konfirmasi dari admin.',
                'dikemas': 'Pesanan Anda sedang dikemas oleh tim kami.',
                'dikirim': 'Pesanan Anda telah dikirim! Silakan cek status pengiriman.',
                'selesai': 'Pesanan Anda telah selesai. Terima kasih telah berbelanja!',
                'dibatalkan': 'Pesanan Anda telah dibatalkan.'
            }
            
            # Buat notifikasi untuk user pemilik pesanan
            if old_status != new_status:
                Notification.objects.create(
                    user=pesanan.user,
                    title=f'Status Pesanan {pesanan.id}',
                    message=f'Status pesanan Anda berubah menjadi: {status_labels.get(new_status, new_status)}. {status_messages.get(new_status, "")}',
                    status=new_status,
                    is_read=False
                )
                print(f"✅ Notifikasi dibuat untuk {pesanan.user.username}: {new_status}")
        except Exception as e:
            print(f"Error creating notification: {e}")
            # Jangan gagalkan request utama jika notifikasi gagal
        
        return JsonResponse({
            'success': True,
            'message': 'Status pesanan berhasil diperbarui',
            'status': new_status
        })
        
    except Pesanan.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Pesanan tidak ditemukan'
        }, status=404)
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Data tidak valid'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@login_required
@csrf_exempt
def batal_pesanan(request):
    """API untuk membatalkan pesanan"""
    if request.method != 'POST':
        return JsonResponse({
            'success': False, 
            'error': 'Method tidak diizinkan'
        }, status=405)
    
    try:
        data = json.loads(request.body)
        order_id = data.get('order_id')
        
        pesanan = Pesanan.objects.get(id=order_id, user=request.user)
        
        if pesanan.status != 'menunggu':
            return JsonResponse({
                'success': False, 
                'error': f'Pesanan tidak bisa dibatalkan karena statusnya "{pesanan.status}"'
            }, status=400)
        
        pesanan.status = 'dibatalkan'
        pesanan.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Pesanan berhasil dibatalkan'
        })
        
    except Pesanan.DoesNotExist:
        return JsonResponse({
            'success': False, 
            'error': 'Pesanan tidak ditemukan'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False, 
            'error': str(e)
        }, status=500)

@login_required
@csrf_exempt
def selesai_pesanan(request):
    """API untuk menyelesaikan pesanan"""
    if request.method != 'POST':
        return JsonResponse({
            'success': False, 
            'error': 'Method tidak diizinkan'
        }, status=405)
    
    try:
        data = json.loads(request.body)
        order_id = data.get('order_id')
        
        pesanan = Pesanan.objects.get(id=order_id, user=request.user)
        
        if pesanan.status != 'dikirim':
            return JsonResponse({
                'success': False, 
                'error': f'Pesanan belum dikirim. Status saat ini: "{pesanan.status}"'
            }, status=400)
        
        pesanan.status = 'selesai'
        pesanan.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Pesanan telah selesai'
        })
        
    except Pesanan.DoesNotExist:
        return JsonResponse({
            'success': False, 
            'error': 'Pesanan tidak ditemukan'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False, 
            'error': str(e)
        }, status=500)

@login_required
@csrf_exempt
def save_order(request):
    """API untuk menyimpan order ke database dari checkout user"""
    if request.method != 'POST':
        return JsonResponse({
            'success': False, 
            'error': 'Method tidak diizinkan'
        }, status=405)
    
    try:
        data = json.loads(request.body)
        
        # Validasi data
        items = data.get('items', [])
        if not items:
            return JsonResponse({
                'success': False,
                'error': 'Tidak ada item dalam pesanan'
            }, status=400)
        
        # Buat pesanan baru
        pesanan = Pesanan.objects.create(
            user=request.user,
            total=0,  # Akan diupdate nanti
            status='menunggu',
            alamat_pengiriman=data.get('address', {}).get('alamat', ''),
            catatan=data.get('catatan', '')
        )
        
        total = 0
        
        # Simpan items
        for item_data in items:
            try:
                # Cari produk berdasarkan ID
                produk = Produk.objects.get(id=item_data.get('id'))
                harga = float(item_data.get('price', 0))
                jumlah = int(item_data.get('quantity', 1))
                subtotal = harga * jumlah
                total += subtotal
                
                PesananItem.objects.create(
                    pesanan=pesanan,
                    produk=produk,
                    jumlah=jumlah,
                    harga=harga
                )
            except Produk.DoesNotExist:
                # Jika produk tidak ditemukan, coba cari berdasarkan nama
                produk = Produk.objects.filter(name=item_data.get('name')).first()
                if produk:
                    harga = float(item_data.get('price', 0))
                    jumlah = int(item_data.get('quantity', 1))
                    subtotal = harga * jumlah
                    total += subtotal
                    
                    PesananItem.objects.create(
                        pesanan=pesanan,
                        produk=produk,
                        jumlah=jumlah,
                        harga=harga
                    )
                else:
                    # Jika produk tidak ditemukan, skip
                    print(f"Produk tidak ditemukan: {item_data.get('name')}")
                    continue
        
        # Update total pesanan
        pesanan.total = total
        pesanan.save()
        
        return JsonResponse({
            'success': True,
            'order_id': pesanan.id,
            'total': total,
            'message': 'Order berhasil disimpan'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)
    
#=======================
# LOGGING DAN VALIDASI
#=======================
@login_required
def get_pesanan_user(request):
    """API untuk mendapatkan pesanan user dengan status terbaru"""
    try:
        pesanan_list = Pesanan.objects.filter(user=request.user).order_by('-tanggal_pesan')
        data = []
        
        for p in pesanan_list:
            items = []
            for item in p.items.all():
                items.append({
                    'id': str(item.produk.id),
                    'name': item.produk.name,  # ← PAKAI name (sesuai model)
                    'brand': item.produk.brand,
                    'price': float(item.harga),
                    'image': item.produk.image_link if item.produk.image_link else '',  # ← PAKAI image_link (sesuai model)
                    'quantity': item.jumlah
                })
            
            data.append({
                'order_id': p.id,
                'date': p.tanggal_pesan.isoformat(),
                'status': p.status,
                'total': float(p.total),
                'items': items
            })
        
        return JsonResponse({
            'success': True,
            'orders': data
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)
    
#==========
# AI CHAT
#==========
@login_required
def ai_chat_view(request):
    """Halaman AI Chat"""
    return render(request, 'toko/ai_chat.html')

def format_ai_response(text):
    """Merapikan response AI agar lebih mudah dibaca"""
    
    # 1. Hapus markdown berlebihan
    text = text.replace('---', '\n')
    text = text.replace('**', '')
    text = text.replace('###', '\n')
    text = text.replace('##', '\n')
    text = text.replace('#', '\n')
    
    # 2. Perbaiki bullet points
    text = text.replace('* ', '• ')
    
    # 3. Hapus newline berlebihan (lebih dari 2)
    import re
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    # 4. Rapikan spasi
    text = text.strip()
    
    return text

@login_required
def ai_chat_api(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method POST required'}, status=405)
    
    try:
        data = json.loads(request.body)
        message = data.get('message', '')
        
        if not message:
            return JsonResponse({'error': 'Pesan tidak boleh kosong'}, status=400)
        
        print(f"📝 Pesan diterima: {message}")
        
        # ===== COBA GEMINI =====
        try:
            import google.generativeai as genai
            
            genai.configure(api_key=settings.GEMINI_API_KEY)
            model = genai.GenerativeModel('gemini-1.5-flash')
            
            system_prompt = """
            Anda adalah asisten kecantikan untuk toko makeup "MyBelin" yang menjual produk Maybelline.
            
            ATURAN JAWAB:
            1. Gunakan bahasa Indonesia yang ramah dan profesional
            2. Jawab dengan ringkas, maksimal 3-4 paragraf
            3. Gunakan bullet points (•) untuk daftar produk
            4. Jangan gunakan markdown (**), (###), atau (---)
            5. Sertakan estimasi harga produk
            6. Akhiri dengan pertanyaan balik yang ramah
            """
            
            response = model.generate_content(f"{system_prompt}\n\nPertanyaan user: {message}")
            reply = response.text
            reply = format_ai_response(reply)
            
        except Exception as e:
            print(f"⚠️ Gemini Error: {e}, pakai mock response")
            reply = get_mock_response(message)
        
        return JsonResponse({'reply': reply})
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return JsonResponse({'error': str(e)}, status=500)

# ===== MOCK RESPONSE (Fallback jika Gemini error) =====
def get_mock_response(message):
    message = message.lower()
    
    responses = {
        'foundation': "🌸 Rekomendasi foundation Maybelline:\n\n• **Fit Me Matte + Poreless** (Rp90.000-150.000) - Untuk kulit berminyak, hasil matte natural\n• **Fit Me Dewy + Smooth** (Rp100.000-160.000) - Untuk kulit kering, hasil glowing\n• **Dream Radiant Liquid** (Rp85.000-140.000) - Medium coverage, cocok semua kulit",
        'lipstick': "💄 Rekomendasi lipstick Maybelline:\n\n• **Superstay Matte Ink** (Rp120.000-180.000) - Tahan 16 jam, warna intens\n• **Color Sensational** (Rp90.000-150.000) - Pelembab, warna natural\n• **Ultimatte** (Rp100.000-160.000) - Matte flawless, ringan",
        'mascara': "👁️ Rekomendasi mascara Maybelline:\n\n• **Lash Sensational** (Rp100.000-170.000) - Full fan effect, waterproof\n• **The Colossal** (Rp80.000-140.000) - Volume ekstra\n• **Falsies Lash Lift** (Rp90.000-150.000) - Efek bulu mata palsu",
        'concealer': "🎨 Rekomendasi concealer Maybelline:\n\n• **Instant Age Rewind Eraser** (Rp80.000-130.000) - Untuk lingkaran hitam, mengandung goji berry\n• **Fit Me Concealer** (Rp70.000-120.000) - Tutupan ringan, natural",
        'eyeliner': "✍️ Rekomendasi eyeliner Maybelline:\n\n• **Hyper Precise All Day** (Rp90.000-150.000) - Tahan 24 jam, presisi tinggi\n• **Tattoo Liner** (Rp85.000-140.000) - Tahan air, tidak luntur"
    }
    
    for key, value in responses.items():
        if key in message:
            return value + "\n\n💄 Ada pertanyaan lain tentang makeup? Tanyakan saja!"
    
    return "🌸 Halo! Saya asisten kecantikan MyBelin. Tanyakan produk Maybelline seperti foundation, lipstick, mascara, concealer, atau eyeliner. Saya siap membantu! 💄"

#==========
# BANTUAN
#==========
@login_required
def bantuan_view(request):
    return render(request, 'toko/bantuan.html')

#============
# PENGATURAN 
#============
@login_required
def pengaturan_view(request):
    return render(request, 'toko/pengaturan.html')

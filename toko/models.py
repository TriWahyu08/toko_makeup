from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.db.models.signals import post_save
from django.dispatch import receiver
import uuid

class Notification(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Menunggu'),
        ('processed', 'Diproses'),
        ('shipped', 'Dikirim'),
        ('delivered', 'Selesai'),
        ('cancelled', 'Dibatalkan'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=200)
    message = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    is_read = models.BooleanField(default=False)
    order_id = models.CharField(max_length=50, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.title} - {self.user.username}"
    
    def mark_as_read(self):
        self.is_read = True
        self.save()

# pesanan
class Order(models.Model):
    STATUS_CHOICES = [
        ('menunggu', 'Menunggu'),
        ('dikemas', 'Dikemas'),
        ('dikirim', 'Dikirim'),
        ('selesai', 'Selesai'),
        ('dibatalkan', 'Dibatalkan'),
    ]
    
    order_id = models.CharField(max_length=50, unique=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders', null=True, blank=True)
    items = models.JSONField(default=list)
    total = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='menunggu')
    shipping_cost = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    shipping_service = models.CharField(max_length=50, blank=True, null=True)
    payment_method = models.CharField(max_length=50, blank=True, null=True)
    address = models.JSONField(default=dict, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.order_id} - {self.user.username if self.user else 'Guest'}"
    
    class Meta:
        ordering = ['-created_at']


# ===== NOTIFICATION MODEL =====
class Notification(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Menunggu'),
        ('processed', 'Diproses'),
        ('shipped', 'Dikirim'),
        ('delivered', 'Selesai'),
        ('cancelled', 'Dibatalkan'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=200)
    message = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    is_read = models.BooleanField(default=False)
    order_id = models.CharField(max_length=50, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.title} - {self.user.username}"
    
    def mark_as_read(self):
        self.is_read = True
        self.save()

from django.db import models

class Produk(models.Model):
    id_api = models.CharField(max_length=50, blank=True, null=True)  # ID dari API
    brand = models.CharField(max_length=100)
    name = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    image_link = models.URLField(max_length=500, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    product_type = models.CharField(max_length=100, blank=True, null=True)
    rating = models.DecimalField(max_digits=3, decimal_places=1, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.name

class Pesanan(models.Model):
    STATUS_CHOICES = [
        ('menunggu', 'Menunggu'),
        ('dikemas', 'Dikemas'),
        ('dikirim', 'Dikirim'),
        ('selesai', 'Selesai'),
        ('dibatalkan', 'Dibatalkan'),
    ]
    
    id = models.CharField(max_length=20, primary_key=True, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='pesanan')
    tanggal_pesan = models.DateTimeField(default=timezone.now)
    total = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='menunggu')
    alamat_pengiriman = models.TextField()
    catatan = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.id:
            # Generate ID: ORDER- + timestamp hex
            timestamp = int(timezone.now().timestamp() * 1000)
            random_part = uuid.uuid4().hex[:8].upper()
            self.id = f"ORDER-{timestamp:X}{random_part}"[:20]
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.id} - {self.user.username}"

class PesananItem(models.Model):
    pesanan = models.ForeignKey(Pesanan, on_delete=models.CASCADE, related_name='items')
    produk = models.ForeignKey(Produk, on_delete=models.CASCADE)
    jumlah = models.IntegerField(default=1)
    harga = models.DecimalField(max_digits=15, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.pesanan.id} - {self.produk.nama} x{self.jumlah}"
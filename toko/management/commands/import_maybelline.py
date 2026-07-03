from django.core.management.base import BaseCommand
from toko.models import Produk
import requests

class Command(BaseCommand):
    help = 'Import produk Maybelline dari API eksternal'

    def handle(self, *args, **options):
        self.stdout.write('Mulai import data produk Maybelline...')
        
        url = 'http://makeup-api.herokuapp.com/api/v1/products.json?brand=maybelline'
        
        try:
            response = requests.get(url)
            response.raise_for_status()
            products = response.json()
            
            count = 0
            for item in products:
                # Cek apakah produk sudah ada berdasarkan ID API
                produk, created = Produk.objects.get_or_create(
                    id_api=str(item.get('id')),
                    defaults={
                        'brand': item.get('brand', 'maybelline'),
                        'name': item.get('name', ''),
                        'price': float(item.get('price', 0)) if item.get('price') else 0,
                        'image_link': item.get('image_link', ''),
                        'description': item.get('description', ''),
                        'product_type': item.get('product_type', ''),
                        'rating': float(item.get('rating', 0)) if item.get('rating') else None,
                    }
                )
                
                if created:
                    count += 1
                    self.stdout.write(f'✓ Produk "{produk.name}" berhasil diimport')
                else:
                    # Update jika ada perubahan
                    produk.brand = item.get('brand', 'maybelline')
                    produk.name = item.get('name', '')
                    produk.price = float(item.get('price', 0)) if item.get('price') else 0
                    produk.image_link = item.get('image_link', '')
                    produk.description = item.get('description', '')
                    produk.product_type = item.get('product_type', '')
                    produk.rating = float(item.get('rating', 0)) if item.get('rating') else None
                    produk.save()
            
            self.stdout.write(self.style.SUCCESS(f'✅ Selesai! {count} produk baru berhasil diimport.'))
            
        except requests.exceptions.RequestException as e:
            self.stdout.write(self.style.ERROR(f'❌ Error saat mengakses API: {e}'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Error: {e}'))
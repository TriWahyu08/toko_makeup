# toko/xendit_payment.py
import requests
import json
import base64
from django.conf import settings

class XenditPayment:
    def __init__(self):
        self.secret_key = settings.XENDIT_SECRET_KEY
        self.publishable_key = settings.XENDIT_PUBLISHABLE_KEY
        self.is_production = settings.XENDIT_IS_PRODUCTION
        
        if self.is_production:
            self.api_url = 'https://api.xendit.co'
        else:
            self.api_url = 'https://api.xendit.co'
    
    def _get_auth_header(self):
        """Generate Basic Auth header"""
        auth_string = f"{self.secret_key}:"
        encoded = base64.b64encode(auth_string.encode()).decode()
        return f"Basic {encoded}"
    
    def create_qris_payment(self, external_id, amount, customer_name, customer_email, customer_phone=''):
        """
        Membuat pembayaran QRIS
        """
        url = f"{self.api_url}/qr_codes"
        
        headers = {
            'Content-Type': 'application/json',
            'Authorization': self._get_auth_header()
        }
        
        payload = {
            'external_id': external_id,
            'type': 'DYNAMIC',
            'callback_url': f'{settings.BASE_URL}/api/xendit-callback/',
            'amount': amount,
            'customer_name': customer_name,
            'customer_email': customer_email,
            'customer_phone': customer_phone
        }
        
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            return response.json()
        except Exception as e:
            return {'error': str(e)}
    
    def create_va_payment(self, external_id, bank_code, name, amount, phone=''):
        """
        Membuat pembayaran Virtual Account
        bank_code: BCA, MANDIRI, BNI, BRI, PERMATA
        """
        url = f"{self.api_url}/callback_virtual_accounts"
        
        headers = {
            'Content-Type': 'application/json',
            'Authorization': self._get_auth_header()
        }
        
        payload = {
            'external_id': external_id,
            'bank_code': bank_code,
            'name': name,
            'amount': amount,
            'phone': phone,
            'expiration_date': '2026-12-31T23:59:59Z'
        }
        
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            return response.json()
        except Exception as e:
            return {'error': str(e)}
    
    def create_ewallet_payment(self, external_id, amount, phone, ewallet_type='OVO'):
        """
        Membuat pembayaran E-Wallet (OVO, DANA, GoPay)
        """
        url = f"{self.api_url}/ewallets"
        
        headers = {
            'Content-Type': 'application/json',
            'Authorization': self._get_auth_header()
        }
        
        payload = {
            'external_id': external_id,
            'amount': amount,
            'phone': phone,
            'ewallet_type': ewallet_type,
            'callback_url': f'{settings.BASE_URL}/api/xendit-callback/'
        }
        
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            return response.json()
        except Exception as e:
            return {'error': str(e)}
    
    def get_payment_status(self, payment_id, payment_type='qr'):
        """
        Cek status pembayaran
        payment_type: 'qr', 'va', 'ewallet'
        """
        if payment_type == 'qr':
            url = f"{self.api_url}/qr_codes/{payment_id}"
        elif payment_type == 'va':
            url = f"{self.api_url}/callback_virtual_accounts/{payment_id}"
        elif payment_type == 'ewallet':
            url = f"{self.api_url}/ewallets/{payment_id}"
        else:
            return {'error': 'Invalid payment type'}
        
        headers = {
            'Authorization': self._get_auth_header()
        }
        
        try:
            response = requests.get(url, headers=headers, timeout=30)
            return response.json()
        except Exception as e:
            return {'error': str(e)}
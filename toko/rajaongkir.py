import requests

RAJAONGKIR_API_KEY = '0L30VMjx7dad169827d7407dw2penNJZ'

# ORIGIN (KOTA ASAL) - SAMARINDA
# ID Kota Samarinda di RajaOngkir = 501
ORIGIN_CITY_ID = '501'

# ============================================
# MAPPING ID KOTA EMSIFA → ID KOTA RAJAONGKIR
# ============================================
CITY_ID_MAPPING = {
    # ===== KALIMANTAN TIMUR =====
    '6472': '501',  # Samarinda → 501
    '6471': '2',    # Balikpapan → 2
    '6474': '3',    # Bontang → 3
    '6403': '502',  # Kutai Kartanegara → 502
    '6404': '503',  # Kutai Timur → 503
    '6402': '504',  # Kutai Barat → 504
    '6401': '505',  # Paser → 505
    '6409': '506',  # Penajam Paser Utara → 506
    '6405': '507',  # Berau → 507
    '6411': '508',  # Mahakam Ulu → 508
    
    # ===== DKI JAKARTA =====
    '3171': '152',  # Jakarta Selatan → 152
    '3172': '153',  # Jakarta Timur → 153
    '3173': '154',  # Jakarta Pusat → 154
    '3174': '155',  # Jakarta Barat → 155
    '3175': '156',  # Jakarta Utara → 156
    
    # ===== JAWA TIMUR =====
    '3578': '444',  # Surabaya → 444
    '3573': '445',  # Malang → 445
    '3571': '446',  # Kediri → 446
    '3572': '447',  # Blitar → 447
    '3577': '448',  # Madiun → 448
    
    # ===== JAWA BARAT =====
    '3273': '313',  # Bandung → 313
    '3271': '314',  # Bogor → 314
    '3275': '315',  # Bekasi → 315
    '3276': '316',  # Depok → 316
    '3277': '317',  # Cimahi → 317
    
    # ===== JAWA TENGAH =====
    '3374': '419',  # Yogyakarta → 419
    '3372': '420',  # Solo → 420
    '3375': '421',  # Semarang → 421
    
    # ===== BALI =====
    '5171': '430',  # Denpasar → 430
    '5103': '431',  # Badung → 431
    '5104': '432',  # Gianyar → 432
    
    # ===== SUMATERA UTARA =====
    '1271': '442',  # Medan → 442
    '1275': '443',  # Binjai → 443
    
    # ===== SULAWESI SELATAN =====
    '7371': '455',  # Makassar → 455
    '7372': '456',  # Parepare → 456
    
    # ===== KALIMANTAN SELATAN =====
    '6371': '510',  # Banjarmasin → 510
    '6372': '511',  # Banjarbaru → 511
    
    # ===== KALIMANTAN TENGAH =====
    '6271': '520',  # Palangka Raya → 520
    
    # ===== KALIMANTAN BARAT =====
    '6171': '530',  # Pontianak → 530
    '6172': '531',  # Singkawang → 531
    
    # ===== SUMATERA BARAT =====
    '1371': '540',  # Padang → 540
    '1372': '541',  # Bukittinggi → 541
    
    # ===== RIAU =====
    '1471': '550',  # Pekanbaru → 550
    '1472': '551',  # Dumai → 551
    
    # ===== KEPULAUAN RIAU =====
    '2171': '560',  # Batam → 560
    '2172': '561',  # Tanjung Pinang → 561
    
    # ===== JAMBI =====
    '1571': '570',  # Jambi → 570
    
    # ===== SUMATERA SELATAN =====
    '1671': '580',  # Palembang → 580
    
    # ===== LAMPUNG =====
    '1871': '590',  # Bandar Lampung → 590
    
    # ===== BENGKULU =====
    '1771': '600',  # Bengkulu → 600
    
    # ===== BANGKA BELITUNG =====
    '1971': '610',  # Pangkal Pinang → 610
    
    # ===== NUSA TENGGARA BARAT =====
    '5271': '620',  # Mataram → 620
    '5272': '621',  # Bima → 621
    
    # ===== NUSA TENGGARA TIMUR =====
    '5371': '630',  # Kupang → 630
    
    # ===== SULAWESI UTARA =====
    '7171': '640',  # Manado → 640
    
    # ===== SULAWESI TENGAH =====
    '7271': '650',  # Palu → 650
    
    # ===== SULAWESI TENGGARA =====
    '7471': '660',  # Kendari → 660
    
    # ===== GORONTALO =====
    '7571': '670',  # Gorontalo → 670
    
    # ===== SULAWESI BARAT =====
    '7671': '680',  # Mamuju → 680
    
    # ===== MALUKU =====
    '8171': '690',  # Ambon → 690
    
    # ===== MALUKU UTARA =====
    '8271': '700',  # Ternate → 700
    
    # ===== PAPUA =====
    '9471': '710',  # Jayapura → 710
    
    # ===== PAPUA BARAT =====
    '9171': '720',  # Manokwari → 720
    
    # ===== BANTEN =====
    '3671': '730',  # Tangerang → 730
    '3672': '731',  # Cilegon → 731
    '3673': '732',  # Serang → 732
    '3674': '733',  # Tangerang Selatan → 733
}

def get_rajaongkir_city_id(emsifa_city_id):
    """
    Konversi ID kota EMSIFA ke ID kota RajaOngkir
    Jika tidak ada mapping, kembalikan ID asli
    """
    return CITY_ID_MAPPING.get(str(emsifa_city_id), str(emsifa_city_id))

# ============================================
# API WILAYAH INDONESIA (EMSIFA)
# ============================================
EMSIFA_BASE_URL = 'https://www.emsifa.com/api-wilayah-indonesia/api'

def get_provinces():
    """
    Mendapatkan daftar provinsi dari API EMSIFA
    """
    try:
        url = f"{EMSIFA_BASE_URL}/provinces.json"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            # Format ulang agar sesuai dengan struktur RajaOngkir
            formatted = {
                'rajaongkir': {
                    'results': [
                        {'province_id': str(p['id']), 'province': p['name'].title()}
                        for p in data
                    ]
                }
            }
            return formatted
        else:
            print(f"⚠️ Error: {response.status_code}")
            return None
    except Exception as e:
        print(f"⚠️ Error get_provinces: {e}")
        return None

def get_cities(province_id=None):
    """
    Mendapatkan daftar kota dari API EMSIFA
    Jika province_id diberikan, hanya kota di provinsi tersebut
    """
    try:
        if province_id:
            url = f"{EMSIFA_BASE_URL}/regencies/{province_id}.json"
        else:
            # Jika tidak ada province_id, ambil semua kota (bisa lambat)
            # Lebih baik tetap minta province_id
            return {'rajaongkir': {'results': []}}
        
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            formatted = {
                'rajaongkir': {
                    'results': [
                        {
                            'city_id': str(c['id']),
                            'city_name': c['name'].title(),
                            'rajaongkir_id': get_rajaongkir_city_id(c['id'])  # Tambahkan ID RajaOngkir
                        }
                        for c in data
                    ]
                }
            }
            return formatted
        else:
            print(f"⚠️ Error: {response.status_code}")
            return None
    except Exception as e:
        print(f"⚠️ Error get_cities: {e}")
        return None
    
def get_districts(city_id):
    """
    Mendapatkan daftar kecamatan berdasarkan kota/kabupaten dari API EMSIFA
    """
    try:
        url = f"{EMSIFA_BASE_URL}/districts/{city_id}.json"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            # Response dari EMSIFA: list of districts
            formatted = {
                'rajaongkir': {
                    'results': [
                        {'district_id': str(d['id']), 'district_name': d['name'].title()}
                        for d in data
                    ]
                }
            }
            return formatted
        else:
            print(f"⚠️ Error: {response.status_code}")
            return {'rajaongkir': {'results': []}}
    except Exception as e:
        print(f"⚠️ Error get_districts: {e}")
        return {'rajaongkir': {'results': []}}

def get_all_cities():
    """
    Mendapatkan semua kota dari semua provinsi
    (Hati-hati: bisa lambat karena banyak request)
    """
    try:
        # Ambil semua provinsi dulu
        provinces = get_provinces()
        if not provinces:
            return {'rajaongkir': {'results': []}}
        
        all_cities = []
        for prov in provinces['rajaongkir']['results']:
            prov_id = prov['province_id']
            cities = get_cities(prov_id)
            if cities:
                for city in cities['rajaongkir']['results']:
                    city['province_id'] = prov_id
                    all_cities.append(city)
        
        return {'rajaongkir': {'results': all_cities}}
    except Exception as e:
        print(f"⚠️ Error get_all_cities: {e}")
        return {'rajaongkir': {'results': []}}

def search_city(city_name):
    """
    Mencari kota berdasarkan nama (case insensitive)
    """
    try:
        # Ambil semua kota
        all_cities = get_all_cities()
        if not all_cities:
            return {'rajaongkir': {'results': []}}
        
        # Filter berdasarkan nama
        results = []
        for city in all_cities['rajaongkir']['results']:
            if city_name.lower() in city['city_name'].lower():
                results.append(city)
        
        return {'rajaongkir': {'results': results}}
    except Exception as e:
        print(f"⚠️ Error search_city: {e}")
        return {'rajaongkir': {'results': []}}

# ============================================
# ONGKIR (RAJAONGKIR KOMERCE - REAL API)
# ============================================
def get_shipping_cost(destination_city_id, weight, courier='jne'):
    """
    Menghitung ongkir menggunakan RajaOngkir Komerce
    destination_city_id bisa ID EMSIFA atau ID RajaOngkir
    """
    # Konversi ke ID RajaOngkir jika perlu
    rajaongkir_id = get_rajaongkir_city_id(destination_city_id)
    
    try:
        url = 'https://rajaongkir.komerce.id/api/v1/calculate/domestic-cost'
        headers = {
            'key': RAJAONGKIR_API_KEY,
            'content-type': 'application/x-www-form-urlencoded'
        }
        data = {
            'origin': ORIGIN_CITY_ID,
            'destination': str(rajaongkir_id),
            'weight': str(weight),
            'courier': courier
        }
        response = requests.post(url, data=data, headers=headers, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            formatted = {
                'rajaongkir': {
                    'results': [{
                        'code': item.get('code'),
                        'name': item.get('name'),
                        'costs': [{
                            'service': item.get('service'),
                            'description': item.get('description'),
                            'cost': [{'value': item.get('cost'), 'etd': item.get('etd')}]
                        }]
                    } for item in result.get('data', [])]
                }
            }
            return formatted
        else:
            print(f"⚠️ Ongkir API Error: {response.status_code}")
            return None
    except Exception as e:
        print(f"⚠️ Error get_shipping_cost: {e}")
        return None
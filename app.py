from flask import Flask, request, jsonify
from flask_cors import CORS
import cv2
import pytesseract
import numpy as np
import re
import os

app = Flask(__name__)
CORS(app)

def extract_imei(text):
    imei_pattern = r'\b\d{15}\b'
    match = re.search(imei_pattern, text)
    return match.group(0) if match else None

def extract_model(text):
    model_pattern = r'(iPhone|iPad|iPod|Apple Watch|MacBook|iMac)\s*(\d{1,2}\s*(?:Pro|Max|Plus|Mini)?)'
    match = re.search(model_pattern, text, re.IGNORECASE)
    return f"{match.group(1)} {match.group(2)}".strip() if match else None

def extract_storage(text):
    storage_pattern = r'\b(64|128|256|512|1024|1|2)(?:GB|TB)\b'
    match = re.search(storage_pattern, text, re.IGNORECASE)
    return match.group(0) if match else None

def extract_color(text):
    color_pattern = r'\b(Space Gray|Silver|Gold|Rose Gold|Black|White|Blue|Green|Red|Purple|Graphite|Midnight|Starlight)\b'
    match = re.search(color_pattern, text, re.IGNORECASE)
    return match.group(0) if match else None

def extract_tracking(text):
    patterns = {
        'usps': r'\b(94|93|92|94|95)\d{20,22}\b',
        'ups': r'\b1Z[A-Z0-9]{16}\b',
        'fedex': r'\b\d{12,15}\b'
    }
    for carrier, pattern in patterns.items():
        match = re.search(pattern, text)
        if match:
            return match.group(0), carrier.upper()
    return None, None

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'healthy', 'service': 'OCR Scanner'})

@app.route('/scan', methods=['POST'])
def scan():
    try:
        if 'image' not in request.files:
            return jsonify({'success': False, 'error': 'No image provided'}), 400
        
        file = request.files['image']
        image_bytes = file.read()
        nparr = np.frombuffer(image_bytes, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if image is None:
            return jsonify({'success': False, 'error': 'Invalid image'}), 400
        
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        processed = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
        text = pytesseract.image_to_string(processed)
        
        device_info = {}
        shipping_info = {}
        
        imei = extract_imei(text)
        if imei:
            device_info['imei'] = imei
        
        model = extract_model(text)
        if model:
            device_info['model'] = model
        
        storage = extract_storage(text)
        if storage:
            device_info['storage'] = storage
        
        color = extract_color(text)
        if color:
            device_info['color'] = color
        
        tracking, carrier_from_tracking = extract_tracking(text)
        if tracking:
            shipping_info['tracking_number'] = tracking
            if carrier_from_tracking:
                shipping_info['carrier'] = carrier_from_tracking
        
        return jsonify({
            'success': True,
            'device': device_info,
            'shipping': shipping_info,
            'raw_text': text
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    # Get port from environment or use 8080
    port = int(os.getenv('PORT', 8080))
    print(f"Starting OCR service on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)

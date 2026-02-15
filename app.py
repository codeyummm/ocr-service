from flask import Flask, request, jsonify
from flask_cors import CORS
import cv2
import pytesseract
import numpy as np
import re
import os

app = Flask(__name__)
CORS(app)

def preprocess_image(image):
    """Enhanced preprocessing for shipping labels"""
    # Convert to grayscale
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # Resize if image is too small
    height, width = gray.shape
    if height < 1000:
        scale = 1000 / height
        gray = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
    
    # Denoise
    denoised = cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)
    
    # Increase contrast using CLAHE
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
    enhanced = clahe.apply(denoised)
    
    # Apply adaptive threshold
    binary = cv2.adaptiveThreshold(enhanced, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
    
    return binary

def extract_imei(text):
    # IMEI is exactly 15 digits
    pattern = r'\b\d{15}\b'
    matches = re.findall(pattern, text)
    return matches[0] if matches else None

def extract_model(text):
    # Look for iPhone, iPad, etc with model number
    pattern = r'(iPhone|iPad|iPod)\s*(\d{1,2}\s*(?:Pro|Max|Plus|Mini)?(?:\s*(?:Pro|Max))?)'
    match = re.search(pattern, text, re.IGNORECASE)
    if match:
        return f"{match.group(1)} {match.group(2)}".strip()
    return None

def extract_tracking(text):
    patterns = {
        'UPS': r'1Z[A-Z0-9]{16}',
        'USPS': r'\b(94|93|92|95)\d{20,22}\b',
        'FEDEX': r'\b\d{12,14}\b'
    }
    
    for carrier, pattern in patterns.items():
        match = re.search(pattern, text)
        if match:
            return match.group(0), carrier
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
        
        # Preprocess image
        processed = preprocess_image(image)
        
        # Extract text with multiple PSM modes
        custom_config = r'--oem 3 --psm 6'
        text = pytesseract.image_to_string(processed, config=custom_config)
        
        # Try PSM 11 (sparse text) if PSM 6 didn't work well
        if len(text.strip()) < 20:
            custom_config = r'--oem 3 --psm 11'
            text = pytesseract.image_to_string(processed, config=custom_config)
        
        print(f"Extracted text: {text}")
        
        device_info = {}
        shipping_info = {}
        
        # Extract device information
        imei = extract_imei(text)
        if imei:
            device_info['imei'] = imei
        
        model = extract_model(text)
        if model:
            device_info['model'] = model
        
        # Extract shipping information
        tracking, carrier = extract_tracking(text)
        if tracking:
            shipping_info['tracking_number'] = tracking
            shipping_info['carrier'] = carrier
        
        return jsonify({
            'success': True,
            'device': device_info,
            'shipping': shipping_info,
            'raw_text': text
        })
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.getenv('PORT', 8080))
    print(f"Starting OCR service on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)

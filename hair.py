from flask import Flask, request, jsonify
import cv2
import numpy as np
from flask_cors import CORS
from collections import Counter
import webcolors
from scipy.spatial import KDTree

app = Flask(__name__)
CORS(app)


# تابعی برای پیدا کردن نزدیک‌ترین نام رنگ (دقیق‌تر با KDTree)
def get_closest_color_name(requested_color):
    css3_db = webcolors.CSS3_NAMES_TO_HEX
    names = []
    rgb_values = []

    for name, hex_value in css3_db.items():
        names.append(name)
        rgb_values.append(webcolors.hex_to_rgb(hex_value))

    kdtree = KDTree(rgb_values)
    distance, index = kdtree.query(requested_color)
    return names[index]


# تشخیص رنگ‌های مو از تصویر
def detect_hair_colors(image_path):
    image = cv2.imread(image_path)
    image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

    # فقط ناحیه بالای تصویر (حدس می‌زنیم مو اینجاست)
    height, width, _ = image.shape
    top_section = image[:height // 3]

    # آماده‌سازی داده‌ها برای KMeans
    pixels = np.float32(top_section.reshape(-1, 3))

    num_clusters = 6  # خوشه‌بندی برای پیدا کردن چند رنگ غالب
    _, labels, centers = cv2.kmeans(pixels, num_clusters, None,
                                    (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 100, 0.2),
                                    10, cv2.KMEANS_RANDOM_CENTERS)

    centers = np.uint8(centers)
    counts = Counter(labels.flatten())
    total_pixels = sum(counts.values())

    # استخراج رنگ‌های اصلی و نام آن‌ها
    colors_info = []

    for idx, count in counts.items():
        rgb_color = tuple(int(c) for c in centers[idx])  # تبدیل uint8 به int
        hex_color = "#{:02x}{:02x}{:02x}".format(*rgb_color)
        color_name = get_closest_color_name(rgb_color)
        percentage = (count / total_pixels) * 100

        colors_info.append({
            'hex': hex_color,
            'rgb': rgb_color,
            'name': color_name,
            'percentage': round(percentage, 2)
        })

    colors_info.sort(key=lambda x: x['percentage'], reverse=True)

    # تشخیص ترکیب رنگ‌ها (ترکیب 2 یا 3 تا رنگ)
    primary_colors = [c['name'] for c in colors_info[:2]]

    # ترکیب رنگ‌ها (یک فرض ساده برای رنگ مو)
    if len(primary_colors) >= 2:
        blend_name = f"{primary_colors[0]} + {primary_colors[1]}"
    else:
        blend_name = primary_colors[0]

    return {
        'dominant_colors': colors_info,
        'blend_suggestion': blend_name
    }


@app.route('/analyze_hair', methods=['POST'])
def analyze_hair():
    if 'image' not in request.files:
        return jsonify({'error': 'No image uploaded'}), 400

    image = request.files['image']
    image_path = 'uploaded_image.jpg'
    image.save(image_path)

    result = detect_hair_colors(image_path)

    return jsonify(result)


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)

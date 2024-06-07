from flask import Flask, render_template, request, abort, send_from_directory
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image, ImageEnhance
import requests
import os
import base64

app = Flask(__name__)  # Создание экземпляра приложения Flask
app.config['MAX_CONTENT_LENGTH'] = 1024 * 1024  # 1 MB лимит для загружаемых файлов
UPLOAD_FOLDER = './uploads'  # Папка для загруженных файлов
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
RECAPTCHA_SITE_KEY = '6LdlLBAmAAAAADEkPEp1BIl_lbDYwzeE_n6lkhBt'


# Эндпоинт для изменения контрастности изображения
@app.route('/contrast', methods=['POST'])
def contrast():
    # Получение загруженного файла и значения контрастности из запроса
    file = request.files.get('file')

    # Получение значений контрастности для каждого цветового канала из запроса
    red_contrast_str = request.form.get('red_contrast')
    green_contrast_str = request.form.get('green_contrast')
    blue_contrast_str = request.form.get('blue_contrast')

    # Проверка наличия загруженного файла
    if not file:
        abort(400, 'No file was uploaded')
    # Проверка формата загруженного файла
    if not file.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
        abort(400, 'File is not an image')

    # Проверка результата проверки reCAPTCHA
    recaptcha_response = request.form.get('g-recaptcha-response')
    if not recaptcha_response:
        abort(400, 'reCAPTCHA verification failed')
    # Проверка результата верификации reCAPTCHA
    payload = {
        'secret': '6LdlLBAmAAAAABbqK-N4kGXshV9m_96TNR9Ka6ER',
        'response': recaptcha_response
    }
    response = requests.post('https://www.google.com/recaptcha/api/siteverify', payload).json()
    if not response['success']:
        abort(400, 'reCAPTCHA verification failed')

    # Загрузка изображения
    img = Image.open(file)

    # Разделение изображения на каналы RGB
    red_channel, green_channel, blue_channel = img.split()

    # Преобразование значений контрастности в числовой формат
    red_contrast = float(red_contrast_str) / 50.0 if red_contrast_str else 1.0
    green_contrast = float(green_contrast_str) / 50.0 if green_contrast_str else 1.0
    blue_contrast = float(blue_contrast_str) / 50.0 if blue_contrast_str else 1.0

    # Применение изменения контрастности к каждому каналу
    red_contrasted = ImageEnhance.Contrast(red_channel).enhance(red_contrast)
    green_contrasted = ImageEnhance.Contrast(green_channel).enhance(green_contrast)
    blue_contrasted = ImageEnhance.Contrast(blue_channel).enhance(blue_contrast)

    # Сборка каналов в единое изображение
    contrasted_img = Image.merge('RGB', (red_contrasted, green_contrasted, blue_contrasted))

    # Вычисление распределения цветов оригинального и измененного изображений
    orig_colors = get_color_distribution(img)
    contrasted_colors = get_color_distribution(contrasted_img)

    # Построение графиков распределения цветов
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 6))
    fig.suptitle('Color Distribution')
    ax1.bar(np.arange(len(orig_colors)), [c[0] / 255 for c in orig_colors],
            color=[tuple(np.array(c[1]) / 255) for c in orig_colors])
    ax1.set_xticks(np.arange(len(orig_colors)))
    ax1.set_xticklabels([c[1] for c in orig_colors], rotation=45)
    ax1.set_title('Original Image')
    ax2.bar(np.arange(len(contrasted_colors)), [c[0] / 255 for c in contrasted_colors],
            color=[tuple(np.array(c[1]) / 255) for c in contrasted_colors])
    ax2.set_xticks(np.arange(len(contrasted_colors)))
    ax2.set_xticklabels([c[1] for c in contrasted_colors], rotation=45)
    ax2.set_title('Contrasted Image')
    plt.tight_layout()

    # Сохранение графика в файл
    plot_filename = os.path.join(app.config['UPLOAD_FOLDER'], 'plot.png')
    plt.savefig(plot_filename)
    # Сохранение измененного изображения в файл
    contrasted_filename = os.path.join(app.config['UPLOAD_FOLDER'], 'contrasted.png')
    contrasted_img.save(contrasted_filename)
    orig_filename = os.path.join(app.config['UPLOAD_FOLDER'], 'orig.png')
    img.save(orig_filename)

    # Получение имени файла для результата
    result_filename = os.path.basename(plot_filename)

    # Открытие файла с графиком в бинарном режиме
    with open(plot_filename, 'rb') as f:
        plot_bytes = f.read()

    # Кодирование графика в base64 для отображения на веб-странице
    plot_base64 = base64.b64encode(plot_bytes).decode('utf-8')

    # Возврат шаблона страницы результата с данными для отображения
    return render_template('result.html', orig=orig_filename, plot=plot_base64, result_filename=result_filename)


# Главная страница
@app.route('/', methods=['GET'])
def index():
    return render_template('index.html', sitekey=RECAPTCHA_SITE_KEY)


# Вспомогательная функция для получения распределения цветов изображения
def get_color_distribution(img):
    colors = img.getcolors(img.size[0] * img.size[1])
    return sorted(colors, key=lambda x: x[0], reverse=True)[:10]


# Маршрут для отображения загруженных файлов
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


if __name__ == '__main__':
    app.config['UPLOAD_FOLDER'] = 'uploads'
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    app.run(debug=True)

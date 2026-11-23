import os
import json
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, send_from_directory
import torch
import torch.nn as nn
from torchvision import models, transforms
from PIL import Image

app = Flask(__name__)

CLASSES = ['BA', 'BL', 'BNE', 'EO', 'LY', 'MMY', 'MO', 'MY', 'PC', 'PLY', 'PMY', 'SNE', 'VLY']

CLASS_NAMES_PL = {
    'BA': 'Bazofil (BA)',
    'BL': 'Blast (BL)',
    'BNE': 'Neutrofil pałeczkowaty (BNE)',
    'EO': 'Eozynofil (EO)',
    'LY': 'Limfocyt typowy (LY)',
    'MMY': 'Metamielocyt (MMY)',
    'MO': 'Monocyt (MO)',
    'MY': 'Mielocyt (MY)',
    'PC': 'Komórka plazmatyczna (PC)',
    'PLY': 'Prolimfocyt (PLY)',
    'PMY': 'Promielocyt (PMY)',
    'SNE': 'Neutrofil segmentowany (SNE)',
    'VLY': 'Limfocyt atypowy (VLY)'
}

#historia analiz i model wybrany przez dewelopera
BASE_DIR = os.path.dirname(__file__)
HISTORY_FILE = os.path.join(BASE_DIR, 'history.json')
SETTINGS_FILE = os.path.join(BASE_DIR, 'model_settings.json')

#folder do zapisywania przesłanych obrazów
app.config['UPLOAD_FOLDER'] = os.path.join(BASE_DIR, 'static', 'uploads')
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

if os.path.exists(HISTORY_FILE):
    with open(HISTORY_FILE, 'r', encoding='utf-8') as file:
        history = json.load(file)
else:
    history = []

if os.path.exists(SETTINGS_FILE):
    with open(SETTINGS_FILE, 'r', encoding='utf-8') as file:
        ACTIVE_MODEL = json.load(file)['active_model']
else:
    ACTIVE_MODEL = 'resnet50'

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

def load_model(model_name):
    if model_name == 'resnet18':
        loaded_model = models.resnet18(weights=None)
    elif model_name == 'resnet50':
        loaded_model = models.resnet50(weights=None)
    elif model_name == 'resnet152':
        loaded_model = models.resnet152(weights=None)
    else:
        raise ValueError(f'Nieznany model: {model_name}')

    loaded_model.fc = nn.Linear(loaded_model.fc.in_features, len(CLASSES))

    model_path = os.path.join(BASE_DIR, 'reports', model_name, f'best_{model_name}_wbc.pth')
    loaded_model.load_state_dict(torch.load(model_path, map_location=device, weights_only=True))
    loaded_model.to(device)
    loaded_model.eval()

    return loaded_model


model = load_model(ACTIVE_MODEL)

transform = transforms.Compose([
    transforms.Resize((368, 368)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
])


@app.route("/", methods=['GET', 'POST'])
def home():
    image_path = None
    result = None
    confidence = None
    top_alternatives = None
    all_probabilities = []
    selected = None

    if request.method == 'POST':
        if 'file' in request.files:
            file = request.files['file']
            if file.filename != '':
                analysis_id = datetime.now().strftime('%Y%m%d%H%M%S%f') #nazwa pliku w historii analiz
                filename = analysis_id + '.jpg'
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)

                image = Image.open(file.stream).convert('RGB')
                image.save(file_path)
                
                input_tensor = transform(image).unsqueeze(0).to(device)
                with torch.no_grad():
                    outputs = model(input_tensor)
                    probabilities = torch.nn.functional.softmax(outputs, dim=1)[0]
                    top_probabilities, top_index = torch.topk(probabilities, 3)

                short_label = CLASSES[top_index[0].item()]
                result = CLASS_NAMES_PL.get(short_label, short_label)
                confidence = f"{top_probabilities[0].item() * 100:.2f}%"

                top_alternatives = []
                for i in range(1, 3):
                    alt_label = CLASSES[top_index[i].item()]
                    alt_name = CLASS_NAMES_PL.get(alt_label, alt_label)
                    alt_conf = f"{top_probabilities[i].item() * 100:.2f}%"
                    top_alternatives.append((alt_name, alt_conf))

                probabilities_dict = {}
                for i, code in enumerate(CLASSES):
                    probabilities_dict[code] = round(probabilities[i].item() * 100, 2)
                history.insert(0, {
                    'id': analysis_id,
                    'date': datetime.now().strftime('%d.%m.%Y %H:%M'),
                    'filename': filename,
                    'model': ACTIVE_MODEL,
                    'prediction': short_label,
                    'confidence': confidence,
                    'probabilities': probabilities_dict,
                    'corrected_label': None
                })
                with open(HISTORY_FILE, 'w', encoding='utf-8') as file:
                    json.dump(history, file, indent=4, ensure_ascii=False)
                return redirect(url_for('home', analysis_id=analysis_id))

    #odczyt wybranej analizy z historii
    for item in history:
        if item['id'] == request.args.get('analysis_id'):
            selected = item
            break

    if selected:
        image_path = url_for('static', filename='uploads/' + selected['filename'])
        result = CLASS_NAMES_PL[selected['prediction']]
        confidence = selected['confidence']

        all_probabilities = [
            (CLASS_NAMES_PL[code], value)
            for code, value in selected['probabilities'].items()
        ]

        all_probabilities.sort(key=lambda item: item[1], reverse=True)

        top_alternatives = [
            (name, f'{value:.2f}%')
            for name, value in all_probabilities[1:3]
        ]

    return render_template(
        'laboratory.html',
        image_path=image_path,
        result=result,
        confidence=confidence,
        alternatives=top_alternatives,
        all_probabilities=all_probabilities,
        history=history,
        selected=selected,
        class_names=CLASS_NAMES_PL,
        active_model=ACTIVE_MODEL
    )

#ręczna korekta etykiety
@app.route('/correct/<analysis_id>', methods=['POST'])
def correct_label(analysis_id):
    new_label = request.form['new_label']

    if new_label in CLASSES:
        for item in history:
            if item['id'] == analysis_id:
                item['corrected_label'] = new_label

                with open(HISTORY_FILE, 'w', encoding='utf-8') as file:
                    json.dump(history, file, indent=4, ensure_ascii=False)

                break

    return redirect(url_for('home', analysis_id=analysis_id))

#zmiana modelu aktywnego w laboratorium
@app.route('/set-active-model', methods=['POST'])
def set_active_model():
    global ACTIVE_MODEL, model
    new_model = request.form['active_model']
    if new_model in ['resnet18', 'resnet50', 'resnet152']:
        path = os.path.join(BASE_DIR, 'reports', new_model, f'best_{new_model}_wbc.pth')
        if not os.path.exists(path):
            return 'Najpierw wytrenuj i zapisz wybrany model.', 400
        model = load_model(new_model)
        ACTIVE_MODEL = new_model
        with open(SETTINGS_FILE, 'w', encoding='utf-8') as file:
            json.dump({'active_model': ACTIVE_MODEL}, file, indent=4)
    return redirect(url_for(
        'developer',
        model=request.form.get('view_model', 'resnet50'),
        tab=request.form.get('tab', 'classes'),
        cell=request.form.get('cell', 'all'),
        split=request.form.get('split', 'test')
    ))

#odczyt raportów
def read_json(path):
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as file:
            return json.load(file)
    return None

@app.route('/developer')
def developer():
    selected_model = request.args.get('model', 'resnet50')
    selected_class = request.args.get('cell', 'all')
    split = request.args.get('split', 'test')
    tab = request.args.get('tab', 'classes')

    report_dir = os.path.join(BASE_DIR, 'reports', selected_model)

    #dane o zbiorze 
    dataset = read_json(
        os.path.join(BASE_DIR, '..', 'data', 'wbcbench', 'dataset_info.json')
    )
    #parametry treningu i historia uczenia
    parameters = read_json(
        os.path.join(report_dir, 'training_params.json')
    )
    training_history = read_json(
        os.path.join(report_dir, 'training_history.json')
    )
    #wyniki walidacyjne lub testowe
    metrics = read_json(
        os.path.join(report_dir, f'{split}_metrics.json')
    )
    #wyniki obu sieci do porównania
    comparison = {}

    for name in ['resnet50', 'resnet152', 'resnet18']:
        comparison[name] = read_json(
            os.path.join(BASE_DIR, 'reports', name, f'{split}_metrics.json')
        )

    max_count = max(dataset['counts']['train'].values()) if dataset else 1

    #statystyki wybranej klasy
    selected_stats = None
    confusion_row = []

    if selected_class != 'all' and metrics:
        i = CLASSES.index(selected_class)
        cm = metrics['confusion_matrix']

        correct = cm[i][i]
        predicted_total = sum(row[i] for row in cm)
        actual_total = sum(cm[i])

        precision = round(100 * correct / predicted_total, 2) if predicted_total else 0
        recall = round(100 * correct / actual_total, 2) if actual_total else 0
        f1 = round(2 * precision * recall / (precision + recall), 2) if precision + recall else 0

        selected_stats = {
            'precision': precision,
            'recall': recall,
            'f1': f1,
            'support': actual_total,
            'correct': correct,
            'errors': actual_total - correct
        }

        confusion_row = list(zip(CLASSES, cm[i]))

    return render_template(
        'developer.html',
        model_name=selected_model,
        active_model=ACTIVE_MODEL,
        selected_class=selected_class,
        split=split,
        tab=tab,
        dataset=dataset,
        parameters=parameters,
        training_history=training_history,
        metrics=metrics,
        comparison=comparison,
        max_count=max_count,
        selected_stats=selected_stats,
        confusion_row=confusion_row,
        classes=CLASSES,
        class_names=CLASS_NAMES_PL
    )

#wykresy treningów
@app.route('/reports/<model_name>/<filename>')
def report_image(model_name, filename):
    if model_name not in ['resnet50', 'resnet152', 'resnet18']:
        return 'Nie znaleziono modelu', 404
    return send_from_directory(
        os.path.join(BASE_DIR, 'reports', model_name),
        filename
    )

if __name__ == '__main__':
    app.run(debug=True)

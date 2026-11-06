import os
from flask import Flask, render_template, request
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

UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'static', 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model = models.resnet50(weights=None)
model.fc = nn.Linear(model.fc.in_features, len(CLASSES))

MODEL_PATH = os.path.join(os.path.dirname(__file__), "best_resnet50_wbc.pth")
model.load_state_dict(torch.load(MODEL_PATH, map_location=device, weights_only=True))
model.to(device)
model.eval()

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

    if request.method == 'POST':
        if 'file' in request.files:
            file = request.files['file']
            if file.filename != '':
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
                file.save(file_path)
                image_path = "static/uploads/" + file.filename

                image = Image.open(file_path).convert('RGB')
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

    return render_template('index.html', image_path=image_path, result=result, confidence=confidence, alternatives=top_alternatives)

if __name__ == '__main__':
    app.run(debug=True)

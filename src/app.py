import os
from flask import Flask, render_template, request

app = Flask(__name__)

UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
@app.route("/", methods=['GET', 'POST'])
def home():
    image_path = None
    result = ""

    if request.method == 'POST':
        if 'file' in request.files:
            file = request.files['file']
            if file.filename != '':
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
                file.save(file_path)
                image_path = "static/uploads/" + file.filename
                result = ""

    return render_template('index.html', image_path=image_path, result=result)

if __name__ == '__main__':
    app.run(debug=True)

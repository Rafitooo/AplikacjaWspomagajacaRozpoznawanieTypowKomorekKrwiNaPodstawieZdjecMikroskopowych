function previewImage(event) {
    var input = event.target;

    var reader = new FileReader();
    reader.onload = function() {
        var output = document.getElementById('output-left');
        output.src = reader.result;
        output.style.display = 'block';
    }
    reader.readAsDataURL(input.files[0]);

    if (input.files && input.files[0]) {
        var fileName = input.files[0].name;
        document.getElementById('fileNameText').innerText = "Wybrany plik: " + fileName;
    }
}

var zoom = 1;
function changeZoom(value) {
    zoom = zoom + value;
    if (zoom < 1) zoom = 1;
    if (zoom > 4) zoom = 4;
    document.getElementById('output-left').style.transform =
        'scale(' + zoom + ')';
}

function resetZoom() {
    zoom = 1;
    document.getElementById('output-left').style.transform = 'scale(1)';
}

function showLoading() {
    var button = document.getElementById('analyzeButton');
    button.innerText = 'Trwa analiza...';
    button.disabled = true;
}
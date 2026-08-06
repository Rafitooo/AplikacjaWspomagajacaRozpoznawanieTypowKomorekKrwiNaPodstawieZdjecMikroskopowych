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
import copy
import datetime
import os
import pandas as pd
import sqlite3
import urllib.request
from app import app
from flask import Flask, flash, request, redirect, render_template, send_from_directory
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS
from sqlalchemy import create_engine
from werkzeug.utils import secure_filename

ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg', 'tif'])
# https://developer.here.com/blog/getting-started-with-geocoding-exif-image-metadata-in-python3
# https://speckyboy.com/custom-file-upload-fields/

def allowed_file(filename):
	return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

    
def get_geo(file):
    image = Image.open(file)
    image.verify()
    imgExif = image._getexif()
    labeled = {TAGS.get(k):v for k, v in imgExif.items()}
    # return imgExif[34853] if 34853 in imgExif else None
    return labeled['GPSInfo'] if 'GPSInfo' in labeled else None
    
def transform_geo(exif):
    # exif = imgExif[34853]
    geotagging = {}
    for (key, val) in GPSTAGS.items():
        if key in exif:
            geotagging[val] = exif[key]
    return geotagging


def get_decimal_from_dms(dms, ref):
    degrees = dms[0][0] / dms[0][1]
    minutes = dms[1][0] / dms[1][1] / 60.0
    seconds = dms[2][0] / dms[2][1] / 3600.0

    if ref in ['S', 'W']:
        degrees = -degrees
        minutes = -minutes
        seconds = -seconds

    return round(degrees + minutes + seconds, 5)

    
def get_coordinates(geotags):
    lat = get_decimal_from_dms(geotags['GPSLatitude'], geotags['GPSLatitudeRef'])
    lon = get_decimal_from_dms(geotags['GPSLongitude'], geotags['GPSLongitudeRef'])
    return {'x': lon, 'y': lat}


def manage_file(filename, orfilename, forma):      
    # exif = get_geo("F:/Git/geopictures_miranda/uploads/1583276828.549976.jpg")
    exif = get_geo(filename)
    if exif:
        geotags = transform_geo(exif)
        coords = get_coordinates(geotags)
        forma['latitud'] = coords['y']
        forma['longitud'] = coords['x']
        pdForma = pd.DataFrame(forma, index=[1])
        sent_to_db(pdForma, filename, orfilename)
        return 'Las coordenadas de la imagen {} son: Latitud {} y Longitud {}'.format(orfilename, coords['y'], coords['x'])
    else:
        os.remove(filename)
        return 'La imagen {} no contiene coordenadas. Activa el GPS (o los servicios de localización) de tu celular/cámara e intentálo otra vez.'.format(orfilename)
    
    
def sent_to_db(pdf, name1, name2):
    conn = sqlite3.connect("imagenes.db")
    pdf['nombre_imagen'] = name2
    pdf['ruta_imagen'] = name1
    # pdf['img_link'] = '<a href="http://example.com/{0}">link</a>'.format(1)
    pdf['img_link'] = '<a href="/uploads/{}">link</a>'.format(os.path.basename(name1))
    pdf.to_sql("listado", conn, if_exists="append", index=False)
    
    
@app.route('/')
def index():
    return render_template('index.html')
  
@app.route('/', methods=['POST'])
def upload_file():
    if request.method == 'POST':
        # check if the post request has the files part
        if 'files[]' not in request.files:
            flash('No file part')
            return redirect(request.url)
        files = request.files.getlist('files[]')
        responses = []
        forma = {k: request.form[k] for k in ["nombre", "apellidop", "apellidom", "correo", "localidad"]}
        for file in files:
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                newFilename = os.path.join(app.config['UPLOAD_FOLDER'], '{}{}'.format(datetime.datetime.now().timestamp(), os.path.splitext(filename)[1]))
                file.save(newFilename)
                responses.append(manage_file(newFilename, os.path.basename(filename), forma))
        for res in responses: 
            flash(res)
        return redirect('/')
        
@app.route('/data')
def results():
    engine = create_engine('sqlite:///imagenes.db')
    df = pd.read_sql_table("listado", engine)
    return render_template('results.html',  tables=[df.to_html(classes='data', escape=False)] , titles=['Resultados'])


@app.route('/uploads/<path:filename>')
def download_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'],
                               filename, as_attachment=True)    

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0')

if False:
    import sqlite3
    import pandas as pd
    from sqlalchemy import create_engine
    # conn = sqlite3.connect("imagenes.db")

import os
import re
import subprocess
from flask import Flask, request, jsonify, render_template_string

app = Flask(__name__)
SOUND_DIR = os.path.expanduser("~/sounds")
os.makedirs(SOUND_DIR, exist_ok=True)
ALLOWED = {".mp3", ".wav", ".ogg", ".m4a", ".flac", ".aac"}
current = None  # текущий процесс воспроизведения


def clean_name(name):
    name = os.path.basename(name)
    name = re.sub(r"[^\w .\-()]", "_", name, flags=re.UNICODE)
    return name


def stop_sound():
    global current
    if current and current.poll() is None:
        current.terminate()
    current = None


def play_sound(path):
    global current
    stop_sound()
    current = subprocess.Popen(
        ["mpv", "--no-video", "--really-quiet", "--ao=opensles", path],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def list_sounds():
    return sorted(
        f for f in os.listdir(SOUND_DIR)
        if os.path.splitext(f)[1].lower() in ALLOWED
    )


PAGE = """
<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Звуковая панель</title>
<style>
  body { font-family: sans-serif; background:#111; color:#eee; margin:0; padding:12px; }
  h2 { margin:8px 0; }
  .grid { display:grid; grid-template-columns:1fr 1fr; gap:10px; }
  .item { display:flex; gap:4px; }
  .play { flex:1; padding:18px 8px; font-size:16px; border:0; border-radius:10px;
          background:#2d7ff9; color:#fff; word-break:break-word; }
  .play:active { background:#1b5fc4; }
  .del { width:40px; border:0; border-radius:10px; background:#552; color:#fff; }
  .stop { width:100%; padding:16px; font-size:18px; border:0; border-radius:10px;
          background:#d33; color:#fff; margin:10px 0; }
  .box { background:#222; padding:12px; border-radius:10px; margin-top:16px; }
  #msg { color:#8f8; min-height:20px; }
</style>
</head>
<body>
<h2>🔊 Звуковая панель</h2>
<button class="stop" onclick="stopAll()">⏹ СТОП</button>
<div id="msg"></div>

<div class="grid">
{% for s in sounds %}
  <div class="item">
    <button class="play" onclick="play('{{ s|e }}')">{{ s }}</button>
    <button class="del" onclick="del('{{ s|e }}')">✕</button>
  </div>
{% else %}
  <p>Звуков пока нет. Загрузи ниже.</p>
{% endfor %}
</div>

<div class="box">
  <b>Добавить звуки (с этого телефона):</b><br><br>
  <input type="file" id="files" multiple accept="audio/*"><br><br>
  <button onclick="upload()" style="padding:12px 20px;">Загрузить</button>
</div>

<script>
function show(t){ document.getElementById('msg').textContent = t; }
async function post(url, data){
  const r = await fetch(url, {method:'POST',
    headers:{'Content-Type':'application/json'}, body:JSON.stringify(data)});
  return r.json();
}
async function play(name){ const j = await post('/play', {name}); show(j.ok ? '▶ ' + name : 'Ошибка'); }
async function stopAll(){ await post('/stop', {}); show('Остановлено'); }
async function del(name){
  if(!confirm('Удалить ' + name + '?')) return;
  await post('/delete', {name}); location.reload();
}
async function upload(){
  const files = document.getElementById('files').files;
  if(!files.length){ show('Выбери файлы'); return; }
  const fd = new FormData();
  for (const f of files) fd.append('files', f);
  show('Загружаю...');
  await fetch('/upload', {method:'POST', body:fd});
  location.reload();
}
</script>
</body>
</html>
"""


@app.route("/")
def index():
    return render_template_string(PAGE, sounds=list_sounds())


@app.route("/play", methods=["POST"])
def play():
    name = clean_name(request.json.get("name", ""))
    path = os.path.join(SOUND_DIR, name)
    if not os.path.isfile(path):
        return jsonify(ok=False), 404
    play_sound(path)
    return jsonify(ok=True)


@app.route("/stop", methods=["POST"])
def stop():
    stop_sound()
    return jsonify(ok=True)


@app.route("/upload", methods=["POST"])
def upload():
    for f in request.files.getlist("files"):
        name = clean_name(f.filename or "")
        if os.path.splitext(name)[1].lower() in ALLOWED:
            f.save(os.path.join(SOUND_DIR, name))
    return jsonify(ok=True)


@app.route("/delete", methods=["POST"])
def delete():
    name = clean_name(request.json.get("name", ""))
    path = os.path.join(SOUND_DIR, name)
    if os.path.isfile(path):
        os.remove(path)
    return jsonify(ok=True)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)

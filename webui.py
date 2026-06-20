"""圣栎美家·视频生成器 Web界面"""
import json, subprocess, os, sys, threading, webbrowser, time
from pathlib import Path
from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
import uvicorn

app = FastAPI(title='圣栎美家·视频生成器')

BASE = Path(__file__).parent
OUT_DIR = Path(r'D:\全屋定制\圣栎美家文件夹\测试输出')

# 配置数据
TEMPLATES = {
    'product-showcase': {'label': '全屏产品图轮播', 'desc': '产品图全屏展示+交叉淡入淡出+Ken Burns'},
    'talking-head': {'label': '全屏人物口播', 'desc': '人物视频全屏+柔化暗角'},
    'split-screen': {'label': '分屏（人物+产品）', 'desc': '上半人物口播+下半产品轮播'},
    'pip': {'label': '画中画', 'desc': '产品全屏背景+右下角人物'},
}

BGMS = {
    'emotional-piano': '温馨钢琴',
    'calm-piano': '平静钢琴',
    'piano-classical': '古典钢琴',
    'soft-instrumental': '柔和器乐',
    'bright-corporate': '轻快企业',
    'inspiring-corporate': '励志管弦',
    'upbeat-corporate': '欢快企业',
}

STYLES = ['', '现代简约', '轻奢', '新中式', '北欧', '意式', '日式']

# 状态
gen_status = {'running': False, 'log': [], 'output': '', 'error': ''}


@app.get('/api/status')
def get_status():
    return gen_status


@app.get('/api/options')
def get_options():
    videos = []
    for f in sorted(OUT_DIR.glob('*.mp4')):
        if f.stat().st_size > 1024 * 1024:
            videos.append({'name': f.name, 'size': f.stat().st_size // 1024 // 1024})
    return {
        'videos': videos,
        'templates': TEMPLATES,
        'bgms': BGMS,
        'styles': STYLES,
    }


@app.post('/api/generate')
def start_generate(
    script: str = Form(''),
    video: str = Form(''),
    template: str = Form(...),
    bgm: str = Form(...),
    style: str = Form(''),
):
    if gen_status['running']:
        return JSONResponse({'error': '已有任务在运行'}, status_code=400)
    if not video and not script:
        return JSONResponse({'error': '请选择视频或输入文案'}, status_code=400)

    gen_status['running'] = True
    gen_status['log'] = []
    gen_status['output'] = ''
    gen_status['error'] = ''

    def run():
        try:
            hf = BASE / 'make_hf_subtitle.py'
            env = os.environ.copy()
            env['HF_TEMPLATE'] = template
            env['HF_BGM'] = bgm
            if style: env['HF_STYLE'] = style

            if video:
                env['HF_VIDEO'] = str(OUT_DIR / video)
            if script:
                env['HF_SCRIPT'] = script

            proc = subprocess.Popen(
                [sys.executable, str(hf)],
                cwd=str(BASE), stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, env=env, encoding='utf-8', errors='replace',
            )
            for line in proc.stdout:
                line = line.rstrip()
                if line and 'Exception' not in line and 'Traceback' not in line:
                    gen_status['log'].append(line)
            proc.wait()
            outs = sorted(OUT_DIR.glob('*.mp4'), key=lambda p: p.stat().st_mtime, reverse=True)
            if outs:
                gen_status['output'] = outs[0].name
        except Exception as e:
            gen_status['error'] = str(e)
        finally:
            gen_status['running'] = False

    threading.Thread(target=run, daemon=True).start()
    return {'ok': True}


@app.get('/download/{name}')
def download(name: str):
    fp = OUT_DIR / name
    if fp.exists():
        return FileResponse(str(fp), filename=name)
    return JSONResponse({'error': 'not found'}, status_code=404)


HTML = '''<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=900">
<title>圣栎美家 · 视频生成器</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:'Microsoft YaHei','PingFang SC',sans-serif;background:#0f0d0a;color:#d4c8b0;min-height:100vh}
.header{background:linear-gradient(135deg,#1a1410 0%,#2a2218 100%);border-bottom:1px solid rgba(201,160,48,0.15);padding:20px 0}
.header-inner{max-width:800px;margin:0 auto;padding:0 24px;display:flex;align-items:center;gap:16px}
.header-logo{width:48px;height:48px;background:linear-gradient(135deg,#c9a030,#e8c860);border-radius:12px;display:flex;align-items:center;justify-content:center;font-size:24px;font-weight:900;color:#1a1410}
.header-title{font-size:22px;font-weight:700;color:#e8dcc0;letter-spacing:4px}
.header-sub{font-size:13px;color:#6a6040;letter-spacing:2px}
.container{max-width:800px;margin:0 auto;padding:24px}
.card{background:linear-gradient(180deg,#1a1612 0%,#15110d 100%);border:1px solid rgba(201,160,48,0.1);border-radius:12px;padding:24px;margin-bottom:16px}
.card-title{font-size:14px;color:#8a7a5a;margin-bottom:12px;letter-spacing:2px;display:flex;align-items:center;gap:8px}
.card-title::before{content:'';width:3px;height:14px;background:#c9a030;border-radius:2px}
.row{display:flex;gap:12px;flex-wrap:wrap}
.col{flex:1;min-width:180px}
label{display:block;font-size:12px;color:#6a6040;margin-bottom:4px;letter-spacing:1px}
select{width:100%;padding:10px 12px;background:#0f0d0a;border:1px solid rgba(201,160,48,0.15);border-radius:8px;color:#d4c8b0;font-size:14px;font-family:inherit;cursor:pointer;transition:border-color 0.2s}
select:hover,select:focus{border-color:rgba(201,160,48,0.4);outline:none}
select option{background:#1a1612;color:#d4c8b0}
.desc-text{font-size:12px;color:#5a5040;margin-top:4px;min-height:18px}
.btn-generate{width:100%;padding:16px;background:linear-gradient(135deg,#c9a030,#e8c860);border:none;border-radius:10px;color:#1a1410;font-size:18px;font-weight:700;cursor:pointer;letter-spacing:4px;transition:all 0.3s;margin-top:4px}
.btn-generate:hover{transform:translateY(-1px);box-shadow:0 4px 20px rgba(201,160,48,0.3)}
.btn-generate:disabled{opacity:0.3;cursor:not-allowed;transform:none;box-shadow:none}
.btn-generate.running{background:linear-gradient(135deg,#6a6040,#8a7a5a)}
.log-box{background:#080604;border-radius:8px;padding:16px;height:200px;overflow-y:auto;font-size:13px;font-family:'Consolas','Courier New',monospace;color:#6a6050;line-height:1.6;margin-top:8px;white-space:pre-wrap}
.log-box .highlight{color:#9a8a6a}
.download-box{display:none;background:rgba(201,160,48,0.06);border:1px solid rgba(201,160,48,0.2);border-radius:10px;padding:20px;text-align:center;margin-top:12px}
.download-link{display:inline-block;padding:12px 32px;background:linear-gradient(135deg,#c9a030,#e8c860);border-radius:8px;color:#1a1410;font-size:16px;font-weight:700;text-decoration:none;letter-spacing:2px;transition:all 0.3s}
.download-link:hover{transform:translateY(-1px);box-shadow:0 4px 15px rgba(201,160,48,0.3)}
.status-bar{display:flex;align-items:center;gap:10px;margin-bottom:8px}
.status-dot{width:8px;height:8px;border-radius:50%;background:#3a3a2a}
.status-dot.busy{background:#c9a030;animation:pulse 1.2s infinite}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:0.3}}
.status-text{font-size:13px;color:#5a5040}
.progress-bar{height:2px;background:rgba(201,160,48,0.1);border-radius:2px;overflow:hidden;margin-bottom:8px}
.progress-fill{height:100%;background:linear-gradient(90deg,#c9a030,#e8c860);border-radius:2px;transition:width 0.5s;width:0%}
@media(max-width:600px){.col{min-width:100%}}
</style>
</head>
<body>
<div class="header">
  <div class="header-inner">
    <div class="header-logo">圣</div>
    <div>
      <div class="header-title">圣栎美家</div>
      <div class="header-sub">短视频一键生成器</div>
    </div>
  </div>
</div>

<div class="container">
  <div class="card">
    <div class="card-title">创作文案</div>
    <textarea id="script" rows="5" style="width:100%;padding:12px;background:#0f0d0a;border:1px solid rgba(201,160,48,0.15);border-radius:8px;color:#d4c8b0;font-size:14px;font-family:inherit;resize:vertical" placeholder="输入你的口播文案..."></textarea>
    <div style="display:flex;gap:8px;margin-top:8px;align-items:center">
      <span style="font-size:12px;color:#5a5040">可手动输入或留空直接使用视频</span>
    </div>
  </div>

  <div class="card">
    <div class="card-title">选择视频源</div>
    <select id="video"><option value="">加载中...</option></select>
    <div class="desc-text" id="video-desc">选择需要处理的口播视频</div>
  </div>

  <div class="card">
    <div class="card-title">模板与配乐</div>
    <div class="row">
      <div class="col">
        <label>视频模板</label>
        <select id="template"></select>
        <div class="desc-text" id="template-desc"></div>
      </div>
      <div class="col">
        <label>背景音乐</label>
        <select id="bgm"></select>
        <div class="desc-text" id="bgm-desc"></div>
      </div>
      <div class="col">
        <label>产品图风格</label>
        <select id="style"><option value="">自动匹配</option></select>
        <div class="desc-text">留空则自动从素材库匹配</div>
      </div>
    </div>
  </div>

  <button class="btn-generate" id="genBtn" onclick="generate()">开始生成</button>

  <div class="card" style="margin-top:16px">
    <div class="status-bar">
      <div class="status-dot" id="statusDot"></div>
      <span class="status-text" id="statusText">就绪</span>
    </div>
    <div class="progress-bar"><div class="progress-fill" id="progressFill"></div></div>
    <div class="log-box" id="logBox">选择视频和模板，点击「开始生成」</div>
  </div>

  <div class="download-box" id="downloadBox">
    <div style="margin-bottom:10px;font-size:14px;color:#8a7a5a">🎬 视频生成完成</div>
    <a class="download-link" id="downloadLink" href="#">下载视频</a>
  </div>
</div>

<script>
async function loadOptions(){
  const res = await fetch('/api/options');
  const data = await res.json();

  const vs = document.getElementById('video');
  vs.innerHTML = '<option value="">使用已有视频（选一个）</option>' +
    data.videos.map(v => '<option value="' + v.name + '">' + v.name + ' (' + v.size + 'MB)</option>').join('');
  vs.onchange = () => document.getElementById('video-desc').textContent = vs.value ? '已选择: ' + vs.value : '选择需要处理的口播视频';

  const ts = document.getElementById('template');
  ts.innerHTML = Object.entries(data.templates).map(([k, v]) =>
    '<option value="' + k + '">' + v.label + '</option>').join('');
  ts.onchange = () => {
    const t = data.templates[ts.value];
    document.getElementById('template-desc').textContent = t ? t.desc : '';
  };
  ts.onchange();

  const bs = document.getElementById('bgm');
  bs.innerHTML = Object.entries(data.bgms).map(([k, v]) =>
    '<option value="' + k + '">' + v + '</option>').join('');
  bs.onchange = () => {
    const b = data.bgms[bs.value];
    document.getElementById('bgm-desc').textContent = b || '';
  };
  bs.onchange();

  const ss = document.getElementById('style');
  ss.innerHTML = '<option value="">自动匹配</option>' +
    data.styles.filter(Boolean).map(s => '<option value="' + s + '">' + s + '</option>').join('');
}
loadOptions();

function generate(){
  const btn = document.getElementById('genBtn');
  const video = document.getElementById('video').value;
  if (!video) { alert('请选择视频'); return; }
  btn.disabled = true; btn.textContent = '生成中...'; btn.classList.add('running');
  document.getElementById('downloadBox').style.display = 'none';
  document.getElementById('logBox').textContent = '';
  document.getElementById('progressFill').style.width = '5%';
  document.getElementById('statusText').textContent = '渲染中...';
  document.getElementById('statusDot').className = 'status-dot busy';

  const fd = new FormData();
  fd.append('script', document.getElementById('script').value);
  fd.append('video', video);
  fd.append('template', document.getElementById('template').value);
  fd.append('bgm', document.getElementById('bgm').value);
  fd.append('style', document.getElementById('style').value);

  fetch('/api/generate', {method:'POST', body:fd})
    .then(r => r.json())
    .then(d => { if (d.error) { log(d.error); resetBtn(); } else pollStatus(); })
    .catch(e => { log('错误: ' + e); resetBtn(); });
}

function pollStatus(){
  fetch('/api/status').then(r => r.json()).then(s => {
    const box = document.getElementById('logBox');
    if (s.running) {
      if (s.log.length) {
        const lines = s.log.slice(-60).join('\\n');
        box.textContent = lines;
        box.scrollTop = box.scrollHeight;
      }
      const progress = Math.min(s.log.length * 3, 90);
      document.getElementById('progressFill').style.width = progress + '%';
      setTimeout(pollStatus, 1500);
    } else {
      document.getElementById('progressFill').style.width = '100%';
      document.getElementById('statusDot').className = 'status-dot';
      document.getElementById('statusText').textContent = '完成';
      if (s.output) {
        document.getElementById('downloadLink').href = '/download/' + s.output;
        document.getElementById('downloadBox').style.display = 'block';
      }
      if (s.error) { box.textContent += '\\n错误: ' + s.error; }
      resetBtn();
    }
  });
}

function resetBtn(){
  const btn = document.getElementById('genBtn');
  btn.disabled = false; btn.textContent = '开始生成'; btn.classList.remove('running');
}

function log(msg){
  document.getElementById('logBox').textContent += msg + '\\n';
}
</script>
</body>
</html>'''


@app.get('/')
def index():
    return HTMLResponse(HTML)


if __name__ == '__main__':
    print('  ╔══════════════════════════════════════╗')
    print('  ║    圣栎美家 · 视频生成器            ║')
    print('  ║    http://localhost:9000              ║')
    print('  ╚══════════════════════════════════════╝')
    webbrowser.open('http://localhost:9000')
    uvicorn.run(app, host='0.0.0.0', port=9000, log_level='warning')

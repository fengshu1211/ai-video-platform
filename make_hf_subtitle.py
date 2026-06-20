"""HF字幕版 — 三种模板：产品展示 / 全口播 / 分屏，一键切换"""
import json, subprocess, os, shutil, glob, random, sys, time
from pathlib import Path
from PIL import Image

# ============================================================
# == 模板选择（改这里切换模式） =================================
TEMPLATE = os.environ.get('HF_TEMPLATE', 'product-showcase')
# 可选:
#   'product-showcase' — 全屏产品图轮播
#   'talking-head'     — 全屏人物口播
#   'split-screen'     — 上半人物 + 下半产品图
# ============================================================
# BGM预设（用 bgm_manager.py 管理曲库）
BGM_LIB = {
    'emotional-piano': r'D:\全屋定制\圣栎美家文件夹\知识库\素材入库工具\bgm_emotional_piano.mp3',
    'bright-corporate': r'D:\全屋定制\圣栎美家文件夹\知识库\素材入库工具\bgm_bright_corporate.mp3',
    'inspiring-corporate': r'D:\全屋定制\圣栎美家文件夹\知识库\素材入库工具\bgm_inspiring_corporate.mp3',
    'calm-piano': r'D:\全屋定制\圣栎美家文件夹\知识库\素材入库工具\bgm_calm_piano.mp3',
    'soft-instrumental': r'D:\全屋定制\圣栎美家文件夹\知识库\素材入库工具\bgm_soft_instrumental.mp3',
    'piano-classical': r'D:\全屋定制\圣栎美家文件夹\知识库\素材入库工具\bgm_piano_classical.mp3',
    'upbeat-corporate': r'D:\全屋定制\圣栎美家文件夹\知识库\素材入库工具\bgm_upbeat_corporate.mp3',
}
BGM_PRESET = os.environ.get('HF_BGM', 'emotional-piano')
BGM_VOLUME = 0.24
VIDEO_STYLE = os.environ.get('HF_STYLE', '')
# ============================================================

# ============ 文件路径 ============
VIDEO = os.environ.get('HF_VIDEO', '')
SCRIPT_TEXT = os.environ.get('HF_SCRIPT', '')
TTS_VOICE = os.environ.get('HF_TTS_VOICE', 'longanyang')
CLONE_VOICE_ID = os.environ.get('HF_CLONE_VOICE_ID', '')
OUT_DIR = r'D:\全屋定制\圣栎美家文件夹\测试输出'
MAT_DIR = r'D:\全屋定制\圣栎美家文件夹\知识库\公司各类图片、视频素材'

# ============================================================
# == TTS合成（无视频时用文案生成语音） ==========================
if not VIDEO or not os.path.exists(VIDEO):
    if SCRIPT_TEXT:
        print('TTS合成中...')
        tts_audio = str(Path(OUT_DIR) / '_tts_temp.mp3')
        model = 'cosyvoice-v3.5-flash' if CLONE_VOICE_ID else 'cosyvoice-v3-flash'
        voice = CLONE_VOICE_ID or TTS_VOICE
        subprocess.run(['bl','speech','synthesize','--text',SCRIPT_TEXT,'--voice',voice,
            '--model',model,'--out',tts_audio], capture_output=True, timeout=120)
        if os.path.exists(tts_audio) and os.path.getsize(tts_audio) > 1000:
            print('TTS完成')
            VIDEO = tts_audio
        else:
            print('TTS失败，使用默认视频')
            VIDEO = r'D:\全屋定制\圣栎美家文件夹\测试输出\姜口播视频.mp4'
    else:
        VIDEO = r'D:\全屋定制\圣栎美家文件夹\测试输出\姜口播视频.mp4'
else:
    print('使用视频:', os.path.basename(VIDEO))

# 自定义音色样本（全屏产品模式用）
custom_voice = str(Path(OUT_DIR) / 'custom_voice.mp3')
if TEMPLATE == 'product-showcase' and os.path.exists(custom_voice) and os.path.getsize(custom_voice) > 1000:
    print('使用自定义音色样本，克隆合成中...')
    # 上传声音样本到百炼并克隆
    import uuid
    clone_id = f"custom_clone_{uuid.uuid4().hex[:8]}"
    # 直接用cosyvoice-v3.5-flash配合参考音频做零样本克隆
    tts_audio = str(Path(OUT_DIR) / '_tts_temp.mp3')
    subprocess.run(['bl','speech','synthesize','--text',SCRIPT_TEXT,'--voice',custom_voice,
        '--model','cosyvoice-v3.5-flash','--out',tts_audio], capture_output=True, timeout=120)
    if os.path.exists(tts_audio) and os.path.getsize(tts_audio) > 1000:
        print('自定义音色合成完成')
        VIDEO = tts_audio
    else:
        print('自定义音色合成失败，使用默认TTS')
        # 继续走下面的TTS流程

# ============================================================
# == ① 自动化ASR — 有缓存就用，没有就自动调百炼识别 ============
ASR_CACHE = Path(OUT_DIR) / (Path(VIDEO).stem + '_asr.json')
# 也兼容旧版命名（手动生成的）
OLD_ASR = Path(OUT_DIR) / '姜口播_asr.json'
if OLD_ASR.exists() and not ASR_CACHE.exists():
    shutil.copy2(OLD_ASR, ASR_CACHE)

if ASR_CACHE.exists():
    print('使用ASR缓存:', ASR_CACHE.name)
    d = json.loads(open(ASR_CACHE, encoding='utf-8').read())
else:
    print('提取音频...')
    audio_wav = str(Path(OUT_DIR) / (Path(VIDEO).stem + '_audio.wav'))
    subprocess.run(['ffmpeg','-y','-i',VIDEO,'-vn','-acodec','pcm_s16le','-ar','16000',audio_wav],
                   capture_output=True, check=True)
    print('调用百炼语音识别...')
    r = subprocess.run(['bl','speech','recognize','--url',audio_wav,'--language','zh',
                        '--out',str(ASR_CACHE)],
                       capture_output=True, text=True, timeout=300)
    if r.returncode != 0:
        print('ASR失败:', r.stderr[-300:])
        sys.exit(1)
    print('ASR完成')
    d = json.loads(open(ASR_CACHE, encoding='utf-8').read())

sentences = d['transcripts'][0]['sentences']
print(f'模板: {TEMPLATE} | ASR: {len(sentences)}段, {sum(len(s.get("words",[])) for s in sentences)}词')

WORK = Path('d:/应用开发项目集/AI短视频创作平台项目') / 'render_work_hfsub'
WORK.mkdir(parents=True, exist_ok=True)
(WORK/'assets').mkdir(exist_ok=True)
subprocess.run(['ffmpeg','-y','-i',VIDEO,'-vn','-acodec','pcm_s16le','-ar','22050',
                str(WORK/'assets/audio.wav')], capture_output=True, timeout=180)

# === 产品图（分屏和展示模式需要，智能匹配） ===
valid_imgs = []
if TEMPLATE in ('product-showcase', 'split-screen'):
    mat_index_file = Path(MAT_DIR).parent / '_material_index.json'
    mat_index = {}
    if mat_index_file.exists():
        mat_index = json.loads(mat_index_file.read_text(encoding='utf-8'))
        print(f'素材索引: {len(mat_index)}张')

    # 智能匹配
    if mat_index and VIDEO_STYLE:
        matched = []
        for name, info in mat_index.items():
            if info.get('style') == VIDEO_STYLE and info.get('orientation') == '竖屏':
                matched.append(str(Path(MAT_DIR) / name))
        valid_imgs = matched[:10]
        if valid_imgs:
            print(f'智能匹配: {VIDEO_STYLE} -> {len(valid_imgs)}张')
        else:
            # 如果没匹配到同风格，用任何竖屏
            for name, info in mat_index.items():
                if info.get('orientation') == '竖屏':
                    valid_imgs.append(str(Path(MAT_DIR) / name))
            random.shuffle(valid_imgs)
            print(f'无精确匹配, 使用{len(valid_imgs)}张竖屏')
    else:
        # 无索引或无风格: 随机选竖屏
        mat_images = []
        for root, dirs, files in os.walk(MAT_DIR):
            for f in files:
                if f.lower().endswith(('.png', '.jpg', '.jpeg')):
                    mat_images.append(os.path.join(root, f))
        random.shuffle(mat_images)
        valid_imgs = [img for img in mat_images[:20] if Image.open(img).height > Image.open(img).width * 1.2]

    if not valid_imgs:
        from PIL import ImageDraw
        for i in range(3):
            dst = str(WORK/'assets'/f'prod_{i}.jpg')
            img = Image.new('RGB', (720, 1280), (42, 38, 32))
            draw = ImageDraw.Draw(img)
            for y in range(0, 1280, 40):
                c = 30 + y * 20 // 1280
                draw.rectangle([0, y, 720, y+20], fill=(c, c-5, c-10))
            img.save(dst, quality=85)
            valid_imgs.append(dst)
    else:
        for i, img in enumerate(valid_imgs):
            shutil.copy2(img, str(WORK/'assets'/f'prod_{i}.jpg'))
    print(f'产品图: {len(valid_imgs)}张')

# === 人物视频转码（口播和分屏需要） ===
if TEMPLATE in ('talking-head', 'split-screen'):
    subprocess.run(['ffmpeg','-y','-i',VIDEO,'-c:v','libx264','-b:v','3M','-an',
                    str(WORK/'assets/person.mp4')], capture_output=True, timeout=180)

# === 时长 ===
first_word_t = sentences[0]['words'][0]['begin_time'] / 1000
hook_dur = first_word_t
last_sent_end = sentences[-1]['end_time'] / 1000
outro_start = last_sent_end + 0.5
total_dur = outro_start + 3.0
FADE_DUR = 0.5  # 背景交叉淡入淡出时间

S = ''  # 全部场景HTML

# ============================================================
# 1. 钩子开场（通用）
# ============================================================
hook_title = "选择比努力更重要"
hook_sub = "愿赌服输是成年人的清醒"
S += f'''<div data-start="0" data-duration="{hook_dur:.2f}" class="clip">
  <div class="scene hook-scene">
    <div class="hook-bg"></div>
    <div class="hook-wrap">
      <div class="hook-title hook-anim">{hook_title}</div>
      <div class="hook-sub hook-anim-sub">{hook_sub}</div>
    </div>
  </div>
</div>'''

# ============================================================
# 2. 背景层（按模板不同）
# ============================================================
SUB_BOTTOM = 320  # 字幕距底距离，分屏模式下调

if TEMPLATE == 'product-showcase':
    # ---- 全屏产品图轮播 ----
    for si, sent in enumerate(sentences):
        sent_st = sent['begin_time'] / 1000
        sent_ed = sent['end_time'] / 1000
        bg_idx = si % max(len(valid_imgs), 1)
        bg_src = f'assets/prod_{bg_idx}.jpg'

        if si < len(sentences) - 1:
            next_st = sentences[si+1]['begin_time'] / 1000
            bg_end = next_st
        else:
            next_st = sent_ed
            bg_end = sent_ed + FADE_DUR

        bg_start = 0 if si == 0 else max(0, sent_st - FADE_DUR)
        bg_dur = max(bg_end - bg_start, 0.3)
        fade_out_delay = bg_dur - FADE_DUR
        zoom_dur = max(fade_out_delay - 0.3, 0)
        zoom_css = f',kenBurns {zoom_dur:.1f}s ease-out 0.3s both' if zoom_dur > 0.5 else ''

        S += f'''<div data-start="{bg_start:.2f}" data-duration="{bg_dur:.2f}" class="clip"
          style="animation:bgFadeIn {FADE_DUR}s ease 0s both,bgFadeOut {FADE_DUR}s ease {fade_out_delay:.2f}s both{zoom_css}">
          <img class="full-img product-img" src="{bg_src}" alt="">
          <div class="img-frame"></div>
          <div class="vignette"></div>
        </div>'''

elif TEMPLATE == 'talking-head':
    # ---- 全屏人物口播 ----
    S += f'''<div data-start="0" data-duration="{total_dur:.1f}" class="clip"
      style="animation:personZoom 30s ease-out 0.3s both">
      <video class="full-img" src="assets/person.mp4" muted playsinline loop></video>
      <div class="vignette-soft"></div>
    </div>'''

elif TEMPLATE == 'split-screen':
    if TEMPLATE == 'split-screen':
        SUB_BOTTOM = 180
        S += f'''<div data-start="0" data-duration="{total_dur:.1f}" class="clip">
          <div class="split-top">
            <video class="person-vid" src="assets/person.mp4" muted playsinline loop></video>
          </div>
        </div>'''

    # 产品图背景
    for si, sent in enumerate(sentences):
        sent_st = sent['begin_time'] / 1000
        sent_ed = sent['end_time'] / 1000
        bg_idx = si % max(len(valid_imgs), 1)
        bg_src = f'assets/prod_{bg_idx}.jpg'

        if si < len(sentences) - 1:
            next_st = sentences[si+1]['begin_time'] / 1000
            bg_end = next_st
        else:
            next_st = sent_ed
            bg_end = sent_ed + FADE_DUR

        bg_start = 0 if si == 0 else max(0, sent_st - FADE_DUR)
        bg_dur = max(bg_end - bg_start, 0.3)
        fade_out_delay = bg_dur - FADE_DUR
        zoom_dur = max(fade_out_delay - 0.3, 0)
        zoom_css = f',kenBurns {zoom_dur:.1f}s ease-out 0.3s both' if zoom_dur > 0.5 else ''

        S += f'''<div data-start="{bg_start:.2f}" data-duration="{bg_dur:.2f}" class="clip"
          style="animation:bgFadeIn {FADE_DUR}s ease 0s both,bgFadeOut {FADE_DUR}s ease {fade_out_delay:.2f}s both{zoom_css}">
          <div class="split-bottom">
            <img class="prod-img product-img" src="{bg_src}" alt="">
            <div class="img-frame-split"></div>
          </div>
        </div>'''



# ============================================================
# 3. 字幕 + 逐词高亮（通用）
# ============================================================
ENTRY_STYLES = ['slide-up', 'scale-in', 'fade-blur', 'slide-left']
for si, sent in enumerate(sentences):
    sent_st = sent['begin_time'] / 1000
    sent_ed = sent['end_time'] / 1000
    dur = sent_ed - sent_st
    words = sent.get('words', [])
    if not words: continue
    n_words = len(words)
    entry = ENTRY_STYLES[si % len(ENTRY_STYLES)]

    S += f'''<div data-start="{sent_st:.2f}" data-duration="{dur:.2f}" class="clip entry-{entry}">
    <div class="scene">
      <div class="sub-box" style="bottom:{SUB_BOTTOM}px">
        <div class="sub-line">'''
    for wi in range(n_words):
        S += f'<span class="word" id="ws{si}w{wi}">{words[wi]["text"]} </span>'
    S += '</div></div></div></div>'

    # 逐词高亮覆盖层
    for wi in range(n_words):
        w = words[wi]
        w_st = w['begin_time'] / 1000
        w_ed = w['end_time'] / 1000
        w_dur = max(w_ed - w_st, 0.12)

        S += f'''<div data-start="{w_st:.2f}" data-duration="{w_dur:.2f}" class="clip" style="z-index:12">
        <div class="scene">
          <div class="sub-box" style="bottom:{SUB_BOTTOM}px">
            <div class="sub-line" style="background:transparent">'''
        for wi2 in range(n_words):
            if wi2 == wi:
                S += f'<span class="word-glow">{words[wi2]["text"]} </span>'
            else:
                S += f'<span style="opacity:0">{words[wi2]["text"]} </span>'
        S += '</div></div></div></div>'

# ============================================================
# 4. 品牌结尾（通用）
# ============================================================
S += f'''<div data-start="{outro_start:.1f}" data-duration="3.0" class="clip">
  <div class="scene outro-scene">
    <div class="gold-glow"></div>
    <div class="closing">
      <div class="brand-name outro-anim">圣栎美家</div>
      <div class="brand-tag outro-anim-sub">源头工厂直供 · 免费量尺出图</div>
      <div class="brand-cta">满意再下单</div>
    </div>
  </div>
</div>'''

# 水印 + 分屏分隔线
S += f'''<div data-start="0" data-duration="{total_dur:.1f}" class="clip">
  <div class="watermark">圣栎美家</div>'''
if TEMPLATE == 'split-screen':
    S += '\n  <div class="split-divider"></div>'
S += '\n</div>'''

# ============================================================
# CSS（分屏模式需要额外样式）
# ============================================================
extra_css = ''
if TEMPLATE == 'split-screen':
    extra_css = '''
.split-top{position:absolute;top:0;left:0;right:0;height:50%;overflow:hidden;z-index:1}
.person-vid{width:100%;height:100%;object-fit:cover}
.split-bottom{position:absolute;top:50%;left:0;right:0;bottom:0;overflow:hidden}
.prod-img{width:100%;height:100%;object-fit:cover}
.img-frame-split{position:absolute;top:8px;left:8px;right:8px;bottom:8px;
  border:2px solid rgba(201,160,48,0.2);border-radius:6px;
  box-shadow:inset 0 0 20px rgba(201,160,48,0.06);pointer-events:none;z-index:2}
.split-divider{position:absolute;top:50%;left:40px;right:40px;height:1px;z-index:3;
  background:linear-gradient(90deg,transparent,rgba(201,160,48,0.6),transparent)}
'''
elif TEMPLATE == 'talking-head':
    extra_css = '''
@keyframes personZoom{from{transform:scale(1.02)}to{transform:scale(1.0)}}
.vignette-soft{position:absolute;inset:0;
  background:linear-gradient(180deg,rgba(0,0,0,0.3) 0%,transparent 20%,transparent 60%,rgba(0,0,0,0.6) 100%);z-index:2}
'''

css = f'''
*{{margin:0;padding:0;box-sizing:border-box}}html,body{{width:720px;height:1280px;overflow:hidden;background:#1a1410}}
.clip{{visibility:hidden}}[data-start]{{visibility:visible}}
.scene{{position:absolute;inset:0}}
.full-img{{position:absolute;inset:0;width:100%;height:100%;object-fit:cover}}
.product-img{{filter:sepia(0.2) saturate(1.15)}}
.img-frame{{position:absolute;inset:14px;z-index:2;border:2px solid rgba(201,160,48,0.2);
  border-radius:8px;box-shadow:inset 0 0 25px rgba(201,160,48,0.06),0 0 15px rgba(0,0,0,0.2);pointer-events:none}}
.vignette{{position:absolute;inset:0;background:linear-gradient(180deg,transparent 45%,rgba(0,0,0,0.75) 100%);z-index:2}}
@keyframes bgFadeIn{{from{{opacity:0}}to{{opacity:1}}}}
@keyframes bgFadeOut{{from{{opacity:1}}to{{opacity:0}}}}
@keyframes kenBurns{{from{{transform:scale(1.08);transform-origin:50% 50%}}to{{transform:scale(1.0);transform-origin:50% 50%}}}}
@keyframes slideUp{{from{{opacity:0;transform:translateY(40px)}}to{{opacity:1;transform:translateY(0)}}}}
@keyframes scaleIn{{from{{opacity:0;transform:scale(0.85)}}to{{opacity:1;transform:scale(1)}}}}
@keyframes fadeBlur{{from{{opacity:0;filter:blur(8px)}}to{{opacity:1;filter:blur(0)}}}}
@keyframes slideLeft{{from{{opacity:0;transform:translateX(-30px)}}to{{opacity:1;transform:translateX(0)}}}}
.entry-0 .sub-box{{animation:slideUp 0.4s ease-out both}}
.entry-1 .sub-box{{animation:scaleIn 0.5s ease-out both}}
.entry-2 .sub-box{{animation:fadeBlur 0.5s ease-out both}}
.entry-3 .sub-box{{animation:slideLeft 0.4s ease-out both}}
@keyframes hookZoom{{from{{opacity:0;transform:scale(2)}}to{{opacity:1;transform:scale(1)}}}}
@keyframes hookFade{{from{{opacity:1}}to{{opacity:0}}}}
.hook-scene{{z-index:5}}
.hook-bg{{position:absolute;inset:0;background:radial-gradient(ellipse at 50% 40%,rgba(0,0,0,0.15) 0%,rgba(0,0,0,0.5) 100%)}}
.hook-title{{font-size:60px;font-weight:900;color:#ff5530;text-align:center;font-family:Microsoft YaHei,sans-serif;text-shadow:0 2px 12px rgba(0,0,0,0.9)}}
.hook-sub{{font-size:36px;color:#fff;text-align:center;margin-top:16px;font-family:Microsoft YaHei,sans-serif;text-shadow:0 2px 8px rgba(0,0,0,0.8)}}
.hook-anim{{animation:hookZoom 0.5s ease-out 0.1s both,hookFade 0.3s ease-out {hook_dur-0.3:.2f}s both}}
.hook-anim-sub{{animation:slideUp 0.4s ease-out 0.5s both,hookFade 0.3s ease-out {hook_dur-0.25:.2f}s both}}
.sub-box{{position:absolute;left:40px;right:40px;z-index:10;text-align:center}}
.sub-line{{display:inline-block;background:rgba(0,0,0,0.5);padding:12px 22px;border-radius:6px;font-size:30px;font-weight:400;line-height:1.5;font-family:Microsoft YaHei,sans-serif}}
.word{{color:#ffffff;display:inline}}
.word-glow{{color:#ffd700;text-shadow:0 0 8px rgba(255,215,0,0.8),0 0 20px rgba(255,215,0,0.3);font-weight:700}}
.watermark{{position:absolute;top:28px;right:28px;z-index:3;font-size:16px;
  color:#c9a030;opacity:0.7;letter-spacing:3px;font-family:Microsoft YaHei,sans-serif;text-shadow:0 1px 6px rgba(0,0,0,0.5)}}
@keyframes brandIn{{from{{opacity:0;transform:scale(0.92)}}to{{opacity:1;transform:scale(1)}}}}
@keyframes fadeIn{{from{{opacity:0}}to{{opacity:1}}}}
.outro-scene{{background:#1a1410;z-index:8;animation:fadeIn 0.8s ease-out both}}
.gold-glow{{position:absolute;top:50%;left:50%;width:300px;height:300px;transform:translate(-50%,-50%);
  background:radial-gradient(circle,rgba(201,160,48,0.08) 0%,transparent 70%);z-index:1}}
.closing{{position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center;padding:0 40px;z-index:2}}
.brand-name{{font-size:52px;font-weight:bold;color:#c9a030;letter-spacing:6px;font-family:Microsoft YaHei,sans-serif}}
.brand-tag{{font-size:22px;color:rgba(232,200,96,0.7);letter-spacing:4px;margin-top:8px;font-family:Microsoft YaHei,sans-serif}}
.brand-cta{{margin-top:24px;font-size:22px;color:#fff;letter-spacing:2px;font-family:Microsoft YaHei,sans-serif}}
.outro-anim{{animation:brandIn 0.5s ease-out 0.4s both}}
.outro-anim-sub{{animation:fadeIn 0.4s ease-out 0.8s both}}
{extra_css}'''

# === HTML组装 ===
html = f'''<!doctype html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=720,height=1280">
<style>{css}</style></head><body>
<div data-composition-id="hfsub5" data-width="720" data-height="1280" data-start="0" data-duration="{total_dur:.1f}" data-fps="30">{S}</div>
<audio src="assets/audio.wav" data-track-index="2" data-start="0" data-duration="{total_dur:.1f}" class="clip"></audio>
<script src="https://cdn.jsdelivr.net/npm/gsap@3.12.5/dist/gsap.min.js"></script>
<script>window.__timelines=window.__timelines||{{}};window.__timelines["hfsub5"]=gsap.timeline({{paused:true}});</script>
</body></html>'''

(WORK/'index.html').write_text(html, encoding='utf-8')
n_words = sum(len(s.get("words",[])) for s in sentences)
print(f'HTML: {total_dur:.0f}s, {len(sentences)}句+{n_words}词覆盖')

# === 渲染 + BGM ===
print('渲染中...')
r = subprocess.run('npx hyperframes render', cwd=str(WORK), capture_output=True, text=True, timeout=600, shell=True)

vids = sorted((WORK/'renders').glob('*.mp4'), key=lambda p: p.stat().st_mtime, reverse=True)
if vids:
    render_out = str(vids[0])
    bgm_src = BGM_LIB.get(BGM_PRESET)
    if bgm_src and os.path.exists(bgm_src):
        mixed = str(WORK / 'mixed.mp4')
        print('混音BGM中 (%s, 侧链压缩)...' % BGM_PRESET)
        subprocess.run(['ffmpeg','-y','-i',render_out,'-i',bgm_src,
            '-filter_complex',
            '[1:a]volume=%f,sidechaincompress=threshold=0.015:ratio=8:attack=50:release=500[bgm];[0:a][bgm]amix=inputs=2:duration=first' % BGM_VOLUME,
            '-c:v','copy','-c:a','aac','-b:a','128k','-shortest',mixed],
            capture_output=True, timeout=120)
        final_out = mixed
    else:
        print('BGM未找到，使用原始音频')
        final_out = render_out

    final = str(Path(OUT_DIR) / f'HF_{TEMPLATE}_{time.strftime("%m%d_%H%M")}.mp4')
    shutil.copy2(final_out, final)
    sz = Path(final).stat().st_size // 1024
    print(f'完成! {sz}KB (模板:{TEMPLATE})')
else:
    print('渲染失败:', r.stderr[-500:] if r.stderr else '')

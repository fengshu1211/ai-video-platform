"""Test Paraformer ASR on server"""
import os, time, json
from urllib import request
import dashscope
from dashscope.audio.asr import Transcription

audio_dir = '/opt/ai-video-platform/backend/uploads/audio'
files = [f for f in os.listdir(audio_dir) if f.endswith('.mp3')]
if not files:
    print('No audio files found!')
    exit(1)

test_file = files[0]
audio_url = f'http://47.109.78.122/uploads/audio/{test_file}'
print(f'Testing with: {audio_url}')

task = Transcription.async_call(
    model='paraformer-v2',
    file_urls=[audio_url],
    timestamp_alignment_enabled=True,
)
task_id = task.output.task_id
print(f'Task ID: {task_id}')

for i in range(15):
    time.sleep(2)
    result = Transcription.wait(task=task_id)
    status = result.output.get('task_status', '') if result.output else ''
    print(f'  poll {i}: {status}')
    if status == 'SUCCEEDED':
        results = result.output.get('results', [])
        if results:
            url = results[0].get('transcription_url', '')
            data = json.loads(request.urlopen(url).read().decode('utf8'))
            words = []
            for doc in data.get('transcripts', []):
                for sent in doc.get('sentences', []):
                    for w in sent.get('words', []):
                        words.append({'t': w['text'], 's': w['begin_time'], 'e': w['end_time']})
            print(f'SUCCESS: {len(words)} words')
            if words:
                print(f'  First: {words[0]}')
                print(f'  Last: {words[-1]}')
        break
    elif status == 'FAILED':
        print(f'FAILED: {result.output}')
        break
else:
    print('TIMEOUT')

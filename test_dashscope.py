"""测试服务器上 DashScope 环境"""
import os
import sys

# Check env vars
dash_key = os.getenv("DASHSCOPE_API_KEY", "")
sf_key = os.getenv("SILICONFLOW_API_KEY", "")
print(f"DASHSCOPE_KEY: {'SET length='+str(len(dash_key)) if dash_key else 'EMPTY'}", flush=True)
print(f"SILICONFLOW_KEY: {'SET length='+str(len(sf_key)) if sf_key else 'EMPTY'}", flush=True)

# Test actual AI call
if dash_key:
    try:
        from openai import OpenAI
        client = OpenAI(api_key=dash_key, base_url="https://dashscope.aliyuncs.com/compatible-mode/v1")
        r = client.chat.completions.create(
            model="qwen-plus",
            messages=[{"role": "user", "content": "说一个字：好"}],
            max_tokens=10,
        )
        print(f"DashScope OK: {r.choices[0].message.content[:50]}", flush=True)
    except Exception as e:
        print(f"DashScope FAILED: {e}", flush=True)

# Check image gen
if dash_key:
    try:
        from dashscope import ImageSynthesis
        r = ImageSynthesis.call(
            model="wanx2.1-t2i-turbo",
            api_key=dash_key,
            prompt="test landscape, no humans",
            n=1,
            size="720*1280",
        )
        print(f"ImageSynthesis status: {r.status_code}", flush=True)
        if r.status_code == 200 and r.output and r.output.results:
            print(f"Image URL: {r.output.results[0].url[:80]}", flush=True)
        else:
            print(f"ImageSynthesis FAILED: code={r.status_code} msg={r.message if hasattr(r,'message') else '?'}", flush=True)
    except Exception as e:
        print(f"ImageSynthesis EXCEPTION: {e}", flush=True)

print("DONE", flush=True)

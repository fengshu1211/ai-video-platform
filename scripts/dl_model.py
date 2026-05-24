
from modelscope.hub.api import HubApi
api = HubApi()
try:
    result = api.snapshot_download("damo/Wav2Lip", cache_dir="/root/Wav2Lip/checkpoints")
    print(f"Downloaded: {result}")
except Exception as e:
    print(f"ModelScope failed: {e}")
    # 备用：直接找其他镜像
    import urllib.request
    url = "https://www.modelscope.cn/api/v1/models/damo/Wav2Lip/repo?Revision=master&FilePath=wav2lip.pth"
    urllib.request.urlretrieve(url, "/root/Wav2Lip/checkpoints/wav2lip.pth")
    print("Tried direct download")

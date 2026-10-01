import urllib.request
import os
import time

def resilient_download(url, path, retries=5):
    for attempt in range(retries):
        try:
            print(f"Downloading {path}... (Attempt {attempt + 1}/{retries})")
            # Increase timeout and use a clear User-Agent to avoid generic blocks
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=30) as response, open(path, 'wb') as out_file:
                chunk_size = 8192
                while True:
                    chunk = response.read(chunk_size)
                    if not chunk:
                        break
                    out_file.write(chunk)
            print(f"Successfully downloaded {path}")
            return
        except Exception as e:
            print(f"Error occurred: {e}")
            if os.path.exists(path):
                os.remove(path) # Clean partial file
            time.sleep(2)
            
    print(f"Failed to download {path} after {retries} attempts.")

def download_models():
    os.makedirs('models', exist_ok=True)
    
    # We use jsdelivr CDN mirror for github raw content which is much faster and rarely drops connections
    lbf_url = "https://cdn.jsdelivr.net/gh/kurnianggoro/GSOC2017@master/data/lbfmodel.yaml"
    haar_url = "https://cdn.jsdelivr.net/gh/opencv/opencv@master/data/haarcascades/haarcascade_frontalface_default.xml"
    
    lbf_path = "models/lbfmodel.yaml"
    haar_path = "models/haarcascade_frontalface_default.xml"
    
    if not os.path.exists(lbf_path) or os.path.getsize(lbf_path) < 1000000:
        resilient_download(lbf_url, lbf_path)
        
    if not os.path.exists(haar_path) or os.path.getsize(haar_path) < 100000:
        resilient_download(haar_url, haar_path)

if __name__ == "__main__":
    download_models()

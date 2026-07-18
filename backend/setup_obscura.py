import urllib.request
import json
import zipfile
import io
import os

BIN_DIR = os.path.join(os.path.dirname(__file__), 'bin')

def download_obscura():
    if os.path.exists(os.path.join(BIN_DIR, 'obscura.exe')):
        print("Obscura already installed.")
        return

    print("Fetching obscura releases...")
    req = urllib.request.urlopen('https://api.github.com/repos/h4ckf0r0day/obscura/releases/latest')
    data = json.loads(req.read().decode('utf-8'))
    asset = next(a for a in data['assets'] if 'windows.zip' in a['name'])
    
    print(f"Downloading {asset['browser_download_url']}...")
    req_zip = urllib.request.Request(asset['browser_download_url'], headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req_zip) as response:
        with zipfile.ZipFile(io.BytesIO(response.read())) as z:
            z.extractall(BIN_DIR)
            print("Extracted to bin:", z.namelist())

if __name__ == "__main__":
    os.makedirs(BIN_DIR, exist_ok=True)
    download_obscura()

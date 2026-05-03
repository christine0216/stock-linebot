from pyngrok import ngrok
import time

tunnel = ngrok.connect(5000)
print(f"Webhook URL: {tunnel.public_url}/callback")
print("ngrok 持續運行中，按 Ctrl+C 停止")

while True:
    time.sleep(1)
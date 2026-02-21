import base64
import json
import os
import sys
import urllib.request

from dotenv import load_dotenv

load_dotenv()

API_URL = os.environ["TIMEWEB_API_BASE"] + "/responses"
API_TOKEN = os.environ["TIMEWEB_API_TOKEN"]

PROMPT = "Это эскиз страниц детской книжки. Сгенерируй страницу детской книжки на основе этого эскиза, используй в качестве главного персонажа девочку 8ми лет. Стиль изображений рисованный цветными карандашами, просто и приятный. На заднем плане сделай детскую комнату. Надписи должны отстаться на том же языке. Персонаж должен быть одинаковый для всех версий картинок"

INPUT_DIR = "S:/projects/image-regeneration/input"
OUTPUT_DIR = "S:/projects/image-regeneration/output"

HEADERS = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {API_TOKEN}",
}


def generate_image(image_path, output_path):
    with open(image_path, "rb") as f:
        img_b64 = base64.b64encode(f.read()).decode()

    payload = {
        "model": "gpt-5-nano",
        "stream": True,
        "input": [
            {
                "role": "user",
                "content": [
                    {"type": "input_text", "text": PROMPT},
                    {
                        "type": "input_image",
                        "image_url": f"data:image/jpeg;base64,{img_b64}",
                    },
                ],
            }
        ],
        "tools": [{"type": "image_generation"}],
    }

    data = json.dumps(payload).encode()
    req = urllib.request.Request(API_URL, data=data, headers=HEADERS, method="POST")

    with urllib.request.urlopen(req, timeout=600) as resp:
        image_b64 = None

        for line in resp:
            line = line.decode("utf-8").strip()
            if not line or line.startswith(":"):
                continue
            if line.startswith("data: "):
                data_str = line[6:]
                if data_str == "[DONE]":
                    break
                try:
                    event = json.loads(data_str)
                    etype = event.get("type", "")

                    if etype == "response.completed":
                        resp_data = event.get("response", {})
                        for item in resp_data.get("output", []):
                            if item.get("type") == "image_generation_call":
                                result_b64 = item.get("result", "")
                                if result_b64:
                                    image_b64 = result_b64
                except json.JSONDecodeError:
                    pass

    if image_b64:
        img_bytes = base64.b64decode(image_b64)
        with open(output_path, "wb") as f:
            f.write(img_bytes)
        return len(img_bytes)
    return 0


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    images = sorted(
        f
        for f in os.listdir(INPUT_DIR)
        if f.lower().endswith((".jpg", ".jpeg", ".png"))
    )
    print(f"Found {len(images)} images: {images}")

    # Skip already generated images (1.png was already done in testing)
    for img_name in images:
        base_name = os.path.splitext(img_name)[0]
        output_path = os.path.join(OUTPUT_DIR, f"{base_name}.png")

        if os.path.exists(output_path):
            print(f"[SKIP] {img_name} -> {base_name}.png already exists")
            continue

        img_path = os.path.join(INPUT_DIR, img_name)
        print(f"[GEN]  {img_name} -> {base_name}.png ...", end=" ", flush=True)

        try:
            size = generate_image(img_path, output_path)
            if size:
                print(f"OK ({size} bytes)")
            else:
                print("FAILED (no image in response)")
        except Exception as e:
            print(f"ERROR ({type(e).__name__}: {e})")

    print("\nDone! Generated images:")
    for f in sorted(os.listdir(OUTPUT_DIR)):
        fpath = os.path.join(OUTPUT_DIR, f)
        print(f"  {f} ({os.path.getsize(fpath)} bytes)")


if __name__ == "__main__":
    main()

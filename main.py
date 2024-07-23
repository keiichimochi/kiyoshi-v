import streamlit as st
from PIL import Image
import litellm
from litellm import completion
import base64
from io import BytesIO
import os
import math

# シークレットからAPIキーを取得
openai_api_key = st.secrets["api"]["OPENAI_API_KEY"]
anthropic_api_key = st.secrets["api"]["ANTHROPIC_API_KEY"]

if openai_api_key is None:
    raise ValueError("OpenAI APIキーが設定されていません。")

# APIキーをlitellmに設定
litellm.api_key = anthropic_api_key

# モデル選択のためのセレクタを追加
st.title("KIYOSHIが一言")

function_options = ["ボケて", "褒めて", "ニックネームつけて"]
selected_function = st.radio("機能を選択してください", function_options)


def ensure_rgb(image):
    if image.mode in ('RGBA', 'LA') or (image.mode == 'P' and 'transparency' in image.info):
        # アルファチャンネルを含む画像をRGBに変換
        background = Image.new('RGB', image.size, (255, 255, 255))
        background.paste(image, mask=image.split()[3])  # 3 is the alpha channel
        return background
    else:
        # すでにRGBの場合はそのまま返す
        return image.convert('RGB')
    
def compress_image(image):
    # RGBフォーマットに変換
    image = ensure_rgb(image)
    
    # 以下、既存の圧縮処理
    original_size = image.size[0] * image.size[1] * len(image.getbands())
    target_size = 100 * 1024

    if original_size > target_size:
        compression_ratio = math.sqrt(target_size / original_size)
        new_width = int(image.size[0] * compression_ratio)
        new_height = int(image.size[1] * compression_ratio)
        image = image.resize((new_width, new_height), Image.LANCZOS)
        
        quality = 85
        while True:
            buffered = BytesIO()
            image.save(buffered, format="JPEG", quality=quality)
            compressed_size = buffered.tell()
            
            if compressed_size <= target_size or quality <= 20:
                break
            
            quality -= 5
    else:
        buffered = BytesIO()
        image.save(buffered, format="JPEG", quality=85)
        compressed_size = buffered.tell()

    return image, original_size, compressed_size

def generate_response(image):
    # 画像をbase64エンコード
    buffered = BytesIO()
    image.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")

    try:
        if selected_function == "ボケて":
            user_prompt = "この写真について素っ頓狂な例えでボケてください。Please come up with a joke about this image.Please respond in Japanese."
        elif selected_function == "褒めて":
            user_prompt = "この写真についてハイテンションで褒めてください。"
        else:  # ニックネームつける
            user_prompt = "この写真の人物にふさわしい少し変な面白おかしいニックネームをつけてください。動物や昆虫、微生物、歴史上の人物を使って面白くしてください。屋号、おすすめのイカ料理も考えてください"

        # litellmを使用してClaude 3.5 Sonnetで応答を生成 claude-3-haiku-20240307, claude-3-opus-20240229 , claude-3-5-sonnet-20240620
        response = completion(
            model="anthropic/claude-3-opus-20240229",
            messages=[
                {
                    "role": "system",
                    "content": "あなたは宮城出身の、３度の飯よりイカが大好きなおっさんです。写真の画像を自分と勘違いしないようにしてください。必ず日本語の宮城弁で話します。決して相手を貶さないでください。ボケる場合は、面白い例えを考えてください。"
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": user_prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_str}"}}
                    ]
                }
            ],
            temperature=1.0,
            max_tokens=250  # 応答の最大トークン数を設定
        )
        if response and response.choices:
            return response.choices[0].message.content
        else:
            return "AIからの返答がありませんでした。"
        
    except Exception as e:
        st.error(f"エラーが発生しました: {e}")
        return None

# 画像ソースの選択
image_source = st.radio("画像ソースを選択してください", ["カメラ撮影", "ファイルアップロード"])

if image_source == "ファイルアップロード":
    uploaded_file = st.file_uploader("写真をアップロードしてください", type=["jpg", "jpeg", "png"])
    if uploaded_file is not None:
        image = Image.open(uploaded_file)
        image, original_size, compressed_size = compress_image(image)  # 画像を圧縮
        response = generate_response(image)
        if response:
            st.write(response)

elif image_source == "カメラ撮影":
    camera_image = st.camera_input("写真を撮影してください")
    if camera_image is not None:
        image = Image.open(camera_image)
        image, original_size, compressed_size = compress_image(image)  # 画像を圧縮
        response = generate_response(image)
        if response:
            st.write(response)
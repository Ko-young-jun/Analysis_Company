import os
import requests
import google.generativeai as genai

# API 키 설정 (발급받은 API 키로 교체하세요)
API_KEY = "YOUR_API_KEY_HERE"
genai.configure(api_key=API_KEY)

def generate_and_save_image():
    # 저장할 폴더 생성
    os.makedirs("assets", exist_ok=True)

    prompt = "재즈 피아노 위에 놓인 빈티지 만년필과 미러리스 카메라"

    print(f"'{prompt}' 프롬프트로 이미지 생성 요청 중...")

    try:
        # Imagen 모델을 호출하여 이미지 생성 (API 버전에 따라 모델명 등 변경될 수 있음)
        result = genai.generate_images(
            prompt=prompt,
            number_of_images=1,
            output_mime_type="image/png"
        )

        # 생성된 이미지를 저장
        for generated_image in result.images:
            # image.image.content 에 바이너리 데이터가 포함될 수 있습니다
            with open("assets/background.png", "wb") as f:
                f.write(generated_image.image.image_bytes)

            print("assets/background.png 에 이미지가 성공적으로 저장되었습니다.")
            break

    except Exception as e:
        print(f"이미지 생성 중 오류가 발생했습니다: {e}")
        print("최신 google-generativeai SDK 문서에 맞는 올바른 메서드 및 속성을 확인해주세요.")

if __name__ == "__main__":
    generate_and_save_image()

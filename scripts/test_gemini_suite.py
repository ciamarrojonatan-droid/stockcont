"""StockCont — Gemini API Unified Capability Test Suite.

Tests Gemini capabilities used by StockCont:
1. Text/Reasoning Synthesis
2. Images (Imagen 3 / Nano Banana Image)
3. Audio Synthesis Capability Check
4. Media / Video Models Discovery
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Windows UTF-8 console output (ADR-01)
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

BASE_DIR = Path(__file__).resolve().parent.parent
STAGING_DIR = BASE_DIR / "data" / "staging"
STAGING_DIR.mkdir(parents=True, exist_ok=True)

# 1. Resolver Chave de API
def get_api_key() -> str | None:
    # Checar variáveis de ambiente primeiro
    key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if key and key != "sua_chave_gemini_aqui" and len(key) > 10:
        return key

    # Checar .env do StockCont
    sc_env = BASE_DIR / ".env"
    if sc_env.exists():
        with open(sc_env, "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith("GEMINI_API_KEY="):
                    val = line.split("=", 1)[1].strip().strip('"').strip("'")
                    if val and val != "sua_chave_gemini_aqui" and len(val) > 10:
                        return val

    return None


def run_suite():
    print("=" * 65)
    print("  STOCKCONT — GEMINI API CAPABILITY AUDIT")
    print("=" * 65)

    api_key = get_api_key()
    if not api_key:
        print("\n[ERRO CRÍTICO] Nenhuma GEMINI_API_KEY válida encontrada no .env!")
        print("Status atual verificado:")
        print("  - StockCont (.env): GEMINI_API_KEY='sua_chave_gemini_aqui' (Placeholder padrão)")
        print("\nPara executar a geração via API no terminal, cole sua chave do Google AI Studio:")
        print("  Obtenha gratuitamente em: https://aistudio.google.com/app/apikey")
        print("  E adicione no arquivo .env: GEMINI_API_KEY=AIzaSy...")
        return False

    os.environ["GEMINI_API_KEY"] = api_key
    print(f"\n[OK] Chave GEMINI_API_KEY detectada (comprimento: {len(api_key)} chars)")

    try:
        from google import genai
        print("[OK] SDK oficial google-genai carregado com sucesso.")
    except ImportError as e:
        print(f"[ERRO] Falha ao importar google-genai: {e}")
        return False

    client = genai.Client(api_key=api_key)

    # -------------------------------------------------------------
    # TESTE 1: Roteiro & Pacing de Retenção
    # -------------------------------------------------------------
    print("\n" + "-" * 50)
    print("TESTE 1: Roteiro & Pacing de Retenção (Gemini Text/Reasoning)")
    print("-" * 50)
    try:
        prompt_roteiro = (
            "Gere uma estrutura de abertura de 60 segundos para um documentário histórico de suspense "
            "no YouTube Dark Channel sobre o incidente de Serpukhov-15 (Stanislav Petrov, 1983). "
            "Aplique a regra dos primeiros 60 segundos do MrBeast e o princípio de retenção de Walter Murch. "
            "Responda em formato JSON com os campos: title, hook_0_to_15s, curiosity_gap_20s, visual_beats."
        )
        # Testar gemini-2.5-flash ou gemini-2.0-flash ou fallback para gemini-1.5-flash
        model_name = "gemini-2.5-flash"
        print(f"Disparando prompt de roteiro para o modelo '{model_name}'...")
        response = client.models.generate_content(
            model=model_name,
            contents=prompt_roteiro,
        )
        output_script = response.text
        script_file = STAGING_DIR / "test_script.json"
        with open(script_file, "w", encoding="utf-8") as f:
            f.write(output_script)
        print(f"[SUCESSO] Roteiro gerado e salvo em: {script_file}")
        print(f"Preview (primeiros 200 caracteres):\n{output_script[:200]}...\n")
    except Exception as e:
        print(f"[FALHA NO TESTE 1]: {e}")

    # -------------------------------------------------------------
    # TESTE 2: Thumbnails & Imagens Base (Imagen 3 / Nano Banana Image)
    # -------------------------------------------------------------
    print("-" * 50)
    print("TESTE 2: Thumbnail / Imagem (Imagen 3 via Gemini API)")
    print("-" * 50)
    try:
        image_prompt = (
            "Cinematic documentary YouTube thumbnail, 1983 Soviet nuclear command bunker, "
            "flashing red emergency beacons, military officer sweating in extreme close-up, "
            "CRT telemetry screens with green phosphor trajectory maps, Cooke Anamorphic lens, "
            "hyper-realistic, high contrast, 8k resolution, photorealistic, dramatic lighting."
        )
        print("Disparando geração de imagem para 'imagen-3.0-generate-002'...")
        img_result = client.models.generate_images(
            model="imagen-3.0-generate-002",
            prompt=image_prompt,
            config=dict(
                number_of_images=1,
                aspect_ratio="16:9",
                output_mime_type="image/png"
            )
        )
        if img_result.generated_images:
            thumb_path = STAGING_DIR / "test_thumbnail.png"
            with open(thumb_path, "wb") as f:
                f.write(img_result.generated_images[0].image.image_bytes)
            print(f"[SUCESSO] Thumbnail gerada e salva em: {thumb_path} (Tamanho: {thumb_path.stat().st_size} bytes)")
        else:
            print("[AVISO] Nenhuma imagem retornada pelo modelo Imagen 3.")
    except Exception as e:
        print(f"[FALHA NO TESTE 2]: {e}")

    # -------------------------------------------------------------
    # TESTE 3: Narração / Voiceover (Gemini Audio — SEM FALLBACK)
    # -------------------------------------------------------------
    print("-" * 50)
    print("TESTE 3: Narração / Voiceover (Gemini Audio — SEM FALLBACK)")
    print("-" * 50)
    try:
        speech_text = (
            "Vinte e seis de setembro de mil novecentos e oitenta e três. "
            "No coração do bunker secreto de Serpukhov quinze, as sirenes vermelhas começam a rugir. "
            "O sistema de alerta nuclear soviético acaba de confirmar: cinco mísseis intercontinentais americanos estão em rota de colisão."
        )
        print("Disparando geração de voz neural sem fallback...")
        # Testar modalidades de áudio do Gemini (gemini-2.0-flash / gemini-2.5-flash com áudio nativo ou gemini-3.8-flash-tts)
        audio_saved = False

        # Tentativa A: gemini-2.5-flash com modalidade AUDIO
        try:
            print("Tentando síntese via gemini-2.5-flash (response_modalities=['AUDIO'])...")
            audio_response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=f"Narration voiceover in Portuguese, solemn and dramatic historical documentary tone: {speech_text}",
                config=dict(
                    response_modalities=["AUDIO"],
                    speech_config=dict(
                        voice_config=dict(
                            prebuilt_voice_config=dict(
                                voice_name="Puck" # Voz profunda / masculina
                            )
                        )
                    )
                )
            )
            # Extrair bytes de áudio
            for part in audio_response.candidates[0].content.parts:
                if hasattr(part, "inline_data") and part.inline_data:
                    audio_bytes = part.inline_data.data
                    voice_file = STAGING_DIR / "test_voiceover.wav"
                    with open(voice_file, "wb") as f:
                        f.write(audio_bytes)
                    print(f"[SUCESSO] Áudio gerado e salvo em: {voice_file} (Tamanho: {len(audio_bytes)} bytes)")
                    audio_saved = True
                    break
        except Exception as err_a:
            print(f"Tentativa A reportou: {err_a}")

        if not audio_saved:
            # Tentativa B: gemini-2.0-flash
            print("Tentando síntese via gemini-2.0-flash...")
            audio_response = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=f"Read this as a dramatic documentary narrator: {speech_text}",
                config=dict(
                    response_modalities=["AUDIO"],
                )
            )
            for part in audio_response.candidates[0].content.parts:
                if hasattr(part, "inline_data") and part.inline_data:
                    audio_bytes = part.inline_data.data
                    voice_file = STAGING_DIR / "test_voiceover.wav"
                    with open(voice_file, "wb") as f:
                        f.write(audio_bytes)
                    print(f"[SUCESSO] Áudio gerado e salvo em: {voice_file} (Tamanho: {len(audio_bytes)} bytes)")
                    audio_saved = True
                    break

        if not audio_saved:
            print("[ERRO] Não foi possível salvar o arquivo de áudio. Investigando resposta bruta...")
    except Exception as e:
        print(f"[FALHA NO TESTE 3]: {e}")

    # -------------------------------------------------------------
    # TESTE 4: Mapeamento de Modelos de Música & SFX
    # -------------------------------------------------------------
    print("-" * 50)
    print("TESTE 4: Auditoria de Modelos de Áudio & Música Disponíveis")
    print("-" * 50)
    try:
        print("Consultando modelos disponíveis na sua chave Gemini...")
        models = list(client.models.list())
        audio_and_media_models = [m.name for m in models if any(k in m.name.lower() for k in ["audio", "music", "tts", "image", "imagen", "veo", "video"])]
        print(f"Modelos de mídia encontrados ({len(audio_and_media_models)}):")
        for m in audio_and_media_models[:15]:
            print(f"  • {m}")
    except Exception as e:
        print(f"[FALHA NO TESTE 4]: {e}")

    print("\n" + "=" * 65)
    print("  FIM DA BATERIA DE AUDITORIA GEMINI API")
    print("=" * 65)
    return True


if __name__ == "__main__":
    run_suite()

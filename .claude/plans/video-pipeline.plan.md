# Plan: StockCont Video Pipeline Expansion (Fase 1 à Fase 5)

**Complexity**: Large  
**Paradigma**: I2V Multiplier (Image-to-Video) com Dual Export (16:9 Landscape & 9:16 Vertical)  
**Motor de Geração**: RunningHub ComfyUI Cloud (via RPA Playwright)  
**Mastering & Codecs**: Master H.264 MP4 Universal (CRF 18, áudio mudo) + ProRes 422 HQ seletivo para Pond5  
**Metadados**: Dual Fallback (FFmpeg Nativo + ExifTool) com átomos QuickTime e XMP  

---

## Summary
Expande o ecossistema autônomo industrial do StockCont para geração, pós-processamento, catalogação e distribuição de vídeos comerciais (stock footage / B-roll / Reels). O pipeline reutiliza imagens 4K aprovadas pelo controle de qualidade (QC Gemini) como frames-mestre para produzir simultaneamente vídeos em 16:9 (UHD 4K) e 9:16 (Vertical Reels/TikTok), garantindo taxa de aprovação >90%, masterização de áudio mudo e envio multi-plataforma resiliente.

---

## Patterns to Mirror
| Category | Source | Pattern |
|---|---|---|
| Encoding UTF-8 | `src/cataloger/adobe_csv_maker.py:28` | Reconfiguração obrigatória de `sys.stdout`/`sys.stderr` para `utf-8` no Windows (ADR-01). |
| Atomic Writes | `src/analyzer/director.py:411-414` | Gravação segura via arquivo `.tmp.{pid}` e substituição atômica com `Path.replace()` (ADR-02). |
| Cryptographic Ledger | `src/factory/prompt_queue.py:120-135` | Idempotência estrita via hash SHA-256 canônico em `video_generation_history.json` (ADR-03). |
| Anti-Ban Policy | `src/cataloger/platform_compliance.py:41-47` | Bloqueio preventivo e automático de submissões de IA para a Alamy com log explícito (ADR-05). |
| Rolling Quotas | `src/uploader/quota_manager.py:45-80` | Janela deslizante de 7 dias com limites por agência para proteção de reputação de conta. |
| Test Coverage | `tests/test_platform_compliance.py:20-60` | Testes com `pytest`, fixtures de arquivos mock temporários com `tmp_path`, assertions rigorosas. |

---

## Files to Change
| File | Action | Why |
|---|---|---|
| `src/video/ffmpeg_processor.py` | CREATE | Wrapper do FFmpeg/FFprobe: validação técnica (codec, fps, duração), áudio mudo (`-an`), normalização H.264/ProRes, extração de poster JPEG e Seamless Loop Engine. |
| `src/video/video_metadata.py` | CREATE | Injeção atômica de Title, Description, Keywords nos átomos QuickTime/MP4 via FFmpeg nativo com suporte a ExifTool. |
| `src/analyzer/video_director.py` | CREATE | Diretor de Arte de Vídeo: sintetiza prompts temporais cinematográficos (movimento de câmera, iluminação dinâmica, copy-space temporal 35-50%, 16:9 e 9:16). |
| `src/cataloger/video_cataloger.py` | CREATE | Orquestrador da Fase 4 para vídeo: extrai thumbnail, audita com Gemini Vision, injeta metadados e anexa ao `adobe_stock_video_upload.csv` e `pond5_video_upload.csv`. |
| `src/cataloger/platform_compliance.py` | UPDATE | Expandir regras com especificações técnicas de vídeo (duração 5-60s, framerates válidos, codecs, regra anti-IA Alamy mantida). |
| `src/scraper/adobe_stock.py` | UPDATE | Adicionar suporte ao filtro `filters[content_type:video]=1` e download de preview MP4. |
| `src/factory/prompt_queue.py` | UPDATE | Suportar itens com `asset_type='video'` e rastreamento de renders em `data/final/videos/`. |
| `src/uploader/ftp_distributor.py` | UPDATE | Expandir descoberta de arquivos para `.mp4` e `.mov`, com timeouts estendidos e validação de tamanho de vídeo. |
| `src/uploader/quota_manager.py` | UPDATE | Suportar cotas semanais diferenciadas para vídeo (`DEFAULT_WEEKLY_VIDEO_LIMITS`). |
| `main.py` | UPDATE | Adicionar flags `--asset-type [image|video|all]`, `--video`, e suporte de CLI para as Fases 1 a 5 de vídeo. |
| `tests/test_video_pipeline.py` | CREATE | Suíte de testes automatizados com pytest validando FFmpeg processor, metadata injection, compliance e queue de vídeo. |

---

## Tasks

### Task 1: Infraestrutura de Mídia FFmpeg & Injeção de Metadados (Core Engine)
- **Action**: Criar `src/video/ffmpeg_processor.py` e `src/video/video_metadata.py`. Implementar inspeção via `ffprobe`, conversão H.264 (CRF 18), ProRes 422 HQ, remoção de áudio espúrio (`-an`), extração de poster frame e gravação de metadados em contêineres MP4/MOV com `+faststart`. Incluir função para o *Seamless Perfect Loop Engine*.
- **Mirror**: Padrões de I/O de `src/cataloger/reembed_compliance.py` e tratamento de erros com `logging`.
- **Validate**: `pytest tests/test_video_pipeline.py -k "test_ffmpeg or test_metadata"`

### Task 2: Atualização do Motor de Compliance para Vídeo
- **Action**: Atualizar `src/cataloger/platform_compliance.py` adicionando `validate_video_compliance()` com checagem de resolução (4K UHD 3840x2160 / FHD 1920x1080), aspecto (16:9 e 9:16), duração (5 a 60 segundos), ausência de trilha sonora espúria e bloqueio irrevogável para a Alamy.
- **Mirror**: `tests/test_platform_compliance.py`
- **Validate**: `pytest tests/test_platform_compliance.py`

### Task 3: Fase 1 & Fase 2 — Olheiro de Footage & Diretor de Arte de Vídeo
- **Action**: Atualizar `src/scraper/adobe_stock.py` com `content_type="video"` e URL de busca com filtros de vídeo 4K. Criar `src/analyzer/video_director.py` conectando ao Gemini Vision para gerar prompts cinemáticos temporais (cinética de câmera, pacing, lighting shift e copy-space dinâmico) adaptados para 16:9 e 9:16 a partir de referências.
- **Mirror**: `src/analyzer/director.py` (escrita atômica `.tmp.{pid}`).
- **Validate**: `pytest tests/test_video_pipeline.py -k "test_video_director"`

### Task 4: Fase 3 & Fase 4 — Fila Criptográfica e Catalogador de Vídeo
- **Action**: Atualizar `src/factory/prompt_queue.py` para gerenciar `asset_type='video'`. Criar `src/cataloger/video_cataloger.py` que percorre `data/final/videos/`, executa auditoria visual no poster com Gemini Vision, grava tags binárias e registra as linhas nos CSVs incrementais de upload (`adobe_stock_video_upload.csv`).
- **Mirror**: `src/cataloger/adobe_csv_maker.py`
- **Validate**: `pytest tests/test_video_pipeline.py -k "test_video_cataloger"`

### Task 5: Fase 5 — Distribuidor com Cotas & CLI Unificada
- **Action**: Atualizar `src/uploader/ftp_distributor.py` e `src/uploader/quota_manager.py` com suporte a limites de envio semanais de vídeo e transferências de arquivos maiores. Atualizar `main.py` com parâmetros `--video` e `--asset-type [image|video|all]`.
- **Mirror**: `src/uploader/ftp_distributor.py`
- **Validate**: `python main.py --video --status` e `pytest tests/test_video_pipeline.py`

---

## Validation
```bash
# Validação da suíte de testes completa sem regressão
pytest tests/ -v

# Validação do pipeline de vídeo via CLI em modo dry-run
python main.py --video --status
python main.py --phase 4 --asset-type video --dry-run
```

---

## Risks
| Risk | Likelihood | Mitigation |
|---|---|---|
| Rejeição de vídeo por ruído ou áudio acidental | Média | Aplicação mandatória e estrita de `-an` (Audio None) em 100% dos vídeos masterizados. |
| Arquivos pesados saturando o SSD local | Média | Auto-purga automática de vídeos do SSD local logo após confirmação de upload nas agências e backup no Google Drive. |
| Incompatibilidade de átomos MP4 em agências legadas | Baixa | Utilização da flag `-movflags +faststart` no FFmpeg, movendo o índice `moov` para o início do arquivo para streaming instantâneo. |
| Regressão na esteira existente de imagens (118 testes verdes) | Baixa | Namespace isolado `src/video/`, preservação das interfaces existentes e bateria completa de testes de regressão. |

---

## Acceptance
- [ ] Todos os módulos de vídeo criados seguindo os padrões arquiteturais (ADR-01, ADR-02, ADR-03, ADR-05).
- [ ] Geração simultânea de 16:9 Landscape e 9:16 Vertical suportada.
- [ ] Masterização FFmpeg sem áudio e com injeção de metadados binários testada e aprovada.
- [ ] Bloqueio anti-ban Alamy rigorosamente ativo para vídeos de IA.
- [ ] Todos os testes unitários e de integração verdes (0 quebras nos 118 testes existentes + novos testes de vídeo).

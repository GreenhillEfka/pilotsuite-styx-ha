# Vision & Image Models Reference (Stand 2026-02)

## 🏆 Top Vision Models (Image Analysis)

### Leaderboard (Vision Score / MMMU Pro)

| Rank | Model | Vision Score | MMMU Pro | Stärken |
|------|-------|-------------|----------|---------|
| 1 | **Gemini 3 Flash** | 79.0 | 79% | Beste Vision-Performance, 1M+ Context |
| 2 | **Gemini 3 Pro** | 77.0 | 80% | Reasoning, Math, Science, Video |
| 3 | **GPT-5.2** | 75.0 | 75% | Text+Vision kombiniert, strong reasoning |
| 4 | **Claude Opus 4.5** | 74.0 | 74% | Sprache, komplexe Reasoning |
| 5 | **Qwen2.5-VL-72B** | - | - | Multilingual OCR, Document Analysis |
| 6 | **Gemma 3** | - | - | Open-Source, OCR-effizient |
| 7 | **InternVL3-78B** | - | - | Open-Source, Visual Reasoning |

### Use Cases

| Task | Best Model | Alternative |
|------|------------|-------------|
| **Complex Image Scenes** | Gemini 3 Pro | GPT-5.2 |
| **Document/OCR Processing** | Qwen2.5-VL, Gemma 3 | InternVL3 |
| **Edge/IoT Devices** | Pixtral, Phi-4 Multimodal | DeepSeek-VL2 |
| **Video Understanding** | Qwen2.5-VL, Gemini 3 | - |
| **Zero-Shot Segmentation** | SAM 3 | - |
| **Technical Inspection** | Gemini 3 Pro | Claude Opus 4.5 |

### Benchmarks erklärt

- **MMMU Pro** (60% Vision Score): Multimodal Understanding, College-Level Reasoning
- **LM Arena Vision** (40% Vision Score): Real-User Votes
- **MathVista**: Visual Math
- **Video-MME**: Temporal/Video Understanding
- **MMT-Bench**: VQA/Reasoning

---

## 🎨 Top Image Generation Models

| Model | Stärken | Best For |
|-------|---------|----------|
| **DALL-E 3** | High Fidelity, Prompt Adherence, GPT-Integration | Conceptual Art, Marketing |
| **Midjourney v6** | Artistic Style, Photorealism | Creative Design, Illustrations |
| **Flux** (Black Forest Labs) | Speed, Detail, Open Weights | Production, Customization |
| **Stable Diffusion 3** | Fully Open-Source, Fine-tunable | Research, Local Gen, LoRAs |

---

## 🔧 Integration in OpenClaw

### Für Vision Tasks (Image Analysis)

```yaml
# Empfehlung nach Use Case
default_vision: "gemini/gemini-2.0-flash"  # Schnell, gut, günstiger
complex_vision: "gemini/gemini-2.5-pro"    # Beste Quality
document_ocr: "qwen/qwen2.5-vl-32b"        # OCR/Docs
fallback: "openai/gpt-4o"                  # Breite Verfügbarkeit
```

### Für Image Generation

```yaml
# Via API
image_gen_default: "openai/dall-e-3"
image_gen_creative: "midjourney"  # Via Discord/Proxy
image_gen_open: "flux"            # Via API oder Local
image_gen_local: "stabilityai/stable-diffusion-3"
```

---

## 📚 Quellen

- [Best Vision Models Jan 2026](https://whatllm.org/blog/best-vision-models-january-2026)
- [Top 10 Vision Language Models](https://dextralabs.com/blog/top-10-vision-language-models/)
- [Best Multimodal Models](https://www.siliconflow.com/articles/en/best-multimodal-ai-models)
- [Roboflow Multimodal Models](https://blog.roboflow.com/best-multimodal-models/)
- [Artificial Analysis Models](https://artificialanalysis.ai/models)

---

## 🔄 Update-Intervall

- **Quarterly Review**: Neue Modelle, Benchmarks
- **Bei Bedarf**: Wenn neue SOTA-Modelle released
- **Last Update**: 2026-02-17
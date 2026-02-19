# PilotSuite Concept Verification -- Deep Research (2026-02-19)

## Overall Verdict

**The concept is validated and occupies a genuinely unique niche.** No other open-source project combines behavioral mining, mood scoring, conversation memory, and local LLM inference in a single Home Assistant addon. The timing is favorable -- Google, Amazon, and Apple are all validating the "learning smart home" concept with cloud subscriptions, while PilotSuite offers a local, privacy-first alternative.

**Two critical issues identified**: the default model choice (`lfm2.5-thinking` lacks tool calling support in Ollama) and the context window documentation (32K, not 125K).

---

## 1. Competitive Landscape

**No direct open-source competitor exists.**

| Project | What It Does | Gap vs. PilotSuite |
|---|---|---|
| **Home-LLM** (acon96) | Fine-tuned 1B/3B models for HA service calls | No memory, no learning, no behavioral mining, stateless |
| **extended_openai_conversation** (jekalmin) | OpenAI-compatible bridge to HA with function schemas | Pure passthrough layer, no intelligence of its own |
| **Home Generative Agent** (goruck) | LangChain+LangGraph agent with context awareness | Requires Nvidia 3090 + 64GB RAM |
| **hass_local_openai_llm** (skye-harris) | Local OpenAI-compatible server + optional RAG | No learning, no behavioral analysis |
| **HA Assist** (native) | Sentence template matching for voice commands | Cannot handle open-ended queries; no AI, no learning |
| **MCP Servers** (5+ implementations) | Expose HA entities/services to external LLMs | Infrastructure pipes, not intelligent agents |

**Commercial competitors**:
- **Google Home Premium + Gemini** ($10-20/month): Proactive AI automations, camera analysis. Closest to PilotSuite's vision but cloud-dependent.
- **Amazon Alexa Hunches**: Learns sleep/departure patterns. Closest to Habitus Miner, but limited.
- **Josh.ai**: Privacy-first, learns patterns. Targets luxury homes ($10K+), closed-source.

**Academic validation**: IoTGPT paper (arXiv, Jan 2026) -- LLM-based smart home agent with task memory and adaptive personalization achieved 85% higher task success rates. PilotSuite's architecture is more comprehensive.

---

## 2. Architecture Validation

### Brain Graph (Time-Decaying Entity Relationship Graph)
**Sound.** TKGRS paper (MDPI, 2023) validated exponential decay factors outperforming non-temporal baselines.
Improvement: Implement differential decay rates per entity category.

### Habitus Miner (Association Rule Mining)
**Well-validated.** ScienceDirect 2025 applied exactly this technique (LSTM + Apriori) to smart home energy management.
Improvement: FP-Growth over Apriori, temporal windowing for weekday vs. weekend.

### Mood Engine (Comfort/Joy/Frugality)
**Novel differentiator.** No competing project implements zone-level comfort scoring.
Risk: Calibration is personal. Needs user feedback loops.

### Conversation Memory (SQLite)
**Pragmatic.** FadeMem validated dual-layer memory retaining 82.1% of critical facts at 55% storage.
Improvement: LLM-based preference extraction instead of pure keyword matching.

### Tool Calling
**Critical.** MikeVeerman benchmark: "When prompts require judgment -- resisting keyword triggers, respecting negation -- most sub-4B models fail."
Must-have: Confirmation step for destructive actions.

---

## 3. LFM 2.5 Assessment

### Critical Corrections
- **Context window is 32,768 tokens (32K), NOT 125K**
- **`lfm2.5-thinking` does NOT support tool calling in Ollama** (thinking variant generates reasoning traces that interfere with structured JSON)
- `lfm2.5` (instruct variant, non-thinking) scored 0.880 (tied #1) in tool-calling benchmarks

### Model Comparison

| Model | Size | Tool Score | Context | RAM (Q4) |
|---|---|---|---|---|
| **lfm2.5** (instruct) | 1.2B | 0.880 | 32K | ~3GB |
| **lfm2.5-thinking** | 1.2B | Undocumented | 32K | ~3GB |
| **qwen3:4b** | 4B | 0.880 | 32K | ~4-5GB |
| **qwen3:0.6b** | 0.6B | 0.880 | 32K | ~2GB |
| **phi4-mini** | 3.8B | 0.880 | 128K | ~4GB |

**Recommendation**: `qwen3:4b` as recommended model for tool calling. Keep `lfm2.5-thinking` as lightweight conversational default.

---

## 4. Lifelong Learning Viability

### Keyword Extraction: Sufficient for v1
Smart home vocabulary is bounded. Better long-term: use LLM itself to extract structured preferences.

### Memory Decay: Should be Dual-Layer
- 7-14 day short-term for contextual preferences (vacation mode)
- 90-180 day long-term for established preferences (temperature comfort)
- Promote on reinforcement

### Context Budget: Max 500-1000 tokens
Research (arXiv 2506.21568): 1B-4B models "falter with long prompts filled with irrelevant facts." Memory-augmented approaches reduce token usage 90% while maintaining competitive accuracy.

---

## 5. Risks and Gaps

### Critical (Fix Before Release)
1. Switch tool-calling model to `qwen3:4b` (lfm2.5-thinking lacks tool support)
2. Correct context window docs to 32K
3. Implement context budget (500-1000 tokens)
4. Add confirmation for destructive actions

### Moderate
- Cold start (no data for weeks) -- add onboarding + defaults
- Privacy: Add encryption-at-rest, retention limits, "purge my data"
- Resource contention: Document 8GB+ minimum

### Feature Gaps vs. Competitors
1. **No automation generation from patterns** (HIGH -- Habitus already has data)
2. **No multi-user support** (MEDIUM -- use HA person entities)
3. **No vision/camera integration** (MEDIUM -- plan future Vision Neuron)
4. **No energy optimization closed loop** (MEDIUM -- connect Frugality to rates)

---

## Sources
- [Home-LLM (acon96)](https://github.com/acon96/home-llm)
- [IoTGPT (arXiv, Jan 2026)](https://arxiv.org/abs/2601.04680)
- [LFM2.5-Thinking (Hugging Face)](https://huggingface.co/LiquidAI/LFM2.5-1.2B-Thinking)
- [MikeVeerman Tool-Calling Benchmark](https://github.com/MikeVeerman/tool-calling-benchmark)
- [FadeMem (arXiv, 2025)](https://arxiv.org/pdf/2512.12856)
- [TKGRS Temporal Knowledge Graph (MDPI)](https://www.mdpi.com/1999-5903/15/10/323)
- [Behavioral Pattern Mining IoT Survey (ResearchGate)](https://www.researchgate.net/publication/339279681)
- [Small LLM RAG Evaluation (arXiv)](https://arxiv.org/html/2506.21568v1)
- [RL Energy Management (Nature, 2025)](https://www.nature.com/articles/s41598-025-08125-9)

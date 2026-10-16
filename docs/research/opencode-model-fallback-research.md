# OpenCode v2.0.30 model fallback research

Research date: 2026-10-16. Research only; runtime configuration was not changed.

## Finding

OpenCode v2.0.30 has no native ordered model-fallback list in its config schema. [ConfigModel.Selection at tag v2.0.30](https://github.com/anomalyco/opencode/blob/v2.0.30/packages/schema/src/config/model.ts) is one `provider/model` string or one object with `providerID`, `model`, and optional `variant`. Both [root config](https://github.com/anomalyco/opencode/blob/v2.0.30/packages/schema/src/config.ts#L31-L35) and [agent config](https://github.com/anomalyco/opencode/blob/v2.0.30/packages/schema/src/config/agent.ts#L11-L13) reference that singular type. The v2.0.30 tag resolves to [f16ef9ad8878279ea2be3cfab7baeed97aef61aa](https://github.com/anomalyco/opencode/commit/f16ef9ad8878279ea2be3cfab7baeed97aef61aa).

OpenCode's [provider docs](https://dev.opencode.ai/v2/docs/providers/) say a timed-out request fails with a transport error and is retried up to three times. That retry uses the same model. The [still-open native fallback feature request](https://github.com/anomalyco/opencode/issues/48991) describes retrying the same model/provider before halting and proposes an ordered fallback array; it is not a shipped config schema. The older [fallback request #7602](https://github.com/anomalyco/opencode/issues/7602) is closed as not planned. Thus a 503 does not natively switch from Nemotron to Muse in OpenCode v2.0.30.

OpenRouter is a separate provider and is out of scope: this setup uses OpenCode's built-in opencode/* catalog and its fresh-install IP-based access. OpenCode v2.0.30 has no native ordered model-fallback config. The repository's bounded supervisor selects the next configured model only after a structured transient-provider error with no tool event; it records each attempt and never replays a failed turn that may have executed tools.

## Free/promo OpenCode candidates listed on 2026-10-16

The [official OpenCode Console catalog](https://opencode.ai/v2/docs/console/models/) lists each below as free/limited-time. This is not a quota or permanence guarantee.

| Candidate | OpenCode selector | Protocol | Catalog data notice |
|---|---|---|---|
| DeepSeek V4.1 Flash Free | `opencode/deepseek-v4.1-flash-free` | Chat Completions | Zero retention; no training |
| LongCat 2.5 Preview Free | `opencode/longcat-2.5-preview-free` | Chat Completions | Zero retention; no training |
| Space Bunny Free | `opencode/space-bunny-free` | Chat Completions | Zero retention; no training |
| MiMo V2.6 Flash Free | `opencode/mimo-v2.6-flash-free` | Chat Completions | Free-period data may be used to improve the model |
| Nemotron 3.5 Lightning Free | `opencode/nemotron-3.5-lightning-free` | Chat Completions | NVIDIA trial; requests logged for security/product improvement; no personal/confidential data |
| Muse Spark 1.3 Contributor Free | `opencode/muse-spark-1.3-contributor-free` | Responses API | Prompts/completions may train future Meta models |

The catalog also lists Nemotron 3 Ultra Free, MiMo V2.5 Free, Exo Free, Cat Jam Free, Big Pickle, and other offers. Terms vary: Cat Jam has regional restrictions and 30-day safety retention; Big Pickle, Exo, and MiMo V2.5 disclose free-period data use for improvement. The catalog publishes no numeric quota or promotion end date. Availability and terms can change.

This is a candidate list, not a quality ranking. Verify each model appears in `/models` and successfully makes a tool call before using it for autonomous coding. A same-protocol fallback chain is simpler if the router cannot mix Chat Completions and Responses models. Keep sensitive/private data out of endpoints with the notices above.

## Suggested next step

The configured pool is drawn from the local opencode models catalog. Model listings establish catalog presence only; successful end-to-end tool-call smoke requests are the runtime availability gate.

## Primary sources

- [v2.0.30 model selection schema](https://github.com/anomalyco/opencode/blob/v2.0.30/packages/schema/src/config/model.ts)
- [v2.0.30 root config schema](https://github.com/anomalyco/opencode/blob/v2.0.30/packages/schema/src/config.ts#L31-L35)
- [v2.0.30 agent schema](https://github.com/anomalyco/opencode/blob/v2.0.30/packages/schema/src/config/agent.ts#L11-L13)
- [OpenCode v2 model docs](https://dev.opencode.ai/v2/docs/models/)
- [OpenCode v2 provider retry docs](https://dev.opencode.ai/v2/docs/providers/)
- [OpenCode feature request #48991](https://github.com/anomalyco/opencode/issues/48991)
- [OpenCode Console model IDs, prices, and privacy notices](https://opencode.ai/v2/docs/console/models/)

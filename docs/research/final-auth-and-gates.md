# Final auth and CodeQL gates

Verified 2026-10-15 against primary sources, using the Matt Pocock research workflow.

## OpenCode v2 authentication

No interactive login is required by the OpenCode v2.0.30 client to enable free OpenCode-provider models. Its provider plugin sets the public API credential when neither OPENCODE_API_KEY, a Console connection, nor a configured key exists; it then disables models with nonzero input cost. This is explicit client behavior, not an inference from the general Console sign-in guide. [Versioned provider implementation, lines 326-350](https://github.com/anomalyco/opencode/blob/v2.0.30/packages/core/src/plugin/provider/opencode.ts#L326-L350)

The current official catalog lists `opencode/nemotron-3-ultra-free` and `opencode/muse-spark-1.3-contributor-free` as free, limited-time offerings. Nemotron uses chat completions; Muse uses responses. Their availability is not a permanent entitlement. Nemotron trial requests are logged; Muse contributor prompts/completions may be used for training. [Official models catalog](https://opencode.ai/v2/docs/console/models/)

Therefore neither configured model needs one-time user authentication under the current free-provider path. This source finding does not establish endpoint health or successful execution: retain separate live smoke evidence for each model. If a Console account is deliberately connected, its device OAuth path requires browser interaction; expired/revoked sessions or SSO can require reconnection. [Versioned OAuth implementation](https://github.com/anomalyco/opencode/blob/v2.0.30/packages/core/src/plugin/provider/opencode.ts#L94-L176)

## GitHub CodeQL merge protection

Public GitHub.com repositories support code scanning merge protection. An authorized administrator can require CodeQL results and choose alert/security thresholds through a branch ruleset. [GitHub merge-protection documentation](https://docs.github.com/en/code-security/how-tos/find-and-fix-code-vulnerabilities/manage-your-configuration/set-merge-protection)

The REST rule type is `code_scanning`. Its required `parameters.code_scanning_tools` array contains required `tool`, `alerts_threshold`, and `security_alerts_threshold` fields. Valid ordinary-alert values are `none`, `errors`, `errors_and_warnings`, `all`; security values are `none`, `critical`, `high_or_higher`, `medium_or_higher`, `all`. Results must exist for both the commit and reference being updated. [GitHub REST rules schema](https://docs.github.com/en/rest/repos/rules)

Recommended declared gate:

```json
{
  "type": "code_scanning",
  "parameters": {
    "code_scanning_tools": [
      {
        "tool": "CodeQL",
        "alerts_threshold": "errors_and_warnings",
        "security_alerts_threshold": "high_or_higher"
      }
    ]
  }
}
```

The workflow producing results and the server-side ruleset are separate deployment steps. A committed JSON policy alone does not enforce merge protection. Seed CodeQL results on main and the proposal before enforcing the rule, then verify the installed ruleset through GitHub's API.

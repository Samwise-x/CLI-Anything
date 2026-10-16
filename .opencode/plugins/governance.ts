import { Plugin } from "@opencode/plugin"
const denied = [/\bgit\s+push\b/i, /\bgit\s+reset\s+--hard\b/i, /\bgit\s+clean\b/i, /\brm\s+-rf\b/i, /\bsudo\b/i, /\b(mkfs|dd\s+if=)\b/i, /\b(powershell|pwsh|cmd\.exe)\b/i, /\/mnt\/[a-z]\//i]
const secret = /(^|[\\/])(\.env[^\\/]*|[^\\/]*\.(pem|key)|credentials?[^\\/]*\.json|secrets?[^\\/]*\.(json|ya?ml)|id_(rsa|ed25519)[^\\/]*|\.netrc|\.npmrc|\.pypirc|auth\.json)([\\/]|$)/i
const policy = /(^|[\\/])(\.opencode|\.github|docs[\\/]adr|AGENTS\.md|CONTEXT\.md|GLOSSARY\.md|\.pre-commit-config\.yaml)([\\/]|$)/i
export default Plugin.define({ id:"cli-anything-governance", async setup(ctx) {
 await ctx.permission.hook("evaluate", (e) => {
  const target=e.resources.join(" ")
  if ((e.action==="shell" && denied.some((r)=>r.test(target))) || (["read","edit"].includes(e.action) && secret.test(target)) || (e.action==="edit" && policy.test(target))) { e.effect="deny"; e.message="Blocked by local WSL governance policy." }
 })
 await ctx.shell.hook("create.before", (e) => { e.timeout=Math.min(e.timeout,120000) })
 await ctx.session.hook("context", (e) => { e.system.push({type:"text",text:"Work only in this WSL2 checkout. Never expose secrets to free models. Never push, merge, alter governance, or claim completion without deterministic verification and independent review. Persist evidence for each bounded goal."}) })
 await ctx.session.hook("retry", (e) => { if (e.attempt>=3) e.decision={retry:false} })
 await ctx.tool.hook("execute.after", async (e) => { await ctx.storage.set("tool-audit:last",{status:e.status,tool:e.tool,timestamp:new Date().toISOString()}) })
}})

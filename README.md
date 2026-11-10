# 演示服务骨架（free-tier-demo）

目的：用最小可跑的服务跑通整条链路
`健康检查 → OpenRouter 免费模型调用 → Supabase 写记录 → R2 存文件`

## 结构

- `app.py`：纯标准库 HTTP 服务，无第三方依赖
  - `GET /health` → `{"ok": true, "service": "free-tier-demo"}`
  - `POST /demo` → 调 OpenRouter `:free` 模型，返回一句话回复；
    若环境变量配了 Supabase / R2，会尝试写记录、存文件，否则在响应里明确标
    `supabase: "not_configured"` / `r2: "not_configured"`，不假装已接通
- `test.sh`：本地自测（健康检查 + 一次 /demo 调用），OpenRouter key 由
  `print_surrogate.py` 现取，不落盘、不打印
- `hidden_files/`：核实报告与运行日志（不对外）

## 环境变量（全部可选，未配即跳过对应环节）

- `OPENROUTER_API_KEY`：OpenRouter key（演示用免费模型
  `nvidia/nemotron-3.5-lightning:free`，2026-11-09 实测 probe 通过）
- `OPENROUTER_MODEL`：默认 `cohere/north-mini-code:free`
  （2026-11-09 实测一次调用返回 `Hello!`；
  原默认 `nvidia/nemotron-3.5-lightning:free` probe 通过但实测推理占满 token 预算、
  两次返回 null 内容；`liquid/lfm-3-1.7b:free` 与 `google/gemma-4-26b-a4b-it:free`
  当时上游共享池 429 限流）
- `SUPABASE_URL` / `SUPABASE_SERVICE_KEY`：配好后才写记录
- `R2_*`：配好后才存文件（待接 Cloudflare R2 凭证后补）

## 运行

```bash
python3 app.py            # 默认 :8080
./test.sh                 # 健康检查 + /demo 一次
```

## 当前状态（2026-11-09）

- 免费额度核实：见 `hidden_files/free-tier-check-2026-11-09.md`
  （6 家已核实，Simular Box / Cloady / OpenRouter 日限 / Sakupa 上限 4 项部分核实）
- OpenRouter 免费模型：`cohere/north-mini-code:free` 实测一次调用返回 `Hello!`；
  `nvidia/nemotron-3.5-lightning:free` probe 通过但实测两次空回复（推理占满预算）；
  另两款当时上游 429 限流 —— 免费池“能调通”和“每次都稳”不是一回事
- Supabase / R2：未接通，等用户确认账号授权后逐项接
- Kaggle：注册卡在 Google 密码步骤（已存密码被拒一次、重输后凭证服务称不可用），
  等用户决定自己登入或再处理；演示链路先走其他环节

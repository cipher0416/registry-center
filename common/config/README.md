# LLM 配置文件（llm_config.json）说明

本配置文件 (`llm_config.json`) 用于定义不同场景下使用的大语言模型、Embedding 模型及重排序模型的连接参数。支持两种类型的 API：
- **OpenAI 风格**：标准的 OpenAI 兼容接口（如 DeepSeek、GPT）。
- **AOC 平台**：通过特定网关调用的模型，需提供额外的鉴权与路由参数。

## 文件结构概览

```json
{
  "openai_style_llm": { ... },    // 通用对话模型
  "aoc_chat_llm": { ... },        // 企业内部对话模型
  "aoc_embedding_llm": { ... },   // 文本向量化模型
  "aoc_reranker_llm": { ... }     // 搜索结果重排序模型
}
```

## 通用字段说明

每个模型配置都包含以下基础字段：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `description` | string | 否 | 该模型的描述信息，仅用于备注。 |
| `model` | string | **是** | 模型名称，例如 `deepseek-chat`、`Qwen3_32B`、`bge-m3`。 |
| `enable_thinking` | bool | 否 | 是否启用模型“思考链”能力。一般对话模型可设为 `true`，Embedding/ReRanker 模型设为 `false`。 |
| `api` | string | **是** | API 请求的 Endpoint URL。 |
| `api_key` | string | 视情况 | 访问 API 所需的密钥。OpenAI 风格接口通常必填；AOC 接口可能使用 `extra` 中的其他鉴权字段，此处可填 `"dummy"` 或留空。 |
| `extra` | object | 否 | 扩展参数，主要用于 AOC 平台的特殊鉴权和请求模板。 |

---

## 各模型配置详解

### 1. OpenAI 风格模型 (`openai_style_llm`)

**使用场景**：标准的 OpenAI 兼容服务（如 DeepSeek、Qwen等）。  
**必要字段**：`api`、`api_key`、`model`。

```json
{
  "openai_style_llm": {
    "model": "deepseek-chat",
    "enable_thinking": true,
    "api": "https://api.deepseek.com",
    "api_key": "sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
  }
}
```

- **`api`**：服务商提供的 REST API 地址。
- **`api_key`**：鉴权用的 Secret Key。
- `enable_thinking`：按需开启。

### 2. AOC 对话模型 (`aoc_chat_llm`)

**使用场景**：通过企业内部 AOC 网关调用的对话模型（如 Qwen、ChatGLM 等）。  
**关键字段**：`extra` 对象必须完整，其中包含鉴权与路由信息。

| extra 字段 | 说明 |
|------------|------|
| `app_key` | 应用标识 Key，由网关分配。 |
| `app_secret` | 应用对应的密钥，用于生成签名（或配合授权头）。 |
| `authorization` | Bearer Token 或其他授权头，格式通常是 `Bearer <token>`。 |
| `api_code` | 接口编码，标识具体调用的模型能力。 |
| `api_version` | API 版本号，通常为 `"1.0"`。 |
| `scenario_code` / `scenario_version` | 业务场景标识与版本。 |
| `ability_code` | 能力编码，通常与 `api_code` 类似。 |
| `test_flag` | 测试标志，`"1"` 表示测试环境，`"0"` 表示生产。 |
| `request_template` | 请求体的 JSON 模板字符串，支持变量替换。 |

#### `request_template` 变量说明

- `{prompt}`：用户输入的原始文本。
- `{enable_thinking}`：对应当前配置中的 `enable_thinking` 布尔值（自动替换为 `true`/`false`）。

> 示例模板：
> ```json
> "{\"model\": \"Qwen3_32B\", \"messages\": [{\"role\": \"user\", \"content\": \"{prompt}\"}], \"chat_template_kwargs\": {\"enable_thinking\": {enable_thinking}}}"
> ```
> 实际发送前，程序会将 `{prompt}` 替换为用户消息，`{enable_thinking}` 替换为配置的值。

### 3. AOC Embedding 模型 (`aoc_embedding_llm`)

用于文本向量化。`extra` 结构与对话模型类似，但 `request_template` 不同：

```json
{"request_template": "{\"model\": \"bge-m3\", \"input\": \"{prompt}\"}"}
```

- `{prompt}`：需要向量化的文本内容。

### 4. AOC ReRanker 模型 (`aoc_reranker_llm`)

用于对候选文档列表进行相关性重排序。`request_template` 需要接收两个变量：

```json
{"request_template": "{\"model\": \"bge-reranker-v2-m3\", \"query\": \"{query}\", \"documents\": {documents}}"}
```

- `{query}`：用户的查询文本。
- `{documents}`：文档列表（**必须是数组的 JSON 字符串表示**，例如 `["doc1", "doc2"]` 直接嵌入，不带额外引号）。

---

## 填写指南（安全建议）

1. **占位符替换**  
   将所有 `<YOUR_XXX>` 或 `<...>` 形式的字符串替换为您的真实值：
   - API 地址中的主机名、端口、路径中的 endpoint ID。
   - 所有 `app_key`、`app_secret`、`authorization`、`api_code`、`scenario_code` 等业务参数。

2. **测试与验证**  
   填写完整后，可使用 `curl` 或 Postman 模拟一次请求，确保鉴权和请求体格式正确。

## 常见问题

**Q1：`openai_style_llm` 是否需要 `extra` 字段？**  
A：不需要，保留原始结构即可（本模板未提供该字段）。

**Q2：某些 AOC 模型的 `api_key` 是 `"dummy"`，是否必须保留？**  
A：可以保留或删除，实际鉴权通过 `extra.authorization` 和 `app_key`/`app_secret` 完成。如果网关要求必须提供 `api_key`，请替换为有效值。

**Q3：`request_template` 中的模型名称必须与顶层 `model` 字段一致吗？**  
A：建议一致，除非网关有特殊路由规则。本模板中已保持一致，您可按需修改。

---

## 使用示例 (Python)

> 在项目根目录创建llm_test.py文件，并执行测试
```python
from common.llm import get_llm_instance
from common.llm.config.llm_config import LLMType

if __name__ == '__main__':
    llm = get_llm_instance(LLMType.OPENAI_STYLE_LLM)
    reasoning, result = llm.ask_llm("who are you?")
    print(reasoning)
    print(result)
```
>执行脚本测试模型连通性
```bash
./venv/bin/python3 test_llm.py
```
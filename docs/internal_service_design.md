# Agent审核功能设计文档

## 1. 功能概述

### 1.1 背景

注册中心系统(registry-center)作为多个Agent之间的中转站，需要与多个Agent进程进行交互。为了更好地管理Agent的发布流程，需要补充实现Agent审核功能。

### 1.2 核心需求

#### 需求1：审核开关配置

- 用户可通过`python -m agent_registry.init`命令配置审核开关的开启状态
- 审核开关配置写入`etc/conf/server.conf`文件
- 审核开关开启后不能关闭（单向开关）

#### 需求2：Agent状态管理

- **审核开关开启时**：
  - Agent注册后初始状态为"已注册"
  - 调用审核接口后状态更新为"已发布"
  
- **审核开关关闭时**：
  - Agent注册后直接设置为"已发布"状态

#### 需求3：审核接口

- 通过UDS(Unix Domain Socket)接口实现Agent审核能力
- 入参：agentName(agent名称) + organization(组织名称)
- 审核开关开启时：调用接口更新Agent状态为"已发布"
- 审核开关关闭时：接口调用报错

## 2. 系统设计

### 2.1 审核开关配置

#### 2.1.1 配置项

在`etc/conf/server.conf`文件中新增配置项：

```ini
# Agent审核功能开关
agent_audit_enabled=true
```

**配置说明：**
- `true`：审核功能开启，Agent注册后需要审核才能发布
- `false`：审核功能关闭，Agent注册后直接发布

#### 2.1.2 配置流程

```
┌─────────────────────────────────┐
│  执行: python -m agent_registry.init │
└──────────┬──────────────────────┘
           │
           ▼
┌─────────────────────────────────┐
│  读取现有配置: agent_audit_enabled │
└──────────┬──────────────────────┘
           │
           ▼
┌─────────────────────────────────┐
│  提示用户输入审核开关配置         │
│  "是否开启审核功能 (y/n, 默认: true)" │
└──────────┬──────────────────────┘
           │
           ▼
┌─────────────────────────────────┐
│  用户输入: y/n                   │
└──────────┬──────────────────────┘
           │
      ┌────┴────┐
      │         │
  输入y      输入n
      │         │
      │         ▼
      │  ┌──────────────────────┐
      │  │ 检查现有配置           │
      │  │ agent_audit_enabled=? │
      │  └─────────┬────────────┘
      │       ┌────┴────┐
      │       │         │
      │    现有=true  现有=false
      │       │         │
      │       ▼         ▼
      │  ┌─────────┐  ┌─────────┐
      │  │报错：不能│  │允许关闭 │
      │  │关闭审核  │  │→开启审核│
      │  └─────────┘  └─────────┘
      │
      ▼
┌─────────────────────────────────┐
│  写入配置到server.conf            │
│  agent_audit_enabled=true        │
└─────────────────────────────────┘
```

#### 2.1.3 配置变更规则

**规则1：审核开关开启后不能关闭**

```python
# 现有配置: agent_audit_enabled=true
# 用户输入: n (尝试关闭)

# 系统报错：
错误：审核功能已开启，不能关闭！
原因：已存在"已注册"状态的Agent，关闭审核会导致状态不一致。

建议：
1. 保持审核功能开启状态
2. 或先处理所有"已注册"状态的Agent
```

**规则2：审核开关关闭后可以开启**

```python
# 现有配置: agent_audit_enabled=false
# 用户输入: y (尝试开启)

# 系统允许：
配置成功：审核功能已开启
注意：
- 新注册的Agent初始状态为"已注册"
- 已存在的"已发布"状态Agent保持不变
```

### 2.2 Agent状态模型

#### 2.2.1 状态定义

Agent状态分为两种：

| 状态 | 说明 | 可执行操作 |
|------|------|-----------|
| `registered` | 已注册 | 等待审核、可被审核接口调用 |
| `published` | 已发布 | 可被查询、可被调用、可被注销 |

#### 2.2.2 状态转换

```
┌─────────────────┐
│  Agent注册请求   │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────┐
│  检查审核开关配置                 │
│  agent_audit_enabled=?          │
└────────┬────────────────────────┘
         │
    ┌────┴────┐
    │         │
  true      false
    │         │
    ▼         ▼
┌──────────┐ ┌──────────┐
│状态=已注册│ │状态=已发布│
└─────┬────┘ └──────────┘
      │
      │ 审核接口调用
      ▼
┌──────────────┐
│ 检查审核开关  │
│ agent_audit_enabled=? │
└───────┬──────┘
    ┌───┴───┐
    │       │
  true    false
    │       │
    ▼       ▼
┌──────────┐ ┌──────────┐
│状态=已发布│ │报错：审核│
│(审核成功)│ │功能已关闭│
└──────────┘ └──────────┘
```

#### 2.2.3 数据模型变更

**修改AgentCard数据结构：**

在AgentCard中新增`status`字段：

```json
{
  "name": "TestAgent",
  "provider": {
    "organization": "TestOrg",
    "url": "https://test.org"
  },
  "description": "Test Description",
  "url": "https://agent.test",
  "version": "1.0.0",
  "status": "registered",  // 新增字段：registered 或 published
  ...
}
```

**状态字段说明：**
- `status`：字符串类型，枚举值为 `"registered"` 或 `"published"`
- 默认值：根据审核开关配置决定
- 必填字段

### 2.3 注册接口变更

#### 2.3.1 接口定义

**接口路径：** `/rest/a2a-t/v1/agents/register`

**请求体：** AgentCard JSON格式

**响应：**

```json
{
  "success": true,
  "message": "Agent registered successfully",
  "status": "registered",  // 或 "published"
  "agent": {
    "name": "TestAgent",
    "provider": {
      "organization": "TestOrg",
      "url": "https://test.org"
    },
    ...
  }
}
```

#### 2.3.2 注册流程

```python
async def register_agent(agent_card: ValidatedAgentCard):
    # 步骤1：验签（如果验签开关开启）
    if signature_validation_enabled:
        # 验签逻辑...
    
    # 步骤2：读取审核开关配置
    audit_enabled = config.get('agent_audit_enabled', 'false')
    
    # 步骤3：设置Agent初始状态
    if audit_enabled == 'true':
        agent_card.status = 'registered'  # 已注册，等待审核
    else:
        agent_card.status = 'published'   # 已发布，无需审核
    
    # 步骤4：保存Agent
    registry.register(agent_card)
    
    # 步骤5：返回响应
    return {
        "success": true,
        "status": agent_card.status,
        "message": f"Agent registered as {agent_card.status}"
    }
```

### 2.4 UDS审核接口设计

#### 2.4.1 UDS接口定义

**UDS Socket路径：** `/var/run/agent_audit.sock`

**接口协议：** JSON over UDS

**请求格式：**

```json
{
  "action": "audit",
  "agent_name": "TestAgent",
  "organization": "TestOrg"
}
```

**响应格式：**

```json
{
  "success": true,
  "message": "Agent audit successful",
  "agent": {
    "name": "TestAgent",
    "organization": "TestOrg",
    "status": "published"
  }
}
```

#### 2.4.2 UDS服务端设计

**文件结构：**

```
agent_registry/
├── audit/
│   ├── audit_service.py      # UDS服务端
│   ├── audit_handler.py      # 审核处理器
│   └── audit_socket.py       # Socket管理
```

**服务端代码结构：**

```python
class AuditService:
    """Agent审核UDS服务"""
    
    def __init__(self):
        self.socket_path = "/var/run/agent_audit.sock"
        self.registry = get_registry()
        self.config = get_conf()
    
    def start(self):
        """启动UDS服务"""
        # 创建UDS socket
        server_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        
        # 删除旧socket文件
        try:
            os.unlink(self.socket_path)
        except FileNotFoundError:
            pass
        
        # 绑定socket
        server_socket.bind(self.socket_path)
        
        # 设置权限：只有特定组可以访问
        os.chmod(self.socket_path, 0o660)  # rw-rw----
        os.chown(self.socket_path, 0, 1000)  # root:audit_group
        
        # 监听连接
        server_socket.listen(5)
        
        # 处理请求
        while True:
            conn, _ = server_socket.accept()
            self._handle_audit_request(conn)
    
    def _handle_audit_request(self, conn):
        """处理审核请求"""
        # 接收请求
        data = conn.recv(1024)
        request = json.loads(data)
        
        # 检查审核开关
        audit_enabled = self.config.get('agent_audit_enabled', 'false')
        if audit_enabled != 'true':
            # 审核功能关闭，报错
            response = {
                "success": false,
                "error": "Audit function is disabled",
                "message": "Cannot audit agent when audit_enabled=false"
            }
            conn.send(json.dumps(response).encode())
            conn.close()
            return
        
        # 审核功能开启，执行审核
        agent_name = request['agent_name']
        organization = request['organization']
        
        # 查找Agent
        agent = self.registry.get_by_key(agent_name, organization)
        if not agent:
            response = {
                "success": false,
                "error": "Agent not found"
            }
            conn.send(json.dumps(response).encode())
            conn.close()
            return
        
        # 检查Agent状态
        if agent.status == 'published':
            response = {
                "success": false,
                "error": "Agent already published"
            }
            conn.send(json.dumps(response).encode())
            conn.close()
            return
        
        # 更新状态为已发布
        agent.status = 'published'
        self.registry.update(agent_name, organization, agent.model_dump())
        
        # 返回成功响应
        response = {
            "success": true,
            "message": "Agent audit successful",
            "agent": {
                "name": agent_name,
                "organization": organization,
                "status": "published"
            }
        }
        conn.send(json.dumps(response).encode())
        conn.close()
```

#### 2.4.3 UDS客户端设计

**客户端代码：**

```python
class AuditClient:
    """Agent审核UDS客户端"""
    
    def __init__(self):
        self.socket_path = "/var/run/agent_audit.sock"
    
    def audit_agent(self, agent_name: str, organization: str) -> dict:
        """
        审核Agent
        
        Args:
            agent_name: Agent名称
            organization: 组织名称
        
        Returns:
            dict: 审核结果
        """
        # 创建UDS socket
        client_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        
        # 连接服务端
        try:
            client_socket.connect(self.socket_path)
        except PermissionError:
            return {
                "success": false,
                "error": "Permission denied",
                "message": "You don't have permission to audit agents"
            }
        
        # 构造请求
        request = {
            "action": "audit",
            "agent_name": agent_name,
            "organization": organization
        }
        
        # 发送请求
        client_socket.send(json.dumps(request).encode())
        
        # 接收响应
        response = client_socket.recv(1024)
        result = json.loads(response.decode())
        
        # 关闭连接
        client_socket.close()
        
        return result
```

#### 2.4.4 UDS访问控制

**权限设计：**

```bash
# Socket文件权限
ls -la /var/run/agent_audit.sock

# 输出：
srw-rw---- 1 root audit_group 0 Jan 1 12:00 /var/run/agent_audit.sock
```

**权限说明：**
- 所有者：root（可读写）
- 组：audit_group（可读写）
- 其他用户：无权限

**访问控制逻辑：**
1. 只有audit_group组成员可以调用审核接口
2. 普通用户无法访问UDS socket
3. 通过文件权限自动实现访问控制

#### 2.4.5 审核接口流程图

```
┌─────────────────────────────────┐
│  审核客户端调用审核接口           │
│  audit_agent("TestAgent", "TestOrg") │
└──────────┬──────────────────────┘
           │
           ▼
┌─────────────────────────────────┐
│  连接UDS Socket                  │
│  /var/run/agent_audit.sock       │
└──────────┬──────────────────────┘
           │
           ▼
┌─────────────────────────────────┐
│  检查文件权限                     │
│  (audit_group组成员?)            │
└──────────┬──────────────────────┘
           │
      ┌────┴────┐
      │         │
    有权限    无权限
      │         │
      │         ▼
      │  ┌──────────────────────┐
      │  │ 返回错误：Permission │
      │  │ denied               │
      │  └──────────────────────┘
      │
      ▼
┌─────────────────────────────────┐
│  发送审核请求                     │
│  {"action":"audit", ...}         │
└──────────┬──────────────────────┘
           │
           ▼
┌─────────────────────────────────┐
│  UDS服务端接收请求                │
└──────────┬──────────────────────┘
           │
           ▼
┌─────────────────────────────────┐
│  检查审核开关                     │
│  agent_audit_enabled=?          │
└──────────┬──────────────────────┘
           │
      ┌────┴────┐
      │         │
    true      false
      │         │
      │         ▼
      │  ┌──────────────────────┐
      │  │ 返回错误：Audit      │
      │  │ function is disabled │
      │  └──────────────────────┘
      │
      ▼
┌─────────────────────────────────┐
│  查找Agent                       │
│  get_by_key(agent_name, org)     │
└──────────┬──────────────────────┘
           │
      ┌────┴────┐
      │         │
    找到      未找到
      │         │
      │         ▼
      │  ┌──────────────────────┐
      │  │ 返回错误：Agent not │
      │  │ found                │
      │  └──────────────────────┘
      │
      ▼
┌─────────────────────────────────┐
│  检查Agent状态                   │
│  status == "registered"?         │
└──────────┬──────────────────────┘
           │
      ┌────┴────┐
      │         │
  registered  published
      │         │
      │         ▼
      │  ┌──────────────────────┐
      │  │ 返回错误：Already    │
      │  │ published            │
      │  └──────────────────────┘
      │
      ▼
┌─────────────────────────────────┐
│  更新Agent状态                   │
│  status = "published"            │
└──────────┬──────────────────────┘
           │
           ▼
┌─────────────────────────────────┐
│  保存Agent                       │
│  registry.update(...)            │
└──────────┬──────────────────────┘
           │
           ▼
┌─────────────────────────────────┐
│  返回成功响应                     │
│  {"success":true, ...}           │
└─────────────────────────────────┘
```

## 3. 实现方案

### 3.1 文件修改清单

#### 3.1.1 新增文件

```
agent_registry/
├── audit/
│   ├── __init__.py
│   ├── audit_service.py      # UDS审核服务
│   ├── audit_handler.py      # 审核业务逻辑
│   └── audit_client.py       # 审核客户端（供测试使用）
```

#### 3.1.2 修改文件

```
agent_registry/
├── init.py                   # 新增审核开关配置提示
├── server.py                 # 修改注册接口，设置Agent初始状态
├── core.py                   # 新增状态管理方法
├── start.py                  # 启动UDS审核服务
├── model/
│   └── validated_agentcard.py  # 新增status字段验证
```

### 3.2 代码实现要点

#### 3.2.1 init.py修改

在`init_command()`方法中新增审核开关配置：

```python
# 新增代码片段
default_audit_enabled = self.existing_config.get('agent_audit_enabled', 'false')
current_audit_enabled = default_audit_enabled

# 检查现有配置
if current_audit_enabled == 'true':
    print("⚠️  注意：审核功能已开启，不能关闭！")
    audit_input = 'y'  # 强制保持开启
else:
    audit_input = input(
        f"是否开启审核功能 agent_audit_enabled (y/n, 默认: {default_audit_enabled}): "
    ).strip().lower()

# 处理用户输入
if audit_input == 'n':
    if current_audit_enabled == 'true':
        print("❌ 错误：审核功能已开启，不能关闭！")
        print("   原因：已存在'已注册'状态的Agent")
        sys.exit(1)
    config['agent_audit_enabled'] = 'false'
elif audit_input == 'y':
    config['agent_audit_enabled'] = 'true'
else:
    config['agent_audit_enabled'] = default_audit_enabled
```

#### 3.2.2 server.py修改

修改`register_agent`接口，添加状态设置逻辑：

```python
@app.post("/rest/a2a-t/v1/agents/register")
async def register_agent(agent: ValidatedAgentCard, request: Request):
    # 验签逻辑（如果开启）...
    
    # 读取审核开关配置
    audit_enabled = config.get('agent_audit_enabled', 'false')
    
    # 设置Agent初始状态
    if audit_enabled == 'true':
        agent.status = 'registered'
        status_message = "Agent registered, waiting for audit"
    else:
        agent.status = 'published'
        status_message = "Agent registered and published"
    
    # 注册Agent
    result = await _perform_registration(agent, registry, client_ip, details)
    
    # 返回响应
    return JSONResponse(
        content={
            "success": result,
            "status": agent.status,
            "message": status_message
        },
        status_code=status.HTTP_201_CREATED
    )
```

#### 3.2.3 core.py修改

新增状态管理方法：

```python
def update_status(self, name: str, organization: str, new_status: str) -> bool:
    """
    更新Agent状态
    
    Args:
        name: Agent名称
        organization: 组织名称
        new_status: 新状态 (registered/published)
    
    Returns:
        bool: 是否成功更新
    """
    key = self._make_key(name, organization)
    agent = self._agents.get(key)
    
    if not agent:
        logger.warning(f"Agent not found: {name} ({organization})")
        return False
    
    # 更新状态
    agent.status = new_status
    self._agents[key] = agent
    self._save()
    
    logger.info(f"Agent status updated: {name} -> {new_status}")
    return True

def get_agents_by_status(self, status: str) -> List[AgentCard]:
    """
    根据状态查询Agent
    
    Args:
        status: Agent状态
    
    Returns:
        List[AgentCard]: Agent列表
    """
    return [agent for agent in self._agents.values() if agent.status == status]
```

#### 3.2.4 validated_agentcard.py修改

新增status字段验证：

```python
class ValidatedAgentCard(AgentCard):
    """验证后的AgentCard"""
    
    status: Optional[str] = Field(
        default='published',
        description="Agent状态: registered(已注册) 或 published(已发布)"
    )
    
    @field_validator('status')
    @classmethod
    def validate_status(cls, v: str) -> str:
        if v not in ['registered', 'published']:
            raise ValueError('状态仅支持 registered 或 published')
        return v
```

#### 3.2.5 start.py修改

启动UDS审核服务：

```python
def main():
    server_config = get_conf()
    
    # 启动UDS审核服务（如果审核功能开启）
    audit_enabled = server_config.get('agent_audit_enabled', 'false')
    if audit_enabled == 'true':
        from agent_registry.audit.audit_service import AuditService
        
        # 创建审核服务线程
        audit_service = AuditService()
        audit_thread = threading.Thread(target=audit_service.start, daemon=True)
        audit_thread.start()
        
        logger.info("Audit service started on UDS socket")
    
    # 启动HTTP服务
    ...
```

### 3.3 配置变更示例

#### 3.3.1 审核功能开启后的配置

```ini
# etc/conf/server.conf
agent_audit_enabled=true
```

**影响：**
- 新注册的Agent状态为`registered`
- 需要调用审核接口才能变为`published`
- UDS审核服务启动并监听

#### 3.3.2 审核功能关闭时的配置

```ini
# etc/conf/server.conf
agent_audit_enabled=false
```

**影响：**
- 新注册的Agent直接为`published`状态
- UDS审核服务不启动
- 调用审核接口会报错

### 3.4 数据持久化

#### 3.4.1 Agent数据存储格式

**data/agentcard.json：**

```json
[
  {
    "name": "TestAgent",
    "provider": {
      "organization": "TestOrg",
      "url": "https://test.org"
    },
    "description": "Test Description",
    "url": "https://agent.test",
    "version": "1.0.0",
    "status": "registered",  // 新增字段
    "skills": [...],
    ...
  },
  {
    "name": "AnotherAgent",
    "provider": {
      "organization": "AnotherOrg",
      "url": "https://another.org"
    },
    "status": "published",  // 新增字段
    ...
  }
]
```

#### 3.4.2 状态兼容性处理

**启动时加载Agent数据：**

```python
def _load(self):
    """加载Agent数据"""
    data_list = load_from_file(self.persistence_file)
    
    for item in data_list:
        try:
            # 兼容处理：如果没有status字段，默认为published
            if 'status' not in item:
                item['status'] = 'published'
                logger.info(f"Agent {item['name']} missing status, set to published")
            
            agent = AgentCard(**item)
            key = self._make_key(agent.name, agent.provider.organization)
            self._agents[key] = agent
        except Exception as e:
            logger.error(f"Failed to load agent: {e}")
```

## 4. 测试方案

### 4.1 单元测试

#### 4.1.1 审核开关配置测试

```python
def test_audit_config():
    """测试审核开关配置"""
    
    # 测试1：默认配置
    init_cmd = InitCommand()
    assert init_cmd.existing_config.get('agent_audit_enabled') == 'false'
    
    # 测试2：开启审核
    config = {'agent_audit_enabled': 'true'}
    init_cmd.save_config_to_file(config)
    assert get_conf()['agent_audit_enabled'] == 'true'
    
    # 测试3：尝试关闭已开启的审核（应报错）
    # 模拟用户输入'n'
    # 预期：报错，不能关闭
```

#### 4.1.2 Agent状态测试

```python
def test_agent_status():
    """测试Agent状态管理"""
    
    registry = RegistryCore()
    
    # 测试1：审核功能开启时注册
    agent = AgentCard(name="Test", provider=Provider(...), status='registered')
    registry.register(agent)
    assert registry.get_by_key("Test", "Org").status == 'registered'
    
    # 测试2：审核通过
    registry.update_status("Test", "Org", 'published')
    assert registry.get_by_key("Test", "Org").status == 'published'
    
    # 测试3：审核功能关闭时注册
    agent2 = AgentCard(name="Test2", provider=Provider(...), status='published')
    registry.register(agent2)
    assert registry.get_by_key("Test2", "Org").status == 'published'
```

#### 4.1.3 UDS接口测试

```python
def test_audit_uds_interface():
    """测试UDS审核接口"""
    
    # 启动审核服务
    audit_service = AuditService()
    audit_thread = threading.Thread(target=audit_service.start, daemon=True)
    audit_thread.start()
    
    # 创建客户端
    client = AuditClient()
    
    # 测试1：审核功能开启时调用
    result = client.audit_agent("TestAgent", "TestOrg")
    assert result['success'] == True
    assert result['agent']['status'] == 'published'
    
    # 测试2：审核功能关闭时调用（应报错）
    # 修改配置：agent_audit_enabled=false
    result = client.audit_agent("TestAgent", "TestOrg")
    assert result['success'] == False
    assert result['error'] == "Audit function is disabled"
```

### 4.2 集成测试

#### 4.2.1 完整流程测试

**测试场景：**

1. **审核功能开启场景**
   ```bash
   # 步骤1：配置审核功能开启
   python -m agent_registry.init
   # 输入：y
   
   # 步骤2：注册Agent
   curl -X POST http://localhost:5000/rest/a2a-t/v1/agents/register \
     -H "Content-Type: application/json" \
     -d '{"name":"TestAgent", ...}'
   
   # 预期响应：
   {"success":true, "status":"registered", "message":"Agent registered, waiting for audit"}
   
   # 步骤3：调用审核接口
   python audit_client.py TestAgent TestOrg
   
   # 预期响应：
   {"success":true, "status":"published", "message":"Agent audit successful"}
   
   # 步骤4：查询Agent
   curl http://localhost:5000/rest/a2a-t/v1/agents/query?name=TestAgent
   
   # 预期：status="published"
   ```

2. **审核功能关闭场景**
   ```bash
   # 步骤1：配置审核功能关闭
   python -m agent_registry.init
   # 输入：n
   
   # 步骤2：注册Agent
   curl -X POST http://localhost:5000/rest/a2a-t/v1/agents/register \
     -H "Content-Type: application/json" \
     -d '{"name":"TestAgent", ...}'
   
   # 预期响应：
   {"success":true, "status":"published", "message":"Agent registered and published"}
   
   # 步骤3：尝试调用审核接口（应报错）
   python audit_client.py TestAgent TestOrg
   
   # 预期响应：
   {"success":false, "error":"Audit function is disabled"}
   ```

3. **审核功能从关闭到开启场景**
   ```bash
   # 步骤1：审核功能关闭时注册Agent1
   # 预期：status="published"
   
   # 步骤2：开启审核功能
   python -m agent_registry.init
   # 输入：y
   
   # 步骤3：注册Agent2
   # 预期：status="registered"
   
   # 步骤4：查询Agent1
   # 预期：status仍为"published"（保持原状）
   
   # 步骤5：审核Agent2
   # 预期：status变为"published"
   ```

### 4.3 安全测试

#### 4.3.1 UDS权限测试

```bash
# 测试1：普通用户无法访问审核接口
python audit_client.py TestAgent TestOrg

# 预期：
Permission denied: You don't have permission to audit agents

# 测试2：audit_group组成员可以访问
sudo usermod -aG audit_group $USER
python audit_client.py TestAgent TestOrg

# 预期：成功调用审核接口
```

#### 4.3.2 配置安全测试

```bash
# 测试1：尝试关闭已开启的审核功能
python -m agent_registry.init
# 当前配置：agent_audit_enabled=true
# 输入：n

# 预期：
错误：审核功能已开启，不能关闭！

# 测试2：篡改配置文件
echo "agent_audit_enabled=false" >> etc/conf/server.conf

# 启动服务时检查配置一致性
# 预期：检测到配置不一致，报错或警告
```

## 5. 运维方案

### 5.1 配置管理

#### 5.1.1 查看当前配置

```bash
# 查看审核开关配置
cat etc/conf/server.conf | grep agent_audit_enabled

# 输出：
agent_audit_enabled=true
```

#### 5.1.2 修改配置

```bash
# 开启审核功能
python -m agent_registry.init
# 输入：y

# 注意：不能通过直接修改配置文件关闭审核功能
# 必须通过init命令检查配置一致性
```

### 5.2 Agent状态查询

```bash
# 查询所有"已注册"状态的Agent
curl http://localhost:5000/rest/a2a-t/v1/agents/query?status=registered

# 查询所有"已发布"状态的Agent
curl http://localhost:5000/rest/a2a-t/v1/agents/query?status=published
```

### 5.3 批量审核

```python
# 批量审核所有"已注册"状态的Agent
from agent_registry.audit.audit_client import AuditClient

client = AuditClient()

# 获取所有"已注册"Agent
registered_agents = registry.get_agents_by_status('registered')

# 批量审核
for agent in registered_agents:
    result = client.audit_agent(agent.name, agent.provider.organization)
    print(f"{agent.name}: {result['message']}")
```

### 5.4 监控和日志

#### 5.4.1 审核日志

```python
# 记录审核操作日志
await audit_handle.handle({
    "operation_name": OperationName.AUDIT_AGENT,
    "level": LogLevel.MINOR,
    "result": OperationResult.SUCCESS,
    "object_name": OperatorObject.AGENT,
    "details": {
        "agent_name": "TestAgent",
        "organization": "TestOrg",
        "status": "registered -> published"
    },
    "user_name": "admin"
})
```

#### 5.4.2 审核统计

```bash
# 统计Agent状态分布
curl http://localhost:5000/rest/a2a-t/v1/agents/statistics

# 预期响应：
{
  "total": 100,
  "registered": 20,
  "published": 80
}
```

## 6. 总结

### 6.1 功能要点

1. **审核开关配置**
   - 通过`init.py`交互式配置
   - 配置写入`server.conf`文件
   - 开启后不能关闭（单向开关）

2. **Agent状态管理**
   - 新增`status`字段：registered/published
   - 审核开启：注册后为registered，审核后为published
   - 审核关闭：注册后直接为published

3. **UDS审核接口**
   - Socket路径：`/var/run/agent_audit.sock`
   - 入参：agent_name + organization
   - 文件权限实现访问控制
   - 审核关闭时调用报错

### 6.2 安全要点

1. **配置安全**
   - 审核开关开启后不能关闭
   - 防止配置不一致导致状态混乱

2. **访问控制**
   - UDS socket文件权限控制访问
   - 只有audit_group组成员可以审核

3. **状态一致性**
   - 配置变更时保持已存在Agent状态不变
   - 新Agent按新配置设置状态

### 6.3 扩展性

1. **状态扩展**
   - 可扩展更多状态（如：审核中、审核失败等）

2. **审核流程扩展**
   - 可增加多级审核
   - 可增加审核日志和审计

3. **接口扩展**
   - 可增加批量审核接口
   - 可增加审核历史查询接口

该设计文档详细说明了Agent审核功能的实现方案，包括审核开关配置、Agent状态管理、UDS审核接口设计等，为后续实现提供了完整的设计蓝图。
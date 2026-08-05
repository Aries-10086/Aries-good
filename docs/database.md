# 云端 PostgreSQL 连接说明

文墨后端通过 `DATABASE_URL` 连接托管 PostgreSQL，应用代码不绑定具体云厂商。

## 环境划分

| 环境 | 用途 | 连接方式 |
|------|------|----------|
| dev | 日常开发与联调 | 开发者 `.env` 本地保存 |
| staging | 预发布验证 | CI / 部署 Secret |
| prod | 正式环境 | 仅内网或白名单访问 |

## 配置示例

```bash
DATABASE_URL=postgresql://USER:PASSWORD@HOST:5432/wenmo_dev?sslmode=require
```

要求：

- PostgreSQL ≥ 15
- 必须启用 SSL（`sslmode=require`）
- 禁止把真实密码提交到 Git 仓库

## 本地离线备用

如需在无云库环境调试，可启用 compose profile：

```bash
docker compose -f docker/docker-compose.dev.yml --profile offline up -d postgres
export DATABASE_URL=postgresql://wenmo:changeme@localhost:5432/wenmo
```

## 迁移

```bash
cd QuillMind/backend
python manage.py migrate
python manage.py dbshell
```

## 备份

生产环境使用云厂商自动备份与手动快照；应用容器内不执行 `pg_dump` 作为主备份方案。

# 本亦运营后台 V2：Render 免费路线部署说明

这份说明用于把本亦运营后台部署成员工可以通过公开网址访问的网站。

## 当前推荐方案

为了避免在中国付款不方便，本项目现在推荐：

1. Render 免费 Web Service 跑网站。
2. 免费云 PostgreSQL 保存数据。
3. Render 里填写 `DATABASE_URL` 连接云数据库。

这样不需要购买 Render Persistent Disk，服务重启后数据也不会因为网站文件系统清空而丢失。

## 已经做好的线上改造

- 后端监听 `0.0.0.0`，符合 Render Web Service 公开访问要求。
- 自动读取 Render 提供的 `PORT` 端口。
- 本地没设置 `DATABASE_URL` 时，自动使用 SQLite。
- 线上设置 `DATABASE_URL` 后，自动使用 PostgreSQL。
- 已添加 `/api/health` 健康检查接口。
- 已添加 `requirements.txt`，Render 会自动安装 PostgreSQL 驱动。
- `render.yaml` 已改成免费 Web Service 配置。

## 第一步：准备免费云数据库

任选一个即可：

- Supabase：https://supabase.com
- Neon：https://neon.tech

你需要创建一个 PostgreSQL 数据库，然后复制连接地址。

连接地址一般长这样：

```text
postgresql://用户名:密码@主机地址:5432/数据库名?sslmode=require
```

这个地址后面要填到 Render 的环境变量：

```text
DATABASE_URL
```

注意：这个地址相当于数据库钥匙，不要发到微信群，也不要截图公开。

## 第二步：确认 GitHub 仓库有这些文件

你的仓库里应该有：

```text
server.py
index.html
styles.css
app.js
requirements.txt
render.yaml
README.md
DEPLOY_RENDER.md
```

## 第三步：在 Render 创建 Web Service

1. 打开 Render。
2. 点击右上角 `New +`。
3. 选择 `Web Service`。
4. 选择 GitHub 仓库：

```text
anyipei110-max/benyi-ops-v2
```

5. 配置如下：

```text
Name: benyi-ops-v2
Language: Python 3
Branch: main
Region: Oregon 或 Singapore
Root Directory: 留空
Build Command: pip install -r requirements.txt
Start Command: python3 server.py
```

6. Instance Type 选择免费或可用的最低套餐即可。

## 第四步：填写环境变量

在 Render 的 Environment Variables 里添加：

```text
BENYI_HOST=0.0.0.0
DATABASE_URL=你的云 PostgreSQL 连接地址
BENYI_ADMIN_PASSWORD=你想设置的老板初始密码
BENYI_DEFAULT_STAFF_PASSWORD=你想设置的员工初始密码
```

不要再添加 Persistent Disk，也不要设置 `BENYI_DATA_DIR=/var/data`。

## 第五步：创建并等待部署

点击：

```text
Create Web Service
```

等待 Render 显示：

```text
Live
```

部署成功后，Render 会给你一个公开网址，类似：

```text
https://benyi-ops-v2.onrender.com
```

以后员工就打开这个网址登录。

## 默认账号

老板：

```text
账号：admin
密码：BENYI_ADMIN_PASSWORD 里设置的密码
```

员工账号：

```text
轻松：qingsong
王文芳：wangwenfang
谢秀平：xiexiu-ping
文员：clerk
```

员工初始密码：

```text
BENYI_DEFAULT_STAFF_PASSWORD 里设置的密码
```

老板登录后，可以进入「员工账号管理」新增员工、改角色、停用账号、重置密码。

## 如何验证数据不会丢

1. 用 Render 网址打开后台。
2. 用老板账号登录。
3. 新增一所学校。
4. 新增一条 UGC 活动。
5. 新增一条门店日报或工作汇总。
6. 刷新网页，确认数据还在。
7. 在 Render 里手动重启服务，再登录确认数据还在。

## 本地运行仍然可用

本地不设置 `DATABASE_URL` 时，仍然使用：

```text
data/benyi_v2.sqlite
```

启动方式仍然是：

```bash
python3 server.py
```

如果本地也想连接云数据库，可以先安装依赖：

```bash
pip3 install -r requirements.txt
```

然后设置 `DATABASE_URL` 再启动。

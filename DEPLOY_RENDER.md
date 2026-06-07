# 本亦运营后台 V2：Render 线上部署说明

这份说明用于把本亦运营后台部署成员工可以通过公开网址访问的网站。

## 已经为线上部署做好的改造

- 后端监听 `0.0.0.0`，符合 Render Web Service 的公开访问要求。
- 自动读取 Render 提供的 `PORT` 端口。
- 数据库目录支持环境变量 `BENYI_DATA_DIR`。
- Render 上推荐把 `BENYI_DATA_DIR` 设置为 `/var/data`。
- `render.yaml` 已配置 Persistent Disk，数据库会保存到 `/var/data/benyi_v2.sqlite`。
- 已添加 `/api/health` 健康检查接口。
- 已添加 `requirements.txt`。
- 本地仍可用 `python3 server.py` 运行。

## 重要说明：数据库怎么保证不丢

当前线上版为了简单和稳定，继续使用 SQLite，但数据库文件不再放在你电脑上。

Render 部署后，数据库文件会放在 Render Persistent Disk：

```text
/var/data/benyi_v2.sqlite
```

只要 Render Web Service 绑定了 Persistent Disk，服务重启、重新部署后数据都不会丢。

不要把数据库写到项目目录里，因为 Render 普通文件系统是临时的，重启或重新部署后会丢。

## 第一步：把项目上传到 GitHub

### 1. 在 GitHub 创建仓库

1. 打开 GitHub。
2. 点击右上角 `+`。
3. 选择 `New repository`。
4. 仓库名可以叫：

```text
benyi-ops-v2
```

5. 选择 Private 或 Public 都可以。
6. 不要勾选初始化 README。
7. 点击 `Create repository`。

### 2. 在本机终端上传代码

打开终端，执行：

```bash
cd "/Users/xuzirui/Documents/Codex/2026-06-06/0-mvp-1-2-3-4"
git init
git add .
git commit -m "Deployable Benyi ops backend V2"
git branch -M main
```

然后把下面的地址替换成你自己的 GitHub 仓库地址：

```bash
git remote add origin https://github.com/你的用户名/benyi-ops-v2.git
git push -u origin main
```

如果 GitHub 要求登录，按终端提示操作即可。

## 第二步：在 Render 创建 Web Service

推荐用 `render.yaml` Blueprint 创建：

1. 打开 Render。
2. 点击 `New +`。
3. 选择 `Blueprint`。
4. 连接刚刚上传的 GitHub 仓库。
5. Render 会读取项目里的 `render.yaml`。
6. 设置环境变量：

```text
BENYI_ADMIN_PASSWORD=你想设置的老板初始密码
BENYI_DEFAULT_STAFF_PASSWORD=你想设置的员工初始密码
```

7. 确认创建。

如果你不用 Blueprint，也可以手动创建 Web Service：

- Runtime：Python
- Build Command：

```bash
pip install -r requirements.txt
```

- Start Command：

```bash
python3 server.py
```

- Health Check Path：

```text
/api/health
```

- Environment Variables：

```text
BENYI_HOST=0.0.0.0
BENYI_DATA_DIR=/var/data
BENYI_ADMIN_PASSWORD=你想设置的老板初始密码
BENYI_DEFAULT_STAFF_PASSWORD=你想设置的员工初始密码
```

- Persistent Disk：

```text
Mount Path: /var/data
Size: 1 GB 或更高
```

## 第三步：部署后员工打开哪个网址

Render 部署成功后，会给你一个公开网址，类似：

```text
https://benyi-ops-v2.onrender.com
```

以后员工就打开这个网址登录。

默认账号仍然是：

- 老板：admin
- 轻松：qingsong
- 王文芳：wangwenfang
- 谢秀平：xiexiu-ping
- 文员：clerk

密码取决于你首次部署时设置的环境变量：

- `BENYI_ADMIN_PASSWORD`
- `BENYI_DEFAULT_STAFF_PASSWORD`

如果你没有设置环境变量，则默认仍是：

- admin / admin123
- 其他员工 / 123456

线上公开网址强烈建议不要用默认密码。

## 第四步：如何验证部署成功

1. 打开 Render 给你的网址。
2. 用 `admin` 登录。
3. 进入「员工账号管理」，确认员工账号都在。
4. 新增一条学校数据。
5. 用员工账号登录，新增门店日报或工作汇总。
6. 老板账号刷新后能看到员工提交的数据。
7. 在 Render 手动重启服务，再登录确认数据还在。

## 后续升级为 PostgreSQL

SQLite + Persistent Disk 适合第一阶段上线使用。

当数据量变大、多人同时高频录入时，建议升级到 PostgreSQL：

1. 在 Render 创建 PostgreSQL 数据库。
2. 后端增加 PostgreSQL 数据库连接。
3. 把 SQLite 旧数据迁移到 PostgreSQL。
4. Render Web Service 使用 `DATABASE_URL` 连接数据库。

目前这一步没有强制做，是为了保证第一版线上后台尽快可运行。

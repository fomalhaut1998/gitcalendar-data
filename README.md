# 方案 B · 让贡献日历不再依赖任何服务器

## 一句话

用一个每 6 小时跑一次的 GitHub Action，把贡献数据写成一个静态 JSON 文件放进一个公开仓库，前端直接读这个文件。没有 Vercel 函数、没有第三方接口、没有 Vercel 项目会欠费或过期 —— 唯一能让它失效的事情是 GitHub 自己挂了。

## 原理

```
GitHub GraphQL API  →  GitHub Action（每 6 小时）  →  gitcalendar-data 仓库里的 data.json
                                                                  ↓ jsDelivr / jsdmirror 分发
                                    访客浏览器里的 gitcalendar.js 直接 fetch 这个文件
```

和朋友圈那套（hexo-circle-of-friends + jsdmirror）是同一个思路：**把「需要有人维护的服务」换成一个文件。**

为什么单独开一个仓库：如果把这个每 6 小时提交一次的任务放在博客仓库里，每次提交都会触发一次整站重新部署。

## 文件

| 文件 | 说明 |
| --- | --- |
| `generate.py` | 查 GraphQL → 校验形状 → 写 `data.json` |
| `.github/workflows/update.yml` | 定时（每 6 小时）+ 可手动触发 |

`generate.py` 里的形状校验是硬性的：周数不是 53、最后一周为空、GraphQL 报错 —— 任一情况直接退出并且**不覆写 data.json**，CDN 上留着的还是上一份好数据。宁可数据旧 6 小时，也不要页面空白。

## 操作步骤

### 1. 新建仓库

GitHub 上新建一个 **Public** 仓库，名字比如 `gitcalendar-data`。必须是公开的，jsDelivr / jsdmirror 只分发公开仓库。

### 2. 把两个文件传上去

```
gitcalendar-data/
├── generate.py
└── .github/workflows/update.yml     ← 路径不能变，必须放在 .github/workflows/ 下
```

### 3. 打开写权限

仓库 **Settings → Actions → General → Workflow permissions** → 选 **Read and write permissions** → Save。

不开这一步，Action 能生成数据但 `git push` 会被拒。

### 4. 手动跑一次

仓库 **Actions → 更新贡献日历数据 → Run workflow**（选 master/main 分支）。

跑完看日志末尾应该出现：

```
已写出 data.json：11943 字节 · 53 周 · total=4
```

并且仓库根目录多了一个 `data.json`。

### 5. 确认分发地址能用

浏览器直接打开：

```
https://cdn.jsdmirror.com/gh/fomalhaut1998/gitcalendar-data@main/data.json
```

能看到一段 JSON（`{"total":4,"contributions":[[{"date":"2025-09-28","count":0},…`）就算通了。第一次可能要等 1~2 分钟。

（备用地址：`https://cdn.jsdelivr.net/gh/fomalhaut1998/gitcalendar-data@main/data.json`，效果一样。）

### 6. 把博客指过来

`_config.yml` 的 gitcalendar 段，在 `apiurl` 下面加一行：

```yaml
  apiurl: "https://gitcalendar.fomal.cc"
  jsonurl: "https://cdn.jsdmirror.com/gh/fomalhaut1998/gitcalendar-data@main/data.json"
```

然后**重启 hexo server**（`_config.yml` 不在 watch 范围内），push 上线。

## 关于缓存

jsDelivr 对分支地址（`@main`）的缓存最多 12 小时。日历数据慢半天更新是可以接受的；如果你希望更实时，把地址换成 commit 哈希就没法自动更新了 —— 所以不建议。

## 回滚

删掉 `_config.yml` 里那行 `jsonurl` 即可，会回落到 `apiurl + "/api?" + user`，也就是你自己的 Vercel 函数（一直还在，没动过）。

## 和方案 A 的关系

两者不冲突：Vercel 函数继续留着作为备用，哪边都能随时切回去。

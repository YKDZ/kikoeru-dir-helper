# Kikoeru Directory Helper

Kikoeru Directory Helper 是一个简单的 [kikoeru](https://github.com/kikoeru-project) 资源目录自动化工具。

## 功能说明

它遵从以下规则处理工作目录中新增的 `.zip`、`.rar`, `.7z` 压缩文件：

- 若解压出的内容全部都是以 `RJ` 开头的文件夹，则原样保留在工作目录
- 若解压出的内容是一个不以 `RJ` 开头的文件夹，且压缩文件名以 `RJ` 开头，则将解压出的文件夹命名为压缩文件名并保留在工作目录
- 若解压出的内容是多个文件夹，且有任意文件夹不以 `RJ` 开头，则将解压出的所有内容都移动到 `工作目录/[日期]-[压缩文件名]` 中，并附上本次处理的日志文件（要求手动处理）
- 若解压出的内容包含任意一个非文件夹，则将解压出的所有内容都移动到 `工作目录/[日期]-[压缩文件名]` 中，并附上本次处理的日志文件（要求手动处理）
- 若解压出的内容顶层包含压缩文件，且还包含任意非压缩文件，则将解压出的所有内容都移动到 `工作目录/[日期]-[压缩文件名]` 中，并附上本次处理的日志文件（要求手动处理）
- 若解压出的内容全部都是压缩文件，则对每一个压缩文件都递归应用规则

之后，删除压缩文件。

若解压过程中出错，则不删除压缩文件并记录日志。

正常记录的日志文件默认保存在 `工作目录/.helper/helper.log` 中。

工具还支持处理 Xftp、WinSCP 等工具分片上传的形式，会等待文件全部上传完成后再开始处理。

## 边缘情况

### 无扩展名

对于任何没有扩展名的文件，将尝试从文件中推测其是否是压缩文件类型，如果是，视作正常压缩文件应用规则。

## 压缩文件密码

对任何压缩文件要求密码的情况，将尝试在文件名中寻找形如 `文件名 pass-xxx.扩展名` 的部分，并将 `xxx` 视作密码，之后将 ` pass-xxx` 从文件名中删去，不视为所有规则中 `文件名` 的一部分。

对于多层压缩文件，尝试从最外层文件寻找密码，密码的格式为 `文件名 pass-xxx1 xxx2 xxx3 ... xxxn.扩展名`，其中 `xxx1` 是最外层压缩文件的密码，`xxx2` 是第二层压缩文件的密码，以此类推。

对于包含空格的密码，用半角括号包裹：`文件名 pass-(I am password 1) (I am password 2) pass3.扩展名`

## 使用

### Docker 镜像

首先将本仓库克隆到本地。

接着前往 [官网](https://www.rarlab.com/download.htm) 下载 `rar` 工具的 `linux` 命令行版本（文件名格式类似 `rarlinux-x64-712.tar.gz`），放置在 `docker/libs` 目录下（无需解压）。

之后使用如下命令构建镜像：

```bash
docker buildx build . -f docker/Dockerfile -t ykdz/kikoeru-dir-helper
```

之后你可以用 `docker run ykdz/kikoeru-dir-helper:latest` 或 `docker compose` 运行镜像。一个简单的 `compose.yml` 示例如下：

```yml
services:
  helper:
    image: ykdz/kikoeru-dir-helper:latest
    restart: always
    environment:
      - TZ=Asia/Shanghai
    volumes:
      - /mnt/user/kikoeru/VoiceWork:/data
```

#### 环境变量

- `WORK_DIR`: 工作目录路径（默认: /data）
- `CHECK_INTERVAL`: 执行稳定性检查的时间间隔，单位秒（默认: 5）
- `MIN_STABLE_CHECKS`: 文件通过几次稳定性检查后视为已经稳定（默认: 3）
- `MAX_WAIT_TIME`: 等待文件稳定的最长时间，单位秒（默认: 3600）
- `LOG_DIR`: 日志文件存放目录（默认: /data/.helper）

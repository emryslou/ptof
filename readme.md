# 功能说明:
## v0.0.1
- 解析PDF内容，生成Excel，然后Excel文件同步至 FTP
- PDF来源: 1. Email 附件 2. 指定目录
  
# 部署步骤
1. 安装 Python 3.11 环境， 下面是下载地址:
   - x64: https://www.python.org/ftp/python/3.11.1/python-3.11.1-amd64.exe
   - x86: https://www.python.org/ftp/python/3.11.1/python-3.11.1.exe
2. 打开命令行，执行: `python -V`, 输出版本号，即安装成功
3. 打开命令行，执行: `pip -V` 输出版本号，即安装成功
4. 安装包，`pip install X:\your\path\xxxx.whl`, 出现安装成功即可
5. 验证: `python -m ptof` 没有报错即为安装成功

# 执行业务:
1. 自动从邮件下载PDF，解析，并同步到 FTP：`python -m ptof pipeline --config X:\config\file\config.yml`
2. 手动解析指定目录下的 PDF 解析，并同步到 FTP: `python -m ptof parse_attachments --config X:\config\file\config.yml --pdf-dir X:\your\pdf\path`
3. 查看 config.yml 文件示例：`python -m ptof show-config-file`

# 关于解析 PDF 细节说明：
1. 从邮件解析：邮件主题格式：`[PackageList]邮件主题` ，例如: [PackageList]xxxxxx ， 附件为 `pdf`， 文件名没有特别要求
2. 从目录中解析，PDF 文件名格式: `[PackageList]PDF文件名.pdf`, 例如：[PackageList]xxxx.pdf

import sys
from ptof.logger import logger
import click
from ptof.tools import *
from pathlib import Path


config_default_path = os.path.join(Path(os.path.dirname(__file__)), 'resources', 'config.yml')

@click.group()
def cli():
    pass


@cli.command()
@click.option("--config", type=click.Path(), default =config_default_path, help='配置文件的路径')
def pipeline(config: click.Path):
    """
    流程自动化
    """
    config_data = load_config(config)
    if 'demo' in config_data and config_data['demo']:
        print('样例配置文件不可用于实际业务')
        return

    log_init(config_data)
    
    # 获取符合条件的邮件
    emails = fetch_emails(config_data)
    
    if not emails:
        logger.warning("没有需要处理的邮件")
        sys.exit()

    # 下载相关附件    
    files = download_attachments(config_data, emails)
    if not files:
        logger.warning("邮件中没有找到需要处理的附件")
        sys.exit()
    
    upload_files = extract_pdf_to_excel(config_data, files)  # 需要实现具体的PDF解析逻辑
    if not upload_files:
        logger.warning("没有需要上传的文件")
        sys.exit()
    
    upload_to_ftp(config_data, upload_files)


@cli.command()
@click.option("--config", type=click.Path(), default =config_default_path, help='配置文件的路径')
@click.option("--pdf-dir", type=click.Path(), required=True, default ='', help='PDF文件所在目录')
def parse_attachments(config: click.Path, pdf_dir: click.Path):
    """
    解析并上传指定目录下的 pdf 文件
    """

    import glob, re as regex
    config_info = load_config(config)
    if 'demo' in config_info and config_info['demo']:
        print('样例配置文件不可用于实际业务')
        return

    log_init(config_info)

    raw_files = glob.glob(os.path.join(str(pdf_dir), '*' + config_info['attachments']['file_ext']))
    match = regex.compile('^\[([^\[\]]+)\]') # type: ignore
    files = []
    for raw_file in raw_files:
        raw_filename = os.path.basename(raw_file)
        logger.debug('File Name {} From {}', raw_filename, raw_file)
        search = match.search(raw_filename)
        if search:
            logger.debug('Search Result {} From {}', search, raw_file)
            files.append({
                'subject': search[0] + 'From Local Path',
                'dl_file': raw_file,
                'from': 'local@local.com',
                'to': 'local@local.com',
                'attachment_file_name': raw_filename,
            })
        else:
            logger.warning("文件 {} 没有匹配到主题，跳过", raw_file)

    upload_files = extract_pdf_to_excel(config_info, files)  # 需要实现具体的PDF解析逻辑
    if not upload_files:
        logger.warning("没有需要上传的文件")
        sys.exit()
    
    upload_to_ftp(config_info, upload_files)


@cli.command
def show_config_file():
    """
    查看样例配置文件，将输出内容复制并保存为新的 yml 文件，可根据实际业务修改对于配置参数后使用
    """
    try:
        with open(config_default_path, 'r', encoding='utf-8') as f:
            f.seek(11) # 跳过 `demo: true`
            print("#### 请将以下内容复制到新的配置文件中：your/path/to/config.yml or X:\\your\\path\\to\\config.yml\n\n")
            for line in f:
                print(line, end='')
            print('\n\n')
    except FileNotFoundError:
        logger.error('System Error: {}', config_default_path)

__import__ = ["cli"]

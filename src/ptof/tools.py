import os
import yaml
from email.parser import BytesParser
from email.header import decode_header, Header
from email.utils import parseaddr
import imaplib
import ftplib
from pathlib import Path
from datetime import datetime
import re

from ptof.logger import logger, log_init



def load_config(config_file) -> dict:
    # 加载配置文件

    logger.info('从 {} 中加载配置', config_file)
    with open(config_file, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def fetch_emails(config) -> list:
    """
    从IMAP服务器中查找并获取邮件
    """

    # 连接到IMAP服务器
    mail = imaplib.IMAP4_SSL(host=config['imap']['host'])
    mail.login(config['imap']['username'], config['imap']['password'])
    
    # 选择邮件箱（默认inbox）
    mail.select('inbox')
    email_type = 'UNSEEN'
    # email_type = 'ALL'
    # 搜索邮件# UNSEEN / ALL
    status, messages = mail.search(None, email_type, 'FROM "{}"'.format(config['email_criteria']['sender']))
    emails = []
    if status == 'OK':
        for num in messages[0].split():
            status, data = mail.fetch(num, '(RFC822)')
            if status == 'OK':
                email_message = BytesParser().parsebytes(data[0][1])
                emails.append(email_message)
                if email_type != 'ALL':
                    mail.store(num,'+FLAGS','\\Seen')
            else:
                logger.warning('查找邮件失败: {}', status)
    else:
        logger.error('收取邮件失败: {}', status)
    
    mail.close()
    mail.logout()
    return emails

def decode_str(s) -> str:
    value, charset = decode_header(s)[0]
    if charset:
        value = value.decode(charset)
    return value


def download_attachments(config: dict, emails: list) -> list:
    """
    下载PDF附件
    """

    attachment_config = config['attachments']
    save_path = Path(attachment_config['save_path'])
    now_time = datetime.now().strftime('%Y%m%d%H%M%S')
    if not save_path.exists():
        save_path.mkdir(parents=True)
    
    attachment_file_save_paths = []
    for email_msg in emails:
        # 遍历所有附件
        attachment_files = []
        email_meta = {}
        for header in ['From', 'To', 'Subject']:
            value = email_msg.get(header, '')
            if value:
                if header == 'Subject':
                    value = decode_str(value)  # 将主题名称解密
                    email_meta[header.lower()] = value
                else:
                    hdr, addr = parseaddr(value)
                    name = decode_str(hdr)
                    value = u'%s <%s>' % (name, addr)
                    email_meta[header.lower()] = addr

        for part in email_msg.walk():
            file_name = part.get_filename()  # 获取附件名称类型
            contentType = part.get_content_type() #获取数据类型
            mycode = part.get_content_charset()  #获取编码格式
            
            if file_name:
                h = Header(file_name)
                dh = decode_header(h)  # 对附件名称进行解码
                filename = dh[0][0]
                if dh[0][1]:
                    filename = decode_str(str(filename, dh[0][1]))  # 将附件名称可读化
                attachment_files.append(filename)
                attachment_file_ext = filename.split('.')[-1]
                config_file_ext = attachment_config['file_ext'].split('.')[-1]

                if attachment_file_ext.lower() == config_file_ext.lower():
                    data = part.get_payload(decode=True)  # 下载附件
                    download_file = save_path.joinpath(now_time + '_' + filename)
                    with open(download_file, 'wb') as f: # 在当前目录下创建文件，注意二进制文件需要用wb模式打开
                        f.write(data)  # 保存附件
                        attachment_info = email_meta.copy()
                        attachment_info['dl_file'] = download_file
                        attachment_info['attachment_file_name'] = filename
                        attachment_file_save_paths.append(attachment_info)
                    logger.info(f'附件 {filename} 已下载完成')
                else:
                    logger.warning(f'附件 {filename} 后缀 {attachment_file_ext} 和预期 {config_file_ext} 不匹配, 跳过')
            elif contentType == 'text/plain': #or contentType == 'text/html':
                # 输出正文 也可以写入文件
                data = part.get_payload(decode=True)
                content = data.decode(mycode)
                # print('正文：',content)
        logger.info('附件文件名列表: {}', attachment_files)
    
    return attachment_file_save_paths
    


def extract_pdf_to_excel(config: dict, files: list) -> list:
    """
    解析PDF内容并保存到Excel
    """

    logger.debug('files: {}', files)
    handle_files = {}
    for file in files:
        if file['subject'] not in handle_files.keys():
            handle_files[file['subject']] = [ file ]
        else:
            handle_files[file['subject']].append(file)

    logger.debug('dl_files: {}', files)

    parse_config = config['parse_results']
    if not files:
        return []
    
    # 请根据需要实现具体的PDF解析逻辑
    import pandas as pd
    from ptof import pdf_parser
    
    output_files = []
    now_time = datetime.now().strftime('%Y%m%d%H%M')
    
    parser_regex = re.compile('^\[\s*([^\[\]]+)\s*\]') # type: ignore
    for subject, subject_files in handle_files.items():
        search = parser_regex.search(subject)
        if not search:
            logger.warning("邮件主题 {} 中没有找到解析器名称", subject) 
            continue
        parser = pdf_parser.create_parser(search.group(1))
        if not parser:
            logger.warning("主题 {} 的 解析器名称 {} 不支持", subject, search.group(1))
            continue

        parse_files = list(set([ subject_file['dl_file'] for subject_file in subject_files ]))
        attachments = { str(subject_file['dl_file']) : subject_file for subject_file in subject_files }
        
        for sub_file in parse_files:
            
            logger.info('开始解析 来自主题 {} 的文件 {}', subject, sub_file)
            result = parser.do(sub_file)
            if result is not None:
                df = pd.DataFrame(result)
                pdf_file = attachments[str(sub_file)]['attachment_file_name']
                output_file = now_time + '_' + pdf_file.replace('.pdf', '.xlsx').replace('.PDF', '.xlsx')
                output_file = os.path.join(parse_config['output'], parser.name, output_file)
                output_dir = os.path.dirname(output_file)
                if not os.path.exists(output_dir):
                    os.makedirs(output_dir)
                logger.debug('输出文件路径: {}', output_file)
                df.to_excel(output_file, index=False)
                output_files.append(output_file)
                logger.info('主题 {} 的文件 {} 解析结果已保存到 {}'.format(subject, sub_file, output_file))
            else:
                logger.warning('主题 {} 的文件 {} 解析结果为空', subject, sub_file)
    
    
    return output_files


def upload_to_ftp(config: dict, files: list) -> None:
    """
    上传Excel文件到FTP服务器
    """

    upload_config = config['upload_server']
    ftp = ftplib.FTP()
    ftp.connect(host=upload_config['host'], port=upload_config['port'])
    ftp.login(user=upload_config['username'],
              passwd=upload_config['password'])
    encoding = upload_config.get('encoding', 'utf-8')
    ftp.encoding = encoding # TODO: 需确认
    for file in files:
        logger.info('开始上传: {}', file)
        with open(file, 'rb') as f:
            file_name = os.path.basename(file)
            ftp.storbinary(f'STOR {file_name}', f)
        logger.info('上传: {} 完成', file)
    
    ftp.quit()

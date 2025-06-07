from pathlib import Path
from .parser import ParserBase, Optional, List, Dict, Tuple, fitz
from ptof.logger import logger
import re

class PackageListParser(ParserBase):
    name = 'PackageList'

    def do(self, pdf_file: str | Path, *args, **kwargs) -> Optional[List[Dict]]:
        table_sniff_str = re.compile('^([\S]+\s*)?Item')  # type: ignore # 表格标识字符串
        if not table_sniff_str:
            logger.error('未提供表格标识字符串，请检查配置')
            return None
        with fitz.open(pdf_file) as pdf:  # 使用 PyMuPDF 打开 PDF 文件
            flags = fitz.TEXT_PRESERVE_LIGATURES | fitz.TEXT_PRESERVE_WHITESPACE | fitz.TEXT_PRESERVE_SPANS
            page_text = '\n'.join([page.get_text('text', sort=True, flags=flags) for page in pdf.pages()])  # 提取第一页的文本内容
            logger.debug('PDF内容: \n{}', page_text)
            (po_table, line_offset) = self.get_table(page_text, table_sniff_str, line_offset=0)
            po = self.format_table(po_table)  # 格式化表格信息
            # (box_table, line_offset) = self.get_table(page_text, 'Box ID', line_offset=line_offset)
            # box = self.format_table(box_table)  # 格式化表格信息
            po_no = self.get_po_no(page_text)
            lot_no = po['rows'][0][2].split('/')[0].strip() if po['rows'] else ''  # 取第一行的Lot No
            wafer_ids = self.get_wafer_id(page_text)
            extracted_data = {
                'Date': self.get_date(page_text),
                'Cust._Code': '', # N/A
                'DF_Code': self.get_df_code(page_text),
                'PO_No': po_no,
                'Device_Code': self.get_device_code(page_text),
                'Device': po['rows'][0][1].split('/')[1].strip() if po['rows'] else '', #  Customer Device ID
                'OSAT_Device': po['rows'][0][1].split('/')[0].strip() if po['rows'] else '',  # Material
                'OSAT.Lot_no': lot_no,
                'Lot_No': lot_no,
                'Lot_Type': po_no[4] if po_no else '',  # 如果没有PO No 第 5 字符则为 N/A
                'Manufacturing_Mode': '', # N/A
                'BIN': '', # N/A
                'Good_Qty': self.get_good_qty(page_text),
                'Reject_Qty': '', # N/A
                'Datecode': '', # N/A
            }
            logger.debug('提取到的数据: {}', extracted_data)
            parse_results = []
            fields = self.field_names()
            for wafer_id in wafer_ids or []:
                tmp = extracted_data.copy()  # 复制提取到的数据
                tmp['Wafer_ID'] = wafer_id.strip()  # 去掉前后的空格
                data = { v: tmp[k] for k, v in fields.items() }
                parse_results.append(data)
            logger.debug('数据规整后: {}', parse_results)
            return parse_results if parse_results else None

        return None

    def format_table(self, table_info: Dict[str, List]) -> Dict[str, List[str]]:
        """
        格式化表格信息，将表头和行数据分离
        """
        formatted_table = {
            'headers': [],
            'rows': []
        }
        header_offsets = table_info.get('header_offsets', [])
        header_lines = table_info.get('headers', [])
        header_keys = []
        
        header_line = header_lines[0] if header_lines else ''
        start = 0
        for end in header_offsets[1:]:
            if end > len(header_line):
                break
            header_keys.append(header_line[start:end].strip())
            start = end
        header_keys.append(header_line[start:].strip())

        end_word_regex = r'\W$'
        for header_line_ in header_lines[1:]:
            start = header_offsets[0]
            for offset_idx, end in enumerate(header_offsets[1:]):
                try:
                    while header_line_[start - 1] != ' ' and end > start:
                        start -= 1
                except IndexError:
                    pass
                next_header = header_line_[start:end].strip()
                start = end
                logger.debug('处理新的表头: {}, {}, {} => {}', next_header, header_line_, offset_idx, header_keys[offset_idx])
                if next_header:
                    if not re.search(end_word_regex, header_keys[offset_idx]):
                        header_keys[offset_idx] += '\t' + next_header
                    else:
                        header_keys[offset_idx] += next_header
        
        [formatted_table['headers'].extend(header.split('\t'))  for header in header_keys]

        for table_row in table_info.get('rows', []):
            row_data = []
            start = 0
            for end in header_offsets[1:]:
                if end > len(table_row):
                    break
                while table_row[end - 1] != ' ' and end > start:
                    end -= 1
                row_data.append(table_row[start:end].strip())
                start = end
            row_data.append(table_row[start:].strip())
            if row_data[0] == '':
                new_row_data = row_data[1:]
                if str(new_row_data[0]).find(':') != -1:
                    formatted_table['rows'].append(new_row_data)
                else:
                    formatted_table['rows'][-1].extend(new_row_data)  # 如果是续行，则合并到上一行
            else:
                formatted_table['rows'].append(row_data)

        logger.debug('格式化后的表头: {}', formatted_table['headers'])
        logger.debug('格式化后的行: {}', formatted_table['rows'])
        return formatted_table

    def get_table(self, page_text, table_sniff_str: str | re.Pattern, line_offset = 0) -> Tuple[Dict[str, List[str]], int]:
        page_text_lines = page_text.splitlines()
        table_info = {
            'header_offsets': [],
            'headers': [],
            'rows': [],
        }

        # 解析表头
        line_offset_raw = line_offset
        table_sniff_size = None
        for (line_num, line) in enumerate(page_text_lines[line_offset:]):
            if not line.strip():
                continue
            logger.debug('type of sniff str: {}', type(table_sniff_str))
            if isinstance(table_sniff_str, str):
                logger.info('精准嗅探: {}', table_sniff_str)
                if line.startswith(table_sniff_str):
                    table_sniff_size = len(table_sniff_str)
                    logger.debug('找到包含 "{}" 的行: {}', table_sniff_str, line)
                    table_info['headers'].append(line)  # 添加当前行到表格行
                    line_offset = line_offset_raw + line_num  # 记录当前行号
                    continue  # 继续检查下一行
            elif isinstance(table_sniff_str, re.Pattern):
                logger.info('模糊嗅探: {}', table_sniff_str)
                if matched := table_sniff_str.match(line):
                    logger.info('matched: {}', matched.groups())
                    table_sniff_size = len(matched[0])
                    logger.debug('找到包含 "{}" 的行: {}', table_sniff_str, line)
                    table_info['headers'].append(line)  # 添加当前行到表格行
                    line_offset = line_offset_raw + line_num  # 记录当前行号
                    continue  # 继续检查下一行
            
            if len(table_info['headers']) > 0 and table_sniff_size:
                if not line.startswith(' ' * table_sniff_size):
                    logger.debug('找到不以空格开头的行，结束表格提取: {}', line)
                    line_offset = line_offset_raw + line_num  # 记录当前行号
                    break
                logger.debug('找到表格行: {}', line)
                table_info['headers'].append(line)  # 添加当前行到表格行
                continue # 继续检查下一行
        
        logger.debug('{}表表头: {}, Line Offset: {}', table_sniff_str, table_info['headers'], line_offset)
        

        if not table_sniff_size:
            logger.warning("没有检测的表， 检测器：{}", table_sniff_str)
            return ({}, 0)
        
        # 解析表格行
        empty_line_count = 0
        line_offset_raw = line_offset
        for (line_num, line) in enumerate(page_text_lines[line_offset:]):
            logger.debug('{}表处理行: {}', table_sniff_str, line)
            if not line.strip():
                empty_line_count += 1
                if empty_line_count <= 1:  # 允许最多一行空行
                    continue  # 跳过空行
                
                line_offset = line_offset_raw + line_num  # 记录当前行号
                break  # 超过一行空行，结束表格提取
            empty_line_count = 0  # 重置空行计数
            if line.startswith('_' * table_sniff_size): # 检测到分隔线
                logger.debug('检测到分隔线，结束表格提取')
                line_offset = line_offset_raw + line_num  # 记录当前行号
                break
            
            logger.debug('添加行到{}表: {}', table_sniff_str, line)
            table_info['rows'].append(line)  # 添加当前行到表格行

        logger.debug('{}表行: {}', table_sniff_str, table_info['rows'])

        # 处理表头行，提取字段位置
        header_line = table_info['headers'][0] if table_info['headers'] else ''
        if header_line.strip():
            regex = r'\s{3}([\S])'
            handler_header_line = re.sub(regex, r' __\1', header_line)  # 将多个空格替换为单个空格
            headers = handler_header_line.split('__')
            header_offsets = [0]
            for idx, header in enumerate(headers):
                if idx == len(headers) - 1:  # 最后一个字段
                    continue
                headers[idx] = header + ' ' * 2 # 保留两个空格
                header_offsets.append(len(headers[idx]) + header_offsets[-1])  # 计算每个字段的结束位置
            table_info['header_offsets'] = header_offsets
            logger.debug('提取到的字段位置: {}', table_info['header_offsets'])
        

        return (table_info, line_offset)

    def field_names(self) -> Dict[str, str]:
        """
        返回字段名称映射
        入库日期	Cust. Code	DF Code	PO No	Device Code	Device	OSAT Device	OSAT.Lot no	Lot No	Wafer ID	Lot Type	加工模式	BIN	Good Qty	Reject Qty	Datecode
        """
        return {
            'Date': '入库日期',
            'Cust._Code': 'Cust. Code',
            'DF_Code': 'DF Code',
            'PO_No': 'PO No',
            'Device_Code': 'Device Code',
            'Device': 'Device',
            'OSAT_Device': 'OSAT Device',
            'OSAT.Lot_no': 'OSAT.Lot no',
            'Lot_No': 'Lot No',
            'Wafer_ID': 'Wafer ID',
            'Lot_Type': 'Lot Type',
            'Manufacturing_Mode': '加工模式',
            'BIN': 'BIN',
            'Good_Qty': 'Good Qty',
            'Reject_Qty': 'Reject Qty',
            'Datecode': 'Datecode',
        }
    
    def get_device_code(self, _) -> Optional[str]:
        return 'SDC100.01.02'  # 固定值
    
    def get_df_code(self, _) -> Optional[str]:
        return 'DF_SH'  # 固定值

    def get_good_qty(self, page_text) -> Optional[str]:
        regex = r'TOTAL QUANTITY\s*(\d+)\s*PC'
        if match := re.search(regex, page_text):
            good_qty = match.group(1).strip()
            logger.debug('提取到的Good Qty: {}', good_qty)
            return good_qty
        else:
            logger.debug('未提取到Good Qty')
            return None
        
    def get_po_no(self, page_text) -> Optional[str]:
        regex = r'CTM ORDER NO\.\s*(\S+)'
        if match := re.search(regex, page_text):
            po_no = match.group(1).strip()
            logger.debug('提取到的PO No: {}', po_no)
            return po_no.removeprefix('CTM ORDER NO.').strip()  # 去掉前面的 'CTM ORDER NO.' 字符串
        else:
            logger.debug('未提取到PO No')
            return None


    def get_date(self, page_text) -> Optional[str]:
        regex = r'DATE\s+\d{4}-\d{2}-\d{2}'
        if match := re.search(regex, page_text):
            date = match.group(0).strip()
            logger.debug('提取到的日期: {}', date)
            return date.replace('DATE', '').strip()  # 去掉前面的 'DATE' 字符串
        else:
            logger.debug('未提取到日期')
            return None
    
    def get_wafer_id(self, page_text) -> Optional[List]:
        regex = r'Wafer ID:\s*(#)?\s*(\d+,)*(\d+)\s*'
        if match := re.search(regex, page_text):
            wafer_id = match.group(0).strip()
            logger.debug('提取到的Wafer ID: {}', wafer_id)
            return wafer_id.replace('Wafer ID:', '').strip().replace('#', '').split(',')
        else:
            logger.debug('未提取到Wafer ID')
            return None
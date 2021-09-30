# -*- coding: utf-8 -*-
# @Time   : 2021/6/27 21:54
# @Author : zp
# @Python3.7

import shutil
import requests
import time
import re
import os
import urllib3
from urllib.parse import urljoin
from loguru import logger
from Crypto.Cipher import AES
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class M3u8VideoDownloader():
    headers = {
        'Accept': '*/*',
        'Accept-Encoding': 'gzip, deflate, br',
        'Accept-Language': 'zh-CN,zh;q=0.9',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/78.0.3904.108 Safari/537.36',
    }

    def __init__(self, m3u8_url, download_path='video', video_name='xhp', is_del_clip=True,
                 dec_func=None, m3u8_content_plaintext=None):
        """
        :param m3u8_url: m3u8链接
        :param download_path: 下载路径
        :param video_name: 视频名称（不能出现括号）
        :param is_del_clip: 合并视频完成后是否删除ts文件
        :param dec_func: m3u8内容解密函数（内容被加密时可传入解密函数，或直接将解密后的明文内容传递给参数m3u8_content_plaintext）
        :param m3u8_content_plaintext: 已解密的m3u8明文内容
        :param cache_path:默认ts下载目录
        """
        self.m3u8_url = m3u8_url
        self.download_path = download_path
        self.video_name = video_name
        self.is_del_clip = is_del_clip
        self.dec_func = dec_func
        self.m3u8_content_plaintext=m3u8_content_plaintext
        self.video_name_suffix = '.ts'
        self.cache_path = os.path.join(self.download_path, 'tmp')
        self.key_url = None
        self.key = None
        self.iv = None
        self.decipher = None
        self.ts_list = []

    def fetch(self,url,binary=False):
        """
        :param url:
        :param binary: True则下载文件
        :return:
        """
        for retry in range(5):
            try:
                resp = requests.get(url, headers=self.headers, timeout=30, verify=False)
                status_code = resp.status_code
                if status_code != 200:
                    raise Exception
                if binary:
                    return resp.content
                return resp.content.decode()
            except Exception as e:
                logger.error(f"http fetch error {url} retrying {retry+1}")
                time.sleep(5)
        raise Exception

    def get_m3u8_content(self):
        logger.info(f'M3U8链接：{self.m3u8_url}')
        m3u8_content = self.fetch(self.m3u8_url)
        # 有反爬时,m3u8文件是加密的
        if self.dec_func:
            logger.info("解密m3u8文件")
            m3u8_content = self.dec_func(m3u8_content)
        # 没这个你敢说你是m3u8
        if '#EXTM3U' not in m3u8_content:
            raise Exception(f'错误的M3U8信息，请确认链接是否正确：{self.m3u8_url}<{m3u8_content}>')
        # 不同分辨率:请求index.m3u8再解析不同分别率的m3u8,再请求子muu8(默认选第一个)
        if '#EXT-X-STREAM-INF' in m3u8_content:
            m3u8_url_list = [line for line in m3u8_content.split('\n') if line.find('.m3u8') != -1]
            if len(m3u8_url_list) > 1:
                logger.info(f'发现{len(m3u8_url_list)}个m3u8地址：{m3u8_url_list}')
            self.m3u8_url = urljoin(self.m3u8_url, m3u8_url_list[0])
            return self.get_m3u8_content()
        return m3u8_content

    def parse_m3u8_info(self, m3u8_content):
        all_lines = m3u8_content.strip('\n').split('\n')
        for index, line in enumerate(all_lines):
            if '#EXT-X-KEY' in line:
                # 避免重复解析key与iv
                if not (self.key_url and self.iv):
                    method, key_url_part, self.iv = self.parse_ext_x_key(line)
                    self.key_url = urljoin(self.m3u8_url, key_url_part)
                    logger.info(f'ts已加密：{method}  Key地址:{key_url_part}')
            # ts列表
            if not line.startswith('#') or line.startswith('http') or line.endswith('.ts'):
                ts_link = urljoin(self.m3u8_url,line)
                logger.info(f"find ts link {ts_link}")
                self.ts_list.append(ts_link)

    @staticmethod
    def parse_ext_x_key(ext_x_key: str) -> (str, str, bytes):
        """解析#EXT-X-KEY中的key链接与iv"""
        ret = re.search(r'METHOD=(.*?),URI="(.*?)"(?:,IV=(\w+))?', ext_x_key)
        method, key_url, iv = ret.groups()
        iv = iv.replace('0x', '')[:16].encode() if iv else b''
        return method, key_url, iv

    def get_key(self):
        try:
            self.key = self.fetch(self.key_url, binary=True)
        except Exception as e:
            raise Exception(f'获取key失败({self.key_url})：{repr(e)}')
        logger.info(f'key解析已完成：{self.key}  iv:{self.iv or "无"}')

    def init_decipher(self):
        self.decipher = AES.new(self.key, AES.MODE_CBC, self.iv or self.key[:16])

    def download_all_videos(self):
        if not os.path.exists(self.download_path):
            os.makedirs(self.download_path)

        logger.info(f'视频保存目录：{self.download_path}')

        if not os.path.exists(self.cache_path):
            os.makedirs(self.cache_path)

        logger.info(f'即将开始下载视频：{self.video_name}{self.video_name_suffix}')
        start_time = int(time.time())

        for idx,ts_link in enumerate(self.ts_list):
            logger.info(f'开始下载ts {idx} {ts_link}')
            data = self.fetch(ts_link,binary=True)
            if self.key_url:
                logger.info(f'开始解密ts {idx} {ts_link}')
                data = self.decode_video(data)
            with open(self.cache_path+f"/{idx}.ts",'wb+') as f:
                f.write(data)
            logger.info(f'保存ts {idx} {ts_link}')

        spend_time = int(time.time()) - start_time
        logger.info(f'下载{len(self.ts_list)}个ts耗时：{spend_time}秒')

    def decode_video(self, data):
        if self.decipher is not None:
            try:
                data = self.decipher.decrypt(data)
            except Exception as e:
                raise Exception(f'数据解密失败：{repr(e)}<{len(data)}>')
        return data

    def merge_video_file(self):
        file_list = os.listdir(self.cache_path)
        file_list.sort(key= lambda x:int(x[:-3]))
        with open(self.download_path+f"/{self.video_name}{self.video_name_suffix}", 'wb+') as fw:
            for i in range(len(file_list)):
                infile=open(os.path.join(self.cache_path,file_list[i]), 'rb')
                fw.write(infile.read())
                infile.close()
        logger.info(f"合并为{self.video_name}{self.video_name_suffix}")
        shutil.rmtree(self.cache_path)
        logger.info("清理tmp")

    def start(self):
        try:

            # 1.获取m3u8内容
            m3u8_content = self.m3u8_content_plaintext or self.get_m3u8_content()

            # 2.解析m3u8内容
            self.parse_m3u8_info(m3u8_content)

            if not self.ts_list:
                logger.error('解析未发现有效的视频片段')
                return

            # 3.如果存在加密，获取解密key，并初始化解密器
            if self.key_url:
                self.get_key()
                self.init_decipher()

            # 4.下载视频
            self.download_all_videos()

            # 5.合并视频
            self.merge_video_file()

        except Exception as e:
            logger.error(e)

if __name__ == '__main__':
    #ts aes加密
    m3u8_url = "https://vod3.bdzybf3.com/20210617/DmV0P4zD/1000kb/hls/index.m3u8?skipl=1"
    tool = M3u8VideoDownloader(m3u8_url=m3u8_url)
    tool.start()
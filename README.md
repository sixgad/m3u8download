# 开箱即用的m3u8下载器

# 使用方法
拉取代码

> git clone https://github.com/sixgad/m3u8download.git

安装依赖包

> pip install -r requirements.txt

修改download.py中待下载视频的m3u8链接

>  m3u8_url = "***"
>
>   tool = M3u8VideoDownloader(m3u8_url=m3u8_url)
>
>   tool.start()

运行

> python download.py

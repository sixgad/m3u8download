# 开箱即用的m3u8下载器

越来越多的视频网站采用*HLS*(基于HTTP的自适应码率流媒体传输协议)视频流加载和播放视频资源，包括一个m3u8的索引文件，TS媒体分片文件和key加密串文件(不一定全有)，
以前打开network-media就能找到.mp4下载链接的日子一去不复返。从零开发一个m3u8通用下载器，满足动漫和小h片的下载需求。

博客地址：https://paker.net.cn/article?id=23

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

结果

> 视频默认保存在video下，那个大的ts文件就是合并之后的视频，可直接播放（也可使用ffmpeg将视频格式ts转mp4）

todo:版本v2 多线程 or asyncio
todo:暂未提供ts转mp4的功能

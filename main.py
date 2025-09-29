

import time
import os
import sys
import random
import math
import logging

"""
需要的包：playwright，opencv-python，pynput
"""
from playwright.sync_api import sync_playwright, Playwright, Browser, Page, BrowserContext, ElementHandle
import cv2
from pynput.mouse import Controller, Button

# log
LOGDIR = "log"
if True:
    os.makedirs(LOGDIR, exist_ok=True)
    logger = logging.getLogger("my_logger")
    logger.setLevel(logging.DEBUG)
    file_handler = logging.FileHandler(
        filename=os.path.join(LOGDIR, "jigsaw_pass.py.log"),
        mode="w",
        encoding="utf8"
    )
    file_handler.setLevel(logging.INFO)
    stream_handler = logging.StreamHandler(stream=sys.stdout)
    stream_handler.setLevel(logging.DEBUG)
    file_handler_fmt = logging.Formatter(
        fmt="%(asctime)s - %(levelname)s - %(message)s"
    )
    stream_handler_fmt = logging.Formatter(
        fmt="%(asctime)s - %(levelname)s - %(message)s"
    )
    file_handler.setFormatter(file_handler_fmt)
    stream_handler.setFormatter(stream_handler_fmt)

    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)


mouse = Controller()


class JigsawPass:
    def __init__(self, url: str, slide_css_selector: str, slide_img_css_selector: str, background_css_selector: str):
        """
        识别滑块验证码，框架为playwright，可改用selenium
        :param url: 滑块验证码网页url，输入url便于识别浏览器要操作的标签
        :param slide_img_css_selector: 滑块图片css-selector定位，小图片
        :param slide_css_selector: 滑块css-selector定位，鼠标拖动的滑块
        :param background_css_selector: 滑块整个背景css-selector定位
        """
        self.url = url
        self.slide_css_selector = slide_css_selector
        self.slide_img_css_selector = slide_img_css_selector
        self.background_css_selector = background_css_selector

        self.browser: Browser = None  # playwright 的浏览器对象
        self.port = 9225  # playwright使用的端口，playwright需要指定--user-data-dir才能使用
        self.page: Page = None  # 要操作的page

    def __connect_browser(self):
        r"""
        连接playwright浏览器，playwright需要指定--user-data-dir才能使用，
        浏览器得使用命令打开，例如：start chrome --remote-debugging-port=9225 --user-data-dir="C:\chrome_data"
        :return:
        """
        logger.info(f"连接浏览器")
        self.browser = sync_playwright().start().chromium.connect_over_cdp(f"http://localhost:{self.port}")

    @staticmethod
    def __trans_host_to_main(url: str):
        """
        将域名转为主域名
        :param url:
        :return:
        """
        url = url.replace("https://", "")
        url = url.replace("http://", "")
        ans = url[:url.find("/")]
        return ans

    def __get_jigsaw_page(self):
        """
        获取要pass 滑块的标签页
        :return:
        """
        page_ans = None
        flag = False
        for context in self.browser.contexts:
            if flag:
                break
            for page in context.pages:
                # url 转换为 主要域名 然后作对比
                if self.__trans_host_to_main(page.url) == self.__trans_host_to_main(self.url):
                    flag = True
                    self.page = page
                    break
        if self.page is None:
            raise Exception("没有找到要pass的滑块浏览器标签")

    @staticmethod
    def __my_sleep_us(us: int):
        # 1s = 1000 ms
        # 1ms = 1000 us
        # 1us = 1000 ns
        s, us = divmod(us, 1000000)
        time.sleep(s)
        left_ns = us * 1000
        time0 = time.time_ns()
        time1 = time.time_ns()
        while time1 - time0 < left_ns:
            time1 = time.time_ns()
        # print(time1 - time0)

    def __get_element_pos(self, element: ElementHandle = None):
        """
        获取元素在屏幕中的位置
        :return:
        """
        # 获取浏览器窗口的位置
        screen_x = int(self.page.evaluate("window.screenX"))
        screen_y = int(self.page.evaluate("window.screenY"))
        print("获取浏览器窗口的位置", screen_x, " ", screen_y)
        # left = int(self.page.evaluate("h1"))
        pos = element.bounding_box()
        # pos = element.bounding_box()
        real_pos_x = pos['x'] + screen_x + pos['width']//2
        real_pos_y = pos['y'] + screen_y + pos['height']//2 + 100  # 100是浏览器的标题栏，一般为100 view
        pos_x = pos['x']
        pos_y = pos['y']
        print("元素位置：", pos)
        print("real pos:", real_pos_x, " ", real_pos_y)
        return pos_x, pos_y, int(pos['width']), int(pos['height']), real_pos_x, real_pos_y

    @staticmethod
    def __write_png_to_disk(filename, content: bytes):
        """
        图片写入硬盘
        :param filename: 文件名
        :param content: 二进制
        :return:
        """
        with open(filename, mode="wb") as f:
            f.write(content)
        return filename

    def __move_with_a(self, to_x, current_v, a):
        """
        加速度a移动
        :return:
        """
        # 获取当前位置
        now_cursor_x, now_cursor_y = mouse.position
        unit = 1 if to_x - now_cursor_x > 0 else -1
        y_shake = 0
        sleep_factor = 8400  # sleep 因子 ，整10倍
        while abs(now_cursor_x - to_x) >= 1:
            for _ in range(current_v):
                rand = random.randint(0, 100)
                if rand % 7 == 0:
                    y_shake = random.randint(-1, 1)
                else:
                    y_shake = 0
                mouse.position = (now_cursor_x+unit, now_cursor_y+y_shake)
                now_cursor_x, now_cursor_y = mouse.position
                if now_cursor_x >= to_x:
                    return current_v
                self.__my_sleep_us(random.randint(sleep_factor//current_v, (sleep_factor + 0.1*sleep_factor)//current_v))
            current_v = current_v + a
            if current_v <= 0:
                current_v = 1
            sleep_time = random.randint(sleep_factor, (sleep_factor+sleep_factor))
            self.__my_sleep_us(sleep_time)
            print("当前速度：", current_v)
            now_cursor_x, now_cursor_y = mouse.position
        return current_v

    def __move_to_x(self, from_x, from_y, to_x):
        # 模拟x轴移动
        # 加速度由正到负
        a = 2
        v = self.__move_with_a(to_x=from_x + int((to_x - from_x)*0.47), current_v=0, a=a)
        # 网易易盾获取滑块和滑块图片距离的差值然后做补偿
        # sub_distance = self.page.query_selector(self.slide_css_selector).bounding_box()['x'] - self.page.query_selector(self.slide_img_css_selector).bounding_box()['x']
        # print("差值：", sub_distance)
        # self.__move_with_a(to_x=to_x+sub_distance, current_v=v, a=-a)

        self.__move_with_a(to_x=to_x, current_v=v, a=-a)

    def smooth_move(self, to_x, to_y, duration=2.0, steps=800):
        from_x, from_y = mouse.position
        dx = to_x - from_x
        dy = to_y - from_y

        for step in range(steps + 1):
            # 使用余弦插值实现缓入缓出效果（ease-in-ease-out）
            t = step / steps
            ease_t = 0.5 * (1 - math.cos(math.pi * t))  # 从0平滑到1

            new_x = from_x + dx * ease_t
            new_y = from_y + dy * ease_t

            mouse.position = (int(new_x), int(new_y))
            self.__my_sleep_us(int((duration / steps)*1000000))

    def __move_to_x_human(self, from_x, from_y, to_x):
        # 模拟人类移动
        print("模拟人类移动", from_x, " ", from_y)
        self.smooth_move(from_x, from_y, duration=1, steps=100)
        mouse.press(Button.left)
        self.__my_sleep_us(random.randint(111110, 2000000))
        self.__move_to_x(from_x, from_y, to_x)
        # self.smooth_move(to_x, from_y, duration=1, steps=100)  # 方法2，也能成功，但成功率不高
        self.__my_sleep_us(random.randint(111100, 1000000))
        mouse.release(Button.left)

    def __slide_pass(self):
        """
        识别滑块
        :return:
        """
        slide_ele = self.page.query_selector(self.slide_css_selector)
        slide_img_ele = self.page.query_selector(self.slide_img_css_selector)
        background_ele = self.page.query_selector(self.background_css_selector)
        # slide_ele.hover()
        # input()
        slide_img_path = self.__write_png_to_disk("slide_img.png", slide_img_ele.screenshot())
        background_path = self.__write_png_to_disk("background.png", background_ele.screenshot())
        slide_x, slide_y, _, _, slide_real_x, slide_real_y = self.__get_element_pos(slide_ele)
        slide_img_x, slide_img_y, slide_img_width, slide_img_height, slide_img_real_x, slide_img_real_y = self.__get_element_pos(slide_img_ele)
        background_x, background_y, background_width, background_height, background_real_x, background_real_y = self.__get_element_pos(background_ele)

        have_dragged_distance = int(slide_img_x - background_x)  # 相当于网页已经拖动后的距离

        slide_img_canny = cv2.imread(slide_img_path, cv2.COLOR_BGR2GRAY)
        # print([slide_img_width, slide_img_height])
        slide_img_canny = cv2.resize(slide_img_canny, (int(slide_img_width), int(slide_img_height)), interpolation=cv2.INTER_AREA)
        slide_img_canny = cv2.Canny(slide_img_canny, 120, 200)
        background_canny = cv2.imread(background_path, cv2.COLOR_BGR2GRAY)
        background_canny = cv2.resize(background_canny, (int(background_width), int(background_height)), interpolation=cv2.INTER_AREA)
        background_canny = cv2.Canny(background_canny, 120, 200)
        cv2.imwrite("background_canny.png", background_canny)
        background_canny = background_canny[:, have_dragged_distance + slide_img_width + 3:]

        cv2.imwrite("slide_img_canny.png", slide_img_canny)
        # background_canny
        canny_ans = cv2.matchTemplate(background_canny, slide_img_canny, cv2.TM_CCOEFF_NORMED)
        _, _, _, max_loc = cv2.minMaxLoc(canny_ans)
        # print(max_loc)

        cv2.rectangle(background_canny,(max_loc[0],max_loc[1]),(max_loc[0]+slide_img_width, max_loc[1]+slide_img_height),(255,255,0))
        # 创建窗口并显示图像
        # cv2.namedWindow('Image', cv2.WINDOW_NORMAL)
        # cv2.imshow('Image', background_canny)
        cv2.imwrite("background_canny2.png", background_canny)
        # 按下任意键关闭窗口
        # cv2.waitKey(0)
        #
        # # 释放所有窗口
        # cv2.destroyAllWindows()
        need_drag_distance = max_loc[0] + slide_img_width + 3
        print("需要移动的距离：", need_drag_distance)
        self.__move_to_x_human(from_x=slide_real_x, from_y=slide_real_y, to_x=slide_real_x + need_drag_distance)
        # self.__move_to_x_human(from_x=slide_x, from_y=slide_y, to_x=slide_real_x + need_drag_distance)

    def main_work(self):
        time.sleep(3)
        self.__connect_browser()
        self.__get_jigsaw_page()
        max_tries = 3  # 重试次数
        for i in range(max_tries):
            # css = self.slide_img_css_selector + ":not([style*='display: none']):not([style*='display:none'])"
            slide_img_ele = self.page.query_selector(self.slide_img_css_selector)
            try:
                a = slide_img_ele.bounding_box()
            except:
                a = None
            print(a)
            # input()
            if a is None:
                print("没有滑块，可能已经成功")
                break
            self.__slide_pass()
            time.sleep(2)


if __name__ == '__main__':
    # 滑块验证码浏览器标签的url，用于playwright寻找网页标签
    url = "http://passport.jd.com/new/login.aspx?Return"
    # 滑块的css定位，也可以写成滑块图片的css定位，如果滑块图片也能拖动的话
    slide_css_selector = "#JDJRV-wrap-loginsubmit > div > div > div > div.JDJRV-slide-bg > div.JDJRV-slide-inner.JDJRV-slide-btn"
    # 滑块图片的css定位
    slide_img_css_selector = "#JDJRV-wrap-loginsubmit > div > div > div > div.JDJRV-img-panel.JDJRV-click-bind-suspend > div.JDJRV-img-wrap > div.JDJRV-smallimg > img"
    # 滑块背景的css定位
    background_css_selector = "#JDJRV-wrap-loginsubmit > div > div > div > div.JDJRV-img-panel.JDJRV-click-bind-suspend > div.JDJRV-img-wrap > div.JDJRV-bigimg > img"

    # 网易易盾滑块验证码
    url = "https://dun.163.com/trial/sense"
    slide_css_selector = "body > main > div.g-bd > div > div.g-mn2 > div.m-tcapt > div.tcapt-type__container > div.tcapt-type__item.active > div.tcapt_item.is-left > div > div.tcapt_content > div.u-fitem.u-fitem-capt > div > div > div.yidun_classic-container > div > div > div.yidun_control > div.yidun_slider.yidun_slider--hover"
    slide_img_css_selector = "body > main > div.g-bd > div > div.g-mn2 > div.m-tcapt > div.tcapt-type__container > div.tcapt-type__item.active > div.tcapt_item.is-left > div > div.tcapt_content > div.u-fitem.u-fitem-capt > div > div > div.yidun_classic-container > div > div > div.yidun_panel > div > div.yidun_bgimg > img.yidun_jigsaw"
    background_css_selector = "body > main > div.g-bd > div > div.g-mn2 > div.m-tcapt > div.tcapt-type__container > div.tcapt-type__item.active > div.tcapt_item.is-left > div > div.tcapt_content > div.u-fitem.u-fitem-capt > div > div > div.yidun_classic-container > div > div > div.yidun_panel > div > div.yidun_bgimg"

    # 抖音抖店
    url = "https://rmc.bytedance.com/verifycenter/captcha/v2?"
    slide_css_selector = "#vc_captcha_box > div > div > div.captcha-slider.captcha_verify_slide--button > div > div.dragger-box > div.dragger-item > div"
    slide_img_css_selector = "#captcha-verify_img_slide"
    background_css_selector = "#captcha_verify_image"

    # 有赞商家平台测试
    url = "https://account.youzan.com/login"
    slide_css_selector = ".slide-captcha-container:not(.hide) #slideBlockRef"
    slide_img_css_selector = ".slide-captcha-container:not(.hide) #smallImg"
    background_css_selector = ".slide-captcha-container:not(.hide) #slidePicRef > div.bg"

    jigsaw_pass = JigsawPass(url, slide_css_selector, slide_img_css_selector, background_css_selector)
    jigsaw_pass.main_work()


import logging
import os
import json
import shutil
import psutil
import platform
import subprocess

from PIL import Image, ImageDraw

from dearpygui import dearpygui as dpg

import pt

pfm_version = "b-2"
pfm_pre_version = True

pfm_logger = logging.getLogger("positive_file_manager_logger")
main_font_path = os.path.join(
    os.path.dirname(__file__),
    "..",
    "data",
    "font",
    "Noto_Sans_TC",
    "static",
    "NotoSansTC-Regular.ttf",
)

folder_icon_path = os.path.join(
    os.path.dirname(__file__), "..", "data", "icons", "folder.png"
)

file_icon_path = os.path.join(
    os.path.dirname(__file__), "..", "data", "icons", "file.png"
)

selected_rectangle_path = os.path.join(
    os.path.dirname(__file__), "..", "data", "icons", "selected_rectangle.png"
)

config_path = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "data", "config.json")
)

path = os.getcwd()


class FileManager:
    def __init__(self) -> None:
        global config_path
        #
        self.config: dict = {}
        self.init_config()
        if os.path.exists(config_path) is True:
            self.load_config()
        self._config_save_to_file()
        #
        self.load_icons()
        self.create_notification_window()
        self.create_dir_list()
        self.create_control_center()
        self.create_path_viewer()
        self.dir_list_ids = []
        self.dir_list_pictures = []
        self._copy_dir: str | None = None
        self.selected_dir: str | None = None
        self.create_config_window()
        self.refresh_dir_list()
        self._config_refresh()
        #

    def load_config(self) -> None:
        with open(config_path, "r", encoding="utf-8") as f:
            tmp = json.load(f)
        for key in tmp:
            if key in [
                "selected_rectangle_color_fill",
                "selected_rectangle_color_outline",
            ]:
                self.config[key] = tuple(tmp[key])
            else:
                self.config[key] = tmp[key]
        pfm_logger.debug(f"設定：{self.config}")
        return None

    def init_config(self):
        self.config = {
            "selected_rectangle_color_fill": (99, 118, 255, 255),
            "selected_rectangle_color_outline": (99, 118, 255, 255),
            "selected_rectangle_color_width": 2,
        }

    def load_icons(self):
        global file_icon_path, folder_icon_path, selected_rectangle_path
        # 動態繪製
        rectangle_draw_img = Image.new("RGBA", (200, 200), (255, 255, 255, 0))
        rectangle_draw_imgdraw = ImageDraw.Draw(rectangle_draw_img)
        rectangle_draw_imgdraw.rectangle(
            [(0, 0), (10, 10)],
            self.config["selected_rectangle_color_fill"],
            self.config["selected_rectangle_color_outline"],
            self.config["selected_rectangle_color_width"],
        )
        rectangle_draw_img.save(selected_rectangle_path)
        #
        with dpg.texture_registry(tag="icon_reg"):
            width, height, channels, data = dpg.load_image(folder_icon_path)
            dpg.add_static_texture(
                width=width,
                height=height,
                default_value=data,
                tag="folder_icon_texture",
            )
            width, height, channels, data = dpg.load_image(file_icon_path)
            dpg.add_static_texture(
                width=width,
                height=height,
                default_value=data,
                tag="file_icon_texture",
            )
            width, height, channels, data = dpg.load_image(selected_rectangle_path)
            dpg.add_static_texture(
                width=width,
                height=height,
                default_value=data,
                tag="selected_rectangle_texture",
            )

    def create_dir_list(self):
        width = dpg.get_viewport_width()
        height = dpg.get_viewport_height() - 150
        pfm_logger.debug(f"主視窗寬：{width}，主視窗高：{height}")
        with dpg.window(
            width=width,
            height=height,
            pos=[0, 150],
            no_move=True,
            no_resize=True,
            no_title_bar=True,
            no_close=True,
            tag="dir_list_window",
            min_size=[100, 100],
            max_size=[10000, 10000],
        ):
            with dpg.child_window(
                width=width,
                # height=height,
                pos=[0, 0],
                tag="dir_list_child_window",
            ):
                dpg.add_image(
                    "selected_rectangle_texture",
                    tag="selected_rectangle_image",
                    width=1,
                    height=30 - 15,
                    parent="dir_list_child_window",
                    pos=[1, 1],
                    show=False,
                )
                dpg.bind_item_handler_registry(
                    "dir_list_child_window", "dir_list_child_window_handler"
                )
            with dpg.handler_registry(tag="dir_list_child_window_handler"):
                dpg.add_mouse_click_handler(0, callback=self.get_click_pos)
                dpg.add_mouse_click_handler(3, callback=self.wheel_handler)
                dpg.add_mouse_click_handler(4, callback=self.wheel_handler)
                dpg.add_mouse_wheel_handler(callback=self.wheel_handler)

    def wheel_handler(self, arg1, arg2):
        pass

    def refresh_dir_list(self):
        global path
        pfm_logger.info(f"開始重新整理檔案列表...，路徑：「 {path} 」")
        pfm_logger.debug("刪除舊文字、圖片...")
        for dir in self.dir_list_ids:
            dpg.delete_item(dir)
        for dir in self.dir_list_pictures:
            dpg.delete_item(dir)
        self.dir_list_ids.clear()
        self.dir_list_pictures.clear()
        #
        pfm_logger.debug("新增檔案名稱、圖片(icon)...")
        self.dirs = []
        if path == "/":
            disks = psutil.disk_partitions()
            for disk in disks:
                self.dirs.append(disk.device)
        else:
            self.dirs = os.listdir(path)
        pfm_logger.debug(f"路徑：「 {path} 」，取得的檔案列表：「 {self.dirs} 」")
        dir_height = 10
        for dir in self.dirs:
            full_dir_path = os.path.join(path, dir)
            pfm_logger.debug(f"製作檔名文字，檔案：{full_dir_path}")
            if os.path.isdir(full_dir_path) is True:
                picture_id = dpg.add_image(
                    "folder_icon_texture",
                    pos=(5, dir_height),
                    width=30,
                    height=30,
                    # (35, dir_height + 30),
                    parent="dir_list_child_window",
                    use_internal_label=True,
                )
            elif os.path.isfile(full_dir_path) is True:
                picture_id = dpg.add_image(
                    "file_icon_texture",
                    pos=(5, dir_height),
                    width=30,
                    height=30,
                    # (35, dir_height + 30),
                    parent="dir_list_child_window",
                    use_internal_label=True,
                )
            self.dir_list_pictures.append(picture_id)
            text_id = dpg.add_text(
                dir,
                pos=[40, dir_height],
                parent="dir_list_child_window",
                # size=30,
                use_internal_label=True,
            )
            self.dir_list_ids.append(text_id)
            dir_height += 30
        dpg.set_item_height("dir_list_child_window", dir_height + 20)

    def get_click_pos(self, sender, app_data) -> None:
        global path
        window_now = dpg.get_active_window()
        window_now_tag = dpg.get_item_alias(window_now)
        if window_now_tag != "dir_list_child_window":
            return None
        #
        pos_xy = dpg.get_mouse_pos()
        child_window_pos = dpg.get_item_pos("dir_list_child_window")
        pos_y = pos_xy[1] - child_window_pos[1]
        pfm_logger.debug(f"點擊y軸: {pos_y}")
        for y in range(0, len(self.dirs)):
            if pos_y in range(y * 30, y * 30 + 30):
                if (self.selected_dir == os.path.join(path, self.dirs[y])) and (
                    self.selected_dir is not None
                ):
                    # 開啟檔案或資料夾
                    if os.path.isdir(self.selected_dir):
                        path = os.path.join(path, self.dirs[y])
                        self.refresh_dir_list()
                        self.refresh_path_viewer()
                    elif os.path.isfile(self.selected_dir):
                        self.open_file_by_default_app(self.selected_dir)
                else:
                    # 選擇檔案或資料夾
                    self.selected_dir = os.path.join(path, self.dirs[y])
                    pfm_logger.info(f"選擇：{self.selected_dir}")
                    child_window_width = dpg.get_item_width("dir_list_child_window")
                    pfm_logger.debug(
                        f"子視窗寬(width)：{child_window_width}，資料類型：{type(child_window_width)}"
                    )
                    if type(child_window_width) is not int:
                        err_msg = f"DPG回傳值類型錯誤，回傳類型{type(child_window_width)}，應為int"
                        pfm_logger.error(err_msg)
                        raise RuntimeError(err_msg)
                    else:
                        dpg.set_item_pos(
                            "selected_rectangle_image",
                            [3, y * 30 + 30],  # X 軸位置 3, Y 軸位置 (已扣除滾動距離)
                        )
                        dpg.set_item_width(
                            "selected_rectangle_image", child_window_width * 30
                        )
                        dpg.set_item_height(
                            "selected_rectangle_image", (30 * 10 - 30)
                        )  # 項目高度 30 - 15 變類底線
                        dpg.show_item("selected_rectangle_image")
                break
            else:
                pass

    def open_file_by_default_app(self, filepath: str):
        sys_platform = platform.system()
        if sys_platform == "Windows":
            os.startfile(filepath)
        elif sys_platform == "Darwin":  # macOS
            subprocess.run(["open", filepath], check=True)
        elif sys_platform == "Linux":
            subprocess.run(["xdg-open", filepath], check=True)
        else:
            err_msg = f"無法開啟檔案，不支援的系統：{sys_platform}"
            pfm_logger.warning(err_msg)
            self.push_notification(err_msg)

    def create_control_center(self):
        width = dpg.get_viewport_width()
        height = 75
        with dpg.window(
            width=width,
            height=height,
            pos=[0, 0],
            no_move=True,
            no_resize=True,
            no_title_bar=True,
            no_collapse=True,
            no_close=True,
            tag="control_center_window",
        ):
            dpg.add_button(
                label="設定(未完)",
                width=70,
                height=30,
                callback=self.show_config_window,
                pos=[5, 5],
            )
            dpg.add_button(
                label="複製(未完)",
                width=70,
                height=30,
                callback=self._control_copy,
                pos=[100, 5],
            )
            dpg.add_button(
                label="貼上(未完)",
                width=70,
                height=30,
                callback=self._control_paste,
                enabled=False,
                tag="control_paste",
                pos=[200, 5],
            )

    def refresh_control_center(self):
        if self._copy_dir is None:
            dpg.configure_item("control_paste", enabled=False)
        else:
            dpg.configure_item("control_paste", enabled=True)

    def _control_copy(self):
        if self.selected_dir is None:
            return
        self._copy_dir = self.selected_dir
        self.refresh_control_center()

    def _control_paste(self):
        if self._copy_dir is None:
            return
        self.copy(self._copy_dir, path)

    def show_config_window(self):
        dpg.show_item("config_window")

    def create_config_window(self):
        self.config_window_width = 720
        self.config_window_height = 720
        pos_width = dpg.get_viewport_width()
        pos_height = dpg.get_viewport_height()
        window_pos_width = (pos_width - self.config_window_width) // 2
        window_pos_height = (pos_height - self.config_window_height) // 2
        with dpg.window(
            label="FM GUI 設定",
            pos=[window_pos_width, window_pos_height],
            width=self.config_window_width,
            height=self.config_window_height,
            modal=True,
            no_close=True,
            no_collapse=True,
            tag="config_window",
            show=False,
        ):
            with dpg.child_window(
                label="FM GUI 設定",
                pos=[0, 0],
                width=self.config_window_width,
                height=self.config_window_height,
                tag="config_child_window",
            ):
                #
                dpg.add_color_picker(
                    default_value=self.config["selected_rectangle_color_fill"],
                    label="外框顏色",
                    tag="config__selected_rectangle_color_fill",
                    display_rgb=True,
                    display_hex=False,
                    display_hsv=False,
                    pos=[0, 5],
                    width=520,
                    height=720,
                )
                #
                child_window_height = dpg.get_item_height("config_child_window")
                if child_window_height is None:
                    raise RuntimeError
                dpg.add_button(
                    label="儲存",
                    width=70,
                    height=30,
                    pos=[0, child_window_height - 40],
                    callback=self._config_save,
                )
                dpg.add_button(
                    label="全部重設",
                    width=100,
                    height=30,
                    pos=[100, child_window_height - 40],
                    callback=self._config_init,
                )

    def _config_refresh(self):
        dpg.configure_item(
            "config__selected_rectangle_color_fill",
            default_value=self.config["selected_rectangle_color_fill"],
        )

    def _config_init(self):
        dpg.hide_item("config_window")
        self.init_config()
        self._config_save_to_file

    def _config_save(self):
        #
        self.config["config__selected_rectangle_color_fill"] = dpg.get_value(
            "config__selected_rectangle_color_fill"
        )
        #
        self._config_save_to_file()
        dpg.hide_item("config_window")

    def _config_save_to_file(self):
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(self.config, f, ensure_ascii=False, indent=4)
        pfm_logger.debug("已將設定儲存到檔案。")

    def resize_window(self):
        width = dpg.get_viewport_width() - 10
        height = dpg.get_viewport_height() - 180
        dpg.set_item_height("dir_list_window", height)
        dpg.set_item_width("dir_list_window", width)
        dpg.set_item_height("dir_list_child_window", height)
        dpg.set_item_width("dir_list_child_window", width)
        self.refresh_dir_list()
        dpg.set_item_width("path_viewer_window", width)
        dpg.set_item_width("control_center_window", width)
        #
        pos_width = dpg.get_viewport_width()
        pos_height = dpg.get_viewport_height()
        config_window_pos_width = (pos_width - self.config_window_width) // 2
        config_window_pos_height = (pos_height - self.config_window_height) // 2
        dpg.set_item_pos(
            "config_window", [config_window_pos_width, config_window_pos_height]
        )

    def create_notification_window(self):
        window_width = 300
        window_height = 150
        pos_width = dpg.get_viewport_width()
        pos_height = dpg.get_viewport_height()
        window_pos_width = (pos_width - window_width) // 2
        window_pos_height = (pos_height - window_height) // 2
        with dpg.window(
            label="Positive File Manager 通知",
            tag="notification_window",
            pos=[window_pos_width, window_pos_height],
            show=False,
            modal=True,
            height=window_height,
            width=window_width,
        ):
            dpg.add_text("", tag="notification_text")
            dpg.add_button(label="確定", callback=self.hide_notification_window)

    def hide_notification_window(self) -> None:
        dpg.hide_item("notification_window")
        return None

    def show_notification_window(self) -> None:
        dpg.show_item("notification_window")
        return None

    def push_notification(self, text: str):
        dpg.set_value("notification_text", text)
        self.show_notification_window()

    def create_path_viewer(self):
        height = 45
        with dpg.window(
            no_close=True,
            no_move=True,
            no_resize=True,
            no_collapse=True,
            no_scrollbar=True,
            no_title_bar=True,
            no_scroll_with_mouse=True,
            min_size=[10, 10],
            max_size=[5000, 100],
            height=height,
            tag="path_viewer_window",
            pos=[0, 105],
        ):
            dpg.add_text(
                path,
                tag="path_viewer_window_path_text",
                pos=[100, 5],
            )
            dpg.add_button(
                label="上一層",
                width=70,
                height=30,
                callback=self._path_viewer_dirname,
                tag="path_viewer_back_button",
            )

    def _path_viewer_dirname(self):
        global path
        pfm_logger.info(f"返回上層資料夾，原路徑： 「 {path} 」")
        disks = psutil.disk_partitions()
        disks_list = []
        for disk in disks:
            disks_list.append(os.path.normpath(disk.mountpoint))
        pfm_logger.debug(f"偵測到的儲存空間：「 {disks_list} 」")
        if path in disks_list:
            path = "/"
        else:
            path = os.path.dirname(path)
        self.refresh_dir_list()
        self.refresh_path_viewer()

    def refresh_path_viewer(self):
        global path
        dpg.set_value("path_viewer_window_path_text", path)
        if path == "/":
            dpg.hide_item("path_viewer_back_button")
            dpg.disable_item("path_viewer_back_button")
        else:
            dpg.show_item("path_viewer_back_button")
            dpg.enable_item("path_viewer_back_button")

    def copy(self, dir: str, to_dir: str):
        if os.path.isdir(to_dir) is False:
            msg = f"to_dir非資料夾，路徑：{to_dir}"
            pfm_logger.error(msg)
            raise RuntimeError(msg)
        elif (os.path.exists(dir) is False) or (os.path.exists(to_dir) is False):
            msg = "arg包含不存在的路徑"
            pfm_logger.error(msg)
            raise RuntimeError(msg)
        #
        wait_for_copy = []
        if os.path.isfile(dir) is True:
            wait_for_copy.append(dir)
        elif os.path.isdir(dir) is True:
            base_dir_path = dir
            wait_for_copy = self._copy(path, ".", wait_for_copy)
            dir_check_finish = False
            while True:
                for i in wait_for_copy:
                    if os.path.isfile(i) is False:
                        wait_for_copy = self._copy(base_dir_path, i, wait_for_copy)
                        dir_check_finish = False
                        break
                    else:
                        dir_check_finish = True
                if dir_check_finish is True:
                    break
        for file in wait_for_copy:
            print(file)
            # shutil.copy2(file, to_dir)

    def _copy(self, base_dir_path, dir, wait_for_copy):
        dirs = os.listdir(path)
        for dir in dirs:
            dir_full_path = os.path.join(base_dir_path, dir)
            wait_for_copy.append(dir_full_path)
        return wait_for_copy


def launcher():
    dpg.create_context()
    with dpg.font_registry():
        with dpg.font(main_font_path, 30) as default_font:
            dpg.add_font_range_hint(dpg.mvFontRangeHint_Chinese_Full)
    dpg.bind_font(default_font)
    dpg.create_viewport(title="Positive File Manager")
    dpg.setup_dearpygui()
    dpg.show_viewport()
    dpg.maximize_viewport()
    window = FileManager()
    dpg.set_viewport_resize_callback(window.resize_window)
    dpg.start_dearpygui()
    dpg.destroy_context()


if __name__ == "__main__":
    launcher()

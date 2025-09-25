import logging
import os
import json
import shutil
import psutil
import platform
import subprocess

from dearpygui import dearpygui as dpg

import pt

pfm_version = "b-1"
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

path = os.getcwd()


class FileManager:
    def __init__(self) -> None:
        self.create_notification_window()
        self.create_dir_list()
        self.create_control_center()
        self.create_path_viewer()
        self.dir_list_ids = []
        self.dir_list_pictures = []
        self._copy_dir: str | None = None
        self.selected_dir: str | None = None
        self.config: dict = {}
        self.config_path = os.path.join(os.path.dirname(__file__), "config.json")
        if os.path.exists(self.config_path) is False:
            self.init_config()
        else:
            self.load_config()
        self.create_config_window()
        #
        self.load_icons()
        self.refresh_dir_list()
        self._config_refresh()
        #

    def load_config(self) -> None:
        with open(self.config_path, "r", encoding="utf-8") as f:
            self.config = json.load(f)
        return None

    def init_config(self):
        self.config = {
            "selected_rectangle_color": [99, 118, 255, 255],
        }

    def load_icons(self):
        global file_icon_path, folder_icon_path
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

    def create_dir_list(self):
        width = dpg.get_viewport_width()
        height = dpg.get_viewport_height() - 150
        with dpg.window(
            width=width,
            height=height,
            pos=[0, 150],
            no_move=True,
            no_resize=True,
            no_title_bar=True,
            no_collapse=True,
            no_close=True,
            tag="dir_list_window",
        ):
            with dpg.child_window(
                width=width,
                height=height,
                pos=[0, 0],
                tag="dir_list_child_window",
                auto_resize_y=True,
                resizable_y=True,
                always_auto_resize=True,
            ):
                dpg.add_drawlist(width=width, height=height, tag="dir_list_drawlist")
                dpg.bind_item_handler_registry(
                    "dir_list_child_window", "dir_list_child_window_handler"
                )
            with dpg.handler_registry(tag="dir_list_child_window_handler"):
                dpg.add_mouse_click_handler(0, callback=self.get_click_pos)

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
        dir_height = 5
        for dir in self.dirs:
            full_dir_path = os.path.join(path, dir)
            pfm_logger.debug(f"製作檔名文字，檔案：{full_dir_path}")
            if os.path.isdir(full_dir_path) is True:
                picture_id = dpg.draw_image(
                    "folder_icon_texture",
                    (5, dir_height),
                    (35, dir_height + 30),
                    parent="dir_list_drawlist",
                    use_internal_label=True,
                )
            elif os.path.isfile(full_dir_path) is True:
                picture_id = dpg.draw_image(
                    "file_icon_texture",
                    (5, dir_height),
                    (35, dir_height + 30),
                    parent="dir_list_drawlist",
                    use_internal_label=True,
                )
            self.dir_list_pictures.append(picture_id)
            text_id = dpg.draw_text(
                pos=[40, dir_height],
                text=dir,
                parent="dir_list_drawlist",
                size=30,
                use_internal_label=True,
            )
            self.dir_list_ids.append(text_id)
            dir_height += 30
        dpg.set_item_height("dir_list_drawlist", dir_height + 30)

    def get_click_pos(self, sender, app_data) -> None:
        global path
        window_now = dpg.get_active_window()
        window_now_tag = dpg.get_item_alias(window_now)
        if window_now_tag != "dir_list_child_window":
            return None
        #
        pos_xy = dpg.get_mouse_pos()
        pos_y = pos_xy[1]
        pfm_logger.debug(f"點擊y軸: {pos_y}")
        for y in range(0, len(self.dirs)):
            if pos_y in range(y * 30, y * 30 + 30):
                if (self.selected_dir == os.path.join(path, self.dirs[y])) and (
                    self.selected_dir is not None
                ):
                    if os.path.isdir(self.selected_dir):
                        path = os.path.join(path, self.dirs[y])
                        self.refresh_dir_list()
                        self.refresh_path_viewer()
                    elif os.path.isfile(self.selected_dir):
                        self.open_file_by_default_app(self.selected_dir)
                else:
                    self.selected_dir = os.path.join(path, self.dirs[y])
                    pfm_logger.info(f"選擇：{self.selected_dir}")
                    if dpg.does_item_exist("selected_rectangle") is True:
                        dpg.delete_item("selected_rectangle")
                    child_window_width = dpg.get_item_width("dir_list_child_window")
                    if type(child_window_width) is int:
                        child_window_width_float = float(child_window_width - 40)
                    else:
                        raise RuntimeError("dpg回傳錯誤!")
                    dpg.draw_rectangle(
                        [3, float(y * 30) + 10],
                        [child_window_width_float, y * 30 + 30 + 10],
                        tag="selected_rectangle",
                        parent="dir_list_drawlist",
                        color=self.config["selected_rectangle_color"],
                        thickness=2,
                    )
                    dpg.move_item_down("selected_rectangle")
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
            self.push_notification(f"無法開啟檔案，不支援的系統：{sys_platform}")

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
                    default_value=self.config["selected_rectangle_color"],
                    label="外框顏色",
                    tag="config__selected_rectangle_color",
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
            "config__selected_rectangle_color",
            default_value=self.config["selected_rectangle_color"],
        )

    def _config_init(self):
        self.init_config()
        dpg.hide_item("config_window")

    def _config_save(self):
        #
        self.config["config__selected_rectangle_color"] = dpg.get_value(
            "config__selected_rectangle_color"
        )
        #
        self._config_save_to_file()
        dpg.hide_item("config_window")

    def _config_save_to_file(self):
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(self.config, f, ensure_ascii=False, indent=4)
        pfm_logger.debug("已將設定儲存到檔案。")

    def resize_window(self):
        width = dpg.get_viewport_width() - 10
        height = dpg.get_viewport_height() - 180
        dpg.set_item_height("dir_list_window", height)
        dpg.set_item_width("dir_list_window", width)
        dpg.set_item_height("dir_list_child_window", height)
        dpg.set_item_width("dir_list_child_window", width)
        # dpg.set_item_height("dir_list_drawlist", height)
        self.refresh_dir_list()
        dpg.set_item_width("dir_list_drawlist", width)
        dpg.set_item_width("control_center_window", width)
        dpg.set_item_width("path_viewer_window", width)
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

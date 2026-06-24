from __future__ import annotations

import os
import random
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QFileDialog,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMainWindow,
    QTableWidget,
    QTableWidgetItem,
    QAbstractItemView,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)


@dataclass(frozen=True)
class MixOptions:
    input_folder: Path
    output_folder: Path
    folder_count: int
    files_per_folder: int | None
    prefix_files: bool
    clean_output: bool
    seed: str | None


@dataclass(frozen=True)
class PlaylistEntry:
    folder: Path
    files: list[str]

@dataclass(frozen=True)
class MixResult:
    input_folder: Path
    output_folder: Path
    source_file_count: int
    files_per_folder: int
    generated_folders: list[Path]
    playlists: list[PlaylistEntry]


def get_mp3_files(input_folder: Path) -> list[Path]:
    files = sorted(
        [path for path in input_folder.iterdir() if path.is_file() and path.suffix.lower() == ".mp3"],
        key=lambda path: path.name.lower(),
    )

    if not files:
        raise ValueError(f"Không tìm thấy file .mp3 nào trong thư mục: {input_folder}")

    return files


def prefix_name(index: int, file_name: str, total_files: int) -> str:
    width = len(str(total_files))
    order = str(index + 1).zfill(width)
    return f"{order}_{file_name}"


def validate_options(options: MixOptions) -> None:
    if not str(options.input_folder).strip():
        raise ValueError("Vui lòng chọn thư mục nhạc nguồn")

    if not str(options.output_folder).strip():
        raise ValueError("Vui lòng chọn thư mục xuất kết quả")

    if not options.input_folder.exists() or not options.input_folder.is_dir():
        raise ValueError(f"Thư mục nhạc nguồn không tồn tại: {options.input_folder}")

    if options.folder_count < 1:
        raise ValueError("Số thư mục cần tạo phải lớn hơn 0")

    if options.files_per_folder is not None and options.files_per_folder < 1:
        raise ValueError("Số file mỗi thư mục phải lớn hơn 0")


def generate_folders(options: MixOptions) -> MixResult:
    validate_options(options)

    files = get_mp3_files(options.input_folder)
    files_per_folder = options.files_per_folder or min(5, len(files))

    if files_per_folder > len(files):
        raise ValueError(f"Số file mỗi thư mục không được lớn hơn số file MP3 hiện có ({len(files)})")

    if options.folder_count > len(files):
        raise ValueError(
            f"Với luật không lặp bài ở cùng vị trí, số playlist tối đa là {len(files)} "
            f"vì thư mục nguồn có {len(files)} file MP3."
        )

    if files_per_folder == len(files) and options.folder_count > 1:
        raise ValueError("Khi mỗi playlist dùng tất cả file, chỉ tạo được 1 playlist nếu không lặp lại cùng nhóm bài.")

    randomizer = random.Random(options.seed) if options.seed else random.Random()
    playlist_files = build_position_balanced_playlists(files, options.folder_count, files_per_folder, randomizer)

    if options.clean_output and options.output_folder.exists():
        shutil.rmtree(options.output_folder)

    options.output_folder.mkdir(parents=True, exist_ok=True)
    generated_folders: list[Path] = []
    playlists: list[PlaylistEntry] = []

    for folder_index, selected_files in enumerate(playlist_files):
        folder_name = str(folder_index + 1).zfill(len(str(options.folder_count)))
        target_folder = options.output_folder / folder_name

        target_folder.mkdir(parents=True, exist_ok=True)
        generated_folders.append(target_folder)
        display_files: list[str] = []

        for file_index, source_file in enumerate(selected_files):
            target_name = prefix_name(file_index, source_file.name, len(selected_files)) if options.prefix_files else source_file.name
            shutil.copy2(source_file, target_folder / target_name)
            display_files.append(target_name)

        playlists.append(PlaylistEntry(folder=target_folder, files=display_files))

    return MixResult(
        input_folder=options.input_folder,
        output_folder=options.output_folder,
        source_file_count=len(files),
        files_per_folder=files_per_folder,
        generated_folders=generated_folders,
        playlists=playlists,
    )

def build_position_balanced_playlists(
    files: list[Path],
    playlist_count: int,
    files_per_playlist: int,
    randomizer: random.Random,
) -> list[list[Path]]:
    ordered_files = files[:]
    randomizer.shuffle(ordered_files)

    offsets = list(range(len(ordered_files)))
    randomizer.shuffle(offsets)
    offsets = offsets[:files_per_playlist]

    playlists: list[list[Path]] = []
    used_groups: set[tuple[str, ...]] = set()

    for playlist_index in range(playlist_count):
        playlist = [ordered_files[(playlist_index + offset) % len(ordered_files)] for offset in offsets]
        group_key = tuple(sorted(file.name for file in playlist))

        if len({file.name for file in playlist}) != files_per_playlist or group_key in used_groups:
            return build_position_balanced_playlists_with_search(files, playlist_count, files_per_playlist, randomizer)

        used_groups.add(group_key)
        playlists.append(playlist)

    return playlists

def build_position_balanced_playlists_with_search(
    files: list[Path],
    playlist_count: int,
    files_per_playlist: int,
    randomizer: random.Random,
) -> list[list[Path]]:
    used_positions = [set[str]() for _ in range(files_per_playlist)]
    used_groups: set[tuple[str, ...]] = set()
    playlists: list[list[Path]] = []

    for _ in range(playlist_count):
        for _attempt in range(10_000):
            candidates = files[:]
            randomizer.shuffle(candidates)
            playlist: list[Path] = []

            for position in range(files_per_playlist):
                available = [file for file in candidates if file.name not in used_positions[position] and file not in playlist]
                if not available:
                    break
                playlist.append(available[0])

            if len(playlist) != files_per_playlist:
                continue

            group_key = tuple(sorted(file.name for file in playlist))
            if group_key in used_groups:
                continue

            for position, file in enumerate(playlist):
                used_positions[position].add(file.name)
            used_groups.add(group_key)
            playlists.append(playlist)
            break
        else:
            raise ValueError("Không thể tạo thêm playlist thỏa điều kiện không lặp nhóm bài và không lặp vị trí.")

    return playlists


def open_folder(path: Path) -> None:
    if sys.platform == "win32":
        os.startfile(path)
    elif sys.platform == "darwin":
        subprocess.run(["open", str(path)], check=False)
    else:
        subprocess.run(["xdg-open", str(path)], check=False)


class FolderDropLineEdit(QLineEdit):
    def __init__(self, placeholder: str) -> None:
        super().__init__()
        self.setAcceptDrops(True)
        self.setPlaceholderText(placeholder)

    def dragEnterEvent(self, event) -> None:
        if self._folder_from_event(event) is not None:
            event.acceptProposedAction()
            self.setProperty("dragging", True)
            self.style().unpolish(self)
            self.style().polish(self)
        else:
            event.ignore()

    def dragLeaveEvent(self, event) -> None:
        self._clear_drag_state()
        super().dragLeaveEvent(event)

    def dropEvent(self, event) -> None:
        folder = self._folder_from_event(event)

        if folder is None:
            event.ignore()
            self._clear_drag_state()
            return

        self.setText(str(folder))
        event.acceptProposedAction()
        self._clear_drag_state()

    def _folder_from_event(self, event) -> Path | None:
        mime_data = event.mimeData()

        for url in mime_data.urls():
            if not url.isLocalFile():
                continue

            path = Path(url.toLocalFile()).expanduser()
            if path.is_dir():
                return path

        text = mime_data.text().strip()
        if text:
            path = Path(text.strip('"')).expanduser()
            if path.is_dir():
                return path

        return None

    def _clear_drag_state(self) -> None:
        self.setProperty("dragging", False)
        self.style().unpolish(self)
        self.style().polish(self)

class MixWorker(QThread):
    finished_successfully = pyqtSignal(object)
    failed = pyqtSignal(str)

    def __init__(self, options: MixOptions) -> None:
        super().__init__()
        self.options = options

    def run(self) -> None:
        try:
            self.finished_successfully.emit(generate_folders(self.options))
        except Exception as error:
            self.failed.emit(str(error))


class MixFilesWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.worker: MixWorker | None = None
        self.last_output_folder: Path | None = None

        self.setWindowTitle("Mix Files - Trộn thư mục MP3")
        self.setMinimumSize(780, 620)
        self._build_ui()

    def _build_ui(self) -> None:
        root = QWidget()
        layout = QVBoxLayout(root)

        title = QLabel("Mix Files")
        title.setObjectName("title")
        subtitle = QLabel("Trộn ngẫu nhiên file MP3 thành nhiều thư mục. Có thể kéo thả thư mục vào ô nhập.")
        subtitle.setObjectName("subtitle")

        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addWidget(self._create_folder_group())
        layout.addWidget(self._create_options_group())
        layout.addLayout(self._create_actions())

        self.status_label = QLabel("Sẵn sàng")
        self.status_label.setObjectName("status")
        layout.addWidget(self.status_label)

        results_layout = QHBoxLayout()

        folders_layout = QVBoxLayout()
        folders_title = QLabel("Thư mục đã mix")
        folders_title.setObjectName("sectionTitle")
        self.paths_list = QListWidget()
        folders_layout.addWidget(folders_title)
        folders_layout.addWidget(self.paths_list)

        playlist_layout = QVBoxLayout()
        playlist_title = QLabel("Bảng playlist")
        playlist_title.setObjectName("sectionTitle")
        self.playlist_table = QTableWidget()
        self.playlist_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.playlist_table.setAlternatingRowColors(True)
        self.playlist_table.verticalHeader().setVisible(False)
        playlist_layout.addWidget(playlist_title)
        playlist_layout.addWidget(self.playlist_table)

        results_layout.addLayout(folders_layout, stretch=1)
        results_layout.addLayout(playlist_layout, stretch=3)
        layout.addLayout(results_layout, stretch=1)

        self.setCentralWidget(root)
        self.setStyleSheet(
            """
            QMainWindow { background: #f7f7fb; }
            QLabel#title { font-size: 30px; font-weight: 700; color: #161621; }
            QLabel#subtitle { color: #55556a; margin-bottom: 12px; }
            QLabel#sectionTitle { color: #25253a; font-weight: 700; margin-top: 8px; }
            QLabel#status { padding: 10px; border-radius: 8px; background: #ececf5; }
            QGroupBox { font-weight: 700; border: 1px solid #d9d9e8; border-radius: 10px; margin-top: 12px; padding: 14px; background: white; }
            QGroupBox::title { subcontrol-origin: margin; left: 12px; padding: 0 6px; }
            QLineEdit, QSpinBox { padding: 8px; border: 1px solid #c9c9dc; border-radius: 6px; background: white; }
            QLineEdit[dragging="true"] { border: 2px solid #4f46e5; background: #eef2ff; }
            QPushButton { padding: 9px 14px; border-radius: 7px; border: 1px solid #bfc0d8; background: #ffffff; }
            QPushButton:hover { background: #f0f0fb; }
            QPushButton#primary { color: white; background: #4f46e5; border: 1px solid #4f46e5; font-weight: 700; }
            QPushButton#primary:hover { background: #4338ca; }
            QPushButton:disabled { color: #9999aa; background: #eeeeee; }
            QListWidget, QTableWidget { border: 1px solid #d9d9e8; border-radius: 10px; padding: 8px; background: white; }
            QTableWidget::item { padding: 6px; }
            """
        )

    def _create_folder_group(self) -> QGroupBox:
        group = QGroupBox("Thư mục")
        layout = QGridLayout(group)

        self.input_edit = FolderDropLineEdit("Kéo thả hoặc chọn thư mục nhạc nguồn")
        input_button = QPushButton("Chọn")
        input_button.clicked.connect(lambda: self._choose_folder(self.input_edit))

        self.output_edit = FolderDropLineEdit("Kéo thả hoặc chọn thư mục xuất kết quả")
        output_button = QPushButton("Chọn")
        output_button.clicked.connect(lambda: self._choose_folder(self.output_edit))

        layout.addWidget(QLabel("Thư mục nhạc nguồn"), 0, 0)
        layout.addWidget(self.input_edit, 0, 1)
        layout.addWidget(input_button, 0, 2)
        layout.addWidget(QLabel("Thư mục xuất kết quả"), 1, 0)
        layout.addWidget(self.output_edit, 1, 1)
        layout.addWidget(output_button, 1, 2)

        return group

    def _create_options_group(self) -> QGroupBox:
        group = QGroupBox("Tùy chọn trộn")
        layout = QFormLayout(group)

        self.folder_count_spin = QSpinBox()
        self.folder_count_spin.setRange(1, 100000)
        self.folder_count_spin.setValue(50)

        self.files_per_folder_spin = QSpinBox()
        self.files_per_folder_spin.setRange(0, 100000)
        self.files_per_folder_spin.setSpecialValueText("Mặc định 5 file")
        self.files_per_folder_spin.setValue(0)

        self.seed_edit = QLineEdit()
        self.seed_edit.setPlaceholderText("Tùy chọn, ví dụ: dot-1")

        self.prefix_check = QCheckBox("Thêm số thứ tự như 1_baihat.mp3")
        self.prefix_check.setChecked(True)

        self.clean_check = QCheckBox("Xóa sạch thư mục xuất trước khi tạo")

        layout.addRow("Số thư mục cần tạo", self.folder_count_spin)
        layout.addRow("Số file mỗi thư mục", self.files_per_folder_spin)
        layout.addRow("Mã trộn cố định", self.seed_edit)
        layout.addRow("", self.prefix_check)
        layout.addRow("", self.clean_check)

        return group

    def _create_actions(self) -> QHBoxLayout:
        layout = QHBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignLeft)

        self.generate_button = QPushButton("Tạo thư mục")
        self.generate_button.setObjectName("primary")
        self.generate_button.clicked.connect(self._generate)

        self.open_output_button = QPushButton("Mở thư mục xuất")
        self.open_output_button.setEnabled(False)
        self.open_output_button.clicked.connect(self._open_output)

        self.copy_paths_button = QPushButton("Sao chép đường dẫn")
        self.copy_paths_button.setEnabled(False)
        self.copy_paths_button.clicked.connect(self._copy_paths)

        layout.addWidget(self.generate_button)
        layout.addWidget(self.open_output_button)
        layout.addWidget(self.copy_paths_button)

        return layout

    def _choose_folder(self, target: QLineEdit) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Chọn thư mục", target.text() or str(Path.home()))
        if folder:
            target.setText(folder)

    def _read_options(self) -> MixOptions:
        files_per_folder_value = self.files_per_folder_spin.value()
        seed_value = self.seed_edit.text().strip()

        return MixOptions(
            input_folder=Path(self.input_edit.text().strip()).expanduser(),
            output_folder=Path(self.output_edit.text().strip()).expanduser(),
            folder_count=self.folder_count_spin.value(),
            files_per_folder=files_per_folder_value if files_per_folder_value else None,
            prefix_files=self.prefix_check.isChecked(),
            clean_output=self.clean_check.isChecked(),
            seed=seed_value or None,
        )

    def _generate(self) -> None:
        try:
            options = self._read_options()
            validate_options(options)
        except Exception as error:
            QMessageBox.warning(self, "Tùy chọn chưa hợp lệ", str(error))
            return

        self._set_busy(True)
        self._set_status("Đang tạo thư mục...")
        self.paths_list.clear()
        self._render_playlist_table([])
        self.worker = MixWorker(options)
        self.worker.finished_successfully.connect(self._handle_success)
        self.worker.failed.connect(self._handle_failure)
        self.worker.start()

    def _handle_success(self, result: MixResult) -> None:
        self.last_output_folder = result.output_folder
        self.paths_list.clear()

        for folder in result.generated_folders:
            self.paths_list.addItem(str(folder))

        self._render_playlist_table(result.playlists)

        self._set_status(
            f"Hoàn tất: đã tạo {len(result.generated_folders)} thư mục, "
            f"mỗi thư mục có {result.files_per_folder}/{result.source_file_count} file MP3."
        )
        self.open_output_button.setEnabled(True)
        self.copy_paths_button.setEnabled(True)
        self._set_busy(False)

    def _render_playlist_table(self, playlists: list[PlaylistEntry]) -> None:
        if not playlists:
            self.playlist_table.setRowCount(0)
            self.playlist_table.setColumnCount(0)
            return

        max_positions = max(len(playlist.files) for playlist in playlists)
        headers = ["Playlist", *[f"Vị trí {index + 1}" for index in range(max_positions)]]
        self.playlist_table.setColumnCount(len(headers))
        self.playlist_table.setRowCount(len(playlists))
        self.playlist_table.setHorizontalHeaderLabels(headers)

        for row, playlist in enumerate(playlists):
            playlist_item = QTableWidgetItem(f"#{row + 1}")
            playlist_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.playlist_table.setItem(row, 0, playlist_item)

            for column, file_name in enumerate(playlist.files, start=1):
                item = QTableWidgetItem(file_name)
                item.setToolTip(file_name)
                self.playlist_table.setItem(row, column, item)

        self.playlist_table.resizeColumnsToContents()
        self.playlist_table.resizeRowsToContents()

    def _handle_failure(self, message: str) -> None:
        self._set_status("Tạo thư mục thất bại")
        QMessageBox.critical(self, "Tạo thư mục thất bại", message)
        self._set_busy(False)

    def _open_output(self) -> None:
        if self.last_output_folder:
            open_folder(self.last_output_folder)

    def _copy_paths(self) -> None:
        paths = [self.paths_list.item(index).text() for index in range(self.paths_list.count())]
        QApplication.clipboard().setText("\n".join(paths))
        self._set_status("Đã sao chép danh sách đường dẫn vào clipboard.")

    def _set_busy(self, is_busy: bool) -> None:
        self.generate_button.setEnabled(not is_busy)
        self.open_output_button.setEnabled(not is_busy and self.last_output_folder is not None)
        self.copy_paths_button.setEnabled(not is_busy and self.paths_list.count() > 0)

    def _set_status(self, message: str) -> None:
        self.status_label.setText(message)


def main() -> int:
    app = QApplication(sys.argv)
    window = MixFilesWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())

import sys
import os
import threading
import time
import shutil
import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk

# Import core cleaning logic
import cleaner_core

# Set appearance and theme
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class CleanMasterApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("CleanMaster - PC 안전 디스크 정리 도구")
        self.geometry("780x800")
        self.minsize(720, 700)

        # High DPI awareness for Windows
        try:
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass

        self.category_vars = {}
        self.category_widgets = {}
        self.category_sizes = {}
        self.is_busy = False

        self._build_ui()
        self.refresh_disk_status()
        self.start_scan_threads()

    def _build_ui(self):
        # 1. Header Frame
        header = ctk.CTkFrame(self, corner_radius=12, fg_color="#1E293B")
        header.pack(fill="x", padx=16, pady=(16, 10))

        title_row = ctk.CTkFrame(header, fg_color="transparent")
        title_row.pack(fill="x", padx=16, pady=(14, 4))

        title_lbl = ctk.CTkLabel(
            title_row,
            text="🧹 CleanMaster 디스크 정리",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color="#F8FAFC"
        )
        title_lbl.pack(side="left")

        shield_badge = ctk.CTkLabel(
            title_row,
            text="🛡️ 중요 시스템/개인 파일 보호 활성",
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#065F46",
            text_color="#6EE7B7",
            corner_radius=6,
            padx=10,
            pady=3
        )
        shield_badge.pack(side="right")

        # Disk C: status bar
        self.disk_info_lbl = ctk.CTkLabel(
            header,
            text="C: 드라이브 용량 측정 중...",
            font=ctk.CTkFont(size=13),
            text_color="#94A3B8"
        )
        self.disk_info_lbl.pack(anchor="w", padx=16, pady=(4, 6))

        self.disk_progress = ctk.CTkProgressBar(header, height=12, corner_radius=6)
        self.disk_progress.pack(fill="x", padx=16, pady=(0, 14))
        self.disk_progress.set(0.0)

        # 2. Control Toolbar
        toolbar = ctk.CTkFrame(self, fg_color="transparent")
        toolbar.pack(fill="x", padx=16, pady=4)

        sec_title = ctk.CTkLabel(
            toolbar,
            text="정리할 항목 선택",
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color="#E2E8F0"
        )
        sec_title.pack(side="left")

        btn_refresh = ctk.CTkButton(
            toolbar,
            text="🔄 용량 재검색",
            width=100,
            height=28,
            font=ctk.CTkFont(size=12),
            fg_color="#334155",
            hover_color="#475569",
            command=self.start_scan_threads
        )
        btn_refresh.pack(side="right", padx=(6, 0))

        btn_deselect = ctk.CTkButton(
            toolbar,
            text="전체 해제",
            width=75,
            height=28,
            font=ctk.CTkFont(size=12),
            fg_color="#334155",
            hover_color="#475569",
            command=self.deselect_all
        )
        btn_deselect.pack(side="right", padx=6)

        btn_select_all = ctk.CTkButton(
            toolbar,
            text="전체 선택",
            width=75,
            height=28,
            font=ctk.CTkFont(size=12),
            fg_color="#334155",
            hover_color="#475569",
            command=self.select_all
        )
        btn_select_all.pack(side="right", padx=6)

        btn_recommended = ctk.CTkButton(
            toolbar,
            text="권장 선택",
            width=75,
            height=28,
            font=ctk.CTkFont(size=12),
            fg_color="#1E3A8A",
            hover_color="#1D4ED8",
            command=self.select_recommended
        )
        btn_recommended.pack(side="right", padx=6)

        # 3. Category Scrollable Frame
        self.scroll_frame = ctk.CTkScrollableFrame(self, fg_color="#0F172A", corner_radius=10)
        self.scroll_frame.pack(fill="both", expand=True, padx=16, pady=8)

        for cat in cleaner_core.CLEANUP_CATEGORIES:
            self._create_category_card(cat)

        # 4. Action Frame
        action_frame = ctk.CTkFrame(self, corner_radius=12, fg_color="#1E293B")
        action_frame.pack(fill="x", padx=16, pady=(6, 8))

        summary_row = ctk.CTkFrame(action_frame, fg_color="transparent")
        summary_row.pack(fill="x", padx=16, pady=(10, 4))

        self.summary_lbl = ctk.CTkLabel(
            summary_row,
            text="정리 예정 용량: 계산 중...",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#38BDF8"
        )
        self.summary_lbl.pack(side="left")

        self.status_lbl = ctk.CTkLabel(
            summary_row,
            text="대기 중",
            font=ctk.CTkFont(size=13),
            text_color="#94A3B8"
        )
        self.status_lbl.pack(side="right")

        self.clean_progress = ctk.CTkProgressBar(action_frame, height=8, corner_radius=4)
        self.clean_progress.pack(fill="x", padx=16, pady=(0, 10))
        self.clean_progress.set(0.0)

        self.btn_clean = ctk.CTkButton(
            action_frame,
            text="🚀 선택한 항목 정리 시작",
            height=42,
            font=ctk.CTkFont(size=16, weight="bold"),
            fg_color="#2563EB",
            hover_color="#1D4ED8",
            corner_radius=8,
            command=self.start_cleanup
        )
        self.btn_clean.pack(fill="x", padx=16, pady=(0, 12))

        # 5. Console Log Frame
        log_frame = ctk.CTkFrame(self, fg_color="transparent")
        log_frame.pack(fill="both", expand=False, padx=16, pady=(0, 14))

        log_lbl = ctk.CTkLabel(
            log_frame,
            text="실시간 작업 로그",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#64748B"
        )
        log_lbl.pack(anchor="w", pady=(0, 2))

        self.log_box = ctk.CTkTextbox(
            log_frame,
            height=130,
            font=ctk.CTkFont(family="Consolas", size=11),
            fg_color="#090D16",
            text_color="#CBD5E1",
            corner_radius=8
        )
        self.log_box.pack(fill="both", expand=True)

    def _create_category_card(self, cat):
        cid = cat["id"]
        card = ctk.CTkFrame(self.scroll_frame, corner_radius=8, fg_color="#1E293B")
        card.pack(fill="x", pady=4, padx=4)

        row = ctk.CTkFrame(card, fg_color="transparent")
        row.pack(fill="x", padx=12, pady=8)

        var = ctk.BooleanVar(value=cat.get("recommended", True))
        var.trace_add("write", lambda *_: self.update_summary_label())
        self.category_vars[cid] = var

        chk = ctk.CTkCheckBox(
            row,
            text=cat["name"],
            variable=var,
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#F1F5F9",
            checkbox_width=20,
            checkbox_height=20,
            corner_radius=5
        )
        chk.pack(side="left")

        size_lbl = ctk.CTkLabel(
            row,
            text="검색 중...",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#38BDF8"
        )
        size_lbl.pack(side="right")

        desc_lbl = ctk.CTkLabel(
            card,
            text=cat["desc"],
            font=ctk.CTkFont(size=11),
            text_color="#94A3B8",
            anchor="w",
            justify="left"
        )
        desc_lbl.pack(fill="x", padx=38, pady=(0, 8))

        self.category_widgets[cid] = {
            "card": card,
            "chk": chk,
            "size_lbl": size_lbl,
            "cat": cat
        }

    def append_log(self, text: str):
        now_str = time.strftime("[%H:%M:%S] ")
        self.log_box.insert("end", now_str + text + "\n")
        self.log_box.see("end")

    def refresh_disk_status(self):
        try:
            total, used, free = cleaner_core.get_disk_info("C:\\")
            free_gb = free / (1024 ** 3)
            total_gb = total / (1024 ** 3)
            used_gb = used / (1024 ** 3)
            free_pct = (free / total) * 100
            used_pct = (used / total)

            self.disk_info_lbl.configure(
                text=f"C: 드라이브 — 총 {total_gb:.1f} GB 중 {free_gb:.1f} GB 사용 가능 ({free_pct:.1f}% 여유 공간)"
            )
            self.disk_progress.set(used_pct)
        except Exception as e:
            self.disk_info_lbl.configure(text=f"드라이브 정보 오류: {e}")

    def start_scan_threads(self):
        if self.is_busy:
            return
        self.is_busy = True
        self.status_lbl.configure(text="용량 검색 중...")
        self.btn_clean.configure(state="disabled")

        for cid, w in self.category_widgets.items():
            w["size_lbl"].configure(text="검색 중...", text_color="#94A3B8")

        def worker():
            for cat in cleaner_core.CLEANUP_CATEGORIES:
                cid = cat["id"]
                try:
                    b, count = cleaner_core.scan_category(cat)
                    self.category_sizes[cid] = (b, count)
                    txt = f"{cleaner_core.format_bytes(b)} ({count:,}개 파일)" if count > 0 else "0 B"
                    color = "#34D399" if b > 0 else "#64748B"
                    self.after(0, self._update_category_size_ui, cid, txt, color)
                except Exception as e:
                    self.after(0, self._update_category_size_ui, cid, "오류", "#EF4444")

            self.after(0, self._finish_scan)

        threading.Thread(target=worker, daemon=True).start()

    def _update_category_size_ui(self, cid, txt, color):
        if cid in self.category_widgets:
            self.category_widgets[cid]["size_lbl"].configure(text=txt, text_color=color)
        self.update_summary_label()

    def _finish_scan(self):
        self.is_busy = False
        self.status_lbl.configure(text="검색 완료 (정리 준비됨)")
        self.btn_clean.configure(state="normal")
        self.update_summary_label()
        self.append_log("모든 항목의 용량 검사가 완료되었습니다.")

    def update_summary_label(self):
        total_selected_bytes = 0
        total_selected_files = 0
        for cid, var in self.category_vars.items():
            if var.get() and cid in self.category_sizes:
                b, count = self.category_sizes[cid]
                total_selected_bytes += b
                total_selected_files += count

        self.summary_lbl.configure(
            text=f"정리 예정 용량: {cleaner_core.format_bytes(total_selected_bytes)} (총 {total_selected_files:,}개 파일)"
        )

    def select_all(self):
        for var in self.category_vars.values():
            var.set(True)

    def deselect_all(self):
        for var in self.category_vars.values():
            var.set(False)

    def select_recommended(self):
        for cat in cleaner_core.CLEANUP_CATEGORIES:
            cid = cat["id"]
            if cid in self.category_vars:
                self.category_vars[cid].set(cat.get("recommended", True))

    def start_cleanup(self):
        if self.is_busy:
            return

        selected_cats = [
            cat for cat in cleaner_core.CLEANUP_CATEGORIES
            if self.category_vars.get(cat["id"], None) and self.category_vars[cat["id"]].get()
        ]

        if not selected_cats:
            messagebox.showinfo("알림", "정리할 항목을 하나 이상 선택해 주세요.")
            return

        total_est = sum(self.category_sizes.get(c["id"], (0, 0))[0] for c in selected_cats)
        est_str = cleaner_core.format_bytes(total_est)

        confirm = messagebox.askyesno(
            "정리 확인",
            f"선택하신 {len(selected_cats)}개 항목의 정리를 시작하시겠습니까?\n\n"
            f"예상 정리 용량: {est_str}\n\n"
            "※ 중요 시스템 및 개인 문서는 절대 삭제되지 않으며,\n"
            "   현재 다른 프로그램이 사용 중인 파일은 안전하게 자동 보존됩니다."
        )
        if not confirm:
            return

        self.is_busy = True
        self.btn_clean.configure(state="disabled")
        self.status_lbl.configure(text="정리 진행 중...")
        self.clean_progress.set(0.0)
        self.append_log(f"선택된 {len(selected_cats)}개 항목 정리 시작...")

        def worker():
            total_freed = 0
            total_deleted = 0
            total_skipped = 0
            count = len(selected_cats)

            for idx, cat in enumerate(selected_cats):
                cid = cat["id"]
                self.after(0, self.status_lbl.configure, {"text": f"[{idx + 1}/{count}] {cat['name']} 정리 중..."})
                
                def log_cb(msg):
                    self.after(0, self.append_log, msg)

                try:
                    freed, deleted, skipped = cleaner_core.clean_category(cat, log_cb=log_cb)
                    total_freed += freed
                    total_deleted += deleted
                    total_skipped += skipped
                except Exception as ex:
                    self.after(0, self.append_log, f"  ※ 오류 발생: {ex}")

                progress = (idx + 1) / count
                self.after(0, self.clean_progress.set, progress)

            self.after(0, self._finish_cleanup, total_freed, total_deleted, total_skipped)

        threading.Thread(target=worker, daemon=True).start()

    def _finish_cleanup(self, total_freed, total_deleted, total_skipped):
        self.is_busy = False
        self.btn_clean.configure(state="normal")
        self.clean_progress.set(1.0)
        self.status_lbl.configure(text="정리 완료!")
        self.refresh_disk_status()

        freed_str = cleaner_core.format_bytes(total_freed)
        self.append_log("=" * 45)
        self.append_log(f"🎉 정리 완료! 총 {freed_str} 공간을 확보했습니다.")
        self.append_log(f"   (삭제된 파일: {total_deleted:,}개, 사용 중으로 안전 건너뜀: {total_skipped:,}개)")
        self.append_log("=" * 45)

        messagebox.showinfo(
            "정리 완료",
            f"선택하신 항목의 정리가 안전하게 완료되었습니다!\n\n"
            f"• 확보된 디스크 공간: {freed_str}\n"
            f"• 삭제된 임시 파일: {total_deleted:,}개\n"
            f"• 보존/건너뛴 파일: {total_skipped:,}개\n\n"
            "C: 드라이브 여유 공간이 갱신되었습니다."
        )

        # Trigger re-scan to update sizes
        self.start_scan_threads()

if __name__ == "__main__":
    app = CleanMasterApp()
    app.mainloop()


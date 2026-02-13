import sys
import os
import json
import re
import threading
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

from PyQt6.QtCore import QUrl, QObject, pyqtSignal, QPropertyAnimation, QEasingCurve, Qt, QTimer
from PyQt6.QtWidgets import QApplication, QMainWindow, QTabWidget, QGraphicsOpacityEffect, QMessageBox, QSplashScreen
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEngineProfile, QWebEnginePage
from PyQt6.QtGui import QIcon, QDesktopServices, QAction, QPixmap, QPainter, QColor, QFont

APP_VERSION = "1.0.0"
GITHUB_REPO = "sejanH/whatsapp-multi-account"
GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
WHATSAPP_WEB_URL = "https://web.whatsapp.com"
INACTIVE_UNLOAD_MS = 3 * 60 * 1000

class WhatsAppWebPage(QWebEnginePage):
    def __init__(self, profile, parent=None):
        super().__init__(profile, parent)
        # List of WhatsApp domains allowed in-app
        self.allowed_domains = [
            'web.whatsapp.com',
            'whatsapp.com',
            'faq.whatsapp.com',
            'status.whatsapp.com',
            'whatsapp.net'
        ]
    
    def acceptNavigationRequest(self, url, nav_type, is_main_frame):
        # Allow internal non-http(s) schemes used by WebEngine
        if self._is_internal_scheme(url):
            return True

        # Open external links in system browser (only on user link clicks)
        if not self._is_whatsapp_domain(url):
            if is_main_frame and nav_type == QWebEnginePage.NavigationType.NavigationTypeLinkClicked:
                QDesktopServices.openUrl(url)
                return False

        # Allow navigation for WhatsApp pages
        return super().acceptNavigationRequest(url, nav_type, is_main_frame)
    
    def _is_whatsapp_domain(self, url):
        """Check if URL belongs to WhatsApp domain."""
        domain = url.host()
        return any(
            domain == domain_item
            or domain.endswith(f".{domain_item}")
            for domain_item in self.allowed_domains
        )

    def _is_internal_scheme(self, url):
        scheme = url.scheme().lower()
        return scheme in {"about", "blob", "data"}

def _version_tuple(value):
    match = re.findall(r"\d+", value)
    return tuple(int(x) for x in match) if match else (0,)


class UpdateChecker(QObject):
    update_available = pyqtSignal(str)
    no_update = pyqtSignal()
    check_failed = pyqtSignal()

    def run(self):
        try:
            req = Request(GITHUB_API_URL, headers={"User-Agent": "WhatsAppClient"})
            with urlopen(req, timeout=3) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            if data.get("prerelease") or data.get("draft"):
                self.no_update.emit()
                return

            latest_tag = data.get("tag_name", "").strip()
            if not latest_tag:
                self.no_update.emit()
                return
            if _version_tuple(latest_tag) > _version_tuple(APP_VERSION):
                self.update_available.emit(latest_tag)
                return

            self.no_update.emit()
        except (URLError, HTTPError, ValueError, TimeoutError):
            self.check_failed.emit()

class WhatsAppAccount(QWebEngineView):
    def __init__(self, profile_name):
        super().__init__()
        # 1. Create a unique profile for each account
        storage_path = os.path.expanduser(f"~/.config/whatsapp-pyqt/{profile_name}")
        if not os.path.exists(storage_path):
            os.makedirs(storage_path)

        # Create the profile and set storage
        icon_path = os.path.join(os.path.dirname(__file__), 'whatsapp_icon.png')
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        
        self.profile = QWebEngineProfile(profile_name, self)
        self.profile.setPersistentStoragePath(storage_path)
        self.profile.setPersistentCookiesPolicy(QWebEngineProfile.PersistentCookiesPolicy.AllowPersistentCookies)
        self.profile.setHttpCacheType(QWebEngineProfile.HttpCacheType.DiskHttpCache)
        self.profile.setHttpCacheMaximumSize(64 * 1024 * 1024)
        
        # Set User-Agent to modern Chrome
        user_agent = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
        self.profile.setHttpUserAgent(user_agent)

        # 2. Assign the profile to the page
        page = WhatsAppWebPage(self.profile, self)
        self.setPage(page)
        
        self.setUrl(QUrl(WHATSAPP_WEB_URL))

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("WhatsApp Multi-Account")
        self.resize(1200, 900)

        # Create tabs
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)
        self.tabs.currentChanged.connect(self._on_tab_changed)

        # Add Account 1
        self.account1 = WhatsAppAccount("account_1")
        self.tabs.addTab(self.account1, "Personal")

        # Add Account 2
        self.account2 = WhatsAppAccount("account_2")
        self.tabs.addTab(self.account2, "Work / Business")

        self._fade_anim = None
        self._update_checker = None
        self._manual_update_check = False
        self._update_check_in_progress = False
        self._inactive_timers = {}
        self._suspended_tabs = set()
        self._setup_actions_menu()
        self._balance_tab_resources(self.tabs.currentIndex())
        self._schedule_inactive_unload(self.tabs.currentIndex())
        self._check_for_updates()

    def _setup_actions_menu(self):
        menu = self.menuBar().addMenu("Actions")

        clear_cache = QAction("Clear Cache (Current Tab)", self)
        clear_cache.triggered.connect(self._clear_current_cache)
        menu.addAction(clear_cache)

        open_downloads = QAction("Open Downloads Folder", self)
        open_downloads.triggered.connect(self._open_downloads)
        menu.addAction(open_downloads)

        check_updates = QAction("Check for Updates", self)
        check_updates.triggered.connect(lambda: self._check_for_updates(manual=True))
        menu.addAction(check_updates)

    def _current_account(self):
        widget = self.tabs.currentWidget()
        return widget if isinstance(widget, WhatsAppAccount) else None

    def _clear_current_cache(self):
        account = self._current_account()
        if not account:
            return
        profile = account.page().profile()
        profile.clearHttpCache()
        profile.cookieStore().deleteAllCookies()
        profile.clearAllVisitedLinks()
        QMessageBox.information(self, "Cache Cleared", "Cleared cache and cookies for current tab.")

    def _open_downloads(self):
        downloads_path = os.path.expanduser("~/Downloads")
        if not os.path.isdir(downloads_path):
            downloads_path = os.path.expanduser("~")
        QDesktopServices.openUrl(QUrl.fromLocalFile(downloads_path))

    def _animate_tab_fade(self, index):
        widget = self.tabs.widget(index)
        if widget is None:
            return
        effect = QGraphicsOpacityEffect(widget)
        widget.setGraphicsEffect(effect)
        animation = QPropertyAnimation(effect, b"opacity", self)
        animation.setDuration(180)
        animation.setStartValue(0.0)
        animation.setEndValue(1.0)
        animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._fade_anim = animation
        animation.start()

    def _on_tab_changed(self, index):
        self._resume_tab_if_suspended(index)
        self._schedule_inactive_unload(index)
        self._animate_tab_fade(index)
        self._balance_tab_resources(index)

    def _schedule_inactive_unload(self, active_index):
        for i in range(self.tabs.count()):
            widget = self.tabs.widget(i)
            if not isinstance(widget, WhatsAppAccount):
                continue

            timer = self._inactive_timers.get(i)
            if timer is None:
                timer = QTimer(self)
                timer.setSingleShot(True)
                timer.timeout.connect(lambda idx=i: self._suspend_tab(idx))
                self._inactive_timers[i] = timer

            if i == active_index:
                timer.stop()
            else:
                timer.start(INACTIVE_UNLOAD_MS)

    def _suspend_tab(self, index):
        if index == self.tabs.currentIndex():
            return

        widget = self.tabs.widget(index)
        if not isinstance(widget, WhatsAppAccount):
            return
        if index in self._suspended_tabs:
            return

        widget.stop()
        widget.setUrl(QUrl("about:blank"))
        self._suspended_tabs.add(index)

    def _resume_tab_if_suspended(self, index):
        if index not in self._suspended_tabs:
            return
        widget = self.tabs.widget(index)
        if not isinstance(widget, WhatsAppAccount):
            return
        self._suspended_tabs.discard(index)
        widget.setUrl(QUrl(WHATSAPP_WEB_URL))

    def _balance_tab_resources(self, active_index):
        lifecycle_enum = getattr(QWebEnginePage, "LifecycleState", None)
        if lifecycle_enum is None:
            return

        active_state = getattr(lifecycle_enum, "Active", None)
        frozen_state = getattr(lifecycle_enum, "Frozen", None)
        if active_state is None or frozen_state is None:
            return

        for i in range(self.tabs.count()):
            widget = self.tabs.widget(i)
            if not isinstance(widget, WhatsAppAccount):
                continue
            page = widget.page()
            target_state = active_state if i == active_index else frozen_state
            if page.lifecycleState() != target_state:
                page.setLifecycleState(target_state)

    def _check_for_updates(self, manual=False):
        if self._update_check_in_progress:
            if manual:
                QMessageBox.information(self, "Update Check", "An update check is already in progress.")
            return

        self._manual_update_check = manual
        self._update_check_in_progress = True
        self._update_checker = UpdateChecker()
        self._update_checker.update_available.connect(self._on_update_available)
        self._update_checker.no_update.connect(self._on_no_update_available)
        self._update_checker.check_failed.connect(self._on_update_check_failed)
        thread = threading.Thread(target=self._update_checker.run, daemon=True)
        thread.start()

    def _on_update_available(self, latest_tag):
        self._update_check_in_progress = False
        reply = QMessageBox.question(
            self,
            "Update Available",
            (
                f"A new version is available: {latest_tag}\n"
                f"Current version: {APP_VERSION}\n\n"
                "Open releases page?"
            ),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            QDesktopServices.openUrl(QUrl(f"https://github.com/{GITHUB_REPO}/releases"))

    def _on_no_update_available(self):
        self._update_check_in_progress = False
        if self._manual_update_check:
            QMessageBox.information(self, "No Updates", f"You are up to date ({APP_VERSION}).")

    def _on_update_check_failed(self):
        self._update_check_in_progress = False
        if self._manual_update_check:
            QMessageBox.warning(self, "Update Check Failed", "Could not check for updates right now.")


def _create_splash_screen():
    pixmap = QPixmap(520, 280)
    pixmap.fill(QColor("#11161c"))

    icon_path = os.path.join(os.path.dirname(__file__), "whatsapp_icon.png")
    icon_pixmap = QPixmap(icon_path)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.fillRect(20, 20, 480, 240, QColor("#202833"))

    if not icon_pixmap.isNull():
        scaled_icon = icon_pixmap.scaled(
            64,
            64,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        painter.drawPixmap(40, 55, scaled_icon)

    painter.setPen(QColor("#ffffff"))
    painter.setFont(QFont("Sans Serif", 18, QFont.Weight.Bold))
    painter.drawText(120, 95, "WhatsApp Multi-Account")

    painter.setPen(QColor("#c7d0db"))
    painter.setFont(QFont("Sans Serif", 11))
    painter.drawText(120, 130, f"Starting v{APP_VERSION}...")
    painter.end()

    splash = QSplashScreen(pixmap)
    splash.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
    return splash

if __name__ == "__main__":
    app = QApplication(sys.argv)
    splash = _create_splash_screen()
    splash.show()
    app.processEvents()

    window = MainWindow()
    window.show()

    splash_closed = {"done": False}

    def close_splash():
        if splash_closed["done"]:
            return
        splash_closed["done"] = True
        splash.finish(window)

    # Keep splash visible until first account finishes initial load.
    window.account1.loadFinished.connect(lambda _ok: close_splash())
    # Fallback timeout so splash is not stuck forever on bad network.
    QTimer.singleShot(12000, close_splash)

    sys.exit(app.exec())

import sys
import os
import json
import re
import threading
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

from PyQt6.QtCore import QUrl, QObject, pyqtSignal, QPropertyAnimation, QEasingCurve
from PyQt6.QtWidgets import QApplication, QMainWindow, QTabWidget, QGraphicsOpacityEffect
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEngineProfile, QWebEnginePage
from PyQt6.QtGui import QIcon, QDesktopServices, QAction

APP_VERSION = "0.0.2"
GITHUB_REPO = "sejanH/whatsapp-multi-account"
GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"

class WhatsAppWebPage(QWebEnginePage):
    open_in_new_tab = pyqtSignal(QUrl)

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
        self.force_new_tab_domains = {'flows.whatsapp.net'}
    
    def acceptNavigationRequest(self, url, nav_type, is_main_frame):
        # Allow internal non-http(s) schemes used by WebEngine
        if self._is_internal_scheme(url):
            return True

        # Force certain domains to open in a new top-level tab
        if self._is_force_new_tab_domain(url) and not is_main_frame:
            self.open_in_new_tab.emit(url)
            return False

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

    def _is_force_new_tab_domain(self, url):
        domain = url.host()
        return domain in self.force_new_tab_domains


def _version_tuple(value):
    match = re.findall(r"\d+", value)
    return tuple(int(x) for x in match) if match else (0,)


class UpdateChecker(QObject):
    update_available = pyqtSignal(str)

    def run(self):
        try:
            req = Request(GITHUB_API_URL, headers={"User-Agent": "WhatsAppClient"})
            with urlopen(req, timeout=3) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            if data.get("prerelease") or data.get("draft"):
                return

            latest_tag = data.get("tag_name", "").strip()
            if not latest_tag:
                return
            if _version_tuple(latest_tag) > _version_tuple(APP_VERSION):
                self.update_available.emit(latest_tag)
        except (URLError, HTTPError, ValueError, TimeoutError):
            return

class WhatsAppAccount(QWebEngineView):
    def __init__(self, profile_name, on_new_tab=None):
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
        
        # Set User-Agent to modern Chrome
        user_agent = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
        self.profile.setHttpUserAgent(user_agent)

        # 2. Assign the profile to the page
        page = WhatsAppWebPage(self.profile, self)
        if on_new_tab is not None:
            page.open_in_new_tab.connect(on_new_tab)
        self.setPage(page)
        
        self.setUrl(QUrl("https://web.whatsapp.com"))

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("WhatsApp Multi-Account")
        self.resize(1200, 900)

        self.statusBar().showMessage("Ready")

        # Create tabs
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)
        self.tabs.currentChanged.connect(self._animate_tab_fade)

        # Add Account 1
        self.account1 = WhatsAppAccount("account_1", self._open_url_in_new_tab)
        self.tabs.addTab(self.account1, "Personal")

        # Add Account 2
        self.account2 = WhatsAppAccount("account_2", self._open_url_in_new_tab)
        self.tabs.addTab(self.account2, "Work / Business")

        self._fade_anim = None
        self._update_checker = None
        self._setup_actions_menu()
        self._check_for_updates()

    def _setup_actions_menu(self):
        menu = self.menuBar().addMenu("Actions")

        open_settings = QAction("Open Settings", self)
        open_settings.triggered.connect(self._open_settings)
        menu.addAction(open_settings)

        clear_cache = QAction("Clear Cache (Current Tab)", self)
        clear_cache.triggered.connect(self._clear_current_cache)
        menu.addAction(clear_cache)

        open_downloads = QAction("Open Downloads Folder", self)
        open_downloads.triggered.connect(self._open_downloads)
        menu.addAction(open_downloads)

    def _current_account(self):
        widget = self.tabs.currentWidget()
        return widget if isinstance(widget, WhatsAppAccount) else None

    def _open_settings(self):
        account = self._current_account()
        if not account:
            return
        account.setUrl(QUrl("https://web.whatsapp.com/settings"))

    def _clear_current_cache(self):
        account = self._current_account()
        if not account:
            return
        profile = account.page().profile()
        profile.clearHttpCache()
        profile.cookieStore().deleteAllCookies()
        profile.clearAllVisitedLinks()
        self.statusBar().showMessage("Cleared cache and cookies for current tab", 5000)

    def _open_downloads(self):
        downloads_path = os.path.expanduser("~/Downloads")
        if not os.path.isdir(downloads_path):
            downloads_path = os.path.expanduser("~")
        QDesktopServices.openUrl(QUrl.fromLocalFile(downloads_path))

    def _open_url_in_new_tab(self, url):
        if not isinstance(url, QUrl):
            return
        account = self._current_account()
        new_tab = WhatsAppAccount("flows_tab", self._open_url_in_new_tab)
        self.tabs.addTab(new_tab, "Flows")
        self.tabs.setCurrentWidget(new_tab)
        new_tab.setUrl(url)

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

    def _check_for_updates(self):
        self._update_checker = UpdateChecker()
        self._update_checker.update_available.connect(self._on_update_available)
        thread = threading.Thread(target=self._update_checker.run, daemon=True)
        thread.start()

    def _on_update_available(self, latest_tag):
        self.statusBar().showMessage(
            f"Update available: {latest_tag} — https://github.com/{GITHUB_REPO}/releases",
            15000,
        )

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

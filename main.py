import sys
import os
from PyQt6.QtCore import QUrl
from PyQt6.QtWidgets import QApplication, QMainWindow, QTabWidget
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEngineProfile, QWebEnginePage
from PyQt6.QtGui import QIcon, QDesktopServices

class WhatsAppWebPage(QWebEnginePage):
    def __init__(self, profile, parent=None):
        super().__init__(profile, parent)
        # List of WhatsApp domains allowed in-app
        self.allowed_domains = [
            'web.whatsapp.com',
            'whatsapp.com',
            'faq.whatsapp.com',
            'status.whatsapp.com'
        ]
    
    def acceptNavigationRequest(self, url, nav_type, is_main_frame):
        # Check if URL is external (not in allowed domains)
        if not self._is_whatsapp_domain(url):
            # Open in system browser
            QDesktopServices.openUrl(url)
            return False
        
        # Allow navigation for WhatsApp pages
        return super().acceptNavigationRequest(url, nav_type, is_main_frame)
    
    def _is_whatsapp_domain(self, url):
        """Check if URL belongs to WhatsApp domain."""
        domain = url.host()
        return any(domain == domain_item or domain.startswith(f"www.{domain_item}")
                   for domain_item in self.allowed_domains)

class WhatsAppAccount(QWebEngineView):
    def __init__(self, profile_name):
        super().__init__()
        # 1. Create a unique profile for each account
        storage_path = os.path.expanduser(f"~/.config/whatsapp-pyqt6/{profile_name}")
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
        user_agent = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36"
        self.profile.setHttpUserAgent(user_agent)

        # 2. Assign the profile to the page
        self.setPage(WhatsAppWebPage(self.profile, self))
        
        self.setUrl(QUrl("https://web.whatsapp.com"))

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("WhatsApp Multi-Account")
        self.resize(1200, 900)

        # Create tabs
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        # Add Account 1
        self.account1 = WhatsAppAccount("account_1")
        self.tabs.addTab(self.account1, "Personal")

        # Add Account 2
        self.account2 = WhatsAppAccount("account_2")
        self.tabs.addTab(self.account2, "Work / Business")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

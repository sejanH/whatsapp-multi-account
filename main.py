import sys
import os
from PyQt5.QtCore import QUrl
from PyQt5.QtWidgets import QApplication, QMainWindow, QTabWidget
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEngineProfile, QWebEnginePage
from PyQt5.QtGui import QIcon

class WhatsAppAccount(QWebEngineView):
    def __init__(self, profile_name):
        super().__init__()
        # 1. Create a unique profile for each account
        storage_path = os.path.expanduser(f"~/.config/whatsapp-pyqt/{profile_name}")
        if not os.path.exists(storage_path):
            os.makedirs(storage_path)

        # Create the profile and set storage
        self.setWindowIcon(QIcon('whatsapp_icon.png'))
        self.profile = QWebEngineProfile(profile_name, self)
        self.profile.setPersistentStoragePath(storage_path)
        self.profile.setPersistentCookiesPolicy(QWebEngineProfile.AllowPersistentCookies)
        
        # Set User-Agent to avoid "Browser not supported"
        user_agent = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
        self.profile.setHttpUserAgent(user_agent)

        # 2. Assign the profile to the page
        web_page = QWebEnginePage(self.profile, self)
        self.setPage(web_page)
        
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
    sys.exit(app.exec_())
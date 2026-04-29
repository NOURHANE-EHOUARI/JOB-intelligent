import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

def diagnostic():
    options = Options()
    # ⚠️ PAS headless pour voir ce qui se passe visuellement
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--lang=fr-FR")
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)

    try:
        print("📂 Ouverture Glassdoor...")
        driver.get("https://www.glassdoor.fr/Emploi/emplois.htm")
        time.sleep(5)

        # Screenshot de la page d'accueil
        driver.save_screenshot("glassdoor_1_accueil.png")
        print("📸 Screenshot accueil sauvegardé")

        # HTML de la page
        with open("glassdoor_1_accueil.html", "w", encoding="utf-8") as f:
            f.write(driver.page_source)
        print("💾 HTML accueil sauvegardé")

        # Afficher tous les inputs présents
        inputs = driver.find_elements(By.TAG_NAME, "input")
        print(f"\n🔍 {len(inputs)} input(s) trouvé(s) sur la page :")
        for i, inp in enumerate(inputs):
            print(f"   [{i}] name='{inp.get_attribute('name')}' "
                  f"id='{inp.get_attribute('id')}' "
                  f"placeholder='{inp.get_attribute('placeholder')}' "
                  f"type='{inp.get_attribute('type')}'")

        # Afficher tous les boutons
        buttons = driver.find_elements(By.TAG_NAME, "button")
        print(f"\n🔍 {len(buttons)} bouton(s) trouvé(s) :")
        for i, btn in enumerate(buttons[:10]):
            print(f"   [{i}] type='{btn.get_attribute('type')}' "
                  f"class='{btn.get_attribute('class')[:60]}' "
                  f"text='{btn.text[:40]}'")

    finally:
        input("\n⏸️  Appuie sur ENTRÉE pour fermer le navigateur...")
        driver.quit()

if __name__ == "__main__":
    diagnostic()
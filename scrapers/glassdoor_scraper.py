import time
import random
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.common.keys import Keys
from webdriver_manager.chrome import ChromeDriverManager

METIERS = [
    "data scientist",
    "data engineer",
    "data analyst",
    "machine learning",
    "business intelligence"
]

LOCATION = "France"


def creer_driver():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--lang=fr-FR")

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    driver.execute_script(
        "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    )
    return driver


def pause(mn=2.0, mx=4.5):
    time.sleep(random.uniform(mn, mx))


def fermer_modale(driver):
    selecteurs = [
        "button[data-test='modal-cancel']",
        "[data-test='exit-survey-btn']",
        "[alt='Close']",
        ".modal_closeIcon",
        ".CloseButton",
    ]
    for sel in selecteurs:
        try:
            btn = WebDriverWait(driver, 3).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, sel))
            )
            driver.execute_script("arguments[0].click();", btn)
            time.sleep(1)
            return
        except TimeoutException:
            continue


def vider_et_taper(driver, element, texte_a_saisir):
    """Vide un champ et tape le texte — sans triple_click."""
    driver.execute_script("arguments[0].scrollIntoView(true);", element)
    driver.execute_script("arguments[0].click();", element)
    pause(0.3, 0.5)
    # Vider via JS directement sur la valeur du champ
    driver.execute_script("arguments[0].value = '';", element)
    element.send_keys(Keys.CONTROL + "a")
    element.send_keys(Keys.DELETE)
    pause(0.3, 0.5)
    element.send_keys(texte_a_saisir)
    pause(0.8, 1.2)


def texte(element, selecteur, defaut="Non précisé"):
    try:
        return element.find_element(By.CSS_SELECTOR, selecteur).text.strip()
    except NoSuchElementException:
        return defaut


def search_glassdoor(driver, query, location=LOCATION):
    print(f"   🌐 Navigation Glassdoor pour : {query}")
    try:
        driver.get("https://www.glassdoor.fr/Emploi/emplois.htm")
        pause(3, 5)
        fermer_modale(driver)

        wait = WebDriverWait(driver, 20)

        # ── Champ poste ──
        kw_input = wait.until(EC.element_to_be_clickable(
            (By.ID, "searchBar-jobTitle")
        ))
        vider_et_taper(driver, kw_input, query)

        # ── Champ location ──
        loc_input = wait.until(EC.element_to_be_clickable(
            (By.ID, "searchBar-location")
        ))
        vider_et_taper(driver, loc_input, location)

        # ── Vérification des valeurs saisies ──
        val_kw  = driver.execute_script("return document.getElementById('searchBar-jobTitle').value;")
        val_loc = driver.execute_script("return document.getElementById('searchBar-location').value;")
        print(f"   ✏️  Champs : poste='{val_kw}' | lieu='{val_loc}'")

        # ── Soumettre avec ENTRÉE ──
        loc_input.send_keys(Keys.RETURN)
        pause(5, 8)
        fermer_modale(driver)

        print(f"   🔗 URL : {driver.current_url}")

        # ── Attendre les résultats ──
        wait.until(EC.presence_of_all_elements_located(
            (By.CSS_SELECTOR, "li.react-job-listing, [data-test='jobListing']")
        ))

        cards = driver.find_elements(
            By.CSS_SELECTOR, "li.react-job-listing, [data-test='jobListing']"
        )
        return cards

    except TimeoutException:
        driver.save_screenshot(f"timeout_{query.replace(' ', '_')}.png")
        print(f"   ⚠️  Timeout — URL : {driver.current_url}")
        return []
    except Exception as e:
        print(f"   ❌ Erreur : {e}")
        return []


def normaliser_glassdoor(card, query):
    titre      = texte(card, "[data-test='job-title'], .JobCard_jobTitle__GLyJ1, a.jobTitle")
    entreprise = texte(card, "[data-test='employer-name'], .EmployerProfile_employerName__Ug9kB")
    ville      = texte(card, "[data-test='emp-location'], .JobCard_location__Ds1fM")
    salaire    = texte(card, "[data-test='detailSalary'], .JobCard_salaryEstimate__QpbTW", "Non précisé")

    url = ""
    try:
        link = card.find_element(
            By.CSS_SELECTOR, "a[data-test='job-title'], a.JobCard_trackingLink__GrRYn"
        )
        href = link.get_attribute("href") or ""
        url = href if href.startswith("http") else f"https://www.glassdoor.fr{href}"
    except NoSuchElementException:
        pass

    offre_id = url.split("?")[0].split("/")[-1] if url else f"{titre}|{entreprise}"

    return {
        "id":                    offre_id,
        "titre":                 titre.title() if titre != "Non précisé" else titre,
        "entreprise":            entreprise,
        "ville":                 ville,
        "code_postal":           "",
        "contrat":               "Non précisé",
        "salaire":               salaire,
        "experience":            "Non précisé",
        "competences":           "",
        "competences_extraites": query,
        "description":           "",
        "date_publication":      "",
        "url":                   url,
        "source":                "Glassdoor"
    }


def collecter_glassdoor():
    print("🚀 Collecte Glassdoor...\n")
    toutes = []
    driver = creer_driver()

    try:
        for metier in METIERS:
            print(f"🔍 Recherche : {metier}")
            cards = search_glassdoor(driver, metier)

            if cards:
                offres = [normaliser_glassdoor(c, metier) for c in cards]
                toutes.extend(offres)
                print(f"   → {len(offres)} offres trouvées")
            else:
                print(f"   → Aucune offre")

            pause(3, 6)

    except Exception as e:
        print(f"❌ Erreur globale : {e}")
    finally:
        driver.quit()
        print("\n🔒 Navigateur fermé")

    if not toutes:
        print("❌ Aucune offre collectée")
        return pd.DataFrame()

    print("\n⚙️  Normalisation des données...")
    df = pd.DataFrame(toutes)
    df = df.drop_duplicates(subset=["id"])
    df = df.fillna("Non précisé")

    print(f"✅ {len(df)} offres Glassdoor collectées")
    df.to_csv("offres_glassdoor.csv", index=False, encoding="utf-8-sig")
    print("💾 Sauvegardé : offres_glassdoor.csv")

    print("\n📋 Aperçu :")
    print(df[["titre", "entreprise", "ville", "contrat"]].head(5))

    return df


if __name__ == "__main__":
    collecter_glassdoor()
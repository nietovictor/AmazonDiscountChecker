import requests
import re
import smtplib
import json
import datetime
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from bs4 import BeautifulSoup

LOGS_DIR = os.path.join(os.getcwd(), "Logs")
os.makedirs(LOGS_DIR, exist_ok=True)

# Read URLs from products.txt
with open("products.txt", "r", encoding="utf-8") as f:
    URLS = [line.strip() for line in f if line.strip() and not line.startswith("//")]

# SMTP configuration
with open("credentials.json", "r", encoding="utf-8") as f:
    creds = json.load(f)

RECIPIENT = creds["mail_adress_destination"]
SMTP_USER = creds["mail_adress_sender"]
SMTP_PASS = creds["app_password"]

SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587

# Replace single-list URL reading with per-product threshold parsing
DEFAULT_THRESHOLD = 15

def load_products(path="products.txt", default_threshold=DEFAULT_THRESHOLD):
    """
    Lee products.txt y devuelve una lista de dicts: {"url": ..., "threshold": ...}
    Si la línea siguiente al URL contiene un número (ej. 20 o 20%), se usa como threshold.
    """
    products = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            # Filtra líneas vacías y comentarios (líneas que empiezan con //)
            raw_lines = [line.strip() for line in f.readlines() if line.strip() and not line.strip().startswith("//")]
    except FileNotFoundError:
        return products

    i = 0
    while i < len(raw_lines):
        line = raw_lines[i]
        # Considerar como URL si empieza por http o contiene 'amazon.'
        if line.lower().startswith("http") or "amazon." in line.lower():
            url = line
            threshold = default_threshold
            # Verificar la siguiente línea si existe y es un número (con o sin '%')
            if i + 1 < len(raw_lines):
                nxt = raw_lines[i + 1]
                m = re.match(r'^(\d{1,3})\s*%?$', nxt)
                if m:
                    threshold = int(m.group(1))
                    i += 1  # consumir la línea del threshold
            products.append({"url": url, "threshold": threshold})
        else:
            # Línea no reconocida como URL -> ignorar
            pass
        i += 1
    return products

# Cargar productos (cada producto es un dict con url y threshold)
PRODUCTS = load_products("products.txt", DEFAULT_THRESHOLD)

# Functions
def get_discount_and_title(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    }
    resp = requests.get(url, headers=headers)
    soup = BeautifulSoup(resp.text, "html.parser")
    # Discount
    percentage = None
    try:
        span = soup.find("span", class_="a-size-large a-color-price savingPriceOverride aok-align-center reinventPriceSavingsPercentageMargin savingsPercentage")
        if span:
            text = span.get_text(strip=True)
            percentage = int(text.replace("-", "").replace("%", "").replace("\xa0", ""))
    except Exception as e:
        print_log(f"Error extracting discount percentage: {e}", type="ERROR", file=log_file)
        percentage = None
    # Title
    title = ""
    try:
        title_span = soup.find("span", id="productTitle")
        if title_span:
            full_title = title_span.get_text(strip=True)
            title = extract_product_name(full_title)
    except Exception as e:
        print_log(f"Error extracting product title: {e}", type="ERROR", file=log_file)
        title = ""
    return percentage, title

def send_email_smtp(discount, url, title):
    subject = f"Product Tracker - {title} at {discount}% off"
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    html_body = f"""
    <html>
      <body>
        <h2>Wishlist Product Tracker Notification</h2>
        <p><strong>Product:</strong> {title}</p>
        <p><strong>Discount:</strong> {discount}%</p>
        <p><strong>URL:</strong> <a href="{url}">{url}</a></p>
        <p><strong>Date:</strong> {now}</p>
        <hr>
        <p>This is an automated notification from your Amazon price tracker.</p>
      </body>
    </html>
    """

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = SMTP_USER
    msg["To"] = RECIPIENT

    # Attach HTML body
    msg.attach(MIMEText(html_body, "html"))

    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        server.starttls()
        server.login(SMTP_USER, SMTP_PASS)
        server.sendmail(SMTP_USER, RECIPIENT, msg.as_string())

def was_email_sent_recently(text_to_check, days=2, log_file="log.txt"):
    now = datetime.datetime.now()
    try:
        with open(log_file, "r", encoding="utf-8") as f:
            for line in reversed(f.readlines()):
                if text_to_check in line:
                    # Extrae la fecha del log
                    date_str = line[:19]  # 'YYYY-MM-DD HH:MM:SS'
                    log_date = datetime.datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
                    if (now - log_date).days < days:
                        return True
                    else:
                        return False
    except Exception:
        pass
    return False

def extract_product_name(full_title):
    # Remove leading and trailing spaces
    full_title = full_title.strip()
    # Look for the first common separator
    for sep in ['|', '-', ',']:
        if sep in full_title:
            name = full_title.split(sep)[0].strip()
            return name
    # If no separator, look for the first closed parenthesis
    match = re.match(r'^(.+?\))', full_title)
    if match:
        return match.group(1).strip()
    # If no parenthesis, return the first 6 words as fallback
    return " ".join(full_title.split()[:6])

def print_log(message, type="INFO", file="log.txt"):
    now = datetime.datetime.now()
    # Create the file if it doesn't exist
    try:
        with open(file, "r", encoding="utf-8") as f:
            lines = f.readlines()
            last_line = lines[-1].strip()
            last_log_date = last_line[:10]

        if last_log_date != now.strftime("%Y-%m-%d"):
            with open(file, "a", encoding="utf-8") as f:
                f.write("\n" + now.strftime("%d/%m/%Y") + "\n")
    except FileNotFoundError:
        with open(file, "w", encoding="utf-8") as f:
            f.write(now.strftime("%d/%m/%Y") + "\n")
    except Exception:
        pass

    log_line = f"{now.strftime('%Y-%m-%d %H:%M:%S')} [{type}] {message}"
    print(log_line)

    with open(file, "a", encoding="utf-8") as f:
        f.write(log_line + "\n") 


if __name__ == "__main__":
    log_file = os.path.join(LOGS_DIR, "amazonLogs.txt")
    for item in PRODUCTS:
        url = item["url"]
        threshold = item.get("threshold", DEFAULT_THRESHOLD)
        discount, title = get_discount_and_title(url)
        product_name = extract_product_name(title)
        if discount is not None and title:
            print_log(f"The product {product_name} has a discount of {discount}% ", file=log_file)
            if discount >= threshold:
                print_text = f"Notification sent: {product_name} with a {discount}% discount."
                if not was_email_sent_recently(log_file=log_file, text_to_check=print_text):
                    send_email_smtp(discount, url, product_name)
                    print_log(print_text, file=log_file)
                else:
                    print_log(f"Email already sent for {product_name} in the last {2} days.", file=log_file)
        elif discount is None:
            print_log(f"No discount found for the product {product_name}.", file=log_file)

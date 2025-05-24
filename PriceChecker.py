import requests
import re
import smtplib
import json
import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from bs4 import BeautifulSoup

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
        print_log(f"Error extracting discount percentage: {e}", type="ERROR")
        percentage = None
    # Title
    title = ""
    try:
        title_span = soup.find("span", id="productTitle")
        if title_span:
            full_title = title_span.get_text(strip=True)
            title = extract_product_name(full_title)
    except Exception as e:
        print_log(f"Error extracting product title: {e}", type="ERROR")
        title = ""
    return percentage, title

def send_email_smtp(discount, url, title):
    subject = "Wishlist Product Tracker"
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
    for url in URLS:
        discount, title = get_discount_and_title(url)
        if discount is not None and title:
            product_name = extract_product_name(title)
            print_log(f"The product {product_name} has a discount of {discount}% ")
            if discount >= 10:
                send_email_smtp(discount, url, product_name)
                print_log(f"An email has been sent about the product {product_name}.")
        elif discount is None:
            print_log(f"No discount found for the product {title}.")

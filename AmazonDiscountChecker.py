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

# Default threshold configuration
DEFAULT_DISCOUNT_THRESHOLD = 15

def load_products(path="products.txt", default_discount_threshold=DEFAULT_DISCOUNT_THRESHOLD):
    """
    Lee products.txt y devuelve una lista de dicts:
    {"url": ..., "mode": "price"|"discount", "threshold": ...}

    Reglas para la línea siguiente al URL:
    - 15   -> modo precio (notifica si precio <= 15)
    - 15%  -> modo descuento (notifica si descuento >= 15)
    Si no se especifica, usa el modo descuento con el threshold por defecto.
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
            mode = "discount"
            threshold = float(default_discount_threshold)
            # Verificar la siguiente línea si existe y define umbral explícito
            if i + 1 < len(raw_lines):
                nxt = raw_lines[i + 1]
                m_discount = re.match(r'^(\d+(?:[\.,]\d{1,2})?)\s*%\s*$', nxt)
                m_price = re.match(r'^(\d+(?:[\.,]\d{1,2})?)\s*$', nxt)
                if m_discount:
                    mode = "discount"
                    threshold = float(m_discount.group(1).replace(",", "."))
                    i += 1  # consumir la línea del threshold
                elif m_price:
                    mode = "price"
                    threshold = float(m_price.group(1).replace(",", "."))
                    i += 1  # consumir la línea del threshold
            products.append({"url": url, "mode": mode, "threshold": threshold})
        else:
            # Línea no reconocida como URL -> ignorar
            pass
        i += 1
    return products

# Cargar productos (cada producto es un dict con url, mode y threshold)
PRODUCTS = load_products("products.txt", DEFAULT_DISCOUNT_THRESHOLD)

# Functions
def _parse_price_from_whole_span(whole_span):
    """Convierte un span .a-price-whole (+ fracción adyacente) a float."""
    whole_text = whole_span.get_text(strip=True)
    whole_digits = re.sub(r"[^\d]", "", whole_text)
    if not whole_digits:
        return None

    fraction_span = whole_span.find_next_sibling("span", class_="a-price-fraction")
    if fraction_span:
        fraction_digits = re.sub(r"[^\d]", "", fraction_span.get_text(strip=True))
        if fraction_digits:
            return float(f"{whole_digits}.{fraction_digits}")

    return float(whole_digits)


def _extract_main_product_price(soup):
    """
    Extrae el precio SOLO del bloque principal del producto en la PDP.
    Si no está disponible en ese bloque, devuelve None.
    """
    # Priorizamos el acordeón de producto NUEVO para no tomar el de usados/recomendados.
    candidate_selectors = [
        "#ppd #apex_desktop_newAccordionRow #corePriceDisplay_desktop_feature_div span.a-price.priceToPay span.a-price-whole",
        "#ppd #apex_desktop_newAccordionRow #corePrice_feature_div span.a-price.priceToPay span.a-price-whole",
        "#ppd #corePriceDisplay_desktop_feature_div span.a-price.priceToPay span.a-price-whole",
        "#ppd #corePrice_feature_div span.a-price.priceToPay span.a-price-whole",
    ]

    for selector in candidate_selectors:
        whole_span = soup.select_one(selector)
        if whole_span:
            parsed = _parse_price_from_whole_span(whole_span)
            if parsed is not None:
                return parsed

    return None


def get_product_data(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    }
    resp = requests.get(url, headers=headers)
    soup = BeautifulSoup(resp.text, "html.parser")
    # Price (whole number)
    current_price = None
    try:
        current_price = _extract_main_product_price(soup)
    except Exception as e:
        print_log(f"Error extracting current price: {e}", type="ERROR", file=log_file)
        current_price = None

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
    return current_price, percentage, title

def send_email_smtp(url, title, mode, current_price=None, discount=None, threshold=None):
    if mode == "price":
                subject = f"Product Tracker - {title} at {current_price:.2f}€"
                status_label = "Price alert"
                status_color = "#0f766e"
                trigger_line = f"""
                <div style=\"display:flex;justify-content:space-between;align-items:center;padding:10px 12px;border:1px solid #e5e7eb;border-radius:8px;margin-bottom:10px;\"><span style=\"font-size:13px;color:#6b7280;\">Current price</span><span style=\"font-size:16px;font-weight:700;color:#111827;\">{current_price:.2f}€</span></div>
                <div style=\"display:flex;justify-content:space-between;align-items:center;padding:10px 12px;border:1px solid #e5e7eb;border-radius:8px;margin-bottom:10px;\"><span style=\"font-size:13px;color:#6b7280;\">Alert price</span><span style=\"font-size:16px;font-weight:700;color:#111827;\">{threshold:.2f}€</span></div>
                """
    else:
        subject = f"Product Tracker - {title} at {discount:.0f}% off"
        status_label = "Discount alert"
        status_color = "#6d28d9"
        trigger_line = f"""
        <div style=\"display:flex;justify-content:space-between;align-items:center;padding:10px 12px;border:1px solid #e5e7eb;border-radius:8px;margin-bottom:10px;\"><span style=\"font-size:13px;color:#6b7280;\">Discount</span><span style=\"font-size:16px;font-weight:700;color:#111827;\">{discount:.0f}%</span></div>
        <div style=\"display:flex;justify-content:space-between;align-items:center;padding:10px 12px;border:1px solid #e5e7eb;border-radius:8px;margin-bottom:10px;\"><span style=\"font-size:13px;color:#6b7280;\">Alert discount</span><span style=\"font-size:16px;font-weight:700;color:#111827;\">{threshold:.0f}%</span></div>
        """

    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    html_body = f"""
    <html>
      <body>
                <div style="background:#f3f4f6;padding:24px;font-family:Segoe UI,Arial,sans-serif;color:#111827;">
                    <div style="max-width:640px;margin:0 auto;background:#ffffff;border-radius:12px;border:1px solid #e5e7eb;overflow:hidden;">
                        <div style="padding:20px 24px;background:linear-gradient(135deg,#111827 0%,#1f2937 100%);color:#ffffff;">
                            <p style="margin:0 0 8px 0;font-size:12px;letter-spacing:0.08em;text-transform:uppercase;opacity:0.85;">Amazon Tracker</p>
                            <h2 style="margin:0;font-size:22px;font-weight:700;line-height:1.3;">{title}</h2>
                            <span style="display:inline-block;margin-top:12px;padding:6px 10px;border-radius:999px;background:{status_color};font-size:12px;font-weight:600;">{status_label}</span>
                        </div>

                        <div style="padding:22px 24px;">
                            <div style="display:block;">
                                {trigger_line}
                            </div>

                            <div style="margin-top:18px;">
                                <a href="{url}" style="display:inline-block;background:#111827;color:#ffffff;text-decoration:none;padding:10px 14px;border-radius:8px;font-size:14px;font-weight:600;">Open product</a>
                            </div>

                            <p style="margin:18px 0 0 0;font-size:12px;color:#6b7280;word-break:break-all;">{url}</p>
                            <p style="margin:8px 0 0 0;font-size:12px;color:#6b7280;">Detected at: {now}</p>
                        </div>

                        <div style="padding:14px 24px;border-top:1px solid #e5e7eb;background:#fafafa;color:#6b7280;font-size:12px;">
                            This is an automated notification from your Amazon price tracker.
                        </div>
                    </div>
                </div>
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
        mode = item.get("mode", "discount")
        threshold = item.get("threshold", float(DEFAULT_DISCOUNT_THRESHOLD))
        current_price, discount, title = get_product_data(url)
        product_name = extract_product_name(title)

        if mode == "price":
            if current_price is not None and title:
                print_log(f"The product {product_name} currently costs {current_price:.2f}€.", file=log_file)
                if current_price <= threshold:
                    print_text = f"Notification sent: {product_name} at {current_price:.2f}€ (threshold {threshold:.2f}€)."
                    if not was_email_sent_recently(log_file=log_file, text_to_check=print_text):
                        send_email_smtp(url=url, title=product_name, mode="price", current_price=current_price, threshold=threshold)
                        print_log(print_text, file=log_file)
                    else:
                        print_log(f"Email already sent for {product_name} in the last {2} days.", file=log_file)
            elif current_price is None:
                print_log(f"No current price found for the product {product_name}.", file=log_file)

        else:
            if discount is not None and title:
                print_log(f"The product {product_name} has a discount of {discount}%.", file=log_file)
                if discount >= threshold:
                    print_text = f"Notification sent: {product_name} with a {discount:.0f}% discount (threshold {threshold:.0f}%)."
                    if not was_email_sent_recently(log_file=log_file, text_to_check=print_text):
                        send_email_smtp(url=url, title=product_name, mode="discount", discount=discount, threshold=threshold)
                        print_log(print_text, file=log_file)
                    else:
                        print_log(f"Email already sent for {product_name} in the last {2} days.", file=log_file)
            elif discount is None:
                print_log(f"No discount found for the product {product_name}.", file=log_file)

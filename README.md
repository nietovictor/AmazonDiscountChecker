# Amazon Price Tracker and Email Notifier

This Python script monitors a list of Amazon product URLs and can alert you in two ways:
- By price: notify when the current price is less than or equal to a configured value.
- By discount: notify when the discount is greater than or equal to a configured percentage.

The current price is extracted from `class="a-price-whole"`. All activity is logged to a file.

You can schedule a task so this script is run periodically, this way you will get a notification everytime one of your wished products is at a discount.

## How It Works

1. **Product URLs:**  
   The script reads product URLs from a file called `products.txt`. Each line should contain a single Amazon product URL. Lines starting with `//` are ignored as comments.

2. **Credentials:**  
   Email credentials and recipient information are stored in a file called `credentials.json`. This file must be present in the same directory as the script.

3. **Threshold Check (price or discount):**  
   For each product, the script reads the rule defined in `products.txt`:
   - `15` -> notify when price is `<= 15`
   - `15%` -> notify when discount is `>= 15%`

   If no custom value is provided for a product, the default discount threshold is used.

4. **Email Notification:**  
   The email is sent using Gmail's SMTP server and contains product details, trigger type (price or discount), threshold, and a clickable link.

5. **Logging:**  
   All actions and errors are logged to `log.txt`.

---

## Setup

### 1. `credentials.json` Format

Create a file named `credentials.json` in the same directory as the script with the following structure:

```json
{
    "mail_adress_destination": "recipient@example.com",
    "mail_adress_sender": "yourgmail@gmail.com",
    "app_password": "your_gmail_app_password"
}
```

- `mail_adress_destination`: The email address where notifications will be sent.
- `mail_adress_sender`: Your Gmail address (must match the account for the app password).
- `app_password`: A Gmail App Password (not your regular Gmail password).  
  [How to generate an App Password](https://support.google.com/accounts/answer/185833?hl=en).

### 2. `products.txt` Format

Create a file named `products.txt` in the same directory as the script. Add one Amazon product URL per line. Example:

```
https://www.amazon.com/dp/B08N5WRWNW
15
https://www.amazon.com/dp/B07FZ8S74R
20%
// This is a comment and will be ignored
https://www.amazon.com/dp/B09G3HRMVB
```

- Blank lines and lines starting with `//` are ignored.
- A numeric line after a URL (e.g. `15`) means **max price**.
- A numeric percentage after a URL (e.g. `15%`) means **min discount**.

---

## Usage

1. Install dependencies:
   ```
   pip install requests beautifulsoup4
   ```

2. Run the script:
   ```
   python AmazonDiscountChecker.py
   ```

3. Check your email for notifications when a product reaches the configured threshold.

4. **Automate Daily Checks:**  
   You can schedule this script to run automatically every day using your operating system's task scheduler:
   - **Windows:** Use Task Scheduler ([How to schedule a Python script on Windows](https://datatofish.com/python-script-windows-scheduler/))
   - **Linux/macOS:** Use `cron` jobs ([How to schedule a cron job](https://opensource.com/article/19/7/getting-started-cron))

   This is what I do so I don't have to run it manually.

---

## Notes

- The script is configured for Gmail SMTP. If you use another provider, update the SMTP settings in the script.
- Make sure your Gmail account has [App Passwords enabled](https://support.google.com/accounts/answer/185833?hl=en).
- The default threshold can be changed by modifying `DEFAULT_DISCOUNT_THRESHOLD` in the script.

---

## Uso

1. Añade los enlaces de productos de Amazon en el archivo `products.txt`, uno por línea
2. Opcionalmente, puedes especificar un umbral personalizado para cada producto en la línea siguiente al enlace:
   ```
   https://www.amazon.es/dp/PRODUCTO1
   15
   https://www.amazon.es/dp/PRODUCTO2 
   30%
   https://www.amazon.es/dp/PRODUCTO3 
   50
   ```
   En el ejemplo anterior:
   - `15` significa: notificar cuando el precio sea `<= 15`.
   - `30%` significa: notificar cuando el descuento sea `>= 30%`.
   - `50` significa: notificar cuando el precio sea `<= 50`.

   Si no se especifica valor para un producto, se usa el umbral global de descuento.

3. Ejecuta el script:
   ```bash
   python AmazonDiscountChecker.py
   ```

4. Revisa tu correo electrónico para ver las notificaciones cuando se cumpla el umbral configurado.

5. **Automatiza las comprobaciones diarias:**  
   Puedes programar este script para que se ejecute automáticamente todos los días utilizando el programador de tareas de tu sistema operativo:
   - **Windows:** Usa el Programador de tareas ([Cómo programar un script de Python en Windows](https://datatofish.com/python-script-windows-scheduler/))
   - **Linux/macOS:** Usa trabajos de `cron` ([Cómo programar un trabajo de cron](https://opensource.com/article/19/7/getting-started-cron))

   Esto es lo que hago para no tener que ejecutarlo manualmente.

---

## Notas

- El script está configurado para Gmail SMTP. Si utilizas otro proveedor, actualiza la configuración de SMTP en el script.
- Asegúrate de que tu cuenta de Gmail tenga [habilitados los contraseñas de aplicación](https://support.google.com/accounts/answer/185833?hl=en).
- El precio se extrae desde `class="a-price-whole"`.
- El umbral global de descuento se puede cambiar modificando `DEFAULT_DISCOUNT_THRESHOLD` en el script.

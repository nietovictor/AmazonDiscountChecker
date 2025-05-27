# Amazon Price Tracker and Email Notifier

This Python script monitors a list of Amazon product URLs, checks for discounts, and sends an automated HTML email notification when a discount meets or exceeds a specified threshold (default: 10%). All activity is logged to a file.

You can schedule a task so this script is run periodically, this way you will get a notification everytime one of your wished products is at a discount.

## How It Works

1. **Product URLs:**  
   The script reads product URLs from a file called `products.txt`. Each line should contain a single Amazon product URL. Lines starting with `//` are ignored as comments.

2. **Credentials:**  
   Email credentials and recipient information are stored in a file called `credentials.json`. This file must be present in the same directory as the script.

3. **Discount Check:**  
   For each product, the script checks if there is a discount. If the discount is 10% or more, an email notification is sent.

4. **Email Notification:**  
   The email is sent using Gmail's SMTP server and contains product details, the discount, and a clickable link.

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
https://www.amazon.com/dp/B07FZ8S74R
// This is a comment and will be ignored
https://www.amazon.com/dp/B09G3HRMVB
```

- Blank lines and lines starting with `//` are ignored.

---

## Usage

1. Install dependencies:
   ```
   pip install requests beautifulsoup4
   ```

2. Run the script:
   ```
   python PriceChecker.py
   ```

3. Check your email for notifications when discounts are found.

4. **Automate Daily Checks:**  
   You can schedule this script to run automatically every day using your operating system's task scheduler:
   - **Windows:** Use Task Scheduler ([How to schedule a Python script on Windows](https://datatofish.com/python-script-windows-scheduler/))
   - **Linux/macOS:** Use `cron` jobs ([How to schedule a cron job](https://opensource.com/article/19/7/getting-started-cron))

   This is what I do so I don't have to run it manually.

---

## Notes

- The script is configured for Gmail SMTP. If you use another provider, update the SMTP settings in the script.
- Make sure your Gmail account has [App Passwords enabled](https://support.google.com/accounts/answer/185833?hl=en).
- The discount threshold can be changed by modifying the value in the script (`if discount >= 10:`).

---

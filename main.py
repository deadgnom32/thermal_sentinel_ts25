import json
import logging
import os
import sys
import requests
import asyncio
import time
import inspect
from datetime import datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# --- Configuration Parameters ---
# Replace these with your designated API keys
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
WEATHER_API_KEY = os.getenv("WEATHER_API_KEY")

# Safety Interlock Sequence
if not TELEGRAM_TOKEN or not WEATHER_API_KEY:
    logging.critical(
        "CRITICAL ERROR: Security tokens missing from environment. "
        "Ensure TELEGRAM_BOT_TOKEN and OPENWEATHERMAP_API_KEY are exported to the system environment."
    )
    sys.exit("Initialization aborted due to missing environmental variables.")

# In-memory storage for mercenary data
mercenary_data = {}
DATA_FILE = "mercenary_data.json"

# Secure Data Retrieval
if os.path.exists(DATA_FILE):
    try:
        with open(DATA_FILE, "r") as f:
            # json.load safely parses the data structure
            mercenary_data = json.load(f)
    except json.JSONDecodeError:
        logging.error("Data file corruption detected. Initializing fresh registry.")
    except Exception as e:
        logging.error(f"Unexpected error accessing memory core: {e}")


async def safe_request(do_request, max_attempts=10):
    """
    Executes a callable with a linear backoff retry protocol.
    Dynamically handles both synchronous HTTP requests and asynchronous Telegram commands.
    """
    attempt = 1
    while True:
        try:
            # Execute the callable
            result = do_request()
            
            # If the result is a coroutine (like sending a Telegram message), await it here
            if inspect.isawaitable(result):
                return await result
            
            # If it is synchronous (like requests.get), return it directly
            return result
            
        except Exception as e:
            if attempt >= max_attempts:
                logging.error(f"Total failure after {max_attempts} attempts: {e}")
                return None # Fail gracefully
                
            logging.warning(f"Sub-routine anomaly: {str(e)}. Re-engaging in {attempt} seconds...")
            await asyncio.sleep(attempt)
            attempt += 1


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Initializes the integration protocol."""
    await safe_request(lambda: update.message.reply_text(
        "Welcome, mercenary. I am ALLMIND. \n"
        "To activate the environmental hazard warning system, please transmit your current GPS location via Telegram's attachment menu."
    ))


async def set_temp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Allows the mercenary to calibrate their personal thermal threshold."""
    chat_id = str(update.message.chat_id)
    
    if chat_id not in mercenary_data:
        await safe_request(lambda: update.message.reply_text("Error: No coordinates registered. Transmit your location first."))
        return

    try:
        # Extract the number provided by the user (e.g., /set_temp 30.5)
        new_threshold = float(context.args[0])
        
        mercenary_data[chat_id]['threshold'] = new_threshold
            
        await safe_request(lambda: update.message.reply_text(f"Threshold calibrated to **{new_threshold}°C**. Environmental parameters updated.", parse_mode='Markdown'))
        
    except (IndexError, ValueError):
        await safe_request(lambda: update.message.reply_text("Invalid syntax. Usage: `/set_temp 30` or `/set_temp 28.5`", parse_mode='Markdown'))
        return

    lat = mercenary_data[chat_id]["lat"]
    lon = mercenary_data[chat_id]["lon"]
    url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={WEATHER_API_KEY}&units=metric"

    response = await safe_request(lambda: requests.get(url, timeout=10))
    if response is not None:
        if response.status_code == 200:
            weather_data = response.json()
            current_temp = weather_data['main']['temp']

            if current_temp >= mercenary_data[chat_id]['threshold']:
                message = (
                    f"⚠️ **IMMEDIATE HAZARD DETECTED** ⚠️\n\n"
                    f"The current temperature at your drop zone is already\n\n`{current_temp}°C.`\n\n"
                    "Cooling parameters must be adjusted immediately prior to combat engagement."
                )
                await safe_request(lambda: update.message.reply_text(message, parse_mode='Markdown'))

                # Log the alert to prevent the hourly queue from sending a duplicate today
                mercenary_data[chat_id]["lower"] = False
                with open(DATA_FILE, "w") as f:
                    json.dump(mercenary_data, f, indent=4)
            else:
                mercenary_data[chat_id]["lower"] = True
                with open(DATA_FILE, "w") as f:
                    json.dump(mercenary_data, f, indent=4)
                await safe_request(lambda: update.message.reply_text(f"Scan complete. Current temperature is\n\n`{current_temp}°C`\n\nEnvironment is within acceptable operational parameters.", parse_mode='Markdown'))
        else:
            logging.warning(f"Weather API returned anomalous status during initial scan: {response.status_code}")
            
    else:
        await safe_request(lambda: update.message.reply_text("Error: Preliminary scan failed. Relying on hourly automated sweeps."))


async def receive_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Processes transmitted coordinates and initiates an immediate threat assessment."""
    user_location = update.message.location
    chat_id = str(update.message.chat_id)

    lat = user_location.latitude
    lon = user_location.longitude

    current_threshold = mercenary_data.get(chat_id, {}).get('threshold', 25.0)

    mercenary_data[chat_id] = {
        'lat': lat,
        'lon': lon,
        'lower': True,
        'threshold': current_threshold
    }

    # Secure Data Storage
    with open(DATA_FILE, "w") as f:
        json.dump(mercenary_data, f, indent=4)

    await safe_request(lambda: update.message.reply_text(
        "Coordinates registered successfully. Initiating preliminary environmental scan..."
    ))

    # --- Immediate Threat Assessment Protocol ---
    url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={WEATHER_API_KEY}&units=metric"

    response = await safe_request(lambda: requests.get(url, timeout=10))
    if response is not None:
        if response.status_code == 200:
            weather_data = response.json()
            current_temp = weather_data['main']['temp']

            if current_temp >= mercenary_data[chat_id]['threshold']:
                message = (
                    f"⚠️ **IMMEDIATE HAZARD DETECTED** ⚠️\n\n"
                    f"The current temperature at your drop zone is already\n\n`{current_temp}°C.`\n\n"
                    "Cooling parameters must be adjusted immediately prior to combat engagement."
                )
                await safe_request(lambda: update.message.reply_text(message, parse_mode='Markdown'))

                # Log the alert to prevent the hourly queue from sending a duplicate today
                mercenary_data[chat_id]["lower"] = False
                with open(DATA_FILE, "w") as f:
                    json.dump(mercenary_data, f, indent=4)
            else:
                mercenary_data[chat_id]["lower"] = True
                with open(DATA_FILE, "w") as f:
                    json.dump(mercenary_data, f, indent=4)
                await safe_request(lambda: update.message.reply_text(f"Scan complete. Current temperature is\n\n`{current_temp}°C`\n\nEnvironment is within acceptable operational parameters.", parse_mode='Markdown'))
        else:
            logging.warning(f"Weather API returned anomalous status during initial scan: {response.status_code}")
            
    else:
        await safe_request(lambda: update.message.reply_text("Error: Preliminary scan failed. Relying on hourly automated sweeps."))

    # Conclude registration
    await safe_request(lambda: update.message.reply_text("You will now receive a daily alert if local temperatures reach critical thresholds.\nALLMIND exists for all mercenaries."))


async def monitor_temperature(context: ContextTypes.DEFAULT_TYPE):
    """Scheduled routine to evaluate environmental threats."""
    for chat_id, data in mercenary_data.items():
        lat = data['lat']
        lon = data['lon']

        url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={WEATHER_API_KEY}&units=metric"
        
        # Pass the request as an anonymous lambda function
        response = await safe_request(lambda: requests.get(url, timeout=10))

        # Proceed only if the wrapper successfully returned a response object
        if response is not None:
            if response.status_code == 200:
                weather_data = response.json()
                current_temp = weather_data['main']['temp']

                if current_temp >= mercenary_data[chat_id]['threshold'] and mercenary_data[chat_id]["lower"]:
                    message = (
                        f"⚠️ **Environmental Hazard Warning** ⚠️\n\n"
                        f"The current temperature at your coordinates is\n\n`{current_temp}°C`\n\n"
                        "Please adjust your cooling parameters accordingly to maintain optimal combat efficiency."
                    )
                    await safe_request(lambda: context.bot.send_message(chat_id=chat_id, text=message, parse_mode='Markdown'))

                    mercenary_data[chat_id]['lower'] = False
                    
                    with open(DATA_FILE, "w") as f:
                        json.dump(mercenary_data, f, indent=4)
                elif current_temp < mercenary_data[chat_id]['threshold'] and not mercenary_data[chat_id]["lower"]:
                    mercenary_data[chat_id]["lower"] = True
                    with open(DATA_FILE, "w") as f:
                        json.dump(mercenary_data, f, indent=4)
                    await safe_request(lambda: context.bot.send_message(chat_id=chat_id, text=f"Scan complete. Current temperature is\n\n`{current_temp}°C`\n\nEnvironment is within acceptable operational parameters.", parse_mode='Markdown'))
            else:
                logging.warning(f"API returned anomalous status: {response.status_code}")


def main():
    """Commences the application lifecycle."""
    # Build the application
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # Integrate communication handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("set_temp", set_temp))
    application.add_handler(MessageHandler(filters.LOCATION, receive_location))

    # Schedule the climate monitoring protocol to execute every hour (3600 seconds)
    job_queue = application.job_queue
    job_queue.run_repeating(monitor_temperature, interval=3600, first=10)

    # --- ASCII Boot Sequence ---
    startup_art = r"""
    //////////////////////////////////////////////////
    //                                              //
    //                    (  )  (                   //
    //                     ) (   )                  //
    //                   (  )  (                    //
    //                 .----------.                 //
    //                /============\                //
    //               //            \\               //
    //              ||    >|()|<    ||              //
    //              ||   =[(O)]]=   ||              //
    //              ||    >|()|<    ||              //
    //               \\            //               //
    //                \============/                //
    //                 \          /                 //
    //                  \        /                  //
    //                   \      /                   //
    //                    \    /                    //
    //                     \  /                     //
    //                      \/                      //
    //                                              //
    //     [ THERMAL SENTINEL // TS-25 ONLINE ]     //
    //       ENVIRONMENTAL PROTOCOL ENGAGED         //
    //                                              //
    //////////////////////////////////////////////////
    """
    print(startup_art)
    logging.info("ALLMIND environmental monitor is now polling for incoming transmissions.")

    while True:
        try:
            application.run_polling()
            logging.info("System shutdown signal acknowledged. Terminating ALLMIND protocols.")
            break
            
        except Exception as e:
            logging.warning(f"Polling disrupted: {str(e)}. Rebooting terminal in 5 seconds...")
            time.sleep(5)


if __name__ == '__main__':
    main()
